import os
import json
import base64

from notifier import notify_error

ANALYSIS_MODEL = "claude-opus-5"


def _brief_section(brief):
    if not brief:
        return ""
    return f"""
CONTEXTO DEL EQUIPO DE INVESTIGACIÓN (objetivos, participantes, guía de pautas — ancla todo el análisis en esto; usá los nombres y datos de participantes de acá como referencia canónica):
{brief}
"""


def _glossary_line():
    from config import QUALBOT_GLOSSARY
    if not QUALBOT_GLOSSARY:
        return ""
    return ("\nNOMBRES/TÉRMINOS CANÓNICOS (la transcripción puede traerlos mal "
            f"oídos; usá siempre estas grafías): {QUALBOT_GLOSSARY}")


def _run_analysis(client, content, max_tokens, context=""):
    """Llama al modelo con streaming y devuelve el dict del análisis.

    En claude-opus-5 el thinking viene activado por defecto y consume parte de
    max_tokens, por eso el headroom es mayor que el largo esperado del JSON."""
    import time
    t_start = time.time()
    with client.messages.stream(
        model=ANALYSIS_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        # Señal de vida cada 60s: sin esto el paso es mudo por muchos minutos
        # y no se puede distinguir "sigue pensando" de "se colgó"
        last_beat = t_start
        for _ in stream:
            now = time.time()
            if now - last_beat >= 60:
                print(f"   🧠 análisis en curso... {int(now - t_start)}s")
                last_beat = now
        response = stream.get_final_message()
    print(f"   🧠 análisis completado en {int(time.time() - t_start)}s")

    if response.stop_reason == "refusal":
        notify_error(f"analysis refusal / {context}",
                     f"stop_reason=refusal, stop_details={response.stop_details}")
        raise RuntimeError(f"El modelo rechazó el análisis: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        # JSON truncado a mitad de camino: abortar en vez de subir un PDF roto
        notify_error(f"analysis truncado / {context}",
                     f"stop_reason=max_tokens con max_tokens={max_tokens}")
        raise RuntimeError(f"Análisis truncado en max_tokens={max_tokens}")

    raw = "".join(b.text for b in response.content if b.type == "text")
    return _parse_json(raw, context=context)


def analyze_transcript(title, speakers, blocks, summary, topics, brief=""):
    """Análisis solo de texto — se usa cuando no hay video disponible"""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    transcript_text = _format_transcript(blocks)
    speakers_list   = ", ".join(speakers) if speakers else "No identificados"
    topics_list     = ", ".join(topics)   if topics   else "No identificados"

    prompt = _build_text_prompt(title, speakers_list, topics_list, summary,
                                transcript_text, brief=brief)

    return _run_analysis(client, prompt, max_tokens=64000, context=title)


def analyze_integrated(title, speakers, blocks, summary, topics, frames, brief=""):
    """Análisis integrado texto + video — un solo llamado a Claude con todo"""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    transcript_text = _format_transcript(blocks)
    speakers_list   = ", ".join(speakers) if speakers else "No identificados"
    topics_list     = ", ".join(topics)   if topics   else "No identificados"

    print(f"🧠 Análisis integrado: {len(frames)} frames + transcripción → {ANALYSIS_MODEL}")

    content = []

    # Prompt principal
    content.append({
        "type": "text",
        "text": f"""Sos un analista senior especializado en investigación cualitativa de mercado, lenguaje no verbal y comportamiento del consumidor. Tenés más de 15 años de experiencia analizando focus groups combinando análisis del discurso, psicología social y semiótica visual.

SESIÓN: {title}
PARTICIPANTES: {speakers_list}
TEMAS: {topics_list}
RESUMEN READ.AI: {summary}{_glossary_line()}{_brief_section(brief)}

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

Sé específico. Citá momentos reales. Cruzá siempre lo verbal con lo visual cuando tengas ambos. Los hallazgos más valiosos son los que solo se pueden ver combinando texto y cara.

REGLAS DE CALIDAD (obligatorias):
1. Cada hallazgo se desarrolla UNA sola vez, en la sección que mejor le corresponde. Las demás secciones no lo repiten — a lo sumo lo referencian en una frase. Un reporte que repite el mismo hallazgo en varias secciones es un mal reporte.
2. Los frames son muestras espaciadas (~80 segundos entre uno y otro): nunca afirmes que un gesto coincide "exactamente" con una frase. Usá "cerca de [MM:SS]" y presentá la inferencia texto-video como hipótesis, no como certeza.
3. Toda cita textual debe copiarse LITERAL de la transcripción, con el hablante EXACTO del bloque del que la tomaste y el timestamp de ese bloque. Nunca atribuyas una cita a otro participante ni ajustes el timestamp de memoria.
4. No inventes especificidad: si la transcripción no dice una cifra o un dato, no lo agregues en tu interpretación."""
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

    return _run_analysis(client, content, max_tokens=64000, context=title)


def _format_transcript(blocks):
    # Read.ai manda start_time como época Unix en ms — llevar a tiempo relativo
    # para que los [MM:SS] del texto se puedan cruzar con los frames del video
    starts = [int(b.get("start_time", 0) or 0) for b in blocks]
    t0 = min((s for s in starts if s > 0), default=0)

    text = ""
    for block, start in zip(blocks, starts):
        speaker = block.get("speaker", {}).get("name", "?")
        words   = block.get("words", "")
        rel     = max(0, start - t0)
        mins    = int(rel // 60000)
        secs    = int((rel % 60000) // 1000)
        text   += f"[{mins:02d}:{secs:02d}] {speaker}: {words}\n"
    return text


def _build_text_prompt(title, speakers_list, topics_list, summary, transcript_text, brief=""):
    return f"""Sos un analista senior especializado en investigación cualitativa de mercado y comportamiento del consumidor. Tenés más de 15 años de experiencia conduciendo y analizando focus groups para marcas líderes.

SESIÓN: {title}
PARTICIPANTES: {speakers_list}
TEMAS: {topics_list}
RESUMEN READ.AI: {summary}{_glossary_line()}{_brief_section(brief)}

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
    "palabras_clave_positivas": ["palabra1", "palabra2"],
    "palabras_clave_negativas": ["palabra1", "palabra2"],
    "metaforas_usadas": [
      {{"metafora": "frase metafórica usada textualmente", "quien": "nombre del participante", "interpretacion": "qué revela sobre su postura o emoción"}}
    ],
    "eufemismos_detectados": [
      {{"lo_que_dijeron": "frase suavizada", "lo_que_probablemente_quisieron_decir": "interpretación directa", "quien": "nombre"}}
    ],
    "frases_mas_reveladoras": [
      {{"frase": "cita textual de la transcripción", "quien": "nombre", "timestamp": "MM:SS", "por_que_importa": "análisis de por qué esta frase es significativa"}}
    ]
  }},

  "lo_no_dicho": {{
    "temas_evitados": [
      {{"tema": "descripción del tema que se evitó", "evidencia": "cómo se nota en la transcripción (cambios de tema, respuestas vagas)", "posible_razon": "hipótesis sobre por qué lo evitaron"}}
    ],
    "silencios_significativos": [
      {{"timestamp": "MM:SS", "contexto": "ante qué pregunta o comentario se produjo el silencio", "interpretacion": "qué puede significar ese silencio"}}
    ],
    "senales_no_verbales_ignoradas": []
  }},

  "contradicciones": [
    {{
      "participante": "nombre",
      "dijo_primero": "cita textual",
      "dijo_despues": "cita contradictoria",
      "timestamp_1": "MM:SS",
      "timestamp_2": "MM:SS",
      "mostro_visualmente": "",
      "interpretacion": "qué revela esta contradicción sobre su postura real"
    }}
  ],
  "temas_con_carga_emocional": [
    {{
      "tema": "nombre del tema",
      "carga": "Positiva / Negativa / Ambivalente",
      "intensidad": "Baja / Media / Alta",
      "reaccion_verbal": "cómo se expresó en palabras",
      "reaccion_visual": "",
      "coherencia": "si las palabras fueron consistentes entre participantes",
      "implicancia_para_marca": "qué significa para la investigación"
    }}
  ],
  "insights_investigacion": [
    {{
      "insight": "hallazgo claro y accionable",
      "evidencia_verbal": "qué en la transcripción lo sostiene",
      "evidencia_visual": "",
      "nivel_confianza": "Alto / Medio / Requiere validación",
      "implicancia": "qué significa para la marca o investigación"
    }}
  ],
  "hipotesis_no_confirmadas": [
    {{
      "hipotesis": "algo que parece cierto pero necesita más investigación",
      "indicios": "qué sugiere esto en la transcripción",
      "como_validar": "qué metodología podría confirmarlo"
    }}
  ],
  "recomendaciones": [
    {{
      "recomendacion": "acción concreta y específica",
      "prioridad": "Alta / Media / Baja",
      "justificacion": "por qué emerge de los datos"
    }}
  ],
  "proximos_pasos_investigacion": ["pregunta o área que quedó abierta y merece exploración futura"],
  "nota_metodologica": "observaciones sobre la calidad de los datos, sesgos detectados, limitaciones del análisis"
}}

REGLAS DE CALIDAD (obligatorias):
1. Cada hallazgo se desarrolla UNA sola vez, en la sección que mejor le corresponde. Las demás secciones no lo repiten — a lo sumo lo referencian en una frase.
2. Toda cita textual debe copiarse LITERAL de la transcripción, con el hablante EXACTO del bloque del que la tomaste y el timestamp de ese bloque. Nunca atribuyas una cita a otro participante ni ajustes el timestamp de memoria.
3. No inventes especificidad: si la transcripción no dice una cifra o un dato, no lo agregues en tu interpretación."""


def _parse_json(raw, context=""):
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # El fallback degrada el reporte a casi vacío: avisar en vez de fallar mudo
        notify_error(f"JSON malformado del análisis / {context}",
                     f"{e} — primeros 300 chars: {raw[:300]}")
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
