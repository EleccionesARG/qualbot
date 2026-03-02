import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

C_ACCENT = colors.HexColor("#7c6aff")
C_DARK   = colors.HexColor("#1a1a2e")
C_MUTED  = colors.HexColor("#6b6b8a")
C_LIGHT  = colors.HexColor("#f5f5fa")
C_WHITE  = colors.white

EMOTION_COLORS = {
    "Alegría":  colors.HexColor("#ffd166"),
    "Enojo":    colors.HexColor("#ef476f"),
    "Tristeza": colors.HexColor("#118ab2"),
    "Neutral":  colors.HexColor("#aaaaaa"),
    "Sorpresa": colors.HexColor("#06d6a0"),
    "Miedo":    colors.HexColor("#a64ac9"),
    "Disgusto": colors.HexColor("#78290f"),
    "Positiva": colors.HexColor("#06d6a0"),
    "Negativa": colors.HexColor("#ef476f"),
    "Mixta":    colors.HexColor("#ffd166"),
}

def s(name, **kwargs):
    return ParagraphStyle(name, fontName="Helvetica", **kwargs)

def generate_pdf_report(session_id, title, date, speakers, topics, summary, analysis, readai_url=""):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title  = s("T", fontSize=22, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=6)
    S_h2     = s("H2", fontSize=12, textColor=C_ACCENT, fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=12)
    S_body   = s("B", fontSize=9, textColor=C_DARK, spaceAfter=4, leading=13)
    S_muted  = s("M", fontSize=8, textColor=C_MUTED, spaceAfter=3)
    S_center = s("C", fontSize=8, textColor=C_MUTED, alignment=TA_CENTER)

    border = {"style": "SINGLE", "size": 0.5, "col
