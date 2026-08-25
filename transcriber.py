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

MAPPING_PROMPT = """Below is a transcript of a meeting (in Spanish) produced by a high-quality engine that labels speakers generically ({labels}), plus reference material that reveals who was in the room.

Your job: map each generic label to the CANONICAL name of that person.

HOW TO CHOOSE THE NAME (this is a client-facing document — naming must be consistent and clean):
1. If the person is listed in the research team notes, use EXACTLY the name written there, spelling and accents included. Those notes are the naming standard: if they call her "Lucía" and Zoom shows "Adriana Nuñez", the answer is "Lucía".
2. If the person is NOT in the notes, use their real first name, properly capitalized: "belen lopez" -> "Belén", "iPhone de Oriana Raquel" -> "Oriana", "ABEL" -> "Abel". Add a surname only if two people share a first name.
3. NEVER output a device name, a handle, a name in all-lowercase or ALL-CAPS, or anything with a device prefix like "iPhone de".

HOW TO WORK OUT WHO IS WHO:
- The Zoom attendance list tells you who was present and which device belongs to whom. Use it to resolve identity — not to choose how the name is written.
- Match by what people say about themselves: the city they live in, their job, their age, how others address them.
- The engine sometimes splits one person into two labels when people talk over each other. Merge two labels ONLY when everything fits: same voice, same self-description, and they never answer each other. Two labels that name different cities or different jobs are two different people — in a focus group several young men can sound alike, so keep them apart unless the evidence is clear.
- Some people on the attendance list never speak (silent observers, technical staff, client-side listeners) and the host may appear twice after reconnecting. Fewer voices than names is expected.

Respond ONLY with a JSON object mapping every label to a canonical name, e.g. {{"Hablante 1": "Josefina", "Hablante 2": "Lucía"}}. Map a label to itself only as a last resort, when you genuinely cannot tell who it is — a label left generic means its quotes end up unattributed in the client report.

=== TRANSCRIPT (samples per speaker) ===
{samples_a}
{reference}"""


DEVICE_RE = re.compile(r"^(iphone|ipad|android|galaxy|moto|samsung|tecno|celular|usuario|user)\b"
                       r"[\s\-]*(de[l]?\s+)?", re.I)


def _nombre_limpio(nombre):
    """Red de seguridad sobre lo que devuelve el mapeo.

    Aunque el prompt lo pide, conviene no publicar 'iphone de oriana' ni
    'BELEN LOPEZ' en un documento que lee el cliente."""
    n = DEVICE_RE.sub("", str(nombre)).strip(" -_")
    n = re.sub(r"\s+", " ", n)
    if not n:
        return str(nombre)
    if n.isupper() or n.islower():
        n = " ".join(p.capitalize() for p in n.split())
    return n


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


GENERIC_RE = re.compile(r"^Hablante \d+$")


def hablantes_sin_nombre(blocks):
    """Etiquetas que quedaron genéricas, con cuántas intervenciones tiene cada una.

    Si el transcriptor detecta más voces que participantes hay en la sala, alguna
    queda sin nombre y sus citas salen sin atribuir. Conviene saberlo en el
    momento y no al leer el reporte."""
    conteo = {}
    for b in blocks:
        nombre = str((b.get("speaker") or {}).get("name", ""))
        if GENERIC_RE.match(nombre):
            conteo[nombre] = conteo.get(nombre, 0) + 1
    return sorted(conteo.items(), key=lambda kv: -kv[1])


SECCIONES_DE_NOMBRES = ("NOMBRES CANÓNICOS", "NOMBRES CANONICOS",
                        "NO SON PARTICIPANTES", "PARTICIPANTES DE ESTE GRUPO",
                        "EN LA SALA")


