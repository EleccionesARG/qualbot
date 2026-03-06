import os
import json
import base64
import tempfile


def extract_frames(video_path, n_frames=24):
    """Extrae n_frames distribuidos uniformemente del video"""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30
    duration_s   = total_frames / fps

    # Distribuir frames uniformemente
    indices = [int(i * total_frames / n_frames) for i in range(n_frames)]

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        timestamp_s = idx / fps

        # Convertir frame a JPEG en memoria
        import cv2
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        frames.append({
            "timestamp_s": round(timestamp_s, 1),
            "timestamp_fmt": f"{int(timestamp_s//60):02d}:{int(timestamp_s%60):02d}",
            "b64": b64
        })

    cap.release()
    print(f"✅ {len(frames)} frames extraídos de {duration_s/60:.1f} min de video")
    return frames, duration_s


def analyze_video_with_claude(frames, transcript_blocks, meeting_title):
    """Analiza los frames con Claude Vision cruzando con la transcripción"""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Preparar contexto de transcripción simplificado
    transcript_summary = ""
    for block in transcript_blocks[:50]:  # Máximo 50 bloques para no saturar
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "")
        start   = block.get("start_time", 0)
        mins    = int(start // 60000)
        secs    = int((start % 60000) // 1000)
        transcript_summary += f"[{mins:02d}:{secs:02d}] {speaker}: {words}\n"

    # Construir mensaje con imágenes
    content = []

    content.append({
        "type": "text",
        "text": f"""Sos un analista experto en investigación cualitativa y lenguaje no verbal. 
Vas a analizar {len(frames)} frames de video de un focus group llamado "{meeting_title}".

TRANSCRIPCIÓN DE LA SESIÓN (extracto):
{transcript_summary}

A continuación te mando los frames del video con sus timestamps. Para cada frame indicá:
1. Quiénes aparecen y qué expresión facial tienen
2. Si hay lenguaje corporal significativo (postura, gestos, mirada)
3. Si la expresión coincide o contradice lo que se estaba diciendo en ese momento

Al final, dá un análisis integrado en JSON con esta estructura exacta:

{{
  "observaciones_por_frame": [
    {{
      "timestamp": "MM:SS",
      "descripcion_visual": "qué se ve en el frame",
      "expresiones": [{{"persona": "nombre o descripcion", "emocion": "emocion", "intensidad": "baja/media/alta"}}],
      "lenguaje_corporal": "descripcion de posturas y gestos",
      "coherencia_con_discurso": "coincide / contradice / neutro",
      "nota": "observacion relevante si la hay"
    }}
  ],
  "patrones_visuales_globales": {{
    "emocion_dominante_visual": "emocion que mas se vio",
    "momentos_tension_visual": ["timestamp1", "timestamp2"],
    "momentos_apertura_visual": ["timestamp1", "timestamp2"],
    "lenguaje_corporal_grupal": "descripcion general del grupo a lo largo de la sesion"
  }},
  "disonancias_detectadas": [
    {{
      "timestamp": "MM:SS",
      "lo_que_se_decia": "resumen del discurso en ese momento",
      "lo_que_mostraba_el_cuerpo": "descripcion visual",
      "interpretacion": "analisis de la contradiccion"
    }}
  ],
  "insights_visuales": [
    {{
      "insight": "descripcion del hallazgo visual",
      "evidencia": "en qué frames se basa",
      "implicancia": "que significa para la investigacion"
    }}
  ],
  "resumen_visual": "parrafo de 3-4 oraciones que resume lo mas importante del analisis visual"
}}

Respondé ÚNICAMENTE con el JSON, sin texto adicional."""
    })

    # Agregar frames como imágenes
    for frame in frames:
        content.append({
            "type": "text",
            "text": f"Frame [{frame['timestamp_fmt']}]:"
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame["b64"]
            }
        })

    print(f"🧠 Enviando {len(frames)} frames a Claude Vision...")
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": content}]
    )

    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"⚠️  Error parseando JSON de video: {raw[:200]}")
        return {
            "observaciones_por_frame": [],
            "patrones_visuales_globales": {},
            "disonancias_detectadas": [],
            "insights_visuales": [],
            "resumen_visual": raw[:500]
        }
