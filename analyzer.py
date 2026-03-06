

import os
import json
import base64


def analyze_transcript(title, speakers, blocks, summary, topics):
    """Análisis solo de texto — se usa cuando no hay video disponible"""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    transcript_text = _format_transcript(blocks)
    speakers_list   = ", ".join(speakers) if speakers else "No identificados"
    topics_list     = ", ".join(topics)   if topics   else "No identificados"

    prompt = _build_text_prompt(title, speakers_list, topics_list, summary, transcript_text)

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    return _parse_json(response.content[0].text)


def analyze_integrated(title, speakers, blocks, summary, topics, frames):
    """Análisis integrado texto + video — un solo llamado a Claude con todo"""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    transcript_text = _format_transcript(blocks)
    speakers_list   = ", ".join(speakers) if speakers else "No identificados"
    topics_list     = ", ".join(topics)   if topics   else "No identificados"

    print(f"🧠 Análisis integrado: {len(frames)} frames + transcripción → Claude Opus")

    content = []

    # Prompt principal
    content.append({
        "type": "text",
        "text": f"""Sos un analista senior especializado en investigación cualitativa de mercado, lenguaje no verbal y comportamiento del consumidor. Tenés más de 15 años de experiencia analizando focus groups combinando análisis del discurso, psicología social y semiótica visual.

SESIÓN: {title}
PARTICIPANTES: {speakers_list}
TEMAS: {topics_list}
RESUMEN READ.AI: {summary}

TRANSCRIPCIÓN COMPLETA:
{transcript_text}

A continuación te mando {len(frames)} frames del video con sus timestamps. Tu tarea es hacer un análisis PROFUNDO E INTEGRADO que cruce lo que se dijo con lo que se vio. Cuando detectes que en un momento específico alguien dijo X pero su cara o cuerpo mostraba Y, ese es el hallazgo más valioso.

Respondé ÚNICAMENTE con un JSON válido con esta estructura:

{{
  "resumen_ejecutivo": "4-5 oraciones que capturen la esencia de la sesión integrando texto y video",
  "emocion_general_sesion": "una palabra",
  "intensidad_emocional": "Baja / Media / Alta / Muy Alta",
  "emocion_dominante_visual": "emoción más vista en el video",

  "temperatura_grupal": {{
    "inicio": "clima al inicio",
    "desarrollo": "cómo evolucionó",
    "cierre": "cómo terminó",
    "arco_narrativo": "el viaje emocional de inicio a fin"
  }},

  "participantes": [
    {{
      "nombre": "nombre",
      "perfil_psicologico": "personalidad y rol en el grupo (2-3 oraciones)",
      "emocion_predominante": "emoción principal",
      "emociones_secundarias": ["emoción1", "emoción2"],
      "nivel_participacion": "Bajo / Medio / Alto / Dominante",
      "estilo_comunicacional": "cómo se expresa, si usa rodeos, si es directo",
      "expresion_visual": "descripción de cómo se vio visualmente a esta persona a lo largo de la sesión",
      "momento_mas_revelador": "el momento donde más se reveló su postura real",
      "postura_real_vs_declarada": "si hay diferencia entre lo que dijo y lo que parece pensar"
    }}
  ],

  "momentos_criticos_integrados": [
    {{
      "timestamp": "MM:SS",
      "tipo": "Tensión / Acuerdo / Insight / Disonancia / Revelación / Presión social / Momento de verdad",
      "descripcion_verbal": "qué se estaba diciendo",
      "descripcion_visual": "qué se vio en el video en ese momento (si el frame está disponible)",
      "disonancia": "si el cuerpo contradijo las palabras, describir exactamente cómo",
      "importancia_investigativa": "por qué este momento importa"
    }}
  ],

  "dinamicas_de_poder": {{
    "lider_opinion": "quién y por qué",
    "seguidor_principal": "quién se alinea",
    "voz_disidente": "quién desafía",
    "silenciado": "quién fue ignorado o se autocensuró",
    "mapa_de_influencia": "cómo fluye la influencia",
    "momentos_de_presion_social": [
      {{
        "timestamp": "MM:SS",
        "descripcion": "qué pasó",
        "quien_presiono": "nombre",
        "quien_cedio": "nombre"
      }}
    ]
  }},

  "analisis_del_lenguaje": {{
    "palabras_clave_positivas": ["palabra1"],
    "palabras_clave_negativas": ["palabra1"],
    "metaforas_usadas": [
      {{"metafora": "la frase", "quien": "nombre", "interpretacion": "qué revela"}}
    ],
    "eufemismos_detectados": [
      {{"lo_que_dijeron": "frase", "lo_que_probablemente_quisieron_decir": "interpretación", "quien": "nombre"}}
    ],
    "frases_mas_reveladoras": [
      {{"frase": "cita textual", "quien": "nombre", "timestamp": "MM:SS", "por_que_importa": "análisis"}}
    ]
  }},

  "lo_no_dicho": {{
    "temas_evitados": [
      {{"tema": "descripción", "evidencia": "cómo se nota", "posible_razon": "hipótesis"}}
    ],
    "silencios_significativos": [
      {{"timestamp": "MM:SS", "contexto": "ante qué", "interpretacion": "qué significa"}}
    ],
    "senales_no_verbales_ignoradas": [
      {{"timestamp": "MM:SS", "lo_que_mostro_el_cuerpo": "descripción visual", "lo_que_se_decia": "contexto verbal", "interpretacion": "qué revela esta discrepancia"}}
    ]
  }},

  "contradicciones": [
    {{
      "participante": "nombre",
      "dijo_primero": "cita",
      "dijo_despues": "cita contradictoria",
      "timestamp_1": "MM:SS",
      "timestamp_2": "MM:SS",
      "mostro_visualmente": "si el video refuerza o contradice alguna de las dos posturas",
      "interpretacion": "análisis"
    }}
  ],

  "temas_con_carga_emocional": [
    {{
      "tema": "nombre",
      "carga": "Positiva / Negativa / Ambivalente",
      "intensidad": "Baja / Media / Alta",
      "reaccion_verbal": "cómo se expresó en palabras",
      "reaccion_visual": "cómo se expresó en el cuerpo/cara",
      "coherencia": "si lo verbal y visual coincidieron o no",
      "implicancia_para_marca": "qué significa para la investigación"
    }}
  ],

  "insights_investigacion": [
    {{
      "insight": "hallazgo claro",
      "evidencia_verbal": "qué en la transcripción lo sostiene",
      "evidencia_visual": "qué en el video lo sostiene o contradice",
      "nivel_confianza": "Alto / Medio / Requiere validación",
      "implicancia": "qué significa para la marca o investigación"
    }}
  ],

  "hipotesis_no_confirmadas": [
    {{
      "hipotesis": "algo que parece cierto pero necesita más investigación",
      "indicios": "qué sugiere esto",
      "como_validar": "qué metodología podría confirmarlo"
    }}
  ],

  "recomendaciones": [
    {{
      "recomendacion": "acción concreta",
      "prioridad": "Alta / Media / Baja",
      "justificacion": "por qué emerge de los datos"
    }}
  ],

  "proximos_pasos_investigacion": ["pregunta o área que quedó abierta"],

  "nota_metodologica": "observaciones sobre calidad de datos, sesgos detectados, limitaciones"
}}

Sé específico. Citá momentos reales. Cruzá siempre lo verbal con lo visual cuando tengas ambos. Los hallazgos más valiosos son los que solo se pueden ver combinando texto y cara."""
    })

    # Agregar frames
    for frame in frames:
        content.append({"type": "text", "text": f"Frame [{frame['timestamp_fmt']}]:"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame["b64"]
            }
        })

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=10000,
        messages=[{"role": "user", "content": content}]
    )

    return _parse_json(response.content[0].text)


