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
{context_section}{transcript_ref}
Respond ONLY with the translated JSON object. No preamble, no markdown fences.

{json_es}"""

TRANSCRIPT_REF_TEMPLATE = """
REFERENCE — Full English transcript of this session (already translated). When translating verbatim participant quotes, reuse the EXACT wording from this transcript whenever the quoted line appears in it, so quotes in the report match the transcript document word-for-word:
<<<
{transcript_en}
>>>
"""


def _context_section(context):
    from config import QUALBOT_GLOSSARY
    parts = []
    if context:
        parts.append(f"Session context (to disambiguate terminology): {context}")
    if QUALBOT_GLOSSARY:
        parts.append("Known names/terms in this session — normalize obvious "
                     f"transcription mishearings to these exact spellings: {QUALBOT_GLOSSARY}")
    if not parts:
        return ""
    return "\n" + "\n".join(parts) + "\n"


def translate_analysis(analysis, context="", transcript_en=""):
    """Traduce los valores del dict de análisis a inglés. Claves intactas.

    Si se pasa transcript_en (la transcripción ya traducida), las citas
    textuales del reporte se toman verbatim de ahí, para que reporte y
    transcripción coincidan palabra por palabra.

    Lanza TranslationError si el resultado no parsea o cambia la estructura."""
    client = _client()
    json_es = json.dumps(analysis, ensure_ascii=False, indent=2)
    transcript_ref = ""
    if transcript_en:
        transcript_ref = TRANSCRIPT_REF_TEMPLATE.format(transcript_en=transcript_en)
    prompt = ANALYSIS_PROMPT.format(
        json_es=json_es,
        context_section=_context_section(context),
        transcript_ref=transcript_ref,
    )

    with client.messages.stream(
        model=TRANSLATION_MODEL,
        max_tokens=32000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
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
4. Output format: one line per segment, starting with the exact same marker [[N]], followed by the translation ONLY. Same number of segments as the input. Nothing else.
5. NEVER start a translation with the speaker's name or any "Name:" prefix — the speaker labels are re-added later by the system. Output only the spoken words.
6. If a segment is garbled or nonsensical (a transcription artifact), do NOT invent fluent English for it: translate what is recoverable and mark the broken part as [unintelligible].
7. Profanity policy: translate ordinary swearing faithfully (it is research data), but NEVER translate slurs literally — replace the slur itself with [expletive] while keeping the rest of the sentence.
8. For culturally local references (football clubs, TV shows, public agencies, local brands), add a brief clarification in square brackets the first time each appears.
9. AFTER all the numbered segments, output a line containing exactly [[NOTES]] and then flag the passages where your translation is genuinely uncertain: Rioplatense idioms or lunfardo with no clean English equivalent, ambiguous references, irony or sarcasm that may not survive, culturally loaded words whose connotation is lost, and audio garbled enough that you had to guess. One note per line, in this exact format:
[[N]] | <the Spanish fragment, verbatim> | <how you rendered it> | <why it is uncertain and any alternative reading — write THIS FIELD IN SPANISH, the reviewer is Argentine>
Flag only real doubts: at most 5 per batch, and none at all if the batch was straightforward. Never add a note just to fill the section — a short list is the expected outcome.
{session_context}{prev_section}
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


NOTE_RE = re.compile(r"^\s*\[\[(\d+)\]\]\s*\|(.*)$")


def _split_notes(raw):
    """Separa las traducciones numeradas de la sección de notas."""
    parts = raw.split("[[NOTES]]")
    return parts[0], "[[NOTES]]".join(parts[1:])


def _parse_notes(raw, n_expected):
    """Notas de traducción del chunk: [[N]] | original | traducción | duda."""
    notas = []
    for line in (raw or "").splitlines():
        m = NOTE_RE.match(line)
        if not m:
            continue
        idx = int(m.group(1))
        if not 1 <= idx <= n_expected:
            continue
        campos = [c.strip() for c in m.group(2).split("|")]
        if len(campos) < 3 or not campos[2]:
            continue
        notas.append({"idx": idx, "original": campos[0],
                      "translation": campos[1], "issue": " | ".join(campos[2:])})
    return notas[:8]  # techo por chunk: si marca todo, no marcó nada


def _translate_chunk(client, chunk, prev_context, session_context=""):
    prev_section = ""
    if prev_context:
        prev_section = (
            "\nFor continuity, the last lines already translated were:\n"
            + prev_context
            + "\nDo NOT re-translate them.\n"
        )
    prompt = TRANSCRIPT_PROMPT.format(
        session_context=_context_section(session_context),
        prev_section=prev_section,
        chunk_text=_format_chunk(chunk),
    )
    for attempt in range(2):
        response = client.messages.create(
            model=TRANSLATION_MODEL,
            max_tokens=12000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
        cuerpo, notas_raw = _split_notes(raw)
        parsed = _parse_chunk(cuerpo, len(chunk))
        if parsed is not None:
            return parsed, _parse_notes(notas_raw, len(chunk))
        print(f"⚠️  Chunk desalineado (intento {attempt + 1}/2), reintentando...")
    raise TranslationError(f"Chunk de {len(chunk)} bloques no se pudo alinear tras 2 intentos")


def format_translated_transcript(translated_blocks):
    """Texto plano '[MM:SS] Speaker: ...' de la transcripción traducida,
    con tiempos relativos — para usar como referencia de citas."""
    starts = [int(b.get("start_time", 0) or 0) for b in translated_blocks]
    t0 = min((s for s in starts if s > 0), default=0)
    lines = []
    for b, s in zip(translated_blocks, starts):
        rel = max(0, s - t0)
        mins, secs = divmod(rel // 1000, 60)
        lines.append(f"[{mins:02d}:{secs:02d}] {b.get('speaker','?')}: {b.get('text_en','')}")
    return "\n".join(lines)


def _strip_speaker_prefix(text, speaker):
    """Quita un prefijo 'Nombre:' que el modelo a veces agrega pese al prompt.

    Solo lo saca si el prefijo se parece al nombre del hablante (mismas
    primeras letras, ej. 'Asistente'→'Assistant:'), para no comerse diálogo
    real que empiece con dos puntos."""
    m = re.match(r"^([^:\n]{1,30}):\s+", text)
    if not m:
        return text
    prefix = m.group(1).strip().casefold()
    name = (speaker or "").strip().casefold()
    if name and (prefix == name or (len(prefix) >= 2 and prefix[:2] == name[:2])):
        return text[m.end():]
    return text


def translate_transcript_blocks(blocks, context=""):
    """Traduce speaker_blocks de Read.ai en lotes.

    Devuelve (bloques, notas):
    - bloques: [{"speaker": str, "start_time": ms, "text_en": str}, ...]
    - notas:   [{"speaker", "start_time", "original", "translation", "issue"}, ...]
      con los pasajes que el traductor marcó como dudosos."""
    client = _client()
    chunks = _chunk_blocks(blocks)
    print(f"🌐 Transcripción: {len(blocks)} bloques en {len(chunks)} chunks")

    translated, notas = [], []
    for i, chunk in enumerate(chunks, 1):
        prev_context = ""
        if translated:
            prev_context = "\n".join(
                f"{t['speaker']}: {t['text_en']}" for t in translated[-2:]
            )
        texts, chunk_notas = _translate_chunk(client, chunk, prev_context,
                                              session_context=context)
        for n in chunk_notas:
            b = chunk[n["idx"] - 1]
            notas.append({
                "speaker": b.get("speaker", {}).get("name", "?"),
                "start_time": b.get("start_time", 0),
                "original": n["original"],
                "translation": n["translation"],
                "issue": n["issue"],
            })
        for b, text_en in zip(chunk, texts):
            speaker = b.get("speaker", {}).get("name", "?")
            translated.append({
                "speaker": speaker,
                "start_time": b.get("start_time", 0),
                "text_en": _strip_speaker_prefix(text_en, speaker),
            })
        print(f"   ✅ Chunk {i}/{len(chunks)}" +
              (f" · {len(chunk_notas)} nota(s)" if chunk_notas else ""))
    print(f"📝 Notas de traducción: {len(notas)}")
    return translated, notas
