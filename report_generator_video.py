import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER

C_ACCENT  = colors.HexColor("#7c6aff")
C_ACCENT2 = colors.HexColor("#ff6a8a")
C_DARK    = colors.HexColor("#1a1a2e")
C_MUTED   = colors.HexColor("#6b6b8a")
C_LIGHT   = colors.HexColor("#f5f5fa")
C_WHITE   = colors.white

EMOTION_COLORS = {
    "Alegría":  "#ffd166",
    "Enojo":    "#ef476f",
    "Tristeza": "#118ab2",
    "Neutral":  "#aaaaaa",
    "Sorpresa": "#06d6a0",
    "Miedo":    "#a64ac9",
    "Disgusto": "#78290f",
}

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)

def generate_video_report(session_id, title, distribution, timeline,
                           dissonances, total_detections, duration_s):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_Video_{session_id}.pdf"

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
        ("BACKGROUND",     (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",      (0,0), (-1,0), C_WHITE),
        ("FONTNAME",       (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",       (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ("GRID",           (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("TOPPADDING",     (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 6),
        ("LEFTPADDING",    (0,0), (-1,-1), 6),
    ])

    story = []

    # Header
    story.append(Paragraph("QualBot — Análisis de Video", S_title))
    story.append(Paragraph(f"{title}  |  {datetime.now().strftime('%d/%m/%Y')}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT2, spaceAfter=12))

    # KPIs
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)
    top_emotion = list(distribution.keys())[0] if distribution else "N/A"

    kpi = Table([[
        Paragraph(f"<b>{mins}m {secs}s</b><br/><font size='7'>Duración</font>", S_body),
        Paragraph(f"<b>{total_detections}</b><br/><font size='7'>Detecciones</font>", S_body),
        Paragraph(f"<b>{top_emotion}</b><br/><font size='7'>Emoción dominante</font>", S_body),
        Paragraph(f"<b>{len(dissonances)}</b><br/><font size='7'>Momentos disonancia</font>", S_body),
    ]], colWidths=["25%","25%","25%","25%"])
    kpi.setStyle(tbl_style)
    story.append(kpi)
    story.append(Spacer(1, 10))

    # Distribución de emociones
    if distribution:
        story.append(Paragraph("Distribución de emociones", S_h2))
        data = [["Emoción", "Detecciones", "Porcentaje"]]
        for emo, info in distribution.items():
            data.append([emo, str(info["count"]), f"{info['pct']}%"])
        t = Table(data, colWidths=["40%","30%","30%"])
        t.setStyle(hdr_style)
        story.append(t)

    # Timeline por minuto
    if timeline:
        story.append(Paragraph("Timeline emocional por minuto", S_h2))
        data = [["Minuto", "Emoción dominante", "Distribución"]]
        for min_key, info in sorted(timeline.items(), key=lambda x: int(x[0])):
            minuto = info["minuto"]
            dom    = info["dominante"]
            conteos = ", ".join([f"{k}: {v}" for k, v in info["conteos"].items()])
            data.append([f"{minuto:02d}:00", dom, conteos])
        t = Table(data, colWidths=["15%","30%","55%"])
        t.setStyle(hdr_style)
        story.append(t)

    # Momentos de disonancia
    if dissonances:
        story.append(Paragraph("Momentos de disonancia (dice X, muestra Y)", S_h2))
        story.append(Paragraph(
            "Estos son los momentos más valiosos para investigación cualitativa — "
            "cuando el lenguaje verbal y el no verbal no coinciden.", S_muted))
        story.append(Spacer(1, 6))
        data = [["Tiempo", "Speaker", "Texto", "Emoción vista", "Observación"]]
        for d in dissonances:
            data.append([
                d.get("timestamp_fmt",""),
                d.get("speaker",""),
                d.get("texto","")[:60],
                d.get("emocion_vista",""),
                d.get("dissonance","")
            ])
        t = Table(data, colWidths=["8%","15%","35%","15%","27%"])
        t.setStyle(hdr_style)
        story.append(t)
    else:
        story.append(Paragraph("Momentos de disonancia", S_h2))
        story.append(Paragraph("No se detectaron momentos de disonancia significativos.", S_muted))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    story.append(Paragraph(f"QualBot Video Analysis  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}", S_foot))

    doc.build(story)
    print(f"PDF de video generado: {path}")
    return path
