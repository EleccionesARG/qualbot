import os
import json

def analyze_transcript(title, speakers, blocks, summary, topics):
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    transcript_text = ""
    for block in blocks:
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "")
        start   = int(block.get("start_time", 0)) // 1000
        transcript_text += f"[{start//60:02d}:{start%60:02d}] {speaker}: {words}\n"

    prompt = f"""Eres un experto en investigación cualitativa.
Analizá esta transcripción de focus group y devolvé ÚNICAMENTE un JSON válido, sin texto adicional.

TÍTULO: {title}
PARTICIPANTES: {', '.join(speakers)}
TEMAS: {', '.join(topics)}
RESUMEN: {summary}
TRANSCRIPCIÓN:
{transcript_text[:6000]}

Estructura exacta del JSON:
{{
  "emocion_general_sesion": "Positiva/Negativa/Mixta/Neutral",
  "intensidad_emocional": "Alta/Media/Baja",
  "resumen_ejecutivo": "2-3 oraciones",
  "participantes": [
    {{
      "nombre": "...",
      "perfil_emocional": "...",
      "emocion_predominante": "Alegría/Enojo/Tristeza/Sorpresa/Miedo/Disgusto/Neutral",
      "nivel_participacion": "Alto/Medio/Bajo",
      "momentos_clave": ["..."]
    }}
  ],
  "momentos_criticos": [
    {{"timestamp": "MM:SS", "tipo": "Tension/Acuerdo/Sorpresa/Insight",
      "descripcion": "...", "speakers_involucrados": ["..."]}}
  ],
  "temas_con_carga_emocional": [
    {{"tema": "...", "carga": "Positiva/Negativa/Mixta",
      "intensidad": "Alta/Media/Baja", "observacion": "..."}}
  ],
  "patrones_grupales": {{
    "nivel_consenso": "Alto/Medio/Bajo",
    "dinamica_grupal": "...",
    "lider_opinion": "...",
    "temas_evitados": ["..."]
  }},
  "insights_investigacion": ["...", "...", "..."],
  "recomendaciones": ["..."]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
