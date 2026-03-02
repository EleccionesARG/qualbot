"""
analyzer.py
Usa Claude para analizar emociones, tensiones y patrones en la transcripción
"""

import os
import json
import anthropic

client = None

def analyze_transcript(title, speakers, blocks, summary, topics):
    """
    Envía la transcripción a Claude y obtiene análisis emocional profundo
    orientado a investigación cualitativa.
    """
def analyze_transcript(title, speakers, blocks, summary, topics):
    global client
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        
    # Formatear transcripción para Claude
    transcript_text = ""
    for block in blocks:
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "")
        start   = int(block.get("start_time", 0)) // 1000  # ms → segundos
        mins    = start // 60
        secs    = start % 60
        transcript_text += f"[{mins:02d}:{secs:02d}] {speaker}: {words}\n"

    prompt = f"""Eres un experto en investigación cualitativa y análisis emocional de grupos focales.

Analizá la siguiente transcripción de un focus group y devolvé un análisis en formato JSON.

TÍTULO: {title}
PARTICIPANTES: {', '.join(speakers) if speakers else 'No identificados'}
TEMAS DETECTADOS: {', '.join(topics) if topics else 'No detectados'}
RESUMEN: {summary}

TRANSCRIPCIÓN:
{transcript_text[:6000]}

Devolvé ÚNICAMENTE un JSON válido con esta estructura exacta (sin texto adicional):
{{
  "emocion_general_sesion": "una palabra: Positiva/Negativa/Mixta/Neutral",
  "intensidad_emocional": "Alta/Media/Baja",
  "resumen_ejecutivo": "2-3 oraciones resumiendo el tono emocional de la sesión",
  "participantes": [
    {{
      "nombre": "nombre del speaker",
      "perfil_emocional": "descripción breve de su actitud dominante",
      "emocion_predominante": "Alegría/Enojo/Tristeza/Sorpresa/Miedo/Disgusto/Neutral",
      "nivel_participacion": "Alto/Medio/Bajo",
      "momentos_clave": ["frase o momento relevante de este participante"]
    }}
  ],
  "momentos_criticos": [
    {{
      "timestamp": "MM:SS",
      "tipo": "Tension/Acuerdo/Sorpresa/Quiebre/Insight",
      "descripcion": "qué pasó en ese momento",
      "speakers_involucrados": ["nombres"]
    }}
  ],
  "temas_con_carga_emocional": [
    {{
      "tema": "nombre del tema",
      "carga": "Positiva/Negativa/Mixta",
      "intensidad": "Alta/Media/Baja",
      "observacion": "qué dijeron sobre este tema"
    }}
  ],
  "patrones_grupales": {{
    "nivel_consenso": "Alto/Medio/Bajo",
    "dinamica_grupal": "descripción de cómo interactuó el grupo",
    "lider_opinion": "nombre del participante más influyente o Ninguno",
    "temas_evitados": ["temas que el grupo evitó o no profundizó"]
  }},
  "insights_investigacion": [
    "insight 1 relevante para la investigación",
    "insight 2",
    "insight 3"
  ],
  "recomendaciones": [
    "recomendación metodológica o de producto basada en los hallazgos"
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Limpiar posibles backticks
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    analysis = json.loads(raw)
    print(f"  ✅ Análisis completado: {analysis.get('emocion_general_sesion')} / {analysis.get('intensidad_emocional')}")
    return analysis