def _format_transcript(blocks):
    text = ""
    for block in blocks:
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "")
        start   = block.get("start_time", 0)
        mins    = int(start // 60000)
        secs    = int((start % 60000) // 1000)
        text   += f"[{mins:02d}:{secs:02d}] {speaker}: {words}\n"
    return text


def _build_text_prompt(title, speakers_list, topics_list, summary, transcript_text):
    return f"""Sos un analista senior especializado en investigación cualitativa de mercado y comportamiento del consumidor. Tenés más de 15 años de experiencia conduciendo y analizando focus groups para marcas líderes.

SESIÓN: {title}
PARTICIPANTES: {speakers_list}
TEMAS: {topics_list}
RESUMEN READ.AI: {summary}

TRANSCRIPCIÓN COMPLETA:
{transcript_text}

Realizá un análisis EXHAUSTIVO y PROFUNDO. Respondé ÚNICAMENTE con un JSON válido:

{{
  "resumen_ejecutivo": "4-5 oraciones que capturen la esencia de la sesión",
  "emocion_general_sesion": "una palabra",
  "intensidad_emocional": "Baja / Media / Alta / Muy Alta",
  "emocion_dominante_visual": "",

  "temperatura_grupal": {{
    "inicio": "clima al inicio",
    "desarrollo": "cómo evolucionó",
    "cierre": "cómo terminó",
    "arco_narrativo": "el viaje emocional"
  }},

  "participantes": [
    {{
      "nombre": "nombre",
      "perfil_psicologico": "2-3 oraciones",
      "emocion_predominante": "emoción",
      "emociones_secundarias": ["emoción1"],
      "nivel_participacion": "Bajo / Medio / Alto / Dominante",
      "estilo_comunicacional": "descripción",
      "expresion_visual": "",
      "momento_mas_revelador": "descripción",
      "postura_real_vs_declarada": "análisis"
    }}
  ],

  "momentos_criticos_integrados": [
    {{
      "timestamp": "MM:SS",
      "tipo": "tipo",
      "descripcion_verbal": "qué se dijo",
      "descripcion_visual": "",
      "disonancia": "",
      "importancia_investigativa": "por qué importa"
    }}
  ],

  "dinamicas_de_poder": {{
    "lider_opinion": "quién y por qué",
    "seguidor_principal": "quién",
    "voz_disidente": "quién",
    "silenciado": "quién",
    "mapa_de_influencia": "descripción",
    "momentos_de_presion_social": []
  }},

  "analisis_del_lenguaje": {{
    "palabras_clave_positivas": [],
    "palabras_clave_negativas": [],
    "metaforas_usadas": [],
    "eufemismos_detectados": [],
    "frases_mas_reveladoras": []
  }},

  "lo_no_dicho": {{
    "temas_evitados": [],
    "silencios_significativos": [],
    "senales_no_verbales_ignoradas": []
  }},

  "contradicciones": [],
  "temas_con_carga_emocional": [],
  "insights_investigacion": [],
  "hipotesis_no_confirmadas": [],
  "recomendaciones": [],
  "proximos_pasos_investigacion": [],
  "nota_metodologica": ""
}}"""


def _parse_json(raw):
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "resumen_ejecutivo": raw[:500],
            "emocion_general_sesion": "No determinado",
            "intensidad_emocional": "Media",
            "emocion_dominante_visual": "",
            "participantes": [],
            "momentos_criticos_integrados": [],
            "temas_con_carga_emocional": [],
            "insights_investigacion": [{"insight": raw, "evidencia_verbal": "", "evidencia_visual": "", "nivel_confianza": "Requiere validación", "implicancia": ""}],
            "recomendaciones": [],
            "dinamicas_de_poder": {},
            "analisis_del_lenguaje": {},
            "lo_no_dicho": {},
            "contradicciones": [],
            "hipotesis_no_confirmadas": [],
            "proximos_pasos_investigacion": [],
            "nota_metodologica": "",
            "temperatura_grupal": {}
        }
