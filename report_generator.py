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

def st(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)

def safe_str(val):
    if isinstance(val, dict):
        return str(val.get("insight") or val.get("recomendacion") or val.get("hipotesis") or list(val.values())[0] if val else "")
    return str(val) if val else ""

def tbl(story, data, col_widths, hdr=False):
    C_LIGHT2 = colors.HexColor("#f5f5fa")
    base = [
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0f0")),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
    ]
    if hdr:
        base += [
            ("BACKGROUND",     (0,0), (-1,0),  C_DARK),
            ("TEXTCOLOR",      (0,0), (-1,0),  C_WHITE),
            ("FONTNAME",       (0,0), (-1,0),  "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_LIGHT2]),
        ]
    else:
        base += [("BACKGROUND", (0,0), (-1,-1), C_LIGHT2)]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(base))
    story.append(t)
    story.append(Spacer(1, 4))

def section(story, title, color=None):
    c = color or C_ACCENT
    story.append(Paragraph(title, ParagraphStyle("H2",
        fontName="Helvetica-Bold", fontSize=12,
        textColor=c, spaceAfter=4, spaceBefore=12)))

def generate_pdf_report(session_id, title, date, speakers, topics, summary,
                         analysis, readai_url="", video_analysis=None):
    os.makedirs("reportes", exist_ok=True)
    path = f"reportes/QualBot_{session_id}.pdf"

    doc = SimpleDocTemplate(path, pagesize=A4,
          rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    S_title = st("T", fontSize=20, textColor=C_DARK, fontName="Helvetica-Bold", spaceAfter=6)
    S_sub   = st("S", fontSize=10, textColor=C_MUTED, spaceAfter=4)
    S_body  = st("B", fontSize=9,  textColor=C_DARK,  spaceAfter=4, leading=13)
    S_muted = st("M", fontSize=8,  textColor=C_MUTED, spaceAfter=3)
    S_foot  = st("F", fontSize=8,  textColor=C_MUTED, alignment=TA_CENTER)
    S_label = st("L", fontSize=8,  textColor=C_MUTED, fontName="Helvetica-Bold", spaceAfter=2)

    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph("QualBot — Reporte de Focus Group", S_title))
    has_video = video_analysis and video_analysis.get("resumen_visual")
    badge = "  [Texto + Video]" if has_video else "  [Solo Texto]"
    story.append(Paragraph(f"{title}  |  {date}{badge}", S_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT, spaceAfter=12))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    emo        = analysis.get("emocion_general_sesion", "")
    intensidad = analysis.get("intensidad_emocional", "")
    emo_visual = ""
    if has_video:
        emo_visual = video_analysis.get("patrones_visuales_globales", {}).get("emocion_dominante_visual", "")

    kpi_data = [[
        Paragraph(f"<b>{emo}</b><br/><font size='7'>Emocion (texto)</font>", S_body),
        Paragraph(f"<b>{intensidad}</b><br/><font size='7'>Intensidad</font>", S_body),
        Paragraph(f"<b>{len(speakers)}</b><br/><font size='7'>Participantes</font>", S_body),
        Paragraph(f"<b>{emo_visual or '-'}</b><br/><font size='7'>Emocion (video)</font>", S_body),
    ]]
    tbl(story, kpi_data, ["25%","25%","25%","25%"])

    # ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────────
    section(story, "Resumen ejecutivo")
    story.append(Paragraph(analysis.get("resumen_ejecutivo", ""), S_body))
    if has_video and video_analysis.get("resumen_visual"):
        story.append(Paragraph(f"<b>Visual:</b> {video_analysis['resumen_visual']}", S_muted))
    if summary:
        story.append(Paragraph(f"<i>Read.ai: {summary}</i>", S_muted))

    # ── TEMPERATURA GRUPAL ────────────────────────────────────────────────────
    temp = analysis.get("temperatura_grupal", {})
    if temp:
        section(story, "Temperatura grupal")
        rows = [[k, v] for k, v in [
            ("Inicio",         temp.get("inicio","")),
            ("Desarrollo",     temp.get("desarrollo","")),
            ("Cierre",         temp.get("cierre","")),
            ("Arco narrativo", temp.get("arco_narrativo","")),
        ] if v]
        if rows:
            tbl(story, rows, ["22%","78%"])

    # ── PARTICIPANTES ─────────────────────────────────────────────────────────
    participantes = analysis.get("participantes", [])
    if participantes:
        section(story, "Participantes")
        for p in participantes:
            tbl(story, [[
                Paragraph(f"<b>{p.get('nombre','')}</b>", S_body),
                Paragraph(p.get("emocion_predominante",""), S_body),
                Paragraph(f"Participacion {p.get('nivel_participacion','')}", S_muted),
            ]], ["40%","30%","30%"])
            for campo, label in [
                ("perfil_psicologico","Perfil"),
                ("perfil_emocional","Perfil"),
                ("estilo_comunicacional","Estilo"),
                ("postura_real_vs_declarada","Postura real vs declarada"),
                ("momento_mas_revelador","Momento mas revelador"),
            ]:
                if p.get(campo):
                    story.append(Paragraph(f"{label}: {p[campo]}", S_muted))
            story.append(Spacer(1, 4))

    # ── DINAMICAS DE PODER ────────────────────────────────────────────────────
    poder = analysis.get("dinamicas_de_poder", {})
    if poder:
        section(story, "Dinamicas de poder")
        rows = [[k, v] for k, v in [
            ("Lider de opinion",   poder.get("lider_opinion","")),
            ("Seguidor principal", poder.get("seguidor_principal","")),
            ("Voz disidente",      poder.get("voz_disidente","")),
            ("Silenciado",         poder.get("silenciado","")),
            ("Mapa de influencia", poder.get("mapa_de_influencia","")),
        ] if v]
        if rows:
            tbl(story, rows, ["30%","70%"])
        presiones = poder.get("momentos_de_presion_social", [])
        if presiones:
            story.append(Paragraph("Momentos de presion social:", S_label))
            data = [["Tiempo","Quien presiono","Quien cedio","Descripcion"]]
            for pr in presiones:
                data.append([pr.get("timestamp",""), pr.get("quien_presiono",""), pr.get("quien_cedio",""), pr.get("descripcion","")])
            tbl(story, data, ["10%","18%","18%","54%"], hdr=True)

    # ── ANALISIS DEL LENGUAJE ─────────────────────────────────────────────────
    lenguaje = analysis.get("analisis_del_lenguaje", {})
    if lenguaje:
        section(story, "Analisis del lenguaje")
        pos = lenguaje.get("palabras_clave_positivas", [])
        neg = lenguaje.get("palabras_clave_negativas", [])
        if pos or neg:
            tbl(story, [["Positivas", ", ".join(pos)], ["Negativas", ", ".join(neg)]], ["25%","75%"])
        metaforas = lenguaje.get("metaforas_usadas", [])
        if metaforas:
            story.append(Paragraph("Metaforas:", S_label))
            data = [["Metafora","Quien","Interpretacion"]]
            for m in metaforas:
                data.append([m.get("metafora",""), m.get("quien",""), m.get("interpretacion","")])
            tbl(story, data, ["25%","15%","60%"], hdr=True)
        eufemismos = lenguaje.get("eufemismos_detectados", [])
        if eufemismos:
            story.append(Paragraph("Eufemismos:", S_label))
            data = [["Lo que dijeron","Lo que quisieron decir","Quien"]]
            for e in eufemismos:
                data.append([e.get("lo_que_dijeron",""), e.get("lo_que_probablemente_quisieron_decir",""), e.get("quien","")])
            tbl(story, data, ["30%","55%","15%"], hdr=True)
        frases = lenguaje.get("frases_mas_reveladoras", [])
        if frases:
            story.append(Paragraph("Frases mas reveladoras:", S_label))
            data = [["Tiempo","Quien","Frase","Por que importa"]]
            for f in frases:
                data.append([f.get("timestamp",""), f.get("quien",""), f.get("frase",""), f.get("por_que_importa","")])
            tbl(story, data, ["8%","12%","35%","45%"], hdr=True)

    # ── LO NO DICHO ───────────────────────────────────────────────────────────
    no_dicho = analysis.get("lo_no_dicho", {})
    if no_dicho:
        section(story, "Lo no dicho")
        evitados = no_dicho.get("temas_evitados", [])
        if evitados:
            story.append(Paragraph("Temas evitados:", S_label))
            data = [["Tema","Evidencia","Posible razon"]]
            for e in evitados:
                data.append([e.get("tema",""), e.get("evidencia",""), e.get("posible_razon","")])
            tbl(story, data, ["20%","40%","40%"], hdr=True)
        silencios = no_dicho.get("silencios_significativos", [])
        if silencios:
            story.append(Paragraph("Silencios significativos:", S_label))
            data = [["Tiempo","Contexto","Interpretacion"]]
            for s in silencios:
                data.append([s.get("timestamp",""), s.get("contexto",""), s.get("interpretacion","")])
            tbl(story, data, ["10%","40%","50%"], hdr=True)

    # ── CONTRADICCIONES ───────────────────────────────────────────────────────
    contradicciones = analysis.get("contradicciones", [])
    if contradicciones:
        section(story, "Contradicciones")
        data = [["Participante","Dijo primero","Dijo despues","Interpretacion"]]
        for c in contradicciones:
            data.append([c.get("participante",""), c.get("dijo_primero",""), c.get("dijo_despues",""), c.get("interpretacion","")])
        tbl(story, data, ["15%","25%","25%","35%"], hdr=True)

    # ── MOMENTOS CRITICOS ─────────────────────────────────────────────────────
    momentos = analysis.get("momentos_criticos", [])
    if momentos:
        section(story, "Momentos criticos")
        data = [["Tiempo","Tipo","Descripcion","Por que importa"]]
        for m in momentos:
            data.append([m.get("timestamp",""), m.get("tipo",""), m.get("descripcion",""), m.get("importancia_investigativa","")])
        tbl(story, data, ["10%","15%","40%","35%"], hdr=True)

    # ── TEMAS CON CARGA EMOCIONAL ─────────────────────────────────────────────
    temas = analysis.get("temas_con_carga_emocional", [])
    if temas:
        section(story, "Temas con carga emocional")
        data = [["Tema","Carga","Intensidad","Observacion","Implicancia"]]
        for t in temas:
            data.append([t.get("tema",""), t.get("carga",""), t.get("intensidad",""), t.get("observacion",""), t.get("implicancia_para_marca","")])
        tbl(story, data, ["16%","10%","10%","34%","30%"], hdr=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN DE VIDEO (si está disponible)
    # ══════════════════════════════════════════════════════════════════════════
    if has_video:
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT2, spaceAfter=8))
        story.append(Paragraph("ANÁLISIS VISUAL — Lenguaje no verbal", st("VH",
            fontName="Helvetica-Bold", fontSize=14, textColor=C_ACCENT2, spaceAfter=6)))

        # Patrones visuales globales
        pat = video_analysis.get("patrones_visuales_globales", {})
        if pat:
            section(story, "Patrones visuales globales", C_ACCENT2)
            rows = [[k, v] for k, v in [
                ("Emocion dominante visual",  pat.get("emocion_dominante_visual","")),
                ("Momentos de tension",       ", ".join(pat.get("momentos_tension_visual", []))),
                ("Momentos de apertura",      ", ".join(pat.get("momentos_apertura_visual", []))),
                ("Lenguaje corporal grupal",  pat.get("lenguaje_corporal_grupal","")),
            ] if v]
            if rows:
                tbl(story, rows, ["30%","70%"])

        # Observaciones por frame
        obs = video_analysis.get("observaciones_por_frame", [])
        if obs:
            section(story, "Observaciones frame a frame", C_ACCENT2)
            data = [["Tiempo","Lo que se vio","Expresiones","Coherencia con discurso"]]
            for o in obs:
                exps = "; ".join([f"{e.get('persona','')}: {e.get('emocion','')}" for e in o.get("expresiones",[])])
                data.append([
                    o.get("timestamp",""),
                    o.get("descripcion_visual",""),
                    exps,
                    o.get("coherencia_con_discurso",""),
                ])
            tbl(story, data, ["8%","35%","30%","27%"], hdr=True)

        # Disonancias visuales
        disonancias = video_analysis.get("disonancias_detectadas", [])
        if disonancias:
            section(story, "Disonancias texto vs cara", C_ACCENT2)
            story.append(Paragraph(
                "Momentos donde el lenguaje corporal contradice lo que se estaba diciendo.", S_muted))
            data = [["Tiempo","Lo que se decia","Lo que mostraba el cuerpo","Interpretacion"]]
            for d in disonancias:
                data.append([d.get("timestamp",""), d.get("lo_que_se_decia",""), d.get("lo_que_mostraba_el_cuerpo",""), d.get("interpretacion","")])
            tbl(story, data, ["8%","28%","28%","36%"], hdr=True)

        # Insights visuales
        insights_v = video_analysis.get("insights_visuales", [])
        if insights_v:
            section(story, "Insights visuales", C_ACCENT2)
            for i, ins in enumerate(insights_v, 1):
                if isinstance(ins, dict):
                    story.append(Paragraph(f"<b>{i}. {ins.get('insight','')}</b>", S_body))
                    if ins.get("evidencia"):
                        story.append(Paragraph(f"Evidencia: {ins.get('evidencia')}", S_muted))
                    if ins.get("implicancia"):
                        story.append(Paragraph(f"Implicancia: {ins.get('implicancia')}", S_muted))
                else:
                    story.append(Paragraph(f"{i}. {safe_str(ins)}", S_body))
                story.append(Spacer(1, 3))

    # ══════════════════════════════════════════════════════════════════════════
    # INSIGHTS Y RECOMENDACIONES (texto)
    # ══════════════════════════════════════════════════════════════════════════
    insights = analysis.get("insights_investigacion", [])
    if insights:
        section(story, "Insights de investigacion")
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
        section(story, "Hipotesis no confirmadas")
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
        section(story, "Recomendaciones")
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
        section(story, "Proximos pasos")
        for p in proximos:
            story.append(Paragraph(f"->  {safe_str(p)}", S_body))

    nota = analysis.get("nota_metodologica", "")
    if nota:
        section(story, "Nota metodologica")
        story.append(Paragraph(nota, S_muted))

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
