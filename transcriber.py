"""Transcripción propia del audio de Zoom con ElevenLabs Scribe.

Se activa configurando ELEVENLABS_API_KEY en Railway. Reemplaza la
transcripción de Read.ai para el análisis y las traducciones; Read.ai queda
como plan B y como fuente de nombres reales de los hablantes.
"""
import os
import re
import json

import requests

from notifier import notify_error

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/speech-to-text"
SCRIBE_MODEL = os.environ.get("QUALBOT_SCRIBE_MODEL", "scribe_v1")

# Partir monólogos larguísimos en bloques manejables (en fin de oración)
MAX_BLOCK_CHARS = 4000


def transcriber_enabled():
    return bool(os.environ.get("ELEVENLABS_API_KEY", ""))


def transcribe_recording(audio_path, language="es", num_speakers=None):
    """Transcribe con diarización. Devuelve bloques estilo Read.ai:
    [{"speaker": {"name": "Hablante 1"}, "start_time": ms, "words": str}, ...]
    con start_time relativo al inicio de la grabación."""
    api_key = os.environ["ELEVENLABS_API_KEY"]
    data = {
        "model_id": SCRIBE_MODEL,
        "diarize": "true",
        "language_code": language,
        "timestamps_granularity": "word",
        "tag_audio_events": "false",
    }
    if num_speakers:
        data["num_speakers"] = str(min(int(num_speakers), 32))

    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"🎙️  Enviando {size_mb:.0f} MB a ElevenLabs Scribe...")
    with open(audio_path, "rb") as f:
        resp = requests.post(
            ELEVENLABS_URL,
            headers={"xi-api-key": api_key},
            data=data,
            files={"file": (os.path.basename(audio_path), f)},
            timeout=3600,
        )
    resp.raise_for_status()
    words = resp.json().get("words", [])
    blocks = _words_to_blocks(words)
    print(f"✅ Scribe: {len(words)} palabras → {len(blocks)} bloques")
    return blocks


def _words_to_blocks(words):
    """Agrupa palabras consecutivas del mismo hablante en bloques."""
    blocks, cur, cur_spk = [], None, None
    for w in words:
        wtype = w.get("type", "word")
        if wtype == "audio_event":
            continue
        text = w.get("text", "")
        if wtype == "spacing":
            if cur is not None:
                cur["words"] += text
            continue
        spk = w.get("speaker_id") or "speaker_0"
        start_ms = int(float(w.get("start") or 0) * 1000)
        long_break = (cur is not None and len(cur["words"]) > MAX_BLOCK_CHARS
                      and cur["words"].rstrip().endswith((".", "?", "!")))
        if cur is None or spk != cur_spk or long_break:
            cur = {"speaker": {"name": _label(spk)}, "start_time": start_ms, "words": text}
            cur_spk = spk
            blocks.append(cur)
        else:
            cur["words"] += text
    for b in blocks:
        b["words"] = b["words"].strip()
    return [b for b in blocks if b["words"]]


def _label(speaker_id):
    """speaker_0 → 'Hablante 1' (después se mapea a nombres reales)."""
    m = re.search(r"(\d+)$", str(speaker_id))
    return f"Hablante {int(m.group(1)) + 1}" if m else str(speaker_id)


# ── Mapeo de nombres reales usando la transcripción de Read.ai ─────────────────

MAPPING_PROMPT = """Below are two transcripts of the SAME meeting (in Spanish).

Transcript A was produced by a high-quality engine but labels speakers generically ({labels}).
Transcript B was produced by another tool that knows the participants' real names.

Match each generic label from A to the real name in B, by comparing what each speaker says and when. Respond ONLY with a JSON object mapping every label of A to a name from B, e.g. {{"Hablante 1": "Juan", "Hablante 2": "Ana"}}. If you cannot confidently match a label, map it to itself.

=== TRANSCRIPT A (samples per speaker) ===
{samples_a}

=== TRANSCRIPT B (samples per speaker, real names) ===
{samples_b}"""


def _rel_mmss(ms, t0):
    mins, secs = divmod(max(0, ms - t0) // 1000, 60)
    return f"{mins:02d}:{secs:02d}"


def _samples_by_speaker(blocks, min_chars=40, per_speaker=4):
    starts = [int(b.get("start_time", 0) or 0) for b in blocks]
    t0 = min((s for s in starts if s > 0), default=0)
    samples = {}
    for b, s in zip(blocks, starts):
        name = b.get("speaker", {}).get("name", "?")
        words = (b.get("words", "") or "")[:300]
        if len(words) < min_chars or len(samples.get(name, [])) >= per_speaker:
            continue
        samples.setdefault(name, []).append(f"[{_rel_mmss(s, t0)}] {words}")
    return samples


def map_speaker_names(blocks, readai_blocks):
    """Renombra 'Hablante N' a los nombres reales que Read.ai obtuvo de Zoom.

    Si algo falla, devuelve los bloques con las etiquetas genéricas."""
    if not readai_blocks:
        return blocks
    try:
        import anthropic
        from config import TRANSLATION_MODEL

        samples_a = _samples_by_speaker(blocks)
        samples_b = _samples_by_speaker(readai_blocks)
        fmt = lambda d: "\n".join(f"{k}:\n" + "\n".join(f"  {u}" for u in v)
                                  for k, v in d.items())
        prompt = MAPPING_PROMPT.format(
            labels=", ".join(samples_a.keys()),
            samples_a=fmt(samples_a),
            samples_b=fmt(samples_b),
        )
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=TRANSLATION_MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        mapping = json.loads(raw)
        if not isinstance(mapping, dict):
            raise ValueError("mapping no es un dict")
        print(f"🪪 Mapeo de hablantes: {mapping}")
        for b in blocks:
            name = b.get("speaker", {}).get("name", "")
            if mapping.get(name):
                b["speaker"]["name"] = str(mapping[name])
        return blocks
    except Exception as e:
        import traceback
        notify_error("map_speaker_names", e, traceback.format_exc())
        print(f"⚠️  No se pudieron mapear nombres, quedan etiquetas genéricas: {e}")
        return blocks
