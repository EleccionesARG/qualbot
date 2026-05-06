import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
CACHE_DIR = "session_cache"

# Caché en memoria (capa L1 — más rápida, no sobrevive redeploys)
_session_memory = {}

# ── Redis (capa L2 — persiste entre redeploys) ─────────────────────────────────
def _get_redis():
    """Devuelve cliente Redis si REDIS_URL está configurado, sino None."""
    try:
        import redis
        url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_PRIVATE_URL")
        if url:
            return redis.from_url(url, decode_responses=True, socket_timeout=3)
    except Exception as e:
        print(f"⚠️  Redis no disponible: {e}")
    return None

REDIS_KEY_PREFIX = "qualbot:session:"
REDIS_TTL = 60 * 60 * 48  # 48 horas


def _normalize_title(title):
    """Normaliza el título para que Read.ai y Zoom produzcan la misma clave."""
    title = title.strip().lower()
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)


def _notify_error(context, error, tb=""):
    """Envía alerta a Slack si SLACK_WEBHOOK_URL está configurado."""
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    try:
        import requests as req
        text = f"❌ *QualBot error* en `{context}`\n```{error}```"
        if tb:
            text += f"\n```{tb[-1500:]}```"
        req.post(url, json={"text": text}, timeout=5)
    except Exception as e:
        print(f"⚠️  No se pudo notificar a Slack: {e}")


def save_session(meeting_title, data):
    safe_name = _normalize_title(meeting_title)

    # L1 — memoria
    _session_memory[safe_name] = data

    # L2 — Redis (persistente entre redeploys)
    r = _get_redis()
    if r:
        try:
            r.set(f"{REDIS_KEY_PREFIX}{safe_name}", json.dumps(data, ensure_ascii=False), ex=REDIS_TTL)
            print(f"💾 Sesión guardada en Redis: {safe_name}")
            return
        except Exception as e:
            print(f"⚠️  Redis write error: {e}")

    # L3 — disco (fallback si no hay Redis)
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(f"{CACHE_DIR}/{safe_name}.json", "w") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"💾 Sesión guardada en disco: {safe_name}")
    except Exception as e:
        print(f"⚠️  No se pudo guardar en disco: {e}")

def load_session(meeting_title):
    safe_name = _normalize_title(meeting_title)

    # L1 — memoria
    if safe_name in _session_memory:
        print(f"📂 Sesión desde memoria: {safe_name}")
        return _session_memory[safe_name]

    # L2 — Redis
    r = _get_redis()
    if r:
        try:
            val = r.get(f"{REDIS_KEY_PREFIX}{safe_name}")
            if val:
                data = json.loads(val)
                _session_memory[safe_name] = data  # repoblar L1
                print(f"📂 Sesión desde Redis: {safe_name}")
                return data
        except Exception as e:
            print(f"⚠️  Redis read error: {e}")

    # L3 — disco
    path = f"{CACHE_DIR}/{safe_name}.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        _session_memory[safe_name] = data
        print(f"📂 Sesión desde disco: {safe_name}")
        return data

    print(f"⚠️  Sesión no encontrada: {safe_name}")
    return {}

