import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.enums import TA_CENTER

C_ACCENT = colors.HexColor("#7c6aff")
C_DARK   = colors.HexColor("#1a1a2e")
C_MUTED  = colors.HexColor("#6b6b8a")
C_LIGHT  = colors.HexColor("#f5f5fa")
C_WHITE  = colors.white
C_RED    = colors.HexColor("#ef476f")
C_YELLOW = colors.HexColor("#ffd166")
C_GREEN  = colors.HexColor("#06d6a0")

PAGE_W = A4[0] - 4*cm

# Labels de todo el texto fijo del reporte, por idioma (modo inglés: lang="en")
LABELS = {
    "es": {
        "report_title": "QualBot — Reporte de Focus Group",
        "badge_integrated": "  ·  Análisis Integrado Texto + Video",
        "badge_text": "  ·  Análisis de Texto",
        "kpi_emotion_text": "Emoción (texto)", "kpi_intensity": "Intensidad",
        "kpi_participants": "Participantes", "kpi_emotion_video": "Emoción (video)",
        "resumen_ejecutivo": "Resumen ejecutivo",
        "temperatura_grupal": "Temperatura grupal",
        "inicio": "Inicio", "desarrollo": "Desarrollo", "cierre": "Cierre",
        "arco": "Arco narrativo",
        "participantes": "Participantes", "participacion": "Participación",
        "perfil": "Perfil", "estilo": "Estilo comunicacional",
        "expresion_visual": "Expresión visual",
        "momento_revelador": "Momento más revelador",
        "postura": "Postura real vs. declarada",
        "momentos_criticos": "Momentos críticos",
        "verbal": "Verbal", "visual": "Visual",
        "disonancia": "⚡ Disonancia", "importancia": "Importancia",
        "dinamicas_poder": "Dinámicas de poder",
        "lider": "Líder de opinión", "seguidor": "Seguidor principal",
        "disidente": "Voz disidente", "silenciado": "Silenciado",
        "mapa_influencia": "Mapa de influencia",
        "presion_social": "Momentos de presión social",
        "hdr_tiempo": "Tiempo", "hdr_quien_presiono": "Quién presionó",
        "hdr_quien_cedio": "Quién cedió", "hdr_descripcion": "Descripción",
        "analisis_lenguaje": "Análisis del lenguaje",
        "palabras_pos": "Palabras positivas", "palabras_neg": "Palabras negativas",
        "metaforas": "Metáforas usadas", "hdr_metafora": "Metáfora",
        "hdr_quien": "Quién", "hdr_interpretacion": "Interpretación",
        "eufemismos": "Eufemismos detectados",
        "hdr_dijeron": "Lo que dijeron", "hdr_quisieron": "Lo que quisieron decir",
        "frases_reveladoras": "Frases más reveladoras",
        "hdr_frase": "Frase", "hdr_por_que": "Por qué importa",
        "no_dicho": "Lo no dicho", "temas_evitados": "Temas evitados",
        "hdr_tema": "Tema", "hdr_evidencia": "Evidencia",
        "hdr_razon": "Posible razón",
        "silencios": "Silencios significativos", "hdr_contexto": "Contexto",
        "senales": "Señales no verbales ignoradas",
        "hdr_cuerpo": "Lo que mostró el cuerpo", "hdr_decia": "Lo que se decía",
        "contradicciones": "Contradicciones",
        "dijo_primero": "Primero dijo", "dijo_despues": "Después dijo",
        "interpretacion": "Interpretación",
        "temas_carga": "Temas con carga emocional",
        "coherencia": "Coherencia", "implicancia": "Implicancia",
        "insights": "Insights de investigación",
        "evidencia_verbal": "Evidencia verbal", "evidencia_visual": "Evidencia visual",
        "confianza": "Confianza",
        "hipotesis": "Hipótesis no confirmadas",
        "indicios": "Indicios", "como_validar": "Cómo validar",
        "recomendaciones": "Recomendaciones", "justificacion": "Justificación",
        "proximos_pasos": "Próximos pasos",
        "nota_metodologica": "Nota metodológica",
        "transcript_title": "QualBot — Transcripción de Focus Group",
    },
    "en": {
        "report_title": "QualBot — Focus Group Report",
        "badge_integrated": "  ·  Integrated Text + Video Analysis",
        "badge_text": "  ·  Text Analysis",
        "kpi_emotion_text": "Emotion (text)", "kpi_intensity": "Intensity",
        "kpi_participants": "Participants", "kpi_emotion_video": "Emotion (video)",
        "resumen_ejecutivo": "Executive summary",
        "temperatura_grupal": "Group temperature",
        "inicio": "Opening", "desarrollo": "Development", "cierre": "Closing",
        "arco": "Narrative arc",
        "participantes": "Participants", "participacion": "Participation",
        "perfil": "Profile", "estilo": "Communication style",
        "expresion_visual": "Visual expression",
        "momento_revelador": "Most revealing moment",
        "postura": "Actual vs. stated position",
        "momentos_criticos": "Critical moments",
        "verbal": "Verbal", "visual": "Visual",
        "disonancia": "⚡ Dissonance", "importancia": "Significance",
        "dinamicas_poder": "Power dynamics",
        "lider": "Opinion leader", "seguidor": "Main follower",
        "disidente": "Dissenting voice", "silenciado": "Silenced",
        "mapa_influencia": "Influence map",
        "presion_social": "Social pressure moments",
        "hdr_tiempo": "Time", "hdr_quien_presiono": "Who pressured",
        "hdr_quien_cedio": "Who yielded", "hdr_descripcion": "Description",
        "analisis_lenguaje": "Language analysis",
        "palabras_pos": "Positive words", "palabras_neg": "Negative words",
        "metaforas": "Metaphors used", "hdr_metafora": "Metaphor",
        "hdr_quien": "Who", "hdr_interpretacion": "Interpretation",
        "eufemismos": "Euphemisms detected",
        "hdr_dijeron": "What they said", "hdr_quisieron": "What they likely meant",
        "frases_reveladoras": "Most revealing quotes",
        "hdr_frase": "Quote", "hdr_por_que": "Why it matters",
        "no_dicho": "The unsaid", "temas_evitados": "Avoided topics",
        "hdr_tema": "Topic", "hdr_evidencia": "Evidence",
        "hdr_razon": "Possible reason",
        "silencios": "Meaningful silences", "hdr_contexto": "Context",
        "senales": "Ignored non-verbal signals",
        "hdr_cuerpo": "What the body showed", "hdr_decia": "What was being said",
        "contradicciones": "Contradictions",
        "dijo_primero": "First said", "dijo_despues": "Later said",
        "interpretacion": "Interpretation",
        "temas_carga": "Emotionally charged topics",
        "coherencia": "Consistency", "implicancia": "Implication",
        "insights": "Research insights",
        "evidencia_verbal": "Verbal evidence", "evidencia_visual": "Visual evidence",
        "confianza": "Confidence",
        "hipotesis": "Unconfirmed hypotheses",
        "indicios": "Indications", "como_validar": "How to validate",
        "recomendaciones": "Recommendations", "justificacion": "Rationale",
        "proximos_pasos": "Next steps",
        "nota_metodologica": "Methodological note",
        "transcript_title": "QualBot — Focus Group Transcript",
    },
}