def _brief_para_mapeo(brief, limite=7000, por_seccion=2600):
    """La parte del brief que le sirve al mapeo: quién es quién.

    El brief entero pesa 20 mil caracteres y arranca con objetivos y marco
    metodológico. Mandar el principio era mandarle justo lo que no necesita: la
    tabla de nombres vive al final. Se arman los pedazos por sección, en orden
    de utilidad, hasta llenar el cupo."""
    if not brief:
        return ""
    partes = []
    for clave in SECCIONES_DE_NOMBRES:
        i = brief.find(clave)
        if i >= 0:
            partes.append(brief[i:i + por_seccion])
    texto = "\n\n".join(partes) if partes else brief
    return texto[:limite]


def map_speaker_names(blocks, readai_blocks, brief="", roster=None):
    """Renombra 'Hablante N' a los nombres reales, usando la transcripción
    nombrada de Read.ai y/o el brief del equipo de investigación.

    Si algo falla, devuelve los bloques con las etiquetas genéricas."""
    if not readai_blocks and not brief and not roster:
        return blocks
    try:
        import anthropic
        from config import TRANSLATION_MODEL

        samples_a = _samples_by_speaker(blocks)
        fmt = lambda d: "\n".join(f"{k}:\n" + "\n".join(f"  {u}" for u in v)
                                  for k, v in d.items())
        reference = ""
        if readai_blocks:
            samples_b = _samples_by_speaker(readai_blocks)
            reference += ("\n=== SAME MEETING, transcribed by another tool that knows "
                          "the participants' names (samples per speaker) ===\n" + fmt(samples_b))
        if roster:
            reference += (
                "\n=== ZOOM ATTENDANCE LIST — who was actually in the room ===\n"
                + ", ".join(roster) +
                "\nThis list comes from Zoom itself and is ground truth for WHO was present "
                "and under WHAT name. It overrides the names in the research team notes when "
                "they disagree: people are often recruited under one name and join under "
                "another (a middle name, a nickname, a full legal name). Match by profile — "
                "city, occupation, age — and use the name from THIS list.\n"
                "Two caveats: some people on this list never speak (silent observers, "
                "technical staff, client-side listeners), so expect fewer voices than names; "
                "and the host may appear twice if they reconnected.")
        if brief:
            reference += ("\n=== RESEARCH TEAM NOTES (who is who — the naming standard) ===\n"
                          + _brief_para_mapeo(brief))
        prompt = MAPPING_PROMPT.format(
            labels=", ".join(samples_a.keys()),
            samples_a=fmt(samples_a),
            reference=reference,
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
        mapping = {k: _nombre_limpio(v) for k, v in mapping.items()}
        print(f"🪪 Nombres finales: {sorted(set(mapping.values()))}")
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


# ── Correcciones de nombre declaradas en el brief ─────────────────────────────

ALIAS_SECCION = "CORRECCIONES DE NOMBRE"
ALIAS_LINEA_RE = re.compile(r"^\s*(.+?)\s*(?:->|→|=)\s*(.+?)\s*$")


def _alias_del_brief(brief):
    """Lee la sección CORRECCIONES DE NOMBRE del brief: {como_sale: como_va}.

    Es la red para cuando el nombre del Zoom no es el de la persona (tiles
    cruzados, la moderadora entrando desde la cuenta de otro). El mapeo de
    hablantes trata la lista de Zoom como verdad, así que si Zoom miente hace
    falta decírselo a mano."""
    if not brief:
        return {}
    i = brief.find(ALIAS_SECCION)
    if i < 0:
        return {}
    alias = {}
    for linea in brief[i + len(ALIAS_SECCION):].split("\n"):
        if not linea.strip():
            continue
        if linea.strip().isupper() and "->" not in linea and "=" not in linea:
            break  # empezó la sección siguiente
        m = ALIAS_LINEA_RE.match(linea)
        if m and m.group(1) and m.group(2):
            alias[m.group(1).strip()] = m.group(2).strip()
    return alias


def aplicar_correcciones_nombre(blocks, brief=""):
    """Renombra hablantes según CORRECCIONES DE NOMBRE. Devuelve lo aplicado."""
    alias = _alias_del_brief(brief)
    if not alias:
        return blocks, {}
    aplicados = {}
    for b in blocks:
        spk = b.get("speaker") or {}
        nombre = str(spk.get("name", ""))
        if nombre in alias:
            spk["name"] = alias[nombre]
            aplicados[nombre] = alias[nombre]
    if aplicados:
        print(f"🪪 Correcciones de nombre del brief: {aplicados}")
    return blocks, aplicados


# ── Recorte de la recepción previa a la apertura ──────────────────────────────

# La apertura de la moderadora siempre trae el encuadre: bienvenida, "no hay
# respuestas correctas ni incorrectas", grabación, confidencialidad. Eso marca
# dónde empieza el grupo; todo lo anterior es sala de espera (chequeos de audio,
# saludos de la anfitriona, gente entrando).
APERTURA_RE = re.compile(
    r"respuestas?\s+(?:correctas|incorrectas)"
    r"|(?:correct|right)\s+or\s+(?:incorrect|wrong)\s+answers"
    r"|voy a ser (?:la|el) moderador"
    r"|(?:i'm|i am) going to be the moderator"
    r"|vamos a (?:arrancar|empezar|comenzar) con,? ?(?:la|con la) conversación",
    re.I)

APERTURA_PROMPT = """Below are the first blocks of a focus-group transcript (Spanish), numbered.

The recording starts before the group does: audio checks, the host letting people in, greetings, technical problems. Then the MODERATOR opens the session — she welcomes the group, explains the dynamic (there are no right or wrong answers), mentions the recording and confidentiality, and moves into the round of introductions.

Return the index of the block where that opening STARTS — the first block of the moderator's opening speech, not the greetings before it and not the round of names after it.

Respond ONLY with JSON: {{"indice": N}}

=== BLOCKS ===
{muestras}"""


def _apertura_por_llm(blocks, ventana):
    """Índice del bloque de apertura según el modelo. None si no se puede."""
    try:
        import anthropic
        from config import TRANSLATION_MODEL

        muestras = "\n".join(
            f"[{i}] {(b.get('speaker') or {}).get('name', '?')}: "
            f"{(b.get('words') or b.get('text') or '')[:260]}"
            for i, b in enumerate(blocks[:ventana]))
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=TRANSLATION_MODEL,
            max_tokens=200,
            output_config={"effort": "low"},
            messages=[{"role": "user",
                       "content": APERTURA_PROMPT.format(muestras=muestras)}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        i = int(json.loads(raw).get("indice", -1))
        return i if 0 <= i < ventana else None
    except Exception as e:
        print(f"⚠️  No se pudo detectar la apertura con el modelo: {e}")
        return None


def recortar_apertura(blocks, ventana=140):
    """Descarta todo lo anterior a la apertura de la moderadora.

    Devuelve (blocks_recortados, t0, descartados). t0 es el inicio real de la
    grabación: se lo pasa al generador de transcripciones para que los [MM:SS]
    sigan siendo del reloj de la reunión y sirvan para buscar en el video.

    Si no encuentra la apertura no recorta nada — mejor un documento con sala
    de espera que uno que arranca en el medio de la charla."""
    starts = [int(b.get("start_time", 0) or 0) for b in blocks]
    t0 = min((s for s in starts if s > 0), default=0)
    if len(blocks) < 5:
        return blocks, t0, 0

    corte = next((i for i, b in enumerate(blocks[:ventana])
                  if APERTURA_RE.search(b.get("words") or b.get("text") or "")), None)
    if corte is None:
        corte = _apertura_por_llm(blocks, min(ventana, len(blocks)))
    if not corte:  # 0 o None: no hay nada que recortar
        if corte is None:
            print("⚠️  No se detectó la apertura — la transcripción sale entera")
        return blocks, t0, 0

    primero = (blocks[corte].get("words") or blocks[corte].get("text") or "")[:80]
    print(f"✂️  Recepción recortada: {corte} bloques. Arranca en: {primero}...")
    return blocks[corte:], t0, corte
