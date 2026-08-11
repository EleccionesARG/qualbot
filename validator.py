"""Verificación determinista de citas del análisis contra la transcripción.

El análisis a veces atribuye una cita al participante equivocado o corre el
timestamp. Este validador busca cada cita textual en los bloques de la
transcripción y, cuando encuentra un match confiable, corrige hablante y
timestamp. Lo que no encuentra lo reporta sin tocar.
"""
import re
import unicodedata
from difflib import SequenceMatcher

MATCH_OK = 0.75      # proporción de la cita que debe aparecer en un bloque
MATCH_DUDOSO = 0.55  # debajo de esto se reporta como "no encontrada"


def _norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", " ", s).strip()


def _prep_blocks(blocks):
    starts = [int(b.get("start_time", 0) or 0) for b in blocks]
    t0 = min((s for s in starts if s > 0), default=0)
    prepped = []
    for b, s in zip(blocks, starts):
        rel = max(0, s - t0)
        mins, secs = divmod(rel // 1000, 60)
        prepped.append({
            "speaker": b.get("speaker", {}).get("name", "?"),
            "mmss": f"{mins:02d}:{secs:02d}",
            "norm": _norm(b.get("words", "")),
        })
    return prepped


def _find_quote(qnorm, prepped):
    """Devuelve (bloque, score) del mejor match de la cita en la transcripción."""
    best, best_score = None, 0.0
    for p in prepped:
        if not p["norm"]:
            continue
        if qnorm in p["norm"]:
            return p, 1.0
        m = SequenceMatcher(None, qnorm, p["norm"], autojunk=False).find_longest_match(
            0, len(qnorm), 0, len(p["norm"]))
        score = m.size / max(1, len(qnorm))
        if score > best_score:
            best, best_score = p, score
    return best, best_score


def _locate(item, quote_key, prepped, correcciones, seccion):
    """Busca la cita; devuelve el bloque si el match es confiable, sino None."""
    if not isinstance(item, dict):
        return None
    quote = item.get(quote_key, "")
    qnorm = _norm(quote)
    if len(qnorm) < 12:  # citas muy cortas no se pueden verificar con confianza
        return None
    block, score = _find_quote(qnorm, prepped)
    if block is None or score < MATCH_DUDOSO:
        correcciones.append(f"[{seccion}] cita no encontrada en transcripción: «{quote[:60]}...»")
        return None
    return block if score >= MATCH_OK else None


def _fix_ts(item, ts_key, block, quote_key, correcciones, seccion):
    if not (ts_key and item.get(ts_key)):
        return
    try:
        ts = str(item[ts_key]).strip()
        if re.fullmatch(r"\d{1,3}:\d{2}", ts) and ts != block["mmss"]:
            t_m, t_s = map(int, ts.split(":"))
            b_m, b_s = map(int, block["mmss"].split(":"))
            if abs((t_m * 60 + t_s) - (b_m * 60 + b_s)) > 20:
                correcciones.append(
                    f"[{seccion}] timestamp de «{str(item.get(quote_key,''))[:40]}...» {ts} → {block['mmss']}")
                item[ts_key] = block["mmss"]
    except ValueError:
        pass


def _check(item, quote_key, who_key, ts_key, prepped, correcciones, seccion):
    block = _locate(item, quote_key, prepped, correcciones, seccion)
    if block is None:
        return
    who = item.get(who_key, "")
    if who and _norm(who) != _norm(block["speaker"]):
        correcciones.append(
            f"[{seccion}] «{str(item.get(quote_key,''))[:40]}...» atribuida a {who} → corregida a {block['speaker']}")
        item[who_key] = block["speaker"]
    _fix_ts(item, ts_key, block, quote_key, correcciones, seccion)


def _check_contradiccion(item, prepped, correcciones):
    """Una contradicción tiene UN participante y DOS citas: solo se corrige el
    nombre si ambas citas pertenecen al mismo hablante; si son de personas
    distintas, la contradicción es inválida y se reporta sin tocar."""
    b1 = _locate(item, "dijo_primero", prepped, correcciones, "contradicciones")
    b2 = _locate(item, "dijo_despues", prepped, correcciones, "contradicciones")
    if b1 is not None:
        _fix_ts(item, "timestamp_1", b1, "dijo_primero", correcciones, "contradicciones")
    if b2 is not None:
        _fix_ts(item, "timestamp_2", b2, "dijo_despues", correcciones, "contradicciones")
    if b1 is not None and b2 is not None:
        if _norm(b1["speaker"]) != _norm(b2["speaker"]):
            correcciones.append(
                "[contradicciones] ⚠️ INVÁLIDA: las citas son de hablantes distintos "
                f"({b1['speaker']} y {b2['speaker']}) — revisar a mano")
            return
        who = item.get("participante", "")
        if who and _norm(who) != _norm(b1["speaker"]):
            correcciones.append(
                f"[contradicciones] participante {who} → corregido a {b1['speaker']}")
            item["participante"] = b1["speaker"]


def verify_quotes(analysis, blocks):
    """Corrige atribuciones/timestamps de citas cuando la transcripción da un
    match confiable. Devuelve (analysis, lista de correcciones/avisos)."""
    correcciones = []
    if not blocks or not isinstance(analysis, dict):
        return analysis, correcciones
    prepped = _prep_blocks(blocks)

    lenguaje = analysis.get("analisis_del_lenguaje", {}) or {}
    for item in lenguaje.get("frases_mas_reveladoras", []) or []:
        _check(item, "frase", "quien", "timestamp", prepped, correcciones, "frases")
    for item in lenguaje.get("metaforas_usadas", []) or []:
        _check(item, "metafora", "quien", None, prepped, correcciones, "metáforas")
    for item in lenguaje.get("eufemismos_detectados", []) or []:
        _check(item, "lo_que_dijeron", "quien", None, prepped, correcciones, "eufemismos")
    for item in analysis.get("contradicciones", []) or []:
        if isinstance(item, dict):
            _check_contradiccion(item, prepped, correcciones)

    return analysis, correcciones