# Mapas de color por valor categórico — con claves ES y EN porque el análisis
# traducido llega con los valores en inglés
CARGA_COLORS = {
    "Positiva": "#06d6a0", "Positive": "#06d6a0",
    "Negativa": "#ef476f", "Negative": "#ef476f",
    "Ambivalente": "#ffd166", "Ambivalent": "#ffd166",
}
PRIORIDAD_COLORS = {
    "Alta": "#ef476f", "High": "#ef476f",
    "Media": "#ffd166", "Medium": "#ffd166",
    "Baja": "#06d6a0", "Low": "#06d6a0",
}

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    # El leading default de ReportLab es 12pt fijo: los títulos grandes se
    # pisaban con la línea siguiente. Proporcional al tamaño si no se indica.
    kw.setdefault("leading", round(kw.get("fontSize", 10) * 1.25, 1))
    return ParagraphStyle(name, **kw)

def safe(val):
    if isinstance(val, dict):
        for k in ("insight","recomendacion","hipotesis"):
            if val.get(k): return str(val[k])
        return str(list(val.values())[0]) if val else ""
    return str(val) if val else ""

S_CELL     = st("CELL",  fontSize=8, textColor=C_DARK,  leading=11)
S_CELL_HDR = st("CELLH", fontSize=8, textColor=C_WHITE, leading=11, fontName="Helvetica-Bold")

