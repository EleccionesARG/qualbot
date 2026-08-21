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


from notifier import notify_error as _notify_error


def _verify_zoom_signature(req):
    """Verifica el HMAC x-zm-signature de Zoom en cada evento del webhook.

    Sin esto, cualquiera que conozca la URL puede mandar eventos falsos con un
    download_url propio y robar el access token de Zoom (se agrega como query
    param al descargar). Si ZOOM_WEBHOOK_SECRET no está seteado, no se puede
    verificar y se deja pasar (comportamiento previo)."""
    secret = os.environ.get("ZOOM_WEBHOOK_SECRET", "")
    if not secret:
        print("⚠️  ZOOM_WEBHOOK_SECRET no configurado — webhook sin verificar")
        return True
    import hmac, hashlib
    ts  = req.headers.get("x-zm-request-timestamp", "")
    sig = req.headers.get("x-zm-signature", "")
    msg = f"v0:{ts}:{req.get_data(as_text=True)}"
    expected = "v0=" + hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _check_admin_key(req):
    """Exige ?key=<QUALBOT_ADMIN_KEY> en los endpoints manuales.

    Si la variable no está seteada, los endpoints quedan abiertos (para no
    romper el flujo actual hasta configurarla en Railway)."""
    required = os.environ.get("QUALBOT_ADMIN_KEY", "")
    if not required:
        print("⚠️  QUALBOT_ADMIN_KEY no configurado — endpoints manuales abiertos")
        return True
    import hmac
    return hmac.compare_digest(req.args.get("key", ""), required)


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
    if not _check_admin_key(request):
        return jsonify({"error": "falta ?key="}), 401
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
    """Estado de la configuración: qué falta para que una sesión salga completa.

    Es público (no hay QUALBOT_ADMIN_KEY): solo booleanos y conteos, nunca
    valores de variables ni títulos de sesiones."""
    from config import (QUALBOT_LANG, ENGLISH_MODE, TRANSLATION_MODEL,
                        QUALBOT_GLOSSARY)
    from analyzer import ANALYSIS_MODEL
    from transcriber import transcriber_enabled, SCRIBE_MODEL
    from notifier import canales

    terms = [t for t in QUALBOT_GLOSSARY.split(",") if t.strip()]
    env = os.environ.get
    scribe_on = transcriber_enabled()
    return jsonify({
        "status": "ok",
        "commit": (env("RAILWAY_GIT_COMMIT_SHA", "") or "")[:7] or None,
        "lang": QUALBOT_LANG,
        "english_mode": ENGLISH_MODE,
        "analysis_model": ANALYSIS_MODEL,
        "translation_model": TRANSLATION_MODEL if ENGLISH_MODE else None,
        "transcriber": {"enabled": scribe_on,
                        "model": SCRIBE_MODEL if scribe_on else None,
                        "fallback": "Read.ai"},
        "frames": int(env("QUALBOT_N_FRAMES", "72")),
        "glossary": {"set": bool(terms), "terms": len(terms)},
        "briefs": _count_briefs(),
        "redis": bool(_get_redis()),
        "integraciones": {
            "anthropic": bool(env("ANTHROPIC_API_KEY")),
            "zoom": all(bool(env(k)) for k in
                        ("ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET")),
            "zoom_webhook_firmado": bool(env("ZOOM_WEBHOOK_SECRET")),
            "drive": bool(env("GOOGLE_SERVICE_ACCOUNT_JSON") and env("GOOGLE_DRIVE_FOLDER_ID")),
        },
        "alertas": dict(canales(), errores_recientes=_contar_errores()),
        "endpoints_protegidos": bool(env("QUALBOT_ADMIN_KEY")),
        "entregables_por_sesion": ([
            "analisis_es", "transcripcion_es"] +
            (["transcripcion_en", "analisis_en", "notas_traduccion"] if ENGLISH_MODE else [])),
    }), 200

