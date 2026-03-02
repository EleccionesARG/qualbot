import os
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

@app.route("/health", methods=["GET"])
def health2():
    return "OK", 200

@app.route("/webhook/readai", methods=["POST"])
def readai_webhook():
    from analyzer import analyze_transcript
    from drive_uploader import upload_report
    from report_generator import generate_pdf_report

    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    try:
        meeting_title = data.get("title", "Focus Group")
        meeting_date  = data.get("date", str(datetime.now().date()))
        report_url    = data.get("report_url", "")
        summary       = data.get("summary", "")
        topics        = [t.get("text", "") for t in data.get("topics", [])]
        transcript    = data.get("transcript", {})
        speakers      = [s.get("name", "") for s in transcript.get("speakers", [])]
        blocks        = transcript.get("speaker_blocks", [])

        analysis   = analyze_transcript(meeting_title, speakers, blocks, summary, topics)
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path   = generate_pdf_report(session_id, meeting_title, meeting_date,
                                          speakers, topics, summary, analysis, report_url)
        drive_url  = upload_report(pdf_path, f"QualBot_{meeting_title}_{meeting_date}.pdf")

        return jsonify({"status": "ok", "drive_url": drive_url}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
