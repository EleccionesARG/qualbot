
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

def safe_str(val):
    if isinstance(val, dict):
        return str(val.get("insight") or val.get("recomendacion") or val.get("hipotesis") or list(val.values())[0] if val else "")
    return str(val) if val else ""

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
    S_label = st("L", fontSize=8, textColor=C_MUTED, fontName="Helvetica-Bold", spaceAfter=2)

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

    emo        = analysis.get("emocion_general_sesion", "")
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

    temp = analysis.get("temperatura_grupal", {})
    if temp:
        story.append(Paragraph("Temperatura grupal", S_h2))
        data = [
            ["Inicio",         temp.get("inicio", "")],
            ["Desarrollo",     temp.get("desarrollo", "")],
            ["Cierre",         temp.get("cierre", "")],
            ["Arco narrativo", temp.get("arco_narrativo", "")],
        ]
        t = Table([[k, v] for k, v in data if v], colWidths=["22%","78%"])
        t.setStyle(tbl_style)
        story.append(t)

    participantes = analysis.get("participantes", [])
    if participantes:
        story.append(Paragraph("Participantes", S_h2))
        for p in participantes:
            data = [[
                Paragraph(f"<b>{p.get('nombre','')}</b>", S_body),
                Paragraph(p.get("emocion_predominante",""), S_body),
                Paragraph(f"Participacion {p.get('nivel_participacion','')}", S_muted),
            ]]
            t = Table(data, colWidths=["40%","30%","30%"])
            t.setStyle(tbl_style)
            story.append(t)
            for campo, label in [
                ("perfil_psicologico",         "Perfil"),
                ("perfil_emocional",            "Perfil"),
                ("estilo_comunicacional",       "Estilo"),
                ("postura_real_vs_declarada",   "Postura real vs declarada"),
                ("momento_mas_revelador",       "Momento mas revelador"),
            ]:
                val = p.get(campo, "")
                if val:
                    story.append(Paragraph(f"{label}: {val}", S_muted))
            story.append(Spacer(1, 4))

    poder = analysis.get("dinamicas_de_poder", {})
    if poder:
        story.append(Paragraph("Dinamicas de poder", S_h2))
        campos = [
            ("Lider de opinion",   poder.get("lider_opinion", "")),
            ("Seguidor principal", poder.get("seguidor_principal", "")),
            ("Voz disidente",      poder.get("voz_disidente", "")),
            ("Silenciado",         poder.get("silenciado", "")),
            ("Mapa de influencia", poder.get("mapa_de_influencia", "")),
        ]
        rows = [[k, v] for k, v in campos if v]
        if rows:
            t = Table(rows, colWidths=["30%","70%"])
            t.setStyle(tbl_style)
            story.append(t)
        presiones = poder.get("momentos_de_presion_social", [])
        if presiones:
            story.append(Paragraph("Momentos de presion social:", S_label))
            data = [["Tiempo","Quien presiono","Quien cedio","Descripcion"]]
            for pr in presiones:
                data.append([pr.get("timestamp",""), pr.get("quien_presiono",""), pr.get("quien_cedio",""), pr.get("descripcion","")])
            t = Table(data, colWidths=["10%","18%","18%","54%"])
            t.setStyle(hdr_style)
            story.append(t)

    lenguaje = analysis.get("analisis_del_lenguaje", {})
    if lenguaje:
        story.append(Paragraph("Analisis del lenguaje", S_h2))
        pos = lenguaje.get("palabras_clave_positivas", [])
        neg = lenguaje.get("palabras_clave_negativas", [])
        if pos or neg:
            t = Table([["Palabras positivas", ", ".join(pos)], ["Palabras negativas", ", ".join(neg)]], colWidths=["28%","72%"])
            t.setStyle(tbl_style)
            story.append(t)
            story.append(Spacer(1, 4))
        metaforas = lenguaje.get("metaforas_usadas", [])
        if metaforas:
            story.append(Paragraph("Metaforas:", S_label))
            data = [["Metafora","Quien","Interpretacion"]]
            for m in metaforas:
                data.append([m.get("metafora",""), m.get("quien",""), m.get("interpretacion","")])
            t = Table(data, colWidths=["25%","15%","60%"])
            t.setStyle(hdr_style)
            story.append(t)
            story.append(Spacer(1, 4))
        eufemismos = lenguaje.get("eufemismos_detectados", [])
        if eufemismos:
            story.append(Paragraph("Eufemismos detectados:", S_label))
            data = [["Lo que dijeron","Lo que quisieron decir","Quien"]]
            for e in eufemismos:
                data.append([e.get("lo_que_dijeron",""), e.get("lo_que_probablemente_quisieron_decir",""), e.get("quien","")])
            t = Table(data, colWidths=["30%","55%","15%"])
            t.setStyle(hdr_style)
            story.append(t)
            story.append(Spacer(1, 4))
        frases = lenguaje.get("frases_mas_reveladoras", [])
        if frases:
            story.append(Paragraph("Frases mas reveladoras:", S_label))
            data = [["Tiempo","Quien","Frase","Por que importa"]]
            for f in frases:
                data.append([f.get("timestamp",""), f.get("quien",""), f.get("frase",""), f.get("por_que_importa","")])
            t = Table(data, colWidths=["8%","12%","35%","45%"])
            t.setStyle(hdr_style)
            story.append(t)

    no_dicho = analysis.get("lo_no_dicho", {})
    if no_dicho:
        story.append(Paragraph("Lo no dicho", S_h2))
        evitados = no_dicho.get("temas_evitados", [])
        if evitados:
            story.append(Paragraph("Temas evitados:", S_label))
            data = [["Tema","Evidencia","Posible razon"]]
            for e in evitados:
                data.append([e.get("tema",""), e.get("evidencia",""), e.get("posible_razon","")])
            t = Table(data, colWidths=["20%","40%","40%"])
            t.setStyle(hdr_style)
            story.append(t)
            story.append(Spacer(1, 4))
        silencios = no_dicho.get("silencios_significativos", [])
        if silencios:
            story.append(Paragraph("Silencios significativos:", S_label))
            data = [["Tiempo","Contexto","Interpretacion"]]
            for s in silencios:
                data.append([s.get("timestamp",""), s.get("contexto",""), s.get("interpretacion","")])
            t = Table(data, colWidths=["10%","40%","50%"])
            t.setStyle(hdr_style)
            story.append(t)

    contradicciones = analysis.get("contradicciones", [])
    if contradicciones:
        story.append(Paragraph("Contradicciones", S_h2))
        data = [["Participante","Dijo primero","Dijo despues","Interpretacion"]]
        for c in contradicciones:
            data.append([c.get("participante",""), c.get("dijo_primero",""), c.get("dijo_despues",""), c.get("interpretacion","")])
        t = Table(data, colWidths=["15%","25%","25%","35%"])
        t.setStyle(hdr_style)
        story.append(t)

    momentos = analysis.get("momentos_criticos", [])
    if momentos:
        story.append(Paragraph("Momentos criticos", S_h2))
        data = [["Tiempo","Tipo","Descripcion","Por que importa"]]
        for m in momentos:
            data.append([m.get("timestamp",""), m.get("tipo",""), m.get("descripcion",""), m.get("importancia_investigativa","")])
        t = Table(data, colWidths=["10%","15%","40%","35%"])
        t.setStyle(hdr_style)
        story.append(t)

    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        story.append(Paragraph("Temas con carga emocional", S_h2))
        data = [["Tema","Carga","Intensidad","Observacion","Implicancia"]]
        for t in temas:
            data.append([t.get("tema",""), t.get("carga",""), t.get("intensidad",""), t.get("observacion",""), t.get("implicancia_para_marca","")])
        tbl = Table(data, colWidths=["16%","10%","10%","34%","30%"])
        tbl.setStyle(hdr_style)
        story.append(tbl)

    insights = analysis.get("insights_investigacion", [])
    if insights:
        story.append(Paragraph("Insights", S_h2))
        for i, ins in enumerate(insights, 1):
            if isinstance(ins, dict):
                story.append(Paragraph(f"<b>{i}. {ins.get('insight','')}</b>", S_body))
                if ins.get("evidencia"):
                    story.append(Paragraph(f"Evidencia: {ins.get('evidencia')}", S_muted))
                if ins.get("implicancia"):
                    story.append(Paragraph(f"Implicancia: {ins.get('implicancia')}", S_muted))
                if ins.get("nivel_confianza"):
                    story.append(Paragraph(f"Confianza: {ins.get('nivel_confianza')}", S_muted))
            else:
                story.append(Paragraph(f"{i}. {safe_str(ins)}", S_body))
            story.append(Spacer(1, 4))

    hipotesis = analysis.get("hipotesis_no_confirmadas", [])
    if hipotesis:
        story.append(Paragraph("Hipotesis no confirmadas", S_h2))
        for h in hipotesis:
            if isinstance(h, dict):
                story.append(Paragraph(f"<b>{h.get('hipotesis','')}</b>", S_body))
                if h.get("indicios"):
                    story.append(Paragraph(f"Indicios: {h.get('indicios')}", S_muted))
                if h.get("como_validar"):
                    story.append(Paragraph(f"Como validar: {h.get('como_validar')}", S_muted))
            else:
                story.append(Paragraph(safe_str(h), S_body))
            story.append(Spacer(1, 3))

    recos = analysis.get("recomendaciones", [])
    if recos:
        story.append(Paragraph("Recomendaciones", S_h2))
        for r in recos:
            if isinstance(r, dict):
                story.append(Paragraph(f"<b>[{r.get('prioridad','')}]  {r.get('recomendacion','')}</b>", S_body))
                if r.get("justificacion"):
                    story.append(Paragraph(f"Justificacion: {r.get('justificacion')}", S_muted))
            else:
                story.append(Paragraph(f"->  {safe_str(r)}", S_body))
            story.append(Spacer(1, 4))

    proximos = analysis.get("proximos_pasos_investigacion", [])
    if proximos:
        story.append(Paragraph("Proximos pasos de investigacion", S_h2))
        for p in proximos:
            story.append(Paragraph(f"->  {safe_str(p)}", S_body))

    nota = analysis.get("nota_metodologica", "")
    if nota:
        story.append(Paragraph("Nota metodologica", S_h2))
        story.append(Paragraph(nota, S_muted))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_MUTED, spaceAfter=6))
    footer = f"QualBot  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if readai_url:
        footer += f"  |  {readai_url}"
    story.append(Paragraph(footer, S_foot))

    doc.build(story)
    print(f"PDF generado: {path}")
    return path
