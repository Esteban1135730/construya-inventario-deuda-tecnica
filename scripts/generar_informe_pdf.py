# -*- coding: utf-8 -*-
"""Genera INFORME.pdf (APA 7) alineado al anexo ConstruYA. Máx. ~8 páginas."""

from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "INFORME.pdf"
REPO = "https://github.com/Esteban1135730/construya-inventario-deuda-tecnica"

FONT_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("TimesNewRoman", str(FONT_DIR / "times.ttf")))
pdfmetrics.registerFont(TTFont("TimesNewRoman-Bold", str(FONT_DIR / "timesbd.ttf")))
pdfmetrics.registerFont(TTFont("TimesNewRoman-Italic", str(FONT_DIR / "timesi.ttf")))


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="APACover", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="APATitle", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_CENTER, spaceAfter=24))
    s.add(ParagraphStyle(name="APAHeading1", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_CENTER, spaceBefore=24, spaceAfter=24))
    s.add(ParagraphStyle(name="APAHeading2", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_LEFT, spaceBefore=18, spaceAfter=12))
    s.add(ParagraphStyle(name="APABody", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_JUSTIFY, firstLineIndent=1.27 * cm))
    s.add(ParagraphStyle(name="APABody0", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_JUSTIFY, firstLineIndent=0, spaceBefore=6, spaceAfter=6))
    s.add(ParagraphStyle(name="APARef", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_LEFT, firstLineIndent=-0.5 * inch, leftIndent=0.5 * inch))
    s.add(ParagraphStyle(name="APATableCell", fontName="TimesNewRoman", fontSize=10, leading=13, alignment=TA_LEFT))
    return s


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("TimesNewRoman", 12)
    canvas.drawRightString(letter[0] - inch, letter[1] - 0.6 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def p(st, text, style="APABody"):
    return Paragraph(text, st[style])


def h_table(st, rows, widths=None):
    data = [[Paragraph(c, st["APATableCell"]) for c in row] for row in rows]
    t = Table(data, colWidths=widths or [2.2 * inch, 4.2 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "TimesNewRoman-Bold"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, (0, 0, 0)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, (0, 0, 0)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, (0, 0, 0)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build():
    st = styles()
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.54 * cm, rightMargin=2.54 * cm,
        topMargin=2.54 * cm, bottomMargin=2.54 * cm,
        title="Deuda técnica en el inventario de ConstruYA",
        author="Esteban Amaya",
    )
    story = []

    story.append(Spacer(1, 1.8 * inch))
    story.append(p(st, "Deuda técnica en el inventario de ConstruYA: diagnóstico, refactorización y validación comportamental", "APATitle"))
    story.append(p(st, "Esteban Amaya", "APACover"))
    story.append(p(st, "[código del estudiante]", "APACover"))
    story.append(p(st, "[programa académico]", "APACover"))
    story.append(p(st, "Mantenimiento de Sistemas de Software — Unidad 2", "APACover"))
    story.append(p(st, "[nombre del docente]", "APACover"))
    story.append(p(st, "17 de octubre de 2026", "APACover"))
    story.append(PageBreak())

    story.append(p(st, "Introducción", "APAHeading1"))
    story.append(p(st, "ConstruYA es una cadena de ferreterías que, desde hace ocho años, opera un sistema de gestión de inventario desarrollado internamente. El sistema cumple su función, pero ha acumulado deuda técnica: código duplicado, métodos excesivamente extensos, ausencia histórica de pruebas automatizadas y un control de versiones desordenado. Cada solicitud de cambio —por ejemplo, integrar una pasarela de pagos o corregir errores reportados por usuarios— toma más tiempo y eleva el riesgo de nuevas fallas."))
    story.append(p(st, "En el rol de ingeniero de mantenimiento de software, este informe documenta la intervención completa sobre un módulo crítico del inventario: diagnóstico de <i>bad smells</i>, refactorización, gestión Git, automatización de pruebas y validación de no-regresión. El marco teórico se apoya en Cunningham (1992), Fowler (2018), Martin (2008), ISO/IEC 25010:2011, Pressman y Maxim (2015) y Sommerville (2016)."))
    story.append(p(st, f"Repositorio Git (acceso de lectura): <link href=\"{REPO}\">{REPO}</link>.", "APABody0"))

    story.append(p(st, "Módulo Seleccionado", "APAHeading1"))
    story.append(p(st, "Se intervino el módulo Python <i>SistemaGestionInventario</i> (operaciones ENTRADA, SALIDA, AJUSTE y TRANSFERENCIA), de propósito análogo al inventario de ConstruYA. La versión con deuda (781 líneas según Radon) se conserva en <i>evidencia/antes/gestion_inventario.py</i>. La versión refactorizada es <i>gestion_inventario.py</i>. La API pública —incluida <i>procesar_operacion_completa</i> y las consultas de stock, valorización, mínimos, movimientos e informe operativo— no se modificó."))

    story.append(p(st, "Metodología", "APAHeading1"))
    story.append(p(st, "El procedimiento siguió el anexo de la actividad: (1) selección de un módulo ≥ 150 líneas con deuda; (2) diagnóstico con al menos una herramienta de análisis estático (Pylint, Radon, Vulture, jscpd) y evidencia dinámica (<i>pytest</i>+coverage, cProfile, <i>trace</i>); (3) refactorización con al menos tres técnicas documentadas antes/después; (4) Git con rama independiente de refactorización, commits atómicos y <i>merge</i> a la rama principal; (5) pruebas automatizadas tipo xUnit (<i>pytest</i>) que demuestran preservación del comportamiento externo."))

    story.append(p(st, "Diagnóstico de los Bad Smells", "APAHeading1"))
    story.append(p(st, "Método Excesivamente Largo", "APAHeading2"))
    story.append(p(st, "Antes, <i>procesar_operacion_completa</i> concentraba validación y las cuatro operaciones. Radon reportó complejidad <b>F (67)</b> y promedio del módulo <b>B (9.93)</b>. El efecto es baja analizabilidad y alto riesgo al corregir un solo tipo de movimiento."))
    story.append(p(st, "Código Duplicado", "APAHeading2"))
    story.append(p(st, "El armado del movimiento y de la respuesta se repetía en cada rama. jscpd encontró <b>cinco clones</b> y <b>62 líneas duplicadas (7.94 %)</b>, lo que favorece correcciones inconsistentes entre operaciones."))
    story.append(p(st, "Código Muerto y Generalidad Especulativa", "APAHeading2"))
    story.append(p(st, "Vulture detectó imports no usados, funciones de IVA/descuento nunca llamadas y atributos escritos sin lectura. Ese ruido genera falsa sensación de funcionalidad y dificulta el mantenimiento."))
    story.append(p(st, "Aglomeración de Datos", "APAHeading2"))
    story.append(p(st, "La firma pública expone catorce parámetros y el estado interno usaba diccionarios genéricos. Aunque la firma se conservó por contrato, internamente se introdujo el objeto <i>SolicitudOperacion</i>."))

    story.append(p(st, "Implicaciones para la Mantenibilidad", "APAHeading1"))
    story.append(p(st, "Según ISO/IEC 25010:2011, la deuda degradaba analizabilidad, modificabilidad, capacidad de prueba y modularidad. Ello explica el síntoma de negocio de ConstruYA: cada cambio tarda más y aumenta el riesgo de regresión."))

    story.append(p(st, "Refactorización", "APAHeading1"))
    story.append(p(st, "Se documentan las intervenciones antes/después:"))
    story.append(Spacer(1, 8))
    story.append(h_table(st, [
        ["Técnica", "Antes → Después"],
        ["Extract Method", "Un método F(67) → métodos por operación"],
        ["Replace Magic Literal", "Mensajes embebidos → constantes"],
        ["Introduce Parameter Object", "14 argumentos → SolicitudOperacion (API intacta)"],
        ["Extract Class", "Diccionarios → Producto y Movimiento"],
        ["Remove Dead Code", "IVA/descuentos/imports → eliminados"],
    ], [2.5 * inch, 3.9 * inch]))
    story.append(p(st, "Tabla 1. Técnicas de refactorización aplicadas.", "APABody0"))
    story.append(Spacer(1, 8))
    story.append(h_table(st, [
        ["Métrica", "Antes → Después"],
        ["Complejidad promedio (Radon)", "B (9.93) → A (4.03)"],
        ["Cobertura (coverage)", "75 % → 90 %"],
        ["Clones jscpd", "5 (7.94 %) → 1 (≈2 %)"],
        ["Checksum carga fija", "Idéntico (no-regresión)"],
    ]))
    story.append(p(st, "Tabla 2. Métricas obtenidas con herramientas ejecutadas.", "APABody0"))

    story.append(p(st, "Herramientas, Git y Pruebas", "APAHeading1"))
    story.append(p(st, "Los reportes estáticos y dinámicos están en <i>analisis/antes/</i> y <i>analisis/despues/</i>. El control de versiones usó las ramas <i>diagnostico</i>, <i>refactorizacion</i> y <i>validacion</i>, integradas con <i>git merge --no-ff</i>. Diecisiete pruebas <i>pytest</i> resultaron en <b>17 passed</b>. Checksum SHA-256 idéntico: <i>5b6efe95e65dfd55fab1a73d0ba023c61c4d85418a7d0a569311b7721c379104</i>."))

    story.append(p(st, "Reflexión Final y Conclusiones", "APAHeading1"))
    story.append(p(st, "El mantenimiento perfectivo y preventivo reduce el “interés” de la deuda técnica (Cunningham, 1992): ConstruYA puede integrar cambios con menor riesgo si el inventario es modular, testeado y versionado. La refactorización no añade funcionalidades; recupera capacidad de evolución sostenible (Sommerville, 2016). Se cumplió el ciclo diagnóstico–refactorización–validación con evidencia instrumental y repositorio público para el docente."))

    story.append(PageBreak())
    story.append(p(st, "Referencias", "APAHeading1"))
    for r in [
        "Cunningham, W. (1992). The WyCash portfolio management system. <i>ACM SIGPLAN OOPS Messenger, 4</i>(2), 29–30. https://doi.org/10.1145/157710.157715",
        "Fowler, M. (2018). <i>Refactoring: Improving the design of existing code</i> (2nd ed.). Addison-Wesley.",
        "International Organization for Standardization. (2011). <i>Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models</i> (ISO/IEC 25010:2011).",
        "Martin, R. C. (2008). <i>Clean code: A handbook of agile software craftsmanship</i>. Prentice Hall.",
        "Pressman, R. S., &amp; Maxim, B. R. (2015). <i>Software engineering: A practitioner’s approach</i> (8th ed.). McGraw-Hill.",
        "Sommerville, I. (2016). <i>Software engineering</i> (10th ed.). Pearson.",
    ]:
        story.append(p(st, r, "APARef"))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print("PDF:", OUT)
    return OUT


if __name__ == "__main__":
    build()
