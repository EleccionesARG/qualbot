"""Prueba local del modo inglés: traducción + PDFs, sin Zoom ni Drive.

Uso:
    python test_translation.py           # regresión ES + análisis EN + transcript completo
    python test_translation.py 20        # limita la transcripción a 20 bloques (barato)
    python test_translation.py --solo-es # solo el PDF ES con mock (no llama a la API)

Requiere ANTHROPIC_API_KEY (salvo --solo-es).
"""
import re
import sys

TRANSCRIPT_TXT = "/Users/jadaro/Downloads/Grupo 1 Transcripción.txt"


def parse_readai_txt(path):
    """Parsea el export de Read.ai ('M:SS - Hablante - Speaker N' + párrafos)
    al formato speaker_blocks que llega por webhook."""
    blocks, cur = [], None
    hdr = re.compile(r"^(\d+):(\d{2})(?::(\d{2}))? - (.+?)(?: - Speaker \d+)?\s*$")
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = hdr.match(line.strip())
            if m:
                if cur and cur["words"]:
                    blocks.append(cur)
                a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
                start_ms = ((a * 3600 + b * 60 + int(c)) if c else (a * 60 + b)) * 1000
                cur = {"speaker": {"name": m.group(4)}, "start_time": start_ms, "words": ""}
            elif cur is not None and line.strip():
                cur["words"] += (" " if cur["words"] else "") + line.strip()
    if cur and cur["words"]:
        blocks.append(cur)
    return blocks


MOCK_ANALYSIS = {
    "resumen_ejecutivo": "El grupo mostró un clima inicial de desconfianza que fue cediendo. Los participantes expresaron frustración con la situación económica pero optimismo moderado hacia adelante. Se detectaron tensiones entre los más jóvenes y los adultos del grupo.",
    "emocion_general_sesion": "Frustración",
    "intensidad_emocional": "Alta",
    "emocion_dominante_visual": "Escepticismo",
    "temperatura_grupal": {
        "inicio": "Frío, respuestas cortas y formales",
        "desarrollo": "Se fue soltando a partir del tema del trabajo",
        "cierre": "Cálido, con humor compartido",
        "arco_narrativo": "De la desconfianza a la complicidad grupal",
    },
    "participantes": [
        {
            "nombre": "Pedro",
            "perfil_psicologico": "Pragmático, desconfiado de los discursos políticos. Se posiciona como voz de la experiencia.",
            "emocion_predominante": "Escepticismo",
            "emociones_secundarias": ["cansancio", "ironía"],
            "nivel_participacion": "Alto",
            "estilo_comunicacional": "Directo, usa refranes y ejemplos cotidianos",
            "expresion_visual": "Brazos cruzados la mayor parte de la sesión",
            "momento_mas_revelador": "Cuando contó que su hijo se quiere ir del país",
            "postura_real_vs_declarada": "Dice estar 'esperanzado' pero su lenguaje corporal muestra resignación",
        },
        {
            "nombre": "Ana",
            "perfil_psicologico": "Conciliadora, busca consenso. Evita el conflicto directo.",
            "emocion_predominante": "Ansiedad",
            "emociones_secundarias": ["esperanza"],
            "nivel_participacion": "Medio",
            "estilo_comunicacional": "Usa rodeos, suaviza sus opiniones con 'me parece'",
            "expresion_visual": "Sonrisa nerviosa en temas de plata",
            "momento_mas_revelador": "Su silencio cuando se habló de despidos",
            "postura_real_vs_declarada": "Coherente en general",
        },
    ],
    "momentos_criticos_integrados": [
        {
            "timestamp": "12:45",
            "tipo": "Disonancia",
            "descripcion_verbal": "Pedro dice que 'está todo bien' con su laburo",
            "descripcion_visual": "Baja la mirada y se toca el cuello",
            "disonancia": "El cuerpo contradice el discurso optimista",
            "importancia_investigativa": "Sugiere deseabilidad social en las respuestas sobre empleo",
        }
    ],
    "dinamicas_de_poder": {
        "lider_opinion": "Pedro, por antigüedad y tono asertivo",
        "seguidor_principal": "Ana, valida lo que dice Pedro",
        "voz_disidente": "Mirko, desafía el pesimismo del grupo",
        "silenciado": "Laura, intentó hablar dos veces y fue interrumpida",
        "mapa_de_influencia": "Pedro marca el tono, los jóvenes se agrupan en respuesta",
        "momentos_de_presion_social": [
            {"timestamp": "23:10", "descripcion": "El grupo se ríe cuando Mirko defiende las apps de inversión", "quien_presiono": "Pedro", "quien_cedio": "Mirko"}
        ],
    },
    "analisis_del_lenguaje": {
        "palabras_clave_positivas": ["laburo", "futuro", "cambio"],
        "palabras_clave_negativas": ["quilombo", "verso", "afano"],
        "metaforas_usadas": [
            {"metafora": "Estamos remando en dulce de leche", "quien": "Pedro", "interpretacion": "Esfuerzo percibido como inútil frente al contexto"}
        ],
        "eufemismos_detectados": [
            {"lo_que_dijeron": "Está complicado", "lo_que_probablemente_quisieron_decir": "No llego a fin de mes", "quien": "Ana"}
        ],
        "frases_mas_reveladoras": [
            {"frase": "Yo ya no le creo a nadie, pero a este por ahora le doy una chance", "quien": "Pedro", "timestamp": "31:02", "por_que_importa": "Confianza condicional, no adhesión ideológica"}
        ],
    },
    "lo_no_dicho": {
        "temas_evitados": [
            {"tema": "Endeudamiento personal", "evidencia": "Cambios de tema abruptos al hablar de tarjetas", "posible_razon": "Vergüenza frente al grupo"}
        ],
        "silencios_significativos": [
            {"timestamp": "18:30", "contexto": "Pregunta sobre despidos en el rubro", "interpretacion": "Miedo compartido que nadie quiere verbalizar"}
        ],
        "senales_no_verbales_ignoradas": [
            {"timestamp": "40:12", "lo_que_mostro_el_cuerpo": "Ana negaba con la cabeza", "lo_que_se_decia": "Consenso verbal sobre el optimismo", "interpretacion": "Disenso silencioso no captado por el moderador"}
        ],
    },
    "contradicciones": [
        {
            "participante": "Mirko",
            "dijo_primero": "A mí la política no me interesa nada",
            "dijo_despues": "Milité dos años en la facultad",
            "timestamp_1": "05:20",
            "timestamp_2": "44:50",
            "mostro_visualmente": "Se entusiasma visiblemente al hablar de militancia",
            "interpretacion": "Desencanto reciente más que apatía estructural",
        }
    ],
    "temas_con_carga_emocional": [
        {
            "tema": "Inflación",
            "carga": "Negativa",
            "intensidad": "Alta",
            "reaccion_verbal": "Anécdotas en cascada, se interrumpen entre sí",
            "reaccion_visual": "Gestos amplios, tono elevado",
            "coherencia": "Total coherencia verbal-visual",
            "implicancia_para_marca": "Cualquier mensaje debe reconocer el bolsillo primero",
        }
    ],
    "insights_investigacion": [
        {
            "insight": "La confianza es condicional y de corto plazo: se otorga 'una chance', no adhesión",
            "evidencia_verbal": "Frase de Pedro en 31:02",
            "evidencia_visual": "Lenguaje corporal defensivo durante temas políticos",
            "nivel_confianza": "Alto",
            "implicancia": "Comunicar hitos de corto plazo, no promesas a 10 años",
        }
    ],
    "hipotesis_no_confirmadas": [
        {
            "hipotesis": "El humor funciona como válvula de escape frente a la angustia económica",
            "indicios": "Los picos de risa siguen siempre a los momentos más tensos",
            "como_validar": "Sesiones individuales en profundidad",
        }
    ],
    "recomendaciones": [
        {"recomendacion": "Testear mensajes que reconozcan el esfuerzo cotidiano", "prioridad": "Alta", "justificacion": "El grupo rechaza el triunfalismo"},
        {"recomendacion": "Explorar el segmento joven por separado", "prioridad": "Media", "justificacion": "Dinámica intergeneracional sesgó sus respuestas"},
    ],
    "proximos_pasos_investigacion": ["¿La confianza condicional se sostiene ante una crisis puntual?"],
    "nota_metodologica": "Grupo con leve sobrerrepresentación de mayores de 40. La presencia de un participante dominante pudo inhibir voces disidentes.",
}


