import os
import json


def analyze_transcript(title, speakers, blocks, summary, topics):
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Preparar transcripción formateada
    transcript_text = ""
    for block in blocks:
        speaker_name = block.get("speaker", {}).get("name", "Desconocido")
        words = block.get("words", "")
        start = block.get("start_time", 0)
        mins = int(start // 60000)
        secs = int((start % 60000) // 1000)
        transcript_text += f"[{mins:02d}:{secs:02d}] {speaker_name}: {words}\n"

    speakers_list = ", ".join(speakers) if speakers else "No identificados"
    topics_list   = ", ".join(topics)   if topics   else "No identificados"

    prompt = f"""Eres un analista senior especializado en investigación cualitativa de mercado y comportamiento del consumidor. Tenés más de 15 años de experiencia conduciendo y analizando focus groups para marcas líderes. Tu análisis combina psicología social, análisis del discurso y semiótica.

SESIÓN A ANALIZAR:
- Título: {title}
- Participantes: {speakers_list}
- Temas abordados: {topics_list}
- Resumen automático: {summary}

TRANSCRIPCIÓN COMPLETA:
{transcript_text}

---

Realizá un análisis EXHAUSTIVO y PROFUNDO. No te conformes con lo obvio. Buscá lo que está debajo de la superficie. Tu análisis debe ser el equivalente a lo que haría un investigador senior después de 4 horas revisando el material.

Respondé ÚNICAMENTE con un JSON válido con esta estructura exacta:

{{
  "resumen_ejecutivo": "Síntesis de 4-5 oraciones que capture la esencia de la sesión, el estado emocional general del grupo y el hallazgo más importante que un cliente debería conocer",

  "emocion_general_sesion": "una palabra",
  "intensidad_emocional": "Baja / Media / Alta / Muy Alta",

  "temperatura_grupal": {{
    "inicio": "descripción del clima al inicio",
    "desarrollo": "cómo evolucionó durante la sesión",
    "cierre": "cómo terminó el grupo emocionalmente",
    "arco_narrativo": "descripción del viaje emocional del grupo de inicio a fin"
  }},

  "participantes": [
    {{
      "nombre": "nombre",
      "perfil_psicologico": "descripción de su personalidad y rol en el grupo (2-3 oraciones)",
      "emocion_predominante": "emoción principal",
      "emociones_secundarias": ["emoción1", "emoción2"],
      "nivel_participacion": "Bajo / Medio / Alto / Dominante",
      "estilo_comunicacional": "descripción de cómo se expresa, si usa rodeos, si es directo, si busca consenso, etc.",
      "momento_mas_revelador": "el momento donde más se reveló su postura real y por qué",
      "postura_real_vs_declarada": "si hay diferencia entre lo que dijo y lo que parece pensar realmente"
    }}
  ],

  "dinamicas_de_poder": {{
    "lider_opinion": "quién y por qué",
    "seguidor_principal": "quién tiende a alinearse con el líder",
    "voz_disidente": "quién desafía al grupo o piensa diferente",
    "silenciado": "quién fue interrumpido, ignorado o se autocensuró",
    "mapa_de_influencia": "descripción de cómo fluye la influencia entre participantes",
    "momentos_de_presion_social": [
      {{
        "timestamp": "MM:SS",
        "descripcion": "qué pasó",
        "quien_presiono": "nombre",
        "quien_cedio": "nombre o 'el grupo'"
      }}
    ]
  }},

  "analisis_del_lenguaje": {{
    "palabras_clave_positivas": ["palabra1", "palabra2"],
    "palabras_clave_negativas": ["palabra1", "palabra2"],
    "metaforas_usadas": [
      {{
        "metafora": "la metáfora exacta",
        "quien": "nombre",
        "interpretacion": "qué revela sobre su percepción"
      }}
    ],
    "eufemismos_detectados": [
      {{
        "lo_que_dijeron": "frase exacta",
        "lo_que_probablemente_quisieron_decir": "interpretación",
        "quien": "nombre"
      }}
    ],
    "frases_mas_reveladoras": [
      {{
        "frase": "cita textual",
        "quien": "nombre",
        "timestamp": "MM:SS",
        "por_que_importa": "análisis de por qué esta frase es significativa"
      }}
    ],
    "patron_linguistico_grupal": "descripción de cómo habla el grupo en conjunto, vocabulario compartido, tono colectivo"
  }},

  "lo_no_dicho": {{
    "temas_evitados": [
      {{
        "tema": "descripción del tema",
        "evidencia": "cómo se nota que fue evitado",
        "posible_razon": "hipótesis de por qué no se habló"
      }}
    ],
    "preguntas_que_no_se_hicieron": ["pregunta que hubiera sido natural pero nadie hizo"],
    "silencios_significativos": [
      {{
        "timestamp": "MM:SS",
        "contexto": "ante qué pregunta o comentario",
        "interpretacion": "qué podría significar ese silencio"
      }}
    ],
    "cambios_de_tema_abruptos": [
      {{
        "timestamp": "MM:SS",
        "de_que_a_que": "descripción",
        "quien_cambio": "nombre",
        "interpretacion": "por qué podría haber cambiado el tema"
      }}
    ]
  }},

  "contradicciones": [
    {{
      "participante": "nombre o 'grupo'",
      "dijo_primero": "cita o paráfrasis",
      "dijo_despues": "cita o paráfrasis que contradice",
      "timestamp_1": "MM:SS",
      "timestamp_2": "MM:SS",
      "interpretacion": "qué puede explicar esta contradicción: presión social, reflexión genuina, ambivalencia, etc."
    }}
  ],

  "momentos_criticos": [
    {{
      "timestamp": "MM:SS",
      "tipo": "Tensión / Acuerdo / Insight / Quiebre / Revelación / Presión social / Momento de verdad",
      "descripcion": "qué pasó exactamente",
      "importancia_investigativa": "por qué este momento importa para la investigación"
    }}
  ],

  "temas_con_carga_emocional": [
    {{
      "tema": "nombre del tema",
      "carga": "Positiva / Negativa / Ambivalente / Compleja",
      "intensidad": "Baja / Media / Alta",
      "quienes_reaccionaron": ["nombre1", "nombre2"],
      "observacion": "análisis detallado de la reacción",
      "implicancia_para_marca": "qué significa esto para la investigación de mercado"
    }}
  ],

  "insights_investigacion": [
    {{
      "insight": "descripción clara del insight",
      "evidencia": "qué en la transcripción sostiene este insight",
      "nivel_confianza": "Alto / Medio / Requiere validación",
      "implicancia": "qué significa para la marca o producto"
    }}
  ],

  "hipotesis_no_confirmadas": [
    {{
      "hipotesis": "algo que parece cierto pero necesita más investigación",
      "indicios": "qué sugiere esta hipótesis",
      "como_validar": "qué pregunta o metodología podría confirmarlo"
    }}
  ],

  "recomendaciones": [
    {{
      "recomendacion": "acción concreta",
      "prioridad": "Alta / Media / Baja",
      "justificacion": "por qué esta recomendación emerge de los datos"
    }}
  ],

  "proximos_pasos_investigacion": [
    "pregunta o área que quedó abierta y merece seguimiento"
  ],

  "nota_metodologica": "observaciones sobre la calidad de los datos, sesgos detectados en la dinámica grupal, limitaciones del análisis"
}}

Sé específico, cita momentos reales de la transcripción, y no tengas miedo de hacer interpretaciones audaces siempre que las justifiques con evidencia del texto. Un buen análisis cualitativo va más allá de lo literal."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback si el JSON viene malformado
        return {
            "resumen_ejecutivo": raw[:500],
            "emocion_general_sesion": "No determinado",
            "intensidad_emocional": "Media",
            "participantes": [],
            "momentos_criticos": [],
            "temas_con_carga_emocional": [],
            "insights_investigacion": [{"insight": raw, "evidencia": "", "nivel_confianza": "Requiere validación", "implicancia": ""}],
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