def _wrap(cell, is_hdr=False):
    if isinstance(cell, Paragraph):
        return cell
    s = S_CELL_HDR if is_hdr else S_CELL
    return Paragraph(str(cell) if cell is not None else "", s)

def mk_table(data, pcts, hdr=False):
    widths = [PAGE_W * p for p in pcts]
    wrapped = []
    for i, row in enumerate(data):
        is_hdr_row = (hdr and i == 0)
        wrapped.append([_wrap(cell, is_hdr_row) for cell in row])
    style = [
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
    ]
    if hdr:
        style += [
            ("BACKGROUND",     (0,0),  (-1,0),  C_DARK),
            ("ROWBACKGROUNDS", (0,1),  (-1,-1), [colors.white, C_LIGHT]),
        ]
    else:
        style += [("BACKGROUND", (0,0), (-1,-1), C_LIGHT)]
    t = Table(wrapped, colWidths=widths, repeatRows=1 if hdr else 0)
    t.setStyle(TableStyle(style))
    return t

def h2(text, color=None):
    return Paragraph(text, st("H2", fontName="Helvetica-Bold", fontSize=12,
        textColor=color or C_ACCENT, spaceAfter=5, spaceBefore=14))

def h3(text):
    return Paragraph(text, st("H3", fontName="Helvetica-Bold", fontSize=9,
        textColor=C_MUTED, spaceAfter=3, spaceBefore=6))

def body(text):
    return Paragraph(str(text), st("B", fontSize=9, textColor=C_DARK,
        spaceAfter=3, leading=13))

def note(text):
    return Paragraph(str(text), st("N", fontSize=8, textColor=C_MUTED,
        spaceAfter=3, leading=12))

