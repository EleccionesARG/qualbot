"""
report_generator.py
Genera un reporte PDF profesional del focus group con el análisis de Claude
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Paleta de colores ──────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#1a1a2e")
C_ACCENT    = colors.HexColor("#7c6aff")
C_ACCENT2   = colors.HexColor("#ff6a8a")
C_ACCENT3   = colors.HexColor("#06d6a0")
C_LIGHT     = colors.HexColor("#f5f5fa")
C_MUTED     = colors.HexColor("#6b6b8a")
C_WHITE     = colors.white

EMOTION_COLORS = {
    "Alegría":   colors.HexColor("#ffd166"),
    "Enojo":     colors.HexColor("#ef476f"),
    "Tristeza":  colors.HexColor("#118ab2"),
    "Neutral":   colors.HexColor("#aaaaaa"),
    "Sorpresa":  colors.HexColor("#06d6a0"),
    "Miedo":     colors.HexColor("#a64ac9"),
    "Disgusto":  colors.HexColor("#78290f"),
    "Positiva":  colors.HexColor("#06d6a0"),
    "Negativa":  colors.HexColor("#ef476f"),
    "Mixta":     colors.HexColor("#ffd166"),
}

TIPO_COLORS = {
    "Tension":   colors.HexColor("#ef476f"),
    "Acuerdo":   colors.HexColor("#06d6a0"),
    "Sorpresa":  colors.HexColor("#ffd166"),
    "Quiebre":   colors.HexColor("#ff6a8a"),
    "Insight":   colors.HexColor("#7c6aff"),
}

def generate_pdf_report(session_id, title, date, speakers, topics, summary, analysis, readai_url=""):
    os.makedirs("reportes", exist_ok=True)
    filename = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # ── Estilos personalizados ─────────────────────────────────────────────────
    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    S = {
        "h1": style("H1", fontSize=22, textColor=C_PRIMARY, fontName="Helvetica-Bold",
                    spaceAfter=4, leading=26),
        "h2": style("H2", fontSize=13, textColor=C_ACCENT, fontName="Helvetica-Bold",
                    spaceAfter=6, spaceBefore=14, leading=16),
        "h3": style("H3", fontSize=10, textColor=C_PRIMARY, fontName="Helvetica-Bold",
                    spaceAfter=3, leading=13),
        "body": style("Body", fontSize=9, textColor=C_PRIMARY, fontName="Helvetica",
                      spaceAfter=4, leading=13),
        "muted": style("Muted", fontSize=8, textColor=C_MUTED, fontName="Helvetica",
                       spaceAfter=3, leading=11),
        "badge": style("Badge", fontSize=8, textColor=C_WHITE, fontName="Helvetica-Bold",
                       alignment=TA_CENTER),
        "insight": style("Insight", fontSize=9, textColor=C_PRIMARY, fontName="Helvetica",
                         leftIndent=12, spaceAfter=5, leading=13,
                         borderPad=6),
        "center": style("Center", fontSize=9, textColor=C_MUTED, fontName="Helvetica",
                        alignment=TA_CENTER),
    }

    story = []

    # ── HEADER ─────────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("◆ <b>Qual</b>Bot", style("Logo", fontSize=14, textColor=C_ACCENT,
                                             fontName="Helvetica-Bold")),
        Paragraph(f"Reporte de Focus Group<br/><font size='8' color='#6b6b8a'>{date}</font>",
                  style("HR", fontSize=11, textColor=C_PRIMARY, fontName="Helvetica-Bold",
                        alignment=TA_RIGHT))
    ]]
    header_table = Table(header_data, colWidths=["50%", "50%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=16))

    # Título
    story.append(Paragraph(title, S["h1"]))
    story.append(Spacer(1, 4))

    # ── RESUMEN RÁPIDO ─────────────────────────────────────────────────────────
    emo_general   = analysis.get("emocion_general_sesion", "—")
    intensidad    = analysis.get("intensidad_emocional", "—")
    resumen_exec  = analysis.get("resumen_ejecutivo", "—")
    emo_color     = EMOTION_COLORS.get(emo_general, C_MUTED)

    kpi_data = [
        [
            _kpi_cell("Emoción general", emo_general, emo_color),
            _kpi_cell("Intensidad", intensidad, C_ACCENT),
            _kpi_cell("Participantes", str(len(speakers)), C_ACCENT2),
            _kpi_cell("Temas", str(len(topics)), C_ACCENT3),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=["25%","25%","25%","25%"])
    kpi_table.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # Resumen ejecutivo
    story.append(Paragraph("Resumen ejecutivo", S["h2"]))
    story.append(Paragraph(resumen_exec, S["body"]))

    if summary:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<i>Resumen de Read.ai:</i> {summary}", S["muted"]))

    # ── PARTICIPANTES ──────────────────────────────────────────────────────────
    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(Paragraph("Perfiles de participantes", S["h2"]))
        for p in participantes:
            nombre    = p.get("nombre", "?")
            perfil    = p.get("perfil_emocional", "")
            emo       = p.get("emocion_predominante", "Neutral")
            nivel     = p.get("nivel_participacion", "Medio")
            momentos  = p.get("momentos_clave", [])
            emo_c     = EMOTION_COLORS.get(emo, C_MUTED)

            row = [[
                Paragraph(f"<b>{nombre}</b><br/><font size='8' color='#6b6b8a'>{perfil}</font>",
                          S["body"]),
                _pill(emo, emo_c),
                _pill(f"Participación {nivel}", C_ACCENT if nivel=="Alto" else C_MUTED),
            ]]
            t = Table(row, colWidths=["55%","22%","23%"])
            t.setStyle(TableStyle([
                ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
                ("BACKGROUND",   (0,0), (-1,-1), C_LIGHT),
                ("ROUNDEDCORNERS", (0,0), (-1,-1), [6,6,6,6]),
                ("TOPPADDING",   (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0), (-1,-1), 8),
                ("LEFTPADDING",  (0,0), (-1,-1), 10),
            ]))
            story.append(KeepTogether([t, Spacer(1, 6)]))

            if momentos:
                for m in momentos[:2]:
                    story.append(Paragraph(f"   → {m}", S["muted"]))
                story.append(Spacer(1, 4))

    # ── MOMENTOS CRÍTICOS ──────────────────────────────────────────────────────
    momentos = analysis.get("momentos_criticos", [])
    if momentos:
        story.append(Paragraph("Momentos críticos", S["h2"]))
        mc_data = [["Tiempo", "Tipo", "Descripción", "Speakers"]]
        for m in momentos:
            mc_data.append([
                Paragraph(m.get("timestamp","—"), S["body"]),
                Paragraph(m.get("tipo","—"), S["body"]),
                Paragraph(m.get("descripcion",""), S["body"]),
                Paragraph(", ".join(m.get("speakers_involucrados",[])), S["muted"]),
            ])
        mc_table = Table(mc_data, colWidths=["10%","14%","52%","24%"])
        mc_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), C_PRIMARY),
            ("TEXTCOLOR",    (0,0), (-1,0), C_WHITE),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,0), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_LIGHT]),
            ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ]))
        story.append(mc_table)

    # ── TEMAS CON CARGA EMOCIONAL ──────────────────────────────────────────────
    temas_emo = analysis.get("temas_con_carga_emocional", [])
    if temas_emo:
        story.append(Paragraph("Temas con carga emocional", S["h2"]))
        for t in temas_emo:
            tema  = t.get("tema","")
            carga = t.get("carga","Mixta")
            intens= t.get("intensidad","Media")
            obs   = t.get("observacion","")
            c     = EMOTION_COLORS.get(carga, C_MUTED)

            row = [[
                Paragraph(f"<b>{tema}</b><br/><font size='8'>{obs}</font>", S["body"]),
                _pill(carga, c),
                _pill(intens, C_ACCENT if intens=="Alta" else C_MUTED),
            ]]
            tt = Table(row, colWidths=["62%","18%","20%"])
            tt.setStyle(TableStyle([
                ("VALIGN",      (0,0),(-1,-1),"MIDDLE"),
                ("TOPPADDING",  (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("LEFTPADDING", (0,0),(-1,-1), 8),
                ("LINEBELOW",   (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0f0")),
            ]))
            story.append(tt)

    # ── DINÁMICA GRUPAL ────────────────────────────────────────────────────────
    patrones = analysis.get("patrones_grupales", {})
    if patrones:
        story.append(Paragraph("Dinámica grupal", S["h2"]))
        pg_data = [
            ["Nivel de consenso",  patrones.get("nivel_consenso","—")],
            ["Líder de opinión",   patrones.get("lider_opinion","—")],
            ["Dinámica",           patrones.get("dinamica_grupal","—")],
        ]
        evitados = patrones.get("temas_evitados", [])
        if evitados:
            pg_data.append(["Temas evitados", ", ".join(evitados)])

        pg_table = Table(pg_data, colWidths=["30%","70%"])
        pg_table.setStyle(TableStyle([
            ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 9),
            ("TEXTCOLOR",     (0,0),(0,-1), C_MUTED),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_LIGHT]),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ]))
        story.append(pg_table)

    # ── INSIGHTS ───────────────────────────────────────────────────────────────
    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(Paragraph("Insights para la investigación", S["h2"]))
        for i, ins in enumerate(insights, 1):
            story.append(Paragraph(f"<b>{i}.</b>  {ins}", S["insight"]))

    # ── RECOMENDACIONES ────────────────────────────────────────────────────────
    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(Paragraph("Recomendaciones", S["h2"]))
        for r in recos:
            story.append(Paragraph(f"→  {r}", S["insight"]))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=8))
    footer_txt = f"Generado por QualBot · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if readai_url:
        footer_txt += f" · Transcripción completa: {readai_url}"
    story.append(Paragraph(footer_txt, S["center"]))

    doc.build(story)
    print(f"  ✅ PDF generado: {filename}")
    return filename


# ── Helpers ────────────────────────────────────────────────────────────────────
def _pill(text, bg_color):
    style = ParagraphStyle("Pill", fontSize=7, textColor=colors.white,
                           fontName="Helvetica-Bold", alignment=TA_CENTER,
                           backColor=bg_color, borderPad=4)
    return Paragraph(text, style)

def _kpi_cell(label, value, color):
    content = f"""<font size='7' color='#6b6b8a'>{label}</font><br/>
<font size='16' color='#{color.hexval()[2:]}' name='Helvetica-Bold'><b>{value}</b></font>"""
    s = ParagraphStyle("KPI", fontSize=9, leading=20,
                       borderPad=10, backColor=colors.HexColor("#f5f5fa"),
                       borderRadius=8)
    return Paragraph(content, s)