if __name__ == "__main__":
    from report_generator import generate_pdf_report, generate_transcript_document

    # 1. Regresión ES con mock — no llama a la API
    p = generate_pdf_report("TEST", "Grupo 1", "2026-08-09", ["Pedro", "Ana"],
                            ["política", "economía"], "", MOCK_ANALYSIS, "")
    print(f"✅ ES PDF: {p}")

    if "--solo-es" in sys.argv:
        sys.exit(0)

    from translator import translate_analysis, translate_transcript_blocks

    # 2. Análisis EN (1 llamada a Sonnet)
    an_en = translate_analysis(MOCK_ANALYSIS)
    assert set(an_en.keys()) == set(MOCK_ANALYSIS.keys()), "claves alteradas"
    p = generate_pdf_report("TEST", "Grupo 1", "2026-08-09", ["Pedro", "Ana"],
                            ["política", "economía"], "", an_en, "", lang="en")
    print(f"✅ EN PDF: {p}")

    # 3. Transcripción (opcionalmente limitada: python test_translation.py 20)
    blocks = parse_readai_txt(TRANSCRIPT_TXT)
    limit = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
    if limit:
        blocks = blocks[:limit]
    print(f"Transcripción: {len(blocks)} bloques a traducir")
    tb, notas_tr = translate_transcript_blocks(blocks)
    assert len(tb) == len(blocks), f"se perdieron bloques: {len(tb)} != {len(blocks)}"
    p = generate_transcript_document("TEST", "Grupo 1", "2026-08-09", tb)
    print(f"✅ Transcript PDF: {p} ({len(tb)} bloques)")
    from report_generator import generate_translation_notes_document
    p = generate_translation_notes_document("TEST", "Grupo 1", "2026-08-09", notas_tr)
    print(f"✅ Notas de traducción: {p} ({len(notas_tr)} notas)")
