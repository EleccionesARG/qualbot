
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
    with open(f"{CACHE_DIR}/{safe_name}.json", "w") as f:
        json.dump(data, f)
    print(f"💾 Sesión guardada: {safe_name}")

def load_session(meeting_title):
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in meeting_title)
    path = f"{CACHE_DIR}/{safe_name}.json"
    return json.load(open(path)) if os.path.exists(path) else {}

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

        # Guardar en disco para que el análisis de video lo cruce después
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
        import traceback; traceback.print_exc()
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
    try:
        from zoom_downloader import download_recording
        from video_analyzer import extract_frames
        from analyzer import analyze_integrated
        from drive_uploader import upload_report
        from report_generator import generate_pdf_report

        obj             = data.get("payload", {}).get("object", {})
        meeting_topic   = obj.get("topic", "Focus Group")
        recording_files = obj.get("recording_files", [])

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
        download_recording(mp4.get("download_url",""), video_path)

        # 2. Extraer 36 frames
        print("🎬 Extrayendo 36 frames...")
        frames, _ = extract_frames(video_path, n_frames=36)

        # 3. Cargar transcripción guardada por Read.ai
        cached   = load_session(meeting_topic)
        blocks   = cached.get("blocks", [])
        speakers = cached.get("speakers", [])
        topics   = cached.get("topics", [])
        summary  = cached.get("summary", "")
        date     = cached.get("meeting_date", str(datetime.now().date()))
        url      = cached.get("report_url", "")

        # 4. UN SOLO llamado a Claude con texto + video
        print("🧠 Análisis integrado texto + video...")
        analysis = analyze_integrated(meeting_topic, speakers, blocks, summary, topics, frames)

        # 5. PDF y Drive
        pdf_path  = generate_pdf_report(session_id, meeting_topic, date,
                                         speakers, topics, summary, analysis, url)
        drive_url = upload_report(pdf_path, f"QualBot_Integrado_{meeting_topic}_{session_id}.pdf")
        print(f"✅ Reporte integrado → Drive: {drive_url}")

        os.remove(video_path)

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"❌ Error: {e}")


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
        uuid_encoded = quote(quote(meeting_uuid, safe=""), safe="")
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


def _zoom_token():
    import requests as req
    resp = req.post("https://zoom.us/oauth/token",
                    params={"grant_type": "account_credentials",
                            "account_id": os.environ["ZOOM_ACCOUNT_ID"]},
                    auth=(os.environ["ZOOM_CLIENT_ID"], os.environ["ZOOM_CLIENT_SECRET"]))
    return resp.json()["access_token"]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