@app.route("/errores", methods=["GET"])
def errores():
    """Últimos errores registrados (30 días). La red de seguridad si el push falla."""
    from notifier import ERRORS_KEY
    r = _get_redis()
    if not r:
        return jsonify({"error": "Redis no configurado"}), 200
    try:
        crudos = r.lrange(ERRORS_KEY, 0, 49)
        return jsonify({"errores": [json.loads(e) for e in crudos],
                        "total": len(crudos)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/probar-alerta", methods=["GET"])
def probar_alerta():
    """Manda un mensaje de prueba para verificar el canal de alertas."""
    from notifier import notify, canales
    ok = notify("mensaje de prueba: el canal de alertas funciona.")
    return jsonify({"enviado": bool(ok), "canales": canales()}), 200


# ── Caché del análisis: no re-pagar Opus si falla la subida a Drive ───────────
ANALYSIS_PREFIX = "qualbot:analysis:"
ANALYSIS_TTL = 60 * 60 * 24 * 7  # 7 días
_analysis_memory = {}


def _save_analysis_cache(topic, data):
    safe = _normalize_title(topic)
    _analysis_memory[safe] = data
    r = _get_redis()
    if r:
        try:
            r.set(f"{ANALYSIS_PREFIX}{safe}", json.dumps(data, ensure_ascii=False),
                  ex=ANALYSIS_TTL)
            print(f"💾 Análisis cacheado: {safe}")
        except Exception as e:
            print(f"⚠️  Redis analysis cache error: {e}")


def _load_analysis_cache(topic):
    safe = _normalize_title(topic)
    if safe in _analysis_memory:
        return _analysis_memory[safe]
    r = _get_redis()
    if r:
        try:
            val = r.get(f"{ANALYSIS_PREFIX}{safe}")
            if val:
                return json.loads(val)
        except Exception as e:
            print(f"⚠️  Redis analysis read error: {e}")
    return None


@app.route("/regenerate", methods=["GET"])
def regenerate():
    """Regenera y sube los PDFs desde el análisis cacheado (sin re-analizar).

    Útil si falló la subida a Drive o se cambió la carpeta destino."""
    if not _check_admin_key(request):
        return jsonify({"error": "falta ?key="}), 401
    topic = request.args.get("topic", "")
    if not topic:
        return jsonify({"error": "Falta ?topic="}), 400
    data = _load_analysis_cache(topic)
    if not data:
        return jsonify({"error": f"No hay análisis cacheado para '{topic}' "
                                 "(dura 7 días desde el procesamiento)"}), 404
    threading.Thread(target=_regenerate_outputs, args=(data,), daemon=True).start()
    return jsonify({"status": "regenerando desde caché",
                    "topic": data.get("topic"), "session_id": data.get("session_id")}), 200


def _regenerate_outputs(d):
    try:
        from report_generator import generate_pdf_report
        from drive_uploader import upload_report
        from config import ENGLISH_MODE

        session_id, topic = d["session_id"], d["topic"]
        print(f"♻️  Regenerando reportes de '{topic}' desde caché...")
        pdf_path = generate_pdf_report(session_id, topic, d["date"], d["speakers"],
                                       d["topics"], d["summary"], d["analysis"], d["url"])
        u = upload_report(pdf_path, f"QualBot_Integrado_{topic}_{session_id}.pdf")
        print(f"✅ Reporte integrado (regen) → Drive: {u}")
        _generate_spanish_transcript(session_id, topic, d["date"], d["blocks"])
        if ENGLISH_MODE:
            _generate_english_outputs(session_id, topic, d["date"], d["speakers"],
                                      d["topics"], d["summary"], d["analysis"],
                                      d["url"], d["blocks"])
    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error("regenerate", e, tb)


# ── Brief de sesión: contexto del equipo de investigación ─────────────────────
BRIEF_PREFIX = "qualbot:brief:"
BRIEF_TTL = 60 * 60 * 24 * 60  # 60 días
_brief_memory = {}


def save_brief(topic, text):
    safe = _normalize_title(topic)
    _brief_memory[safe] = text
    r = _get_redis()
    if r:
        try:
            r.set(f"{BRIEF_PREFIX}{safe}", text, ex=BRIEF_TTL)
            print(f"📝 Brief guardado: {safe} ({len(text)} chars)")
        except Exception as e:
            print(f"⚠️  Redis brief error: {e}")


def _contar_errores():
    """Cuántos errores hay registrados, para el /health."""
    from notifier import ERRORS_KEY
    r = _get_redis()
    if not r:
        return None
    try:
        return r.llen(ERRORS_KEY)
    except Exception:
        return None


def _count_briefs():
    """Cuántos briefs vivos hay, para el /health (Redis; si no, los del proceso)."""
    r = _get_redis()
    if r:
        try:
            return len(r.keys(f"{BRIEF_PREFIX}*"))
        except Exception as e:
            print(f"⚠️  Redis brief count error: {e}")
    return len(_brief_memory)


def load_brief(topic):
    safe = _normalize_title(topic)
    if safe in _brief_memory:
        return _brief_memory[safe]
    r = _get_redis()
    if r:
        try:
            val = r.get(f"{BRIEF_PREFIX}{safe}")
            if val:
                _brief_memory[safe] = val
                return val
        except Exception as e:
            print(f"⚠️  Redis brief read error: {e}")
    return ""


@app.route("/brief", methods=["GET", "POST"])
def brief_page():
    """Formulario para cargar el contexto de cada sesión antes del focus.

    El título tiene que coincidir con el nombre de la reunión de Zoom (el
    matching usa la misma normalización que el resto del pipeline)."""
    from markupsafe import escape
    if not _check_admin_key(request):
        return "Falta ?key=<QUALBOT_ADMIN_KEY>", 401

    saved = ""
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        text = request.form.get("text", "").strip()
        if topic and text:
            save_brief(topic, text)
            saved = f"✅ Brief guardado para «{topic}»"

    topic = (request.values.get("topic") or "").strip()
    text = load_brief(topic) if topic else ""
    key = request.values.get("key", "")

    existing = list(_brief_memory.keys())
    r = _get_redis()
    if r:
        try:
            existing = sorted({k.replace(BRIEF_PREFIX, "") for k in r.keys(f"{BRIEF_PREFIX}*")})
        except Exception:
            pass

    links = " · ".join(
        f'<a href="/brief?topic={escape(t)}&key={escape(key)}">{escape(t)}</a>'
        for t in existing) or "ninguno"

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QualBot — Brief de sesión</title>
<style>body{{font-family:sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#1a1a2e}}
textarea{{width:100%;height:340px;font-size:14px;padding:8px}}
input[type=text]{{width:100%;font-size:15px;padding:8px}}
button{{background:#7c6aff;color:#fff;border:0;padding:10px 24px;font-size:15px;border-radius:6px;cursor:pointer}}
.ok{{color:#06d6a0;font-weight:bold}} .hint{{color:#6b6b8a;font-size:13px}}</style></head><body>
<h2>QualBot — Brief de sesión</h2>
<p class="ok">{escape(saved)}</p>
<form method="POST" action="/brief?key={escape(key)}">
<p><label>Título de la reunión de Zoom (tiene que coincidir):<br>
<input type="text" name="topic" value="{escape(topic)}" placeholder="Grupo 1 - Jóvenes" required></label></p>
<p><label>Contexto para el análisis:<br>
<textarea name="text" placeholder="CLIENTE Y OBJETIVOS:\n...\n\nPARTICIPANTES (nombre, edad, perfil):\n...\n\nGUÍA DE PAUTAS / TEMAS:\n...\n\nHIPÓTESIS O FOCOS DE ATENCIÓN:\n...">{escape(text)}</textarea></label></p>
<p class="hint">Este texto se inyecta en el análisis, la traducción y el mapeo de hablantes.
Cargalo antes de que termine la reunión. Dura 60 días.</p>
<button type="submit">Guardar brief</button>
</form>
<p class="hint">Briefs cargados: {links}</p>
</body></html>"""


# ── Read.ai webhook — guarda transcripción y genera reporte de texto ───────────
_readai_recent = {}  # fallback de dedupe si no hay Redis (por proceso)


def _readai_lock(meeting_title, ttl=600):
    """True si somos los primeros en procesar este título en la ventana ttl.

    Read.ai reintenta el webhook si no recibe respuesta rápida; sin este
    candado cada reintento generaba un reporte duplicado en Drive."""
    safe = _normalize_title(meeting_title)
    r = _get_redis()
    if r:
        try:
            return bool(r.set(f"qualbot:readai_lock:{safe}", "1", nx=True, ex=ttl))
        except Exception as e:
            print(f"⚠️  Redis lock error: {e}")
    import time
    now = time.time()
    if now - _readai_recent.get(safe, 0) < ttl:
        return False
    _readai_recent[safe] = now
    return True


@app.route("/webhook/readai", methods=["POST"])
def readai_webhook():
    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    meeting_title = data.get("title", "Focus Group")
    print(f"📥 Read.ai: {datetime.now().strftime('%H:%M:%S')} | {meeting_title}")

    if not _readai_lock(meeting_title):
        print(f"↩️  Webhook duplicado de Read.ai ignorado: {meeting_title}")
        return jsonify({"status": "duplicado ignorado"}), 200

    # Responder ya y procesar en background — si tardamos, Read.ai reintenta
    threading.Thread(target=_process_readai, args=(data,), daemon=True).start()
    return jsonify({"status": "procesando"}), 200


def _process_readai(data):
    from analyzer import analyze_transcript
    from drive_uploader import upload_report
    from report_generator import generate_pdf_report

    try:
        meeting_title = data.get("title", "Focus Group")
        brief         = load_brief(meeting_title)
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
        analysis   = analyze_transcript(meeting_title, speakers, blocks, summary,
                                        topics, brief=brief)
        from validator import verify_quotes
        analysis, _corr = verify_quotes(analysis, blocks)
        pdf_path   = generate_pdf_report(session_id, meeting_title, meeting_date,
                                          speakers, topics, summary, analysis, report_url)
        drive_url  = upload_report(pdf_path, f"QualBot_{meeting_title}_{meeting_date}.pdf")

        print(f"✅ Reporte texto → Drive: {drive_url}")

    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error("readai_webhook", e, tb)


# ── Zoom webhook — dispara análisis integrado cuando la grabación está lista ───
@app.route("/webhook/zoom", methods=["POST"])
def zoom_webhook():
    if not _verify_zoom_signature(request):
        print("🚫 Firma de Zoom inválida — evento rechazado")
        return jsonify({"error": "firma inválida"}), 401
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
    """Descarga video, extrae 72 frames y hace análisis integrado con Claude"""
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
        download_token  = data.get("payload", {}).get("download_token", "")

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
        download_recording(mp4.get("download_url",""), video_path,
                           download_token=download_token)

        # 2. Extraer frames distribuidos uniformemente (configurable por env)
        n_frames = int(os.environ.get("QUALBOT_N_FRAMES", "72"))
        print(f"🎬 Extrayendo {n_frames} frames...")
        frames, duration_s = extract_frames(video_path, n_frames=n_frames)
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

        brief = load_brief(meeting_topic)
        if brief:
            print(f"📝 Brief de sesión encontrado ({len(brief)} chars)")

        # 3.5 Transcripción propia con ElevenLabs Scribe (si hay API key).
        # Reemplaza los bloques de Read.ai para el análisis y las traducciones;
        # Read.ai queda como plan B y aporta los nombres reales de los hablantes.
        from transcriber import transcriber_enabled, transcribe_recording, map_speaker_names
        audio_path = None
        if transcriber_enabled():
            try:
                m4a = next((f for f in recording_files if f.get("file_type") == "M4A"), None)
                src_path = video_path
                if m4a:
                    audio_path = f"recordings/zoom_{session_id}.m4a"
                    download_recording(m4a.get("download_url", ""), audio_path,
                                       download_token=download_token)
                    src_path = audio_path
                el_blocks = transcribe_recording(src_path, num_speakers=len(speakers) or None)
                if el_blocks:
                    el_blocks = map_speaker_names(el_blocks, blocks, brief=brief)
                    blocks = el_blocks
                    print(f"✅ Usando transcripción propia ({len(blocks)} bloques)")
            except Exception as e:
                import traceback; tb = traceback.format_exc()
                print(tb)
                print("⚠️  Falló la transcripción propia — se usa la de Read.ai")
                _notify_error(f"transcriber / {meeting_topic}", e, tb)

        # 4. UN SOLO llamado a Claude con texto + video
        print("🧠 Análisis integrado texto + video...")
        analysis = analyze_integrated(meeting_topic, speakers, blocks, summary,
                                      topics, frames, brief=brief)

        # 4.5 Verificación determinista de citas contra la transcripción
        from validator import verify_quotes
        analysis, correcciones = verify_quotes(analysis, blocks)
        if correcciones:
            print(f"🔎 Validador de citas: {len(correcciones)} correcciones/avisos")
            for linea in correcciones[:10]:
                print(f"   · {linea}")

        # 4.6 Cachear el análisis: si Drive falla, /regenerate lo reusa gratis
        _save_analysis_cache(meeting_topic, {
            "session_id": session_id, "topic": meeting_topic, "date": date,
            "speakers": speakers, "topics": topics, "summary": summary,
            "url": url, "analysis": analysis, "blocks": blocks,
        })

        # 5. PDF y Drive
        print("📄 Generando PDF integrado...")
        pdf_path  = generate_pdf_report(session_id, meeting_topic, date,
                                         speakers, topics, summary, analysis, url)
        drive_url = upload_report(pdf_path, f"QualBot_Integrado_{meeting_topic}_{session_id}.pdf")
        print(f"✅ Reporte integrado → Drive: {drive_url}")

        # 5.5 Transcripción en castellano (verbatim del transcriptor)
        _generate_spanish_transcript(session_id, meeting_topic, date, blocks)

        # 6. Modo inglés: PDF EN + transcripción traducida (QUALBOT_LANG=en)
        from config import ENGLISH_MODE
        if ENGLISH_MODE:
            _generate_english_outputs(session_id, meeting_topic, date, speakers,
                                      topics, summary, analysis, url, blocks)

        try:
            os.remove(video_path)
            if audio_path:
                os.remove(audio_path)
        except Exception:
            pass

    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        print(f"❌ Error en análisis integrado de '{meeting_topic}': {e}")
        _notify_error(f"process_zoom / {meeting_topic}", e, tb)


def _generate_spanish_transcript(session_id, topic, date, blocks):
    """Sube la transcripción en castellano tal como la devolvió el transcriptor.

    Es el verbatim crudo del grupo: mismo origen que la versión en inglés, así
    las dos quedan alineadas bloque a bloque. Falla aislado — si revienta, los
    reportes ya están en Drive."""
    if not blocks:
        print("⚠️  Sin transcripción — se omite el documento de transcripción ES")
        return
    try:
        from report_generator import generate_transcript_document
        from drive_uploader import upload_report
        doc_path = generate_transcript_document(session_id, topic, date, blocks, lang="es")
        u = upload_report(doc_path, f"QualBot_Transcript_{topic}_{session_id}_ES.pdf")
        print(f"✅ Transcripción ES → Drive: {u}")
    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error(f"transcript_es / {topic}", e, tb)


def _generate_translation_notes(session_id, topic, date, notas):
    """Sube el documento de dudas de traducción. Falla aislado."""
    try:
        from report_generator import generate_translation_notes_document
        from drive_uploader import upload_report
        doc_path = generate_translation_notes_document(session_id, topic, date, notas)
        u = upload_report(doc_path, f"QualBot_Notas_Traduccion_{topic}_{session_id}.pdf")
        print(f"✅ Notas de traducción ({len(notas)}) → Drive: {u}")
    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error(f"translation_notes / {topic}", e, tb)


def _generate_english_outputs(session_id, topic, date, speakers, topics,
                              summary, analysis, url, blocks):
    """Genera y sube el PDF EN y la transcripción traducida. Cada artefacto
    falla de forma aislada (alerta a Slack) — los PDFs ES ya están en Drive.

    Nota: el flujo interim de Read.ai (readai_webhook) no genera versión EN a
    propósito; el entregable para el cliente es este reporte integrado. Si algún
    día hace falta, llamar a esta función al final de readai_webhook."""
    from translator import (translate_analysis, translate_transcript_blocks,
                            format_translated_transcript)
    from report_generator import generate_pdf_report, generate_transcript_document
    from drive_uploader import upload_report

    session_context = topic
    if topics:
        session_context += ". Topics discussed: " + ", ".join(topics)
    brief = load_brief(topic)
    if brief:
        session_context += "\nResearch team brief for this session:\n" + brief[:2500]

    # 6a. Transcripción traducida PRIMERO: además de ser un entregable, sirve
    # de referencia para que las citas del reporte EN salgan palabra por
    # palabra iguales a la transcripción.
    transcript_en_text = ""
    if blocks:
        try:
            print(f"🌐 Traduciendo transcripción ({len(blocks)} bloques)...")
            blocks_en, notas = translate_transcript_blocks(blocks, context=session_context)
            doc_path = generate_transcript_document(session_id, topic, date, blocks_en, lang="en")
            u = upload_report(doc_path, f"QualBot_Transcript_{topic}_{session_id}_EN.pdf")
            print(f"✅ Transcripción EN → Drive: {u}")
            transcript_en_text = format_translated_transcript(blocks_en)
            # Dudas del traductor: modismos, ironías, audio dudoso
            _generate_translation_notes(session_id, topic, date, notas)
        except Exception as e:
            import traceback; tb = traceback.format_exc()
            print(tb)
            _notify_error(f"translate_transcript / {topic}", e, tb)
    else:
        print("⚠️  Sin transcripción — se omite el documento de transcripción EN")

    # 6b. Análisis traducido → PDF EN. El summary de Read.ai viaja como clave
    # extra del dict para traducirse en la misma llamada.
    try:
        print("🌐 Traduciendo análisis a inglés...")
        payload = dict(analysis)
        if summary:
            payload["resumen_readai"] = summary
        analysis_en = translate_analysis(payload, context=session_context,
                                         transcript_en=transcript_en_text)
        summary_en = analysis_en.pop("resumen_readai", "")
        pdf_en = generate_pdf_report(session_id, topic, date, speakers, topics,
                                     summary_en, analysis_en, url, lang="en")
        u = upload_report(pdf_en, f"QualBot_Integrado_{topic}_{session_id}_EN.pdf")
        print(f"✅ Reporte EN → Drive: {u}")
    except Exception as e:
        import traceback; tb = traceback.format_exc()
        print(tb)
        _notify_error(f"translate_analysis / {topic}", e, tb)


# ── Listar grabaciones recientes ───────────────────────────────────────────────
@app.route("/zoom-recordings", methods=["GET"])
def list_zoom_recordings():
    if not _check_admin_key(request):
        return jsonify({"error": "falta ?key="}), 401
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
    if not _check_admin_key(request):
        return jsonify({"error": "falta ?key="}), 401
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
    if not _check_admin_key(request):
        return jsonify({"error": "falta ?key="}), 401
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
