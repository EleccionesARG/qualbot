
import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

CACHE_DIR = "session_cache"

def save_session(meeting_title, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in meeting_title)
    path = f"{CACHE_DIR}/{safe_name}.json"
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"💾 Sesión guardada: {path}")

def load_session(meeting_title):
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in meeting_title)
    path = f"{CACHE_DIR}/{safe_name}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# ── Health check ───────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return "OK", 200

@app.route("/health", methods=["GET"])
def health2():
    return "OK", 200

# ── Webhook de Read.ai (transcripción) ────────────────────────────────────────
@app.route("/webhook/readai", methods=["POST"])
def readai_webhook():
    from analyzer import analyze_transcript
    from drive_uploader import upload_report
    from report_generator import generate_pdf_report

    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    print(f"📥 Read.ai webhook: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        meeting_title = data.get("title", "Focus Group")
        meeting_date  = data.get("date", str(datetime.now().date()))
        report_url    = data.get("report_url", "")
        summary       = data.get("summary", "")
        topics        = [t.get("text", "") for t in data.get("topics", [])]
        transcript    = data.get("transcript", {})
        speakers      = [s.get("name", "") for s in transcript.get("speakers", [])]
        blocks        = transcript.get("speaker_blocks", [])

        print(f"📋 {meeting_title} | {len(speakers)} speakers | {len(blocks)} bloques")

        analysis   = analyze_transcript(meeting_title, speakers, blocks, summary, topics)
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Guardar en disco para que el análisis de video lo pueda usar después
        save_session(meeting_title, {
            "session_id":    session_id,
            "meeting_title": meeting_title,
            "meeting_date":  meeting_date,
            "speakers":      speakers,
            "topics":        topics,
            "summary":       summary,
            "analysis":      analysis,
            "report_url":    report_url,
            "blocks":        blocks,
        })

        # Generar reporte de solo texto
        pdf_path  = generate_pdf_report(session_id, meeting_title, meeting_date,
                                         speakers, topics, summary, analysis, report_url,
                                         video_analysis=None)
        drive_url = upload_report(pdf_path, f"QualBot_{meeting_title}_{meeting_date}.pdf")

        print(f"✅ Reporte de texto listo: {drive_url}")
        return jsonify({"status": "ok", "drive_url": drive_url}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Webhook de Zoom (grabación lista) ─────────────────────────────────────────
@app.route("/webhook/zoom", methods=["POST"])
def zoom_webhook():
    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    event = data.get("event", "")
    print(f"📥 Zoom webhook: {event}")

    if event == "endpoint.url_validation":
        token = data.get("payload", {}).get("plainToken", "")
        import hmac, hashlib
        secret = os.environ.get("ZOOM_WEBHOOK_SECRET", "")
        encrypted = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return jsonify({"plainToken": token, "encryptedToken": encrypted}), 200

    if event == "recording.completed":
        threading.Thread(target=process_zoom_recording, args=(data,), daemon=True).start()
        return jsonify({"status": "procesando"}), 200

    return jsonify({"status": "ignorado"}), 200


def process_zoom_recording(data):
    """Descarga video, extrae frames, analiza con Claude Vision y genera reporte unificado"""
    try:
        from zoom_downloader import download_recording
        from video_analyzer import extract_frames, analyze_video_with_claude
        from drive_uploader import upload_report
        from report_generator import generate_pdf_report

        payload         = data.get("payload", {})
        obj             = payload.get("object", {})
        meeting_topic   = obj.get("topic", "Focus Group")
        recording_files = obj.get("recording_files", [])

        mp4_file = next(
            (f for f in recording_files
             if f.get("file_type") == "MP4" and f.get("recording_type") == "shared_screen_with_speaker_view"),
            None
        )
        if not mp4_file:
            mp4_file = next((f for f in recording_files if f.get("file_type") == "MP4"), None)

        if not mp4_file:
            print("⚠️  No se encontró archivo MP4")
            return

        download_url = mp4_file.get("download_url", "")
        session_id   = datetime.now().strftime("%Y%m%d_%H%M%S")

        os.makedirs("recordings", exist_ok=True)
        video_path = f"recordings/zoom_{session_id}.mp4"

        # 1. Descargar video
        download_recording(download_url, video_path)

        # 2. Extraer frames
        print("🎬 Extrayendo frames...")
        from video_analyzer import extract_frames, analyze_video_with_claude
        frames, duration_s = extract_frames(video_path, n_frames=24)

        # 3. Cargar datos de transcripción desde disco
        cached = load_session(meeting_topic)
        blocks = cached.get("blocks", [])

        # 4. Analizar con Claude Vision
        video_analysis = analyze_video_with_claude(frames, blocks, meeting_topic)

        # 5. Generar reporte unificado
        print("📄 Generando reporte unificado texto + video...")
        speakers     = cached.get("speakers", [])
        topics       = cached.get("topics", [])
        summary      = cached.get("summary", "")
        analysis     = cached.get("analysis", {})
        meeting_date = cached.get("meeting_date", str(datetime.now().date()))
        report_url   = cached.get("report_url", "")

        pdf_path = generate_pdf_report(
            session_id=session_id,
            title=meeting_topic,
            date=meeting_date,
            speakers=speakers,
            topics=topics,
            summary=summary,
            analysis=analysis,
            readai_url=report_url,
            video_analysis=video_analysis
        )

        drive_url = upload_report(pdf_path, f"QualBot_Completo_{meeting_topic}_{session_id}.pdf")
        print(f"✅ Reporte unificado en Drive: {drive_url}")

        os.remove(video_path)
        print("🧹 Video temporal eliminado")

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"❌ Error procesando video: {e}")


# ── Listar grabaciones recientes ───────────────────────────────────────────────
@app.route("/zoom-recordings", methods=["GET"])
def list_zoom_recordings():
    import requests as req
    try:
        account_id    = os.environ["ZOOM_ACCOUNT_ID"]
        client_id     = os.environ["ZOOM_CLIENT_ID"]
        client_secret = os.environ["ZOOM_CLIENT_SECRET"]

        token_resp = req.post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret)
        )
        token = token_resp.json()["access_token"]

        from datetime import timedelta
        today    = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        resp = req.get(
            "https://api.zoom.us/v2/users/me/recordings",
            headers={"Authorization": f"Bearer {token}"},
            params={"from": week_ago, "to": today}
        )
        data = resp.json()

        meetings = []
        for m in data.get("meetings", []):
            meetings.append({
                "uuid":       m.get("uuid"),
                "id":         m.get("id"),
                "topic":      m.get("topic"),
                "start_time": m.get("start_time"),
                "files":      [f.get("file_type") for f in m.get("recording_files", [])]
            })

        return jsonify({"meetings": meetings}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Trigger manual por UUID ────────────────────────────────────────────────────
@app.route("/process-zoom", methods=["GET"])
def process_zoom_manual():
    import requests as req
    meeting_uuid = request.args.get("id", "")
    if not meeting_uuid:
        return jsonify({"error": "Falta el parametro id"}), 400
    try:
        account_id    = os.environ["ZOOM_ACCOUNT_ID"]
        client_id     = os.environ["ZOOM_CLIENT_ID"]
        client_secret = os.environ["ZOOM_CLIENT_SECRET"]

        token_resp = req.post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret)
        )
        token = token_resp.json()["access_token"]

        from urllib.parse import quote
        uuid_encoded = quote(quote(meeting_uuid, safe=""), safe="")

        resp = req.get(
            f"https://api.zoom.us/v2/meetings/{uuid_encoded}/recordings",
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        recordings = resp.json()

        threading.Thread(
            target=process_zoom_recording,
            args=({"payload": {"object": recordings}},),
            daemon=True
        ).start()
        return jsonify({"status": "procesando", "topic": recordings.get("topic")}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
