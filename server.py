"""
QualBot Server
Recibe webhooks de Read.ai → analiza emociones con Claude → sube reporte a Google Drive
"""

import os
import json
import hmac
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from analyzer import analyze_transcript
from drive_uploader import upload_report
from report_generator import generate_pdf_report

app = Flask(__name__)

# ── Verificación de seguridad del webhook ──────────────────────────────────────
WEBHOOK_SECRET = os.environ.get("READAI_WEBHOOK_SECRET", "")

def verify_signature(payload_bytes, signature_header):
    """Verifica que el webhook viene realmente de Read.ai"""
    if not WEBHOOK_SECRET:
        return True  # En desarrollo, saltar verificación
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header or "")

# ── Endpoint principal ─────────────────────────────────────────────────────────
@app.route("/webhook/readai", methods=["POST"])
def readai_webhook():
    # 1. Verificar firma
    sig = request.headers.get("X-Read-Signature", "")
    if not verify_signature(request.data, sig):
        return jsonify({"error": "Firma inválida"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "Sin datos"}), 400

    print(f"\n{'='*50}")
    print(f"📥 Webhook recibido: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 2. Extraer datos de Read.ai
        meeting_title = data.get("title", "Focus Group")
        meeting_date  = data.get("date", str(datetime.now().date()))
        report_url    = data.get("report_url", "")
        summary       = data.get("summary", "")
        topics        = [t.get("text","") for t in data.get("topics", [])]
        transcript    = data.get("transcript", {})
        speakers      = [s.get("name","") for s in transcript.get("speakers", [])]
        blocks        = transcript.get("speaker_blocks", [])

        print(f"📋 Reunión: {meeting_title}")
        print(f"👥 Participantes: {', '.join(speakers) if speakers else 'Sin datos'}")
        print(f"💬 Bloques de transcripción: {len(blocks)}")

        # 3. Analizar emociones con Claude
        print("🧠 Analizando emociones con Claude...")
        analysis = analyze_transcript(
            title=meeting_title,
            speakers=speakers,
            blocks=blocks,
            summary=summary,
            topics=topics
        )

        # 4. Generar reporte PDF
        print("📄 Generando reporte PDF...")
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = generate_pdf_report(
            session_id=session_id,
            title=meeting_title,
            date=meeting_date,
            speakers=speakers,
            topics=topics,
            summary=summary,
            analysis=analysis,
            readai_url=report_url
        )

        # 5. Subir a Google Drive
        print("☁️  Subiendo a Google Drive...")
        drive_url = upload_report(
            pdf_path=pdf_path,
            filename=f"QualBot_{meeting_title}_{meeting_date}.pdf"
        )

        print(f"✅ Reporte disponible: {drive_url}")
        print(f"{'='*50}\n")

        return jsonify({
            "status": "ok",
            "drive_url": drive_url,
            "session_id": session_id
        }), 200

    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ── Health check ───────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "QualBot activo ✅", "version": "1.0"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 QualBot Server corriendo en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
