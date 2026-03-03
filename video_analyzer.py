import cv2
import json
import os

EMOTION_MAP = {
    "angry":    "Enojo",
    "disgust":  "Disgusto",
    "fear":     "Miedo",
    "happy":    "Alegría",
    "sad":      "Tristeza",
    "surprise": "Sorpresa",
    "neutral":  "Neutral"
}

SAMPLE_EVERY_N_SECONDS = 5  # 1 frame cada 5 segundos


def analyze_video(video_path):
    """
    Analiza expresiones faciales en el video de Zoom.
    Retorna lista de detecciones con timestamp y emoción.
    """
    from deepface import DeepFace

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    fps          = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s   = total_frames / fps
    frame_step   = int(fps * SAMPLE_EVERY_N_SECONDS)

    print(f"🎬 Duración: {duration_s/60:.1f} min | Frames a analizar: {total_frames//frame_step}")

    results  = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step == 0:
            timestamp = round(frame_idx / fps, 1)
            pct = (frame_idx / total_frames) * 100
            print(f"\r   Procesando: {pct:.0f}% | {int(timestamp//60):02d}:{int(timestamp%60):02d}", end="")

            try:
                analyses = DeepFace.analyze(
                    frame,
                    actions=["emotion"],
                    enforce_detection=False,
                    silent=True
                )
                if not isinstance(analyses, list):
                    analyses = [analyses]

                for i, a in enumerate(analyses):
                    dom = a.get("dominant_emotion", "neutral")
                    conf = a.get("emotion", {}).get(dom, 0)
                    region = a.get("region", {})

                    # Filtrar caras muy pequeñas o poco confiables
                    if conf < 50 or region.get("w", 0) < 60:
                        continue

                    results.append({
                        "timestamp":   timestamp,
                        "face_id":     i,
                        "emotion_es":  EMOTION_MAP.get(dom, dom),
                        "emotion_en":  dom,
                        "confidence":  round(conf, 1),
                        "all_emotions": {k: round(v, 1) for k, v in a.get("emotion", {}).items()}
                    })
            except Exception:
                pass

        frame_idx += 1

    cap.release()
    print(f"\n✅ {len(results)} detecciones en {total_frames//frame_step} frames")
    return results, duration_s


def summarize_emotions(detections, duration_s):
    """Genera resumen de emociones y timeline por minuto"""
    if not detections:
        return {}, {}

    # Distribución general
    counts = {}
    for d in detections:
        e = d["emotion_es"]
        counts[e] = counts.get(e, 0) + 1
    total = sum(counts.values())
    distribution = {k: {"count": v, "pct": round(v/total*100, 1)}
                    for k, v in sorted(counts.items(), key=lambda x: -x[1])}

    # Timeline por minuto
    minutes = int(duration_s // 60) + 1
    timeline = {}
    for minute in range(minutes):
        window = [d for d in detections
                  if minute*60 <= d["timestamp"] < (minute+1)*60]
        if not window:
            continue
        min_counts = {}
        for d in window:
            e = d["emotion_es"]
            min_counts[e] = min_counts.get(e, 0) + 1
        timeline[str(minute)] = {
            "minuto":    minute,
            "conteos":   min_counts,
            "dominante": max(min_counts, key=min_counts.get)
        }

    return distribution, timeline


def detect_dissonance(detections, transcript_blocks):
    """
    Cruza emociones del video con el texto de la transcripción.
    Detecta cuando alguien dice algo positivo pero muestra emoción negativa (o viceversa).
    """
    positive_words = ["me gusta", "genial", "excelente", "bueno", "perfecto",
                      "encanta", "increíble", "fantástico", "bien", "copado"]
    negative_words = ["no me gusta", "malo", "terrible", "horrible", "pésimo",
                      "no sirve", "caro", "difícil", "problema", "complicado", "no entiendo"]

    dissonances = []

    for block in transcript_blocks:
        start_s = int(block.get("start_time", 0)) / 1000
        end_s   = int(block.get("end_time", start_s*1000 + 5000)) / 1000
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "").lower()

        # Emociones en esta ventana de tiempo
        window = [d for d in detections if start_s <= d["timestamp"] <= end_s]
        if not window:
            continue

        counts = {}
        for d in window:
            e = d["emotion_es"]
            counts[e] = counts.get(e, 0) + 1
        dom_emotion = max(counts, key=counts.get)

        text_positive = any(w in words for w in positive_words)
        text_negative = any(w in words for w in negative_words)

        msg = None
        if text_positive and dom_emotion in ["Enojo", "Tristeza", "Disgusto", "Miedo"]:
            msg = f"Dice algo positivo pero muestra {dom_emotion}"
        elif text_negative and dom_emotion in ["Alegría"]:
            msg = f"Dice algo negativo pero muestra {dom_emotion}"

        if msg:
            dissonances.append({
                "timestamp_fmt": f"{int(start_s//60):02d}:{int(start_s%60):02d}",
                "speaker":       speaker,
                "texto":         block.get("words", "")[:100],
                "emocion_vista": dom_emotion,
                "dissonance":    msg
            })

    return dissonances