@app.route("/sessions", methods=["GET"])
def list_sessions():
    """Lista todas las sesiones guardadas en Redis (útil para debug)."""
    r = _get_redis()
    if not r:
        return jsonify({"error": "Redis no configurado", "memoria": list(_session_memory.keys())}), 200
    try:
        keys = r.keys(f"{REDIS_KEY_PREFIX}*")
        sessions = [k.replace(REDIS_KEY_PREFIX, "") for k in keys]
        return jsonify({"redis": sessions, "memoria": list(_session_memory.keys())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

# ── Read.ai webhook — guarda transcripción y genera reporte de texto ───────────
@app.route("/webhook/readai", methods=["POST"])
def readai_webhook():
    from analyzer import analyze_transcript
    from drive_uploader import upload_report
    from report_generator import generate_pdf_report

    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    print(f"📥 Read.ai: {datetime.now().strftime('%H:%M:%S')}")
    try:
        meeting_title = data.get("title", "Focus Group")
        meeting_date  = data.get("date", str(datetime.now().date()))
        report_url    = data.get("report_url", "")
        summary       = data.get("summary", "")
        topics        = [t.get("text","") for t in data.get("topics", [])]
        transcript    = data.get("transcript", {})
        speakers      = [s.get("name","") for s in transcript.get("speakers", [])]
        blocks        = transcript.get("speaker_blocks", [])

        print(f"📋 {meeting_title} | {len(speakers)} speakers | {len(blocks)} bloques")

        # Guardar en caché para que el análisis de video lo cruce después
        save_session(meeting_title, {
            "meeting_title": meeting_title,
            "meeting_date":  meeting_date,
            "speakers":      speakers,
            "topics":        topics,
            "summary":       summary,
            "report_url":    report_url,
            "blocks":        blocks,
        })

        # Reporte de solo texto mientras llega el video
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis   = analyze_transcript(meeting_title, speakers, blocks, summary, topics)
        pdf_path   = generate_pdf_report(session_id, meeting_title, meeting_date,
                                          speakers, topics, summary, analysis, report_url)
        drive_url  = upload_report(pdf_path, f"QualBot_{meeting_title}_{meeting_date}.pdf")

        print(f"✅ Reporte texto → Drive: {drive_url}")
        return jsonify({"status": "ok", "drive_url": drive_url}), 200

    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error("readai_webhook", e, tb)
        return jsonify({"error": str(e)}), 500


# ── Zoom webhook — dispara análisis integrado cuando la grabación está lista ───
@app.route("/webhook/zoom", methods=["POST"])
def zoom_webhook():
    data  = request.json or {}
    event = data.get("event", "")
    print(f"📥 Zoom: {event}")

    if event == "endpoint.url_validation":
        import hmac, hashlib
        token     = data.get("payload", {}).get("plainToken", "")
        secret    = os.environ.get("ZOOM_WEBHOOK_SECRET", "")
        encrypted = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return jsonify({"plainToken": token, "encryptedToken": encrypted}), 200

    if event == "recording.completed":
        threading.Thread(target=process_zoom, args=(data,), daemon=True).start()
        return jsonify({"status": "procesando"}), 200

    return jsonify({"status": "ignorado"}), 200


def process_zoom(data):
    """Descarga video, extrae 36 frames y hace análisis integrado con Claude"""
    meeting_topic = "desconocido"
    try:
        from zoom_downloader import download_recording
        from video_analyzer import extract_frames
        from analyzer import analyze_integrated
        from drive_uploader import upload_report
        from report_generator import generate_pdf_report

        obj             = data.get("payload", {}).get("object", {})
        meeting_topic   = obj.get("topic", "Focus Group")
        recording_files = obj.get("recording_files", [])

        print(f"🎬 Iniciando análisis integrado: {meeting_topic}")

        # Buscar el MP4 principal
        mp4 = next((f for f in recording_files
                    if f.get("file_type") == "MP4" and
                    f.get("recording_type") == "shared_screen_with_speaker_view"), None)
        if not mp4:
            mp4 = next((f for f in recording_files if f.get("file_type") == "MP4"), None)
        if not mp4:
            print("⚠️  No hay MP4"); return

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("recordings", exist_ok=True)
        video_path = f"recordings/zoom_{session_id}.mp4"

        # 1. Descargar
        print(f"⬇️  Descargando grabación de: {meeting_topic}")
        download_recording(mp4.get("download_url",""), video_path)

        # 2. Extraer 36 frames distribuidos uniformemente
        print("🎬 Extrayendo 36 frames...")
        frames, duration_s = extract_frames(video_path, n_frames=36)
        print(f"✅ {len(frames)} frames de {duration_s/60:.1f} min")

        # 3. Cargar transcripción guardada por Read.ai
        print(f"📂 Buscando sesión en caché: {_normalize_title(meeting_topic)}")
        cached   = load_session(meeting_topic)
        blocks   = cached.get("blocks", [])
        speakers = cached.get("speakers", [])
        topics   = cached.get("topics", [])
        summary  = cached.get("summary", "")
        date     = cached.get("meeting_date", str(datetime.now().date()))
        url      = cached.get("report_url", "")

        if not blocks:
            print(f"⚠️  Transcripción no encontrada para '{meeting_topic}' — el reporte integrado no tendrá texto")

        # 4. UN SOLO llamado a Claude con texto + video
        print("🧠 Análisis integrado texto + video...")
        analysis = analyze_integrated(meeting_topic, speakers, blocks, summary, topics, frames)

        # 5. PDF y Drive
        print("📄 Generando PDF integrado...")
        pdf_path  = generate_pdf_report(session_id, meeting_topic, date,
                                         speakers, topics, summary, analysis, url)
        drive_url = upload_report(pdf_path, f"QualBot_Integrado_{meeting_topic}_{session_id}.pdf")
        print(f"✅ Reporte integrado → Drive: {drive_url}")

        try:
            os.remove(video_path)
        except Exception:
            pass

    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        print(f"❌ Error en análisis integrado de '{meeting_topic}': {e}")
        _notify_error(f"process_zoom / {meeting_topic}", e, tb)


# ── Listar grabaciones recientes ───────────────────────────────────────────────
@app.route("/zoom-recordings", methods=["GET"])
def list_zoom_recordings():
    import requests as req
    try:
        token = _zoom_token()
        from datetime import timedelta
        today    = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp     = req.get("https://api.zoom.us/v2/users/me/recordings",
                           headers={"Authorization": f"Bearer {token}"},
                           params={"from": week_ago, "to": today})
        meetings = [{"uuid": m.get("uuid"), "id": m.get("id"),
                     "topic": m.get("topic"), "start_time": m.get("start_time"),
                     "files": [f.get("file_type") for f in m.get("recording_files",[])]}
                    for m in resp.json().get("meetings", [])]
        return jsonify({"meetings": meetings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Trigger manual por UUID ────────────────────────────────────────────────────
@app.route("/process-zoom", methods=["GET"])
def process_zoom_manual():
    import requests as req
    from urllib.parse import quote
    meeting_uuid = request.args.get("id","")
    if not meeting_uuid:
        return jsonify({"error": "Falta ?id="}), 400
    try:
        token        = _zoom_token()
        uuid_encoded = quote(meeting_uuid, safe="")
        resp         = req.get(f"https://api.zoom.us/v2/meetings/{uuid_encoded}/recordings",
                               headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        recordings = resp.json()
        threading.Thread(target=process_zoom,
                         args=({"payload": {"object": recordings}},),
                         daemon=True).start()
        return jsonify({"status": "procesando", "topic": recordings.get("topic")}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Trigger manual por nombre del grupo (busca en la lista de grabaciones) ─────
@app.route("/reprocess-meeting", methods=["GET"])
def reprocess_meeting():
    import requests as req
    from datetime import timedelta
    topic_query = request.args.get("topic", "").lower()
    if not topic_query:
        return jsonify({"error": "Falta ?topic=Grupo+1"}), 400
    try:
        token    = _zoom_token()
        today    = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp     = req.get("https://api.zoom.us/v2/users/me/recordings",
                           headers={"Authorization": f"Bearer {token}"},
                           params={"from": week_ago, "to": today})
        meetings = resp.json().get("meetings", [])

        # Buscar el meeting por topic
        match = next((m for m in meetings
                      if topic_query in m.get("topic","").lower()), None)
        if not match:
            available = [m.get("topic") for m in meetings]
            return jsonify({"error": f"No encontré '{topic_query}'",
                            "disponibles": available}), 404

        topic = match.get("topic")
        print(f"🎯 Reprocessing: {topic}")

        # Armar payload igual al webhook de Zoom
        payload = {"payload": {"object": match}}
        threading.Thread(target=process_zoom, args=(payload,), daemon=True).start()
        return jsonify({"status": "procesando", "topic": topic,
                        "files": [f.get("file_type") for f in match.get("recording_files",[])]}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _zoom_token():
    import requests as req
    resp = req.post("https://zoom.us/oauth/token",
                    params={"grant_type": "account_credentials",
                            "account_id": os.environ["ZOOM_ACCOUNT_ID"]},
                    auth=(os.environ["ZOOM_CLIENT_ID"], os.environ["ZOOM_CLIENT_SECRET"]))
    return resp.json()["access_token"]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
