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

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
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
                         analysis, readai_url="", video_analysis=None):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T", fontSize=20, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    S_sub   = st("S", fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_foot  = st("F", fontSize=8,  textColor=C_MUTED, alignment=TA_CENTER)

    story = []
    has_video = bool(analysis.get("emocion_dominante_visual"))

    # ── HEADER ────────────────────────────────────────────────────────────────
    badge = "  ·  Análisis Integrado Texto + Video" if has_video else "  ·  Análisis de Texto"
    story.append(Paragraph("QualBot — Reporte de Focus Group", S_title))
    story.append(Paragraph(f"{title}  |  {date}{badge}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=10))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    emo       = analysis.get("emocion_general_sesion", "—")
    intens    = analysis.get("intensidad_emocional", "—")
    emo_vis   = analysis.get("emocion_dominante_visual", "—") or "—"
    n_part    = str(len(speakers)) if speakers else str(len(analysis.get("participantes",[])))

    S_kv = st("KV", fontSize=13, fontName="Helvetica-Bold", textColor=C_DARK, spaceAfter=1)
    S_kl = st("KL", fontSize=7,  textColor=C_MUTED, spaceAfter=0)

    kpi = Table([
        [Paragraph(emo, S_kv), Paragraph(intens, S_kv), Paragraph(n_part, S_kv), Paragraph(emo_vis, S_kv)],
        [Paragraph("Emoción (texto)", S_kl), Paragraph("Intensidad", S_kl),
         Paragraph("Participantes", S_kl), Paragraph("Emoción (video)", S_kl)],
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
    story.append(h2("Resumen ejecutivo"))
    story.append(body(analysis.get("resumen_ejecutivo", "")))
    if summary:
        story.append(note(f"Read.ai: {summary}"))

    # ── TEMPERATURA GRUPAL ────────────────────────────────────────────────────
    temp = analysis.get("temperatura_grupal", {})
    if temp:
        story.append(h2("Temperatura grupal"))
        rows = [[k, v] for k, v in [
            ("Inicio",         temp.get("inicio","")),
            ("Desarrollo",     temp.get("desarrollo","")),
            ("Cierre",         temp.get("cierre","")),
            ("Arco narrativo", temp.get("arco_narrativo","")),
        ] if v]
        if rows: story.append(mk_table(rows, [0.22, 0.78]))

    # ── PARTICIPANTES ─────────────────────────────────────────────────────────
    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(h2("Participantes"))
        for p in participantes:
            bloque = []
            bloque.append(mk_table([[
                Paragraph(f"<b>{p.get('nombre','')}</b>",
                    st("pn", fontSize=10, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(p.get("emocion_predominante",""),
                    st("pe", fontSize=9, textColor=C_ACCENT)),
                Paragraph(f"Participación: {p.get('nivel_participacion','')}",
                    st("pp", fontSize=8, textColor=C_MUTED)),
            ]], [0.30, 0.35, 0.35]))
            for campo, label in [
                ("perfil_psicologico",       "Perfil"),
                ("estilo_comunicacional",    "Estilo comunicacional"),
                ("expresion_visual",         "Expresión visual"),
                ("momento_mas_revelador",    "Momento más revelador"),
                ("postura_real_vs_declarada","Postura real vs. declarada"),
            ]:
                if p.get(campo):
                    bloque.append(note(f"{label}: {p[campo]}"))
            bloque.append(Spacer(1, 6))
            story.append(KeepTogether(bloque))

    # ── MOMENTOS CRITICOS INTEGRADOS ──────────────────────────────────────────
    momentos = analysis.get("momentos_criticos_integrados", [])
    if momentos:
        story.append(h2("Momentos críticos"))
        for m in momentos:
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
            if verbal:    bloque.append(note(f"Verbal: {verbal}"))
            if visual:    bloque.append(note(f"Visual: {visual}"))
            if disonancia: bloque.append(body(f"⚡ Disonancia: {disonancia}"))
            if importancia: bloque.append(note(f"Importancia: {importancia}"))
            bloque.append(Spacer(1, 5))
            story.append(KeepTogether(bloque))

    # ── DINAMICAS DE PODER ────────────────────────────────────────────────────
    poder = analysis.get("dinamicas_de_poder", {})
    if poder:
        story.append(h2("Dinámicas de poder"))
        rows = [[k, v] for k, v in [
            ("Líder de opinión",   poder.get("lider_opinion","")),
            ("Seguidor principal", poder.get("seguidor_principal","")),
            ("Voz disidente",      poder.get("voz_disidente","")),
            ("Silenciado",         poder.get("silenciado","")),
            ("Mapa de influencia", poder.get("mapa_de_influencia","")),
        ] if v]
        if rows: story.append(mk_table(rows, [0.25, 0.75]))

        presiones = poder.get("momentos_de_presion_social", [])
        if presiones:
            story.append(Spacer(1,4))
            story.append(h3("Momentos de presión social"))
            data = [["Tiempo","Quién presionó","Quién cedió","Descripción"]]
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
        story.append(h2("Análisis del lenguaje"))
        pos = lenguaje.get("palabras_clave_positivas", [])
        neg = lenguaje.get("palabras_clave_negativas", [])
        if pos or neg:
            story.append(mk_table([
                ["Palabras positivas", ", ".join(pos)],
                ["Palabras negativas", ", ".join(neg)],
            ], [0.25, 0.75]))

        metaforas = lenguaje.get("metaforas_usadas", [])
        if metaforas:
            story.append(Spacer(1,4)); story.append(h3("Metáforas usadas"))
            data = [["Metáfora","Quién","Interpretación"]]
            for m in metaforas:
                if isinstance(m, dict):
                    data.append([m.get("metafora",""), m.get("quien",""), m.get("interpretacion","")])
                else:
                    data.append([str(m), "", ""])
            story.append(mk_table(data, [0.28, 0.14, 0.58], hdr=True))

        eufemismos = lenguaje.get("eufemismos_detectados", [])
        if eufemismos:
            story.append(Spacer(1,4)); story.append(h3("Eufemismos detectados"))
            data = [["Lo que dijeron","Lo que quisieron decir","Quién"]]
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
            story.append(Spacer(1,4)); story.append(h3("Frases más reveladoras"))
            data = [["Tiempo","Quién","Frase","Por qué importa"]]
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
        story.append(h2("Lo no dicho"))
        evitados = no_dicho.get("temas_evitados", [])
        if evitados:
            story.append(h3("Temas evitados"))
            data = [["Tema","Evidencia","Posible razón"]]
            for e in evitados:
                data.append([e.get("tema",""), e.get("evidencia",""), e.get("posible_razon","")])
            story.append(mk_table(data, [0.20, 0.42, 0.38], hdr=True))

        silencios = no_dicho.get("silencios_significativos", [])
        if silencios:
            story.append(Spacer(1,4)); story.append(h3("Silencios significativos"))
            data = [["Tiempo","Contexto","Interpretación"]]
            for s in silencios:
                data.append([s.get("timestamp",""), s.get("contexto",""), s.get("interpretacion","")])
            story.append(mk_table(data, [0.10, 0.42, 0.48], hdr=True))

        senales = no_dicho.get("senales_no_verbales_ignoradas", [])
        if senales:
            story.append(Spacer(1,4)); story.append(h3("Señales no verbales ignoradas"))
            data = [["Tiempo","Lo que mostró el cuerpo","Lo que se decía","Interpretación"]]
            for s in senales:
                data.append([s.get("timestamp",""), s.get("lo_que_mostro_el_cuerpo",""),
                              s.get("lo_que_se_decia",""), s.get("interpretacion","")])
            story.append(mk_table(data, [0.09, 0.28, 0.28, 0.35], hdr=True))

    # ── CONTRADICCIONES ───────────────────────────────────────────────────────
    contradicciones = analysis.get("contradicciones", [])
    if contradicciones:
        story.append(h2("Contradicciones"))
        for c in contradicciones:
            bloque = []
            bloque.append(mk_table([[
                Paragraph(f"<b>{c.get('participante','')}</b>",
                    st("cn", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(f"{c.get('timestamp_1','')} → {c.get('timestamp_2','')}",
                    st("ct", fontSize=8, textColor=C_MUTED)),
            ]], [0.70, 0.30]))
            bloque.append(note(f"Primero dijo: {c.get('dijo_primero','')}"))
            bloque.append(note(f"Después dijo: {c.get('dijo_despues','')}"))
            if c.get("mostro_visualmente"):
                bloque.append(note(f"Visual: {c.get('mostro_visualmente','')}"))
            bloque.append(body(f"Interpretación: {c.get('interpretacion','')}"))
            bloque.append(Spacer(1, 5))
            story.append(KeepTogether(bloque))

    # ── TEMAS CON CARGA EMOCIONAL ─────────────────────────────────────────────
    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        story.append(h2("Temas con carga emocional"))
        for t in temas:
            bloque = []
            carga = t.get("carga","")
            color_c = {"Positiva": "#06d6a0", "Negativa": "#ef476f", "Ambivalente": "#ffd166"}.get(carga, "#6b6b8a")
            bloque.append(mk_table([[
                Paragraph(f"<b>{t.get('tema','')}</b>",
                    st("tn", fontSize=9, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(f'<font color="{color_c}"><b>{carga}</b></font> · {t.get("intensidad","")}',
                    st("tc", fontSize=8, textColor=C_DARK)),
            ]], [0.65, 0.35]))
            if t.get("reaccion_verbal"):
                bloque.append(note(f"Verbal: {t.get('reaccion_verbal','')}"))
            if t.get("reaccion_visual"):
                bloque.append(note(f"Visual: {t.get('reaccion_visual','')}"))
            if t.get("coherencia"):
                bloque.append(note(f"Coherencia: {t.get('coherencia','')}"))
            if t.get("implicancia_para_marca"):
                bloque.append(note(f"Implicancia: {t.get('implicancia_para_marca','')}"))
            bloque.append(Spacer(1,5))
            story.append(KeepTogether(bloque))

    # ── INSIGHTS ──────────────────────────────────────────────────────────────
    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(h2("Insights de investigación"))
        for i, ins in enumerate(insights, 1):
            bloque = []
            if isinstance(ins, dict):
                bloque.append(body(f"<b>{i}. {ins.get('insight','')}</b>"))
                if ins.get("evidencia_verbal"):
                    bloque.append(note(f"Evidencia verbal: {ins.get('evidencia_verbal')}"))
                if ins.get("evidencia_visual"):
                    bloque.append(note(f"Evidencia visual: {ins.get('evidencia_visual')}"))
                if ins.get("implicancia"):
                    bloque.append(note(f"Implicancia: {ins.get('implicancia')}"))
                if ins.get("nivel_confianza"):
                    bloque.append(note(f"Confianza: {ins.get('nivel_confianza')}"))
            else:
                bloque.append(body(f"{i}. {safe(ins)}"))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── HIPOTESIS ─────────────────────────────────────────────────────────────
    hipotesis = analysis.get("hipotesis_no_confirmadas", [])
    if hipotesis:
        story.append(h2("Hipótesis no confirmadas"))
        for h in hipotesis:
            bloque = []
            if isinstance(h, dict):
                bloque.append(body(f"<b>{h.get('hipotesis','')}</b>"))
                if h.get("indicios"):   bloque.append(note(f"Indicios: {h.get('indicios')}"))
                if h.get("como_validar"): bloque.append(note(f"Cómo validar: {h.get('como_validar')}"))
            else:
                bloque.append(body(safe(h)))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── RECOMENDACIONES ───────────────────────────────────────────────────────
    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(h2("Recomendaciones"))
        for r in recos:
            bloque = []
            if isinstance(r, dict):
                prioridad = r.get("prioridad","")
                color_p = {"Alta": "#ef476f", "Media": "#ffd166", "Baja": "#06d6a0"}.get(prioridad, "#6b6b8a")
                bloque.append(body(f'<font color="{color_p}"><b>[{prioridad}]</b></font>  {r.get("recomendacion","")}'))
                if r.get("justificacion"):
                    bloque.append(note(f"Justificación: {r.get('justificacion')}"))
            else:
                bloque.append(body(f"→  {safe(r)}"))
            bloque.append(Spacer(1,4))
            story.append(KeepTogether(bloque))

    # ── PROXIMOS PASOS ────────────────────────────────────────────────────────
    proximos = analysis.get("proximos_pasos_investigacion", [])
    if proximos:
        story.append(h2("Próximos pasos"))
        for p in proximos:
            story.append(body(f"→  {safe(p)}"))

    # ── NOTA METODOLOGICA ─────────────────────────────────────────────────────
    nota = analysis.get("nota_metodologica", "")
    if nota:
        story.append(h2("Nota metodológica"))
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
