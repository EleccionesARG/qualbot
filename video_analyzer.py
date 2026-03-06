import os
import base64


def extract_frames(video_path, n_frames=36):
    """Extrae n_frames distribuidos uniformemente del video"""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30
    duration_s   = total_frames / fps

    indices = [int(i * total_frames / n_frames) for i in range(n_frames)]

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        timestamp_s = idx / fps
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        frames.append({
            "timestamp_s":   round(timestamp_s, 1),
            "timestamp_fmt": f"{int(timestamp_s//60):02d}:{int(timestamp_s%60):02d}",
            "b64":           b64
        })

    cap.release()
    print(f"✅ {len(frames)} frames extraídos de {duration_s/60:.1f} min")
    return frames, duration_s
