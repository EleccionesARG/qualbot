import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER

C_ACCENT = colors.HexColor("#7c6aff")
C_DARK   = colors.HexColor("#1a1a2e")
C_MUTED  = colors.HexColor("#6b6b8a")
C_LIGHT  = colors.HexColor("#f5f5fa")
C_WHITE  = colors.white

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)

def generate_pdf_report(session_id, title, date, speakers, topics, summary, analysis, readai_url=""):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T", fontSize=20, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=6)
    S_sub   = st("S", fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_h2    = st("H2", fontSize=12, textColor=C_ACCENT, fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=12)
    S_body  = st("B", fontSize=9, textColor=C_DARK, spaceAfter=4, leading=13)
    S_muted = st("M", fontSize=8, textColor=C_MUTED, spaceAfter=3)
    S_foot  = st("F", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)

    tbl_style = TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
    ])

    hdr_style = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), C_WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ])

    story = []

    story.append(Paragraph("QualBot — Reporte de Focus Group", S_title))
    story.append(Paragraph(f"{title}  |  {date}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=12))

    emo       = analysis.get("emocion_general_sesion", "")
    intensidad = analysis.get("intensidad_emocional", "")

    kpi = Table([[
        Paragraph(f"<b>{emo}</b><br/><font size='7'>Emocion general</font>", S_body),
        Paragraph(f"<b>{intensidad}</b><br/><font size='7'>Intensidad</font>", S_body),
        Paragraph(f"<b>{len(speakers)}</b><br/><font size='7'>Participantes</font>", S_body),
        Paragraph(f"<b>{len(topics)}</b><br/><font size='7'>Temas</font>", S_body),
    ]], colWidths=["25%","25%","25%","25%"])
    kpi.setStyle(tbl_style)
    story.append(kpi)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Resumen ejecutivo", S_h2))
    story.append(Paragraph(analysis.get("resumen_ejecutivo", ""), S_body))
    if summary:
        story.append(Paragraph(f"Resumen Read.ai: {summary}", S_muted))

    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(Paragraph("Participantes", S_h2))
        for p in participantes:
            t = Table([[
                Paragraph(f"<b>{p.get('nombre','')}</b>  {p.get('perfil_emocional','')}", S_body),
                Paragraph(p.get("emocion_predominante",""), S_body),
                Paragraph(f"Participacion {p.get('nivel_participacion','')}", S_muted),
            ]], colWidths=["55%","22%","23%"])
            t.setStyle(tbl_style)
            story.append(t)
            story.append(Spacer(1, 4))

    momentos = analysis.get("momentos_criticos", [])
    if momentos:
        story.append(Paragraph("Momentos criticos", S_h2))
        data = [["Tiempo", "Tipo", "Descripcion"]]
        for m in momentos:
            data.append([
                m.get("timestamp",""),
                m.get("tipo",""),
                m.get("descripcion","")
            ])
        t = Table(data, colWidths=["10%","15%","75%"])
        t.setStyle(hdr_style)
        story.append(t)

    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        story.append(Paragraph("Temas con carga emocional", S_h2))
        data = [["Tema", "Carga", "Intensidad", "Observacion"]]
        for t in temas:
            data.append([
                t.get("tema",""),
                t.get("carga",""),
                t.get("intensidad",""),
                t.get("observacion","")
            ])
        tbl = Table(data, colWidths=["20%","12%","12%","56%"])
        tbl.setStyle(hdr_style)
        story.append(tbl)

    patrones = analysis.get("patrones_grupales", {})
    if patrones:
        story.append(Paragraph("Dinamica grupal", S_h2))
        data = [
            ["Nivel de consenso", patrones.get("nivel_consenso","")],
            ["Lider de opinion",  patrones.get("lider_opinion","")],
            ["Dinamica",          patrones.get("dinamica_grupal","")],
        ]
        evitados = patrones.get("temas_evitados", [])
        if evitados:
            data.append(["Temas evitados", ", ".join(evitados)])
        tbl = Table(data, colWidths=["30%","70%"])
        tbl.setStyle(tbl_style)
        story.append(tbl)

    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(Paragraph("Insights", S_h2))
        for i, ins in enumerate(insights, 1):
            story.append(Paragraph(f"{i}.  {ins}", S_body))

    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(Paragraph("Recomendaciones", S_h2))
        for r in recos:
            story.append(Paragraph(f"->  {r}", S_body))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    footer = f"QualBot  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if readai_url:
        footer += f"  |  {readai_url}"
    story.append(Paragraph(footer, S_foot))

    doc.build(story)
    print(f"PDF generado: {path}")
    return path