def generate_pdf_report(session_id, title, date, speakers, topics, summary,
                         analysis, readai_url="", video_analysis=None, lang="es"):
    L = LABELS.get(lang, LABELS["es"])
    os.makedirs("reportes", exist_ok=True)
    # Sufijo de idioma para que el PDF EN no pise al ES (comparten session_id)
    suffix = "" if lang == "es" else f"_{lang}"
    path = f"reportes/QualBot_{session_id}{suffix}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T", fontSize=20, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    S_sub   = st("S", fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_foot  = st("F", fontSize=8,  textColor=C_MUTED, alignment=TA_CENTER)

    story = []
    has_video = bool(analysis.get("emocion_dominante_visual"))

    # ── HEADER ────────────────────────────────────────────────────────────────
    badge = L["badge_integrated"] if has_video else L["badge_text"]
    story.append(Paragraph(L["report_title"], S_title))
    story.append(Paragraph(f"{title}  |  {date}{badge}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=10))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    emo       = analysis.get("emocion_general_sesion", "—")
    intens    = analysis.get("intensidad_emocional", "—")
    emo_vis   = analysis.get("emocion_dominante_visual", "—") or "—"
    n_part    = str(len(speakers)) if speakers else str(len(analysis.get("participantes",[])))

    S_kl = st("KL", fontSize=7,  textColor=C_MUTED, spaceAfter=0)

    def _kpi(val):
        # El modelo a veces devuelve emociones largas con paréntesis: recortar
        # y achicar la letra para que la celda no se rompa
        val = str(val)
        if "(" in val:
            val = val.split("(")[0].strip()
        if len(val) > 60:
            val = val[:57] + "..."
        size = 13 if len(val) <= 22 else 9
        return Paragraph(val, st(f"KV{size}", fontSize=size,
                                 fontName="Helvetica-Bold", textColor=C_DARK, spaceAfter=1))

    kpi = Table([
        [_kpi(emo), _kpi(intens), _kpi(n_part), _kpi(emo_vis)],
        [Paragraph(L["kpi_emotion_text"], S_kl), Paragraph(L["kpi_intensity"], S_kl),
         Paragraph(L["kpi_participants"], S_kl), Paragraph(L["kpi_emotion_video"], S_kl)],
    ], colWidths=[PAGE_W*0.25]*4)
    kpi.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 10))

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    story.append(h2(L["resumen_ejecutivo"]))
    story.append(body(analysis.get("resumen_ejecutivo", "")))
    if summary:
        story.append(note(f"Read.ai: {summary}"))

    # ── TEMPERATURA GRUPAL ────────────────────────────────────────────────────
    temp = analysis.get("temperatura_grupal", {})
    if temp:
        story.append(h2(L["temperatura_grupal"]))
        rows = [[k, v] for k, v in [
            (L["inicio"],     temp.get("inicio","")),
            (L["desarrollo"], temp.get("desarrollo","")),
            (L["cierre"],     temp.get("cierre","")),
            (L["arco"],       temp.get("arco_narrativo","")),
        ] if v]
        if rows: story.append(mk_table(rows, [0.22, 0.78]))

    # ── PARTICIPANTES ─────────────────────────────────────────────────────────
    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(h2(L["participantes"]))
        for p in participantes:
            bloque = []
            bloque.append(mk_table([[
                Paragraph(f"<b>{p.get('nombre','')}</b>",
                    st("pn", fontSize=10, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(p.get("emocion_predominante",""),
                    st("pe", fontSize=9, textColor=C_ACCENT)),
                Paragraph(f"{L['participacion']}: {p.get('nivel_participacion','')}",
                    st("pp", fontSize=8, textColor=C_MUTED)),
            ]], [0.30, 0.35, 0.35]))
            for campo, label in [
                ("perfil_psicologico",       L["perfil"]),
                ("estilo_comunicacional",    L["estilo"]),
                ("expresion_visual",         L["expresion_visual"]),
                ("momento_mas_revelador",    L["momento_revelador"]),
                ("postura_real_vs_declarada",L["postura"]),
            ]:
                if p.get(campo):
                    bloque.append(note(f"{label}: {p[campo]}"))
            bloque.append(Spacer(1, 6))
            story.append(KeepTogether(bloque))

    # ── MOMENTOS CRITICOS INTEGRADOS ──────────────────────────────────────────
    momentos = analysis.get("momentos_criticos_integrados", [])
    if momentos:
        story.append(h2(L["momentos_criticos"]))
        for m in momentos:
            if not isinstance(m, dict):
                story.append(body(str(m))); continue
            bloque = []
            tipo      = m.get("tipo","")
            ts        = m.get("timestamp","")
            verbal    = m.get("descripcion_verbal","")
            visual    = m.get("descripcion_visual","")
            disonancia = m.get("disonancia","")
            importancia = m.get("importancia_investigativa","")

            bloque.append(mk_table([[
                Paragraph(f"<b>{ts}</b>", st("mt", fontSize=9, fontName="Helvetica-Bold", textColor=C_ACCENT)),
                Paragraph(f"<b>{tipo}</b>", st("mtt", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)),
            ]], [0.12, 0.88]))
            if verbal:    bloque.append(note(f"{L['verbal']}: {verbal}"))
            if visual:    bloque.append(note(f"{L['visual']}: {visual}"))
            if disonancia: bloque.append(body(f"{L['disonancia']}: {disonancia}"))
            if importancia: bloque.append(note(f"{L['importancia']}: {importancia}"))
            bloque.append(Spacer(1, 5))
            story.append(KeepTogether(bloque))

    # ── DINAMICAS DE PODER ────────────────────────────────────────────────────
    poder = analysis.get("dinamicas_de_poder", {})
    if poder:
        story.append(h2(L["dinamicas_poder"]))
        rows = [[k, v] for k, v in [
            (L["lider"],           poder.get("lider_opinion","")),
            (L["seguidor"],        poder.get("seguidor_principal","")),
            (L["disidente"],       poder.get("voz_disidente","")),
            (L["silenciado"],      poder.get("silenciado","")),
            (L["mapa_influencia"], poder.get("mapa_de_influencia","")),
        ] if v]
        if rows: story.append(mk_table(rows, [0.25, 0.75]))

        presiones = poder.get("momentos_de_presion_social", [])
        if presiones:
            story.append(Spacer(1,4))
            story.append(h3(L["presion_social"]))
            data = [[L["hdr_tiempo"], L["hdr_quien_presiono"], L["hdr_quien_cedio"], L["hdr_descripcion"]]]
            for pr in presiones:
                if isinstance(pr, dict):
                    data.append([pr.get("timestamp",""), pr.get("quien_presiono",""),
                                  pr.get("quien_cedio",""), pr.get("descripcion","")])
                else:
                    data.append(["", "", "", str(pr)])
            story.append(mk_table(data, [0.10, 0.18, 0.18, 0.54], hdr=True))

    # ── ANALISIS DEL LENGUAJE ─────────────────────────────────────────────────
    lenguaje = analysis.get("analisis_del_lenguaje", {})
    if lenguaje:
        story.append(h2(L["analisis_lenguaje"]))
        pos = lenguaje.get("palabras_clave_positivas", [])
        neg = lenguaje.get("palabras_clave_negativas", [])
        if pos or neg:
            story.append(mk_table([
                [L["palabras_pos"], ", ".join(pos)],
                [L["palabras_neg"], ", ".join(neg)],
            ], [0.25, 0.75]))

        metaforas = lenguaje.get("metaforas_usadas", [])
        if metaforas:
            story.append(Spacer(1,4)); story.append(h3(L["metaforas"]))
            data = [[L["hdr_metafora"], L["hdr_quien"], L["hdr_interpretacion"]]]
            for m in metaforas:
                if isinstance(m, dict):
                    data.append([m.get("metafora",""), m.get("quien",""), m.get("interpretacion","")])
                else:
                    data.append([str(m), "", ""])
            story.append(mk_table(data, [0.28, 0.14, 0.58], hdr=True))

        eufemismos = lenguaje.get("eufemismos_detectados", [])
        if eufemismos:
            story.append(Spacer(1,4)); story.append(h3(L["eufemismos"]))
            data = [[L["hdr_dijeron"], L["hdr_quisieron"], L["hdr_quien"]]]
            for e in eufemismos:
                if isinstance(e, dict):
                    data.append([e.get("lo_que_dijeron",""),
                                  e.get("lo_que_probablemente_quisieron_decir",""),
                                  e.get("quien","")])
                else:
                    data.append([str(e), "", ""])
            story.append(mk_table(data, [0.30, 0.55, 0.15], hdr=True))

        frases = lenguaje.get("frases_mas_reveladoras", [])
        if frases:
            story.append(Spacer(1,4)); story.append(h3(L["frases_reveladoras"]))
            data = [[L["hdr_tiempo"], L["hdr_quien"], L["hdr_frase"], L["hdr_por_que"]]]
            for f in frases:
                if isinstance(f, dict):
                    data.append([f.get("timestamp",""), f.get("quien",""),
                                  f.get("frase",""), f.get("por_que_importa","")])
                else:
                    data.append(["", "", str(f), ""])
            story.append(mk_table(data, [0.08, 0.13, 0.35, 0.44], hdr=True))

    # ── LO NO DICHO ───────────────────────────────────────────────────────────
    no_dicho = analysis.get("lo_no_dicho", {})
    if no_dicho:
        story.append(h2(L["no_dicho"]))
        evitados = no_dicho.get("temas_evitados", [])
        if evitados:
            story.append(h3(L["temas_evitados"]))
            data = [[L["hdr_tema"], L["hdr_evidencia"], L["hdr_razon"]]]
            for e in evitados:
                if isinstance(e, dict):
                    data.append([e.get("tema",""), e.get("evidencia",""), e.get("posible_razon","")])
                else:
                    data.append([str(e), "", ""])
            story.append(mk_table(data, [0.20, 0.42, 0.38], hdr=True))

        silencios = no_dicho.get("silencios_significativos", [])
        if silencios:
            story.append(Spacer(1,4)); story.append(h3(L["silencios"]))
            data = [[L["hdr_tiempo"], L["hdr_contexto"], L["hdr_interpretacion"]]]
            for s in silencios:
                if isinstance(s, dict):
                    data.append([s.get("timestamp",""), s.get("contexto",""), s.get("interpretacion","")])
                else:
                    data.append(["", str(s), ""])
            story.append(mk_table(data, [0.10, 0.42, 0.48], hdr=True))

        senales = no_dicho.get("senales_no_verbales_ignoradas", [])
        if senales:
            story.append(Spacer(1,4)); story.append(h3(L["senales"]))
            data = [[L["hdr_tiempo"], L["hdr_cuerpo"], L["hdr_decia"], L["hdr_interpretacion"]]]
            for s in senales:
                if isinstance(s, dict):
                    data.append([s.get("timestamp",""), s.get("lo_que_mostro_el_cuerpo",""),
                                  s.get("lo_que_se_decia",""), s.get("interpretacion","")])
                else:
                    data.append(["", str(s), "", ""])
            story.append(mk_table(data, [0.09, 0.28, 0.28, 0.35], hdr=True))

    # ── CONTRADICCIONES ───────────────────────────────────────────────────────
    contradicciones = analysis.get("contradicciones", [])
    if contradicciones:
        story.append(h2(L["contradicciones"]))
        for c in contradicciones:
            if not isinstance(c, dict):
                story.append(body(str(c))); continue
            bloque = []
            bloque.append(mk_table([[
                Paragraph(f"<b>{c.get('participante','')}</b>",
                    st("cn", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(f"{c.get('timestamp_1','')} → {c.get('timestamp_2','')}",
                    st("ct", fontSize=8, textColor=C_MUTED)),
            ]], [0.70, 0.30]))
            bloque.append(note(f"{L['dijo_primero']}: {c.get('dijo_primero','')}"))
            bloque.append(note(f"{L['dijo_despues']}: {c.get('dijo_despues','')}"))
            if c.get("mostro_visualmente"):
                bloque.append(note(f"{L['visual']}: {c.get('mostro_visualmente','')}"))
            bloque.append(body(f"{L['interpretacion']}: {c.get('interpretacion','')}"))
            bloque.append(Spacer(1, 5))
            story.append(KeepTogether(bloque))

    # ── TEMAS CON CARGA EMOCIONAL ─────────────────────────────────────────────
    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        story.append(h2(L["temas_carga"]))
        for t in temas:
            if not isinstance(t, dict):
                story.append(body(str(t))); continue
            bloque = []
            carga = t.get("carga","")
            color_c = CARGA_COLORS.get(carga, "#6b6b8a")
            bloque.append(mk_table([[
                Paragraph(f"<b>{t.get('tema','')}</b>",
                    st("tn", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(f'<font color="{color_c}"><b>{carga}</b></font> · {t.get("intensidad","")}',
                    st("tc", fontSize=8, textColor=C_DARK)),
            ]], [0.65, 0.35]))
            if t.get("reaccion_verbal"):
                bloque.append(note(f"{L['verbal']}: {t.get('reaccion_verbal','')}"))
            if t.get("reaccion_visual"):
                bloque.append(note(f"{L['visual']}: {t.get('reaccion_visual','')}"))
            if t.get("coherencia"):
                bloque.append(note(f"{L['coherencia']}: {t.get('coherencia','')}"))
            if t.get("implicancia_para_marca"):
                bloque.append(note(f"{L['implicancia']}: {t.get('implicancia_para_marca','')}"))
            bloque.append(Spacer(1,5))
            story.append(KeepTogether(bloque))

    # ── INSIGHTS ──────────────────────────────────────────────────────────────
    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(h2(L["insights"]))
        for i, ins in enumerate(insights, 1):
            bloque = []
            if isinstance(ins, dict):
                bloque.append(body(f"<b>{i}. {ins.get('insight','')}</b>"))
                if ins.get("evidencia_verbal"):
                    bloque.append(note(f"{L['evidencia_verbal']}: {ins.get('evidencia_verbal')}"))
                if ins.get("evidencia_visual"):
                    bloque.append(note(f"{L['evidencia_visual']}: {ins.get('evidencia_visual')}"))
                if ins.get("implicancia"):
                    bloque.append(note(f"{L['implicancia']}: {ins.get('implicancia')}"))
                if ins.get("nivel_confianza"):
                    bloque.append(note(f"{L['confianza']}: {ins.get('nivel_confianza')}"))
            else:
                bloque.append(body(f"{i}. {safe(ins)}"))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── HIPOTESIS ─────────────────────────────────────────────────────────────
    hipotesis = analysis.get("hipotesis_no_confirmadas", [])
    if hipotesis:
        story.append(h2(L["hipotesis"]))
        for h in hipotesis:
            bloque = []
            if isinstance(h, dict):
                bloque.append(body(f"<b>{h.get('hipotesis','')}</b>"))
                if h.get("indicios"):   bloque.append(note(f"{L['indicios']}: {h.get('indicios')}"))
                if h.get("como_validar"): bloque.append(note(f"{L['como_validar']}: {h.get('como_validar')}"))
            else:
                bloque.append(body(safe(h)))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── RECOMENDACIONES ───────────────────────────────────────────────────────
    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(h2(L["recomendaciones"]))
        for r in recos:
            bloque = []
            if isinstance(r, dict):
                prioridad = r.get("prioridad","")
                color_p = PRIORIDAD_COLORS.get(prioridad, "#6b6b8a")
                bloque.append(body(f'<font color="{color_p}"><b>[{prioridad}]</b></font>  {r.get("recomendacion","")}'))
                if r.get("justificacion"):
                    bloque.append(note(f"{L['justificacion']}: {r.get('justificacion')}"))
            else:
                bloque.append(body(f"→  {safe(r)}"))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── PROXIMOS PASOS ────────────────────────────────────────────────────────
    proximos = analysis.get("proximos_pasos_investigacion", [])
    if proximos:
        story.append(h2(L["proximos_pasos"]))
        for p in proximos:
            story.append(body(f"→  {safe(p)}"))

    # ── NOTA METODOLOGICA ─────────────────────────────────────────────────────
    nota = analysis.get("nota_metodologica", "")
    if nota:
        story.append(h2(L["nota_metodologica"]))
        story.append(note(nota))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    footer = f"QualBot  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if readai_url: footer += f"  |  {readai_url}"
    story.append(Paragraph(footer, S_foot))

    doc.build(story)
    print(f"PDF generado: {path}")
    return path


def generate_transcript_document(session_id, title, date, translated_blocks, lang="en"):
    """PDF con la transcripción: [MM:SS] Speaker + párrafo por bloque.

    Acepta dos formas de bloque: la traducida
    ({"speaker": str, "start_time": ms, "text_en": str}) y la cruda del
    transcriptor ({"speaker": {"name": str}, "start_time": ms, "words": str}),
    para poder emitir también la transcripción en castellano."""
    L = LABELS.get(lang, LABELS["en"])
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_Transcript_{session_id}_{lang}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T", fontSize=18, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    S_sub   = st("S", fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_spk   = st("SPK", fontSize=9, fontName="Helvetica-Bold", textColor=C_ACCENT,
                 spaceBefore=8, spaceAfter=2)

    story = [
        Paragraph(L["transcript_title"], S_title),
        Paragraph(f"{title}  |  {date}", S_sub),
        HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=10),
    ]

    # Read.ai manda start_time como época Unix en ms — llevar a tiempo relativo
    starts = [int(b.get("start_time", 0) or 0) for b in translated_blocks]
    t0 = min((s for s in starts if s > 0), default=0)

    for b, start in zip(translated_blocks, starts):
        rel = max(0, start - t0)
        mins, secs = divmod(rel // 1000, 60)
        spk = b.get("speaker", "?")
        if isinstance(spk, dict):
            spk = spk.get("name", "?")
        text = b.get("text_en") or b.get("text") or b.get("words") or ""
        story.append(Paragraph(f"[{mins:02d}:{secs:02d}] {spk}", S_spk))
        story.append(body(text))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    story.append(Paragraph(f"QualBot  |  {datetime.now().strftime('%m/%d/%Y %H:%M')}",
                           st("F", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)))

    doc.build(story)
    print(f"Transcript PDF generado: {path}")
    return path
