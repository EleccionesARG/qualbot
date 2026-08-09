"""Traducción ES→EN del análisis y la transcripción (modo inglés)."""
import os
import re
import json

from config import TRANSLATION_MODEL


class TranslationError(Exception):
    pass


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Análisis ───────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """You are a professional Spanish-to-English translator specializing in qualitative market research reports from Argentina.

Below is a JSON object containing a focus group analysis written in Rioplatense Spanish. Translate it to English following these rules EXACTLY:

1. Translate ONLY the string values. Do NOT translate, rename, reorder, add, or remove any JSON keys.
2. Preserve the structure exactly: same nesting, same array lengths, same key order.
3. Do not translate or alter: participant names, timestamps (MM:SS), numbers, empty strings, or null values.
4. Translate categorical values consistently: "Alta"->"High", "Media"->"Medium", "Baja"->"Low", "Muy Alta"->"Very High", "Alto"->"High", "Medio"->"Medium", "Bajo"->"Low", "Dominante"->"Dominant", "Positiva"->"Positive", "Negativa"->"Negative", "Ambivalente"->"Ambivalent", "Requiere validación"->"Needs validation".
5. For verbatim quotes from participants ("frase", "dijo_primero", "dijo_despues", "metafora", "lo_que_dijeron", etc.): translate faithfully, preserving the colloquial spoken register. For untranslatable Argentine idioms, translate the meaning and optionally add a brief clarification in square brackets.
6. Be faithful to the analytical content — do not summarize, soften, or embellish.

Respond ONLY with the translated JSON object. No preamble, no markdown fences.

{json_es}"""


def translate_analysis(analysis):
    """Traduce los valores del dict de análisis a inglés. Claves intactas.

    Lanza TranslationError si el resultado no parsea o cambia la estructura."""
    client = _client()
    json_es = json.dumps(analysis, ensure_ascii=False, indent=2)

    with client.messages.stream(
        model=TRANSLATION_MODEL,
        max_tokens=32000,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(json_es=json_es)}],
    ) as stream:
        response = stream.get_final_message()

    raw = "".join(b.text for b in response.content if b.type == "text").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise TranslationError(f"JSON traducido no parsea: {e}")

    if not isinstance(result, dict) or set(result.keys()) != set(analysis.keys()):
        raise TranslationError("La traducción alteró las claves del análisis")
    return result


# ── Transcripción ──────────────────────────────────────────────────────────────

CHUNK_MAX_CHARS = 9000
CHUNK_MAX_BLOCKS = 40

TRANSCRIPT_PROMPT = """You are a professional Spanish-to-English translator. You are translating the raw transcript of a focus group held in Argentina (Rioplatense Spanish) so that an English-speaking client can read exactly what was said.

Rules:
1. Translate each numbered segment FAITHFULLY and LITERALLY. Do not paraphrase, summarize, clean up, or omit anything — including hesitations, repetitions, and incomplete sentences. Preserve the colloquial, spoken register.
2. For untranslatable Argentine idioms or slang, translate the meaning and, when helpful, add a brief clarification in square brackets, e.g. "che [hey]" or "un quilombo [a huge mess]".
3. Do not translate participant names.
4. Output format: one line per segment, starting with the exact same marker [[N]], followed by the translation ONLY (no speaker name — it will be re-added). Same number of segments as the input. Nothing else.
{context_section}
Segments to translate:
{chunk_text}"""


def _chunk_blocks(blocks):
    chunks, current, current_chars = [], [], 0
    for b in blocks:
        text = b.get("words", "") or ""
        if current and (current_chars + len(text) > CHUNK_MAX_CHARS or len(current) >= CHUNK_MAX_BLOCKS):
            chunks.append(current)
            current, current_chars = [], 0
        current.append(b)
        current_chars += len(text)
    if current:
        chunks.append(current)
    return chunks


def _format_chunk(chunk):
    lines = []
    for i, b in enumerate(chunk, 1):
        speaker = b.get("speaker", {}).get("name", "?")
        lines.append(f"[[{i}]] {speaker}: {b.get('words', '')}")
    return "\n".join(lines)


def _parse_chunk(raw, n_expected):
    """Devuelve lista de n_expected traducciones o None si los marcadores no cierran."""
    parts = re.split(r"\[\[(\d+)\]\]", raw)
    # parts = [preámbulo, "1", texto1, "2", texto2, ...]
    found = {}
    for j in range(1, len(parts) - 1, 2):
        try:
            idx = int(parts[j])
        except ValueError:
            return None
        found[idx] = parts[j + 1].strip()
    if set(found.keys()) != set(range(1, n_expected + 1)):
        return None
    return [found[i] for i in range(1, n_expected + 1)]


def _translate_chunk(client, chunk, prev_context):
    context_section = ""
    if prev_context:
        context_section = (
            "\nFor continuity, the last lines already translated were:\n"
            + prev_context
            + "\nDo NOT re-translate them.\n"
        )
    prompt = TRANSCRIPT_PROMPT.format(
        context_section=context_section, chunk_text=_format_chunk(chunk)
    )
    for attempt in range(2):
        response = client.messages.create(
            model=TRANSLATION_MODEL,
            max_tokens=8000,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
        parsed = _parse_chunk(raw, len(chunk))
        if parsed is not None:
            return parsed
        print(f"⚠️  Chunk desalineado (intento {attempt + 1}/2), reintentando...")
    raise TranslationError(f"Chunk de {len(chunk)} bloques no se pudo alinear tras 2 intentos")


def translate_transcript_blocks(blocks):
    """Traduce speaker_blocks de Read.ai en lotes.

    Devuelve [{"speaker": str, "start_time": ms, "text_en": str}, ...]."""
    client = _client()
    chunks = _chunk_blocks(blocks)
    print(f"🌐 Transcripción: {len(blocks)} bloques en {len(chunks)} chunks")

    translated = []
    for i, chunk in enumerate(chunks, 1):
        prev_context = ""
        if translated:
            prev_context = "\n".join(
                f"{t['speaker']}: {t['text_en']}" for t in translated[-2:]
            )
        texts = _translate_chunk(client, chunk, prev_context)
        for b, text_en in zip(chunk, texts):
            translated.append({
                "speaker": b.get("speaker", {}).get("name", "?"),
                "start_time": b.get("start_time", 0),
                "text_en": text_en,
            })
        print(f"   ✅ Chunk {i}/{len(chunks)}")
    return translated
