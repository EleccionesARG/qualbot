import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

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
        pdf_path   = generate_pdf_report(session_id, meeting_title, meeting_date,
                                          speakers, topics, summary, analysis, report_url)
        drive_url  = upload_report(pdf_path, f"QualBot_{meeting_title}_{meeting_date}.pdf")

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
    """Procesa la grabación de Zoom en background"""
    try:
        from zoom_downloader import download_recording
        from video_analyzer import analyze_video, summarize_emotions, detect_dissonance
        from drive_uploader import upload_report
        from report_generator_video import generate_video_report

        payload         = data.get("payload", {})
        obj             = payload.get("object", {})
        meeting_id      = obj.get("id", "")
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
            print("⚠️  No se encontró archivo MP4 en la grabación")
            return

        download_url = mp4_file.get("download_url", "")
        session_id   = datetime.now().strftime("%Y%m%d_%H%M%S")

        os.makedirs("recordings", exist_ok=True)
        video_path = f"recordings/zoom_{session_id}.mp4"

        download_recording(download_url, video_path)

        print("🧠 Analizando expresiones faciales...")
        detections, duration_s = analyze_video(video_path)
        distribution, timeline = summarize_emotions(detections, duration_s)

        print("📄 Generando reporte de video...")
        pdf_path = generate_video_report(
            session_id=session_id,
            title=meeting_topic,
            distribution=distribution,
            timeline=timeline,
            dissonances=[],
            total_detections=len(detections),
            duration_s=duration_s
        )

        drive_url = upload_report(pdf_path, f"QualBot_Video_{meeting_topic}_{session_id}.pdf")
        print(f"✅ Reporte de video en Drive: {drive_url}")

        os.remove(video_path)
        print("🧹 Video temporal eliminado")

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"❌ Error procesando video: {e}")


# ── Trigger manual para procesar grabación de Zoom ────────────────────────────
@app.route("/process-zoom", methods=["GET"])
def process_zoom_manual():
    from zoom_downloader import get_recording_files
    meeting_id = request.args.get("id", "")
    if not meeting_id:
        return jsonify({"error": "Falta el parametro id"}), 400
    try:
        recordings = get_recording_files(meeting_id)
        threading.Thread(
            target=process_zoom_recording,
            args=({"payload": {"object": recordings}},),
            daemon=True
        ).start()
        return jsonify({"status": "procesando", "meeting_id": meeting_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
