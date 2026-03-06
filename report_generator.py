
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT

C_ACCENT  = colors.HexColor("#7c6aff")
C_ACCENT2 = colors.HexColor("#ff6a8a")
C_DARK    = colors.HexColor("#1a1a2e")
C_MUTED   = colors.HexColor("#6b6b8a")
C_LIGHT   = colors.HexColor("#f5f5fa")
C_LIGHT2  = colors.HexColor("#fff0f3")
C_WHITE   = colors.white

PAGE_W = A4[0] - 4*cm  # ancho útil

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)

def safe_str(val):
    if isinstance(val, dict):
        return str(val.get("insight") or val.get("recomendacion") or val.get("hipotesis") or list(val.values())[0] if val else "")
    return str(val) if val else ""

def make_table(data, col_pcts, hdr=False):
    """Crea tabla con anchos como porcentaje del ancho útil"""
    col_widths = [PAGE_W * p for p in col_pcts]
    base = [
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("WORDWRAP",      (0,0), (-1,-1), True),
    ]
    if hdr:
        base += [
            ("BACKGROUND",     (0,0),  (-1,0),  C_DARK),
            ("TEXTCOLOR",      (0,0),  (-1,0),  C_WHITE),
            ("FONTNAME",       (0,0),  (-1,0),  "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1),  (-1,-1), [colors.white, C_LIGHT]),
        ]
    else:
        base += [("BACKGROUND", (0,0), (-1,-1), C_LIGHT)]
    t = Table(data, colWidths=col_widths, repeatRows=1 if hdr else 0)
    t.setStyle(TableStyle(base))
    return t

def section(title, color=None):
    return Paragraph(title, ParagraphStyle("H2",
        fontName="Helvetica-Bold", fontSize=12,
        textColor=color or C_ACCENT, spaceAfter=5, spaceBefore=14))

def subsection(title):
    return Paragraph(title, ParagraphStyle("H3",
        fontName="Helvetica-Bold", fontSize=9,
        textColor=C_MUTED, spaceAfter=3, spaceBefore=6))

def body(text):
    return Paragraph(str(text), ParagraphStyle("B",
        fontName="Helvetica", fontSize=9, textColor=C_DARK,
        spaceAfter=3, leading=13))

def muted(text):
    return Paragraph(str(text), ParagraphStyle("M",
        fontName="Helvetica", fontSize=8, textColor=C_MUTED,
        spaceAfter=3, leading=12))

def generate_pdf_report(session_id, title, date, speakers, topics, summary,
                         analysis, readai_url="", video_analysis=None):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T",  fontSize=20, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=4)
    S_sub   = st("S",  fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_foot  = st("F",  fontSize=8,  textColor=C_MUTED, alignment=TA_CENTER)

    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    has_video = bool(video_analysis and video_analysis.get("resumen_visual"))
    badge = "  ·  Texto + Video" if has_video else "  ·  Solo Texto"
    story.append(Paragraph("QualBot — Reporte de Focus Group", S_title))
    story.append(Paragraph(f"{title}  |  {date}{badge}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=10))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    emo        = analysis.get("emocion_general_sesion", "—")
    intensidad = analysis.get("intensidad_emocional", "—")
    emo_visual = ""
    if has_video:
        emo_visual = video_analysis.get("patrones_visuales_globales", {}).get("emocion_dominante_visual", "—")

    S_kpi_val = st("KV", fontSize=13, fontName="Helvetica-Bold", textColor=C_DARK, spaceAfter=1)
    S_kpi_lbl = st("KL", fontSize=7,  textColor=C_MUTED, spaceAfter=0)

    kpi_cells = [
        [Paragraph(emo,             S_kpi_val), Paragraph(intensidad,       S_kpi_val),
         Paragraph(str(len(speakers)), S_kpi_val), Paragraph(emo_visual or "—", S_kpi_val)],
        [Paragraph("Emoción (texto)", S_kpi_lbl), Paragraph("Intensidad", S_kpi_lbl),
         Paragraph("Participantes",   S_kpi_lbl), Paragraph("Emoción (video)", S_kpi_lbl)],
    ]
    kpi_t = Table(kpi_cells, colWidths=[PAGE_W*0.25]*4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 10))

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    story.append(section("Resumen ejecutivo"))
    story.append(body(analysis.get("resumen_ejecutivo", "")))
    if has_video and video_analysis.get("resumen_visual"):
        story.append(muted(f"Visual: {video_analysis['resumen_visual']}"))
    if summary:
        story.append(muted(f"Read.ai: {summary}"))

    # ── TEMPERATURA GRUPAL ────────────────────────────────────────────────────
    temp = analysis.get("temperatura_grupal", {})
    if temp:
        story.append(section("Temperatura grupal"))
        rows = [[k, v] for k, v in [
            ("Inicio",         temp.get("inicio","")),
            ("Desarrollo",     temp.get("desarrollo","")),
            ("Cierre",         temp.get("cierre","")),
            ("Arco narrativo", temp.get("arco_narrativo","")),
        ] if v]
        if rows:
            story.append(make_table(rows, [0.22, 0.78]))

    # ── PARTICIPANTES ─────────────────────────────────────────────────────────
    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(section("Participantes"))
        for p in participantes:
            block = []
            block.append(make_table([[
                Paragraph(f"<b>{p.get('nombre','')}</b>", st("pn", fontSize=10, fontName="Helvetica-Bold", textColor=C_DARK)),
                Paragraph(p.get("emocion_predominante",""), st("pe", fontSize=9, textColor=C_ACCENT)),
                Paragraph(f"Participación {p.get('nivel_participacion','')}", st("pp", fontSize=8, textColor=C_MUTED)),
            ]], [0.35, 0.35, 0.30]))
            for campo, label in [
                ("perfil_psicologico",       "Perfil"),
                ("perfil_emocional",         "Perfil"),
                ("estilo_comunicacional",    "Estilo comunicacional"),
                ("postura_real_vs_declarada","Postura real vs. declarada"),
                ("momento_mas_revelador",    "Momento más revelador"),
            ]:
                if p.get(campo):
                    block.append(muted(f"{label}: {p[campo]}"))
            block.append(Spacer(1, 6))
            story.append(KeepTogether(block))

    # ── DINAMICAS DE PODER ────────────────────────────────────────────────────
    poder = analysis.get("dinamicas_de_poder", {})
    if poder:
        story.append(section("Dinámicas de poder"))
        rows = [[k, v] for k, v in [
            ("Líder de opinión",   poder.get("lider_opinion","")),
            ("Seguidor principal", poder.get("seguidor_principal","")),
            ("Voz disidente",      poder.get("voz_disidente","")),
            ("Silenciado",         poder.get("silenciado","")),
            ("Mapa de influencia", poder.get("mapa_de_influencia","")),
        ] if v]
        if rows:
            story.append(make_table(rows, [0.25, 0.75]))

        presiones = poder.get("momentos_de_presion_social", [])
        if presiones:
            story.append(Spacer(1, 4))
            story.append(subsection("Momentos de presión social"))
            data = [["Tiempo", "Quién presionó", "Quién cedió", "Descripción"]]
            for pr in presiones:
                data.append([pr.get("timestamp",""), pr.get("quien_presiono",""), pr.get("quien_cedio",""), pr.get("descripcion","")])
            story.append(make_table(data, [0.10, 0.18, 0.18, 0.54], hdr=True))

    # ── ANALISIS DEL LENGUAJE ─────────────────────────────────────────────────
    lenguaje = analysis.get("analisis_del_lenguaje", {})
    if lenguaje:
        story.append(section("Análisis del lenguaje"))
        pos = lenguaje.get("palabras_clave_positivas", [])
        neg = lenguaje.get("palabras_clave_negativas", [])
        if pos or neg:
            story.append(make_table([
                ["Palabras positivas", ", ".join(pos)],
                ["Palabras negativas", ", ".join(neg)],
            ], [0.25, 0.75]))

        metaforas = lenguaje.get("metaforas_usadas", [])
        if metaforas:
            story.append(Spacer(1, 4))
            story.append(subsection("Metáforas usadas"))
            data = [["Metáfora", "Quién", "Interpretación"]]
            for m in metaforas:
                data.append([m.get("metafora",""), m.get("quien",""), m.get("interpretacion","")])
            story.append(make_table(data, [0.28, 0.14, 0.58], hdr=True))

        eufemismos = lenguaje.get("eufemismos_detectados", [])
        if eufemismos:
            story.append(Spacer(1, 4))
            story.append(subsection("Eufemismos detectados"))
            data = [["Lo que dijeron", "Lo que quisieron decir", "Quién"]]
            for e in eufemismos:
                data.append([e.get("lo_que_dijeron",""), e.get("lo_que_probablemente_quisieron_decir",""), e.get("quien","")])
            story.append(make_table(data, [0.30, 0.55, 0.15], hdr=True))

        frases = lenguaje.get("frases_mas_reveladoras", [])
        if frases:
            story.append(Spacer(1, 4))
            story.append(subsection("Frases más reveladoras"))
            data = [["Tiempo", "Quién", "Frase", "Por qué importa"]]
            for f in frases:
                data.append([f.get("timestamp",""), f.get("quien",""), f.get("frase",""), f.get("por_que_importa","")])
            story.append(make_table(data, [0.08, 0.13, 0.35, 0.44], hdr=True))

    # ── LO NO DICHO ───────────────────────────────────────────────────────────
    no_dicho = analysis.get("lo_no_dicho", {})
    if no_dicho:
        story.append(section("Lo no dicho"))
        evitados = no_dicho.get("temas_evitados", [])
        if evitados:
            story.append(subsection("Temas evitados"))
            data = [["Tema", "Evidencia", "Posible razón"]]
            for e in evitados:
                data.append([e.get("tema",""), e.get("evidencia",""), e.get("posible_razon","")])
            story.append(make_table(data, [0.20, 0.42, 0.38], hdr=True))

        silencios = no_dicho.get("silencios_significativos", [])
        if silencios:
            story.append(Spacer(1, 4))
            story.append(subsection("Silencios significativos"))
            data = [["Tiempo", "Contexto", "Interpretación"]]
            for s in silencios:
                data.append([s.get("timestamp",""), s.get("contexto",""), s.get("interpretacion","")])
            story.append(make_table(data, [0.10, 0.42, 0.48], hdr=True))

    # ── CONTRADICCIONES ───────────────────────────────────────────────────────
    contradicciones = analysis.get("contradicciones", [])
    if contradicciones:
        story.append(section("Contradicciones"))
        data = [["Participante", "Dijo primero", "Dijo después", "Interpretación"]]
        for c in contradicciones:
            data.append([c.get("participante",""), c.get("dijo_primero",""), c.get("dijo_despues",""), c.get("interpretacion","")])
        story.append(make_table(data, [0.15, 0.25, 0.25, 0.35], hdr=True))

    # ── MOMENTOS CRITICOS ─────────────────────────────────────────────────────
    momentos = analysis.get("momentos_criticos", [])
    if momentos:
        story.append(section("Momentos críticos"))
        data = [["Tiempo", "Tipo", "Descripción", "Por qué importa"]]
        for m in momentos:
            data.append([m.get("timestamp",""), m.get("tipo",""), m.get("descripcion",""), m.get("importancia_investigativa","")])
        story.append(make_table(data, [0.10, 0.16, 0.38, 0.36], hdr=True))

    # ── TEMAS CON CARGA EMOCIONAL ─────────────────────────────────────────────
    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        story.append(section("Temas con carga emocional"))
        data = [["Tema", "Carga", "Intensidad", "Observación", "Implicancia"]]
        for t in temas:
            data.append([t.get("tema",""), t.get("carga",""), t.get("intensidad",""), t.get("observacion",""), t.get("implicancia_para_marca","")])
        story.append(make_table(data, [0.16, 0.10, 0.10, 0.34, 0.30], hdr=True))

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN DE VIDEO
    # ══════════════════════════════════════════════════════════════════════════
    if has_video:
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT2, spaceAfter=8))
        story.append(Paragraph("ANÁLISIS VISUAL — Lenguaje no verbal",
            st("VH", fontName="Helvetica-Bold", fontSize=14, textColor=C_ACCENT2, spaceAfter=6)))

        # Patrones visuales globales
        pat = video_analysis.get("patrones_visuales_globales", {})
        if pat:
            story.append(section("Patrones visuales globales", C_ACCENT2))
            rows = [[k, v] for k, v in [
                ("Emoción dominante visual",  pat.get("emocion_dominante_visual","")),
                ("Momentos de tensión",       ", ".join(pat.get("momentos_tension_visual", []))),
                ("Momentos de apertura",      ", ".join(pat.get("momentos_apertura_visual", []))),
                ("Lenguaje corporal grupal",  pat.get("lenguaje_corporal_grupal","")),
            ] if v]
            if rows:
                story.append(make_table(rows, [0.28, 0.72]))

        # Observaciones frame a frame — como bloques de texto, no tabla
        obs = video_analysis.get("observaciones_por_frame", [])
        if obs:
            story.append(section("Observaciones frame a frame", C_ACCENT2))
            for o in obs:
                timestamp   = o.get("timestamp","")
                descripcion = o.get("descripcion_visual","")
                expresiones = "; ".join([
                    f"{e.get('persona','')}: {e.get('emocion','')} ({e.get('intensidad','')})"
                    for e in o.get("expresiones",[])
                ])
                coherencia  = o.get("coherencia_con_discurso","")
                nota        = o.get("nota","")

                bloque = []
                bloque.append(make_table([[
                    Paragraph(f"<b>{timestamp}</b>", st("ot", fontSize=9, fontName="Helvetica-Bold", textColor=C_ACCENT2)),
                    Paragraph(descripcion, st("od", fontSize=9, textColor=C_DARK)),
                ]], [0.10, 0.90]))
                if expresiones:
                    bloque.append(muted(f"Expresiones: {expresiones}"))
                if coherencia:
                    bloque.append(muted(f"Coherencia con discurso: {coherencia}"))
                if nota:
                    bloque.append(muted(f"Nota: {nota}"))
                bloque.append(Spacer(1, 4))
                story.append(KeepTogether(bloque))

        # Disonancias
        disonancias = video_analysis.get("disonancias_detectadas", [])
        if disonancias:
            story.append(section("Disonancias texto vs. cara", C_ACCENT2))
            story.append(muted("Momentos donde el lenguaje corporal contradice lo que se estaba diciendo."))
            story.append(Spacer(1, 4))
            for d in disonancias:
                bloque = []
                bloque.append(make_table([[
                    Paragraph(f"<b>{d.get('timestamp','')}</b>", st("dt", fontSize=9, fontName="Helvetica-Bold", textColor=C_ACCENT2)),
                    Paragraph(d.get("lo_que_se_decia",""), st("dd", fontSize=9, textColor=C_DARK)),
                ]], [0.10, 0.90]))
                bloque.append(muted(f"Lo que mostraba el cuerpo: {d.get('lo_que_mostraba_el_cuerpo','')}"))
                bloque.append(body(f"Interpretación: {d.get('interpretacion','')}"))
                bloque.append(Spacer(1, 5))
                story.append(KeepTogether(bloque))

        # Insights visuales
        insights_v = video_analysis.get("insights_visuales", [])
        if insights_v:
            story.append(section("Insights visuales", C_ACCENT2))
            for i, ins in enumerate(insights_v, 1):
                if isinstance(ins, dict):
                    bloque = []
                    bloque.append(body(f"<b>{i}. {ins.get('insight','')}</b>"))
                    if ins.get("evidencia"):
                        bloque.append(muted(f"Evidencia: {ins.get('evidencia')}"))
                    if ins.get("implicancia"):
                        bloque.append(muted(f"Implicancia: {ins.get('implicancia')}"))
                    bloque.append(Spacer(1, 4))
                    story.append(KeepTogether(bloque))
                else:
                    story.append(body(f"{i}. {safe_str(ins)}"))

    # ══════════════════════════════════════════════════════════════════════════
    # INSIGHTS, HIPÓTESIS Y RECOMENDACIONES
    # ══════════════════════════════════════════════════════════════════════════
    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(section("Insights de investigación"))
        for i, ins in enumerate(insights, 1):
            if isinstance(ins, dict):
                bloque = []
                bloque.append(body(f"<b>{i}. {ins.get('insight','')}</b>"))
                if ins.get("evidencia"):
                    bloque.append(muted(f"Evidencia: {ins.get('evidencia')}"))
                if ins.get("implicancia"):
                    bloque.append(muted(f"Implicancia: {ins.get('implicancia')}"))
                if ins.get("nivel_confianza"):
                    bloque.append(muted(f"Confianza: {ins.get('nivel_confianza')}"))
                bloque.append(Spacer(1, 4))
                story.append(KeepTogether(bloque))
            else:
                story.append(body(f"{i}. {safe_str(ins)}"))

    hipotesis = analysis.get("hipotesis_no_confirmadas", [])
    if hipotesis:
        story.append(section("Hipótesis no confirmadas"))
        for h in hipotesis:
            if isinstance(h, dict):
                bloque = []
                bloque.append(body(f"<b>{h.get('hipotesis','')}</b>"))
                if h.get("indicios"):
                    bloque.append(muted(f"Indicios: {h.get('indicios')}"))
                if h.get("como_validar"):
                    bloque.append(muted(f"Cómo validar: {h.get('como_validar')}"))
                bloque.append(Spacer(1, 4))
                story.append(KeepTogether(bloque))
            else:
                story.append(body(safe_str(h)))

    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(section("Recomendaciones"))
        for r in recos:
            if isinstance(r, dict):
                bloque = []
                prioridad = r.get("prioridad","")
                color_p = {"Alta": "#ef476f", "Media": "#ffd166", "Baja": "#06d6a0"}.get(prioridad, "#6b6b8a")
                bloque.append(body(f'<font color="{color_p}"><b>[{prioridad}]</b></font>  {r.get("recomendacion","")}'))
                if r.get("justificacion"):
                    bloque.append(muted(f"Justificación: {r.get('justificacion')}"))
                bloque.append(Spacer(1, 4))
                story.append(KeepTogether(bloque))
            else:
                story.append(body(f"→  {safe_str(r)}"))

    proximos = analysis.get("proximos_pasos_investigacion", [])
    if proximos:
        story.append(section("Próximos pasos"))
        for p in proximos:
            story.append(body(f"→  {safe_str(p)}"))

    nota = analysis.get("nota_metodologica", "")
    if nota:
        story.append(section("Nota metodológica"))
        story.append(muted(nota))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    footer = f"QualBot  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if readai_url:
        footer += f"  |  {readai_url}"
    story.append(Paragraph(footer, S_foot))

    doc.build(story)
    print(f"PDF generado: {path}")
    return path
