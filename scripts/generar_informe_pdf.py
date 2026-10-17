# -*- coding: utf-8 -*-
"""Genera INFORME.pdf (APA 7, trabajo de estudiante) en Documentos/universidad."""

from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "INFORME.pdf"

FONT_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("TimesNewRoman", str(FONT_DIR / "times.ttf")))
pdfmetrics.registerFont(TTFont("TimesNewRoman-Bold", str(FONT_DIR / "timesbd.ttf")))
pdfmetrics.registerFont(TTFont("TimesNewRoman-Italic", str(FONT_DIR / "timesi.ttf")))


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="APACover", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="APATitle", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_CENTER, spaceAfter=24))
    s.add(ParagraphStyle(name="APAHeading1", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_CENTER, spaceBefore=24, spaceAfter=24))
    s.add(ParagraphStyle(name="APAHeading2", fontName="TimesNewRoman-Bold", fontSize=12, leading=24, alignment=TA_LEFT, spaceBefore=24, spaceAfter=12))
    s.add(ParagraphStyle(name="APABody", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_JUSTIFY, firstLineIndent=1.27 * cm, spaceAfter=0))
    s.add(ParagraphStyle(name="APABody0", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_JUSTIFY, firstLineIndent=0))
    s.add(ParagraphStyle(name="APARef", fontName="TimesNewRoman", fontSize=12, leading=24, alignment=TA_LEFT, firstLineIndent=-0.5 * inch, leftIndent=0.5 * inch, spaceAfter=0))
    s.add(ParagraphStyle(name="APATableCell", fontName="TimesNewRoman", fontSize=11, leading=14, alignment=TA_LEFT))
    return s


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("TimesNewRoman", 12)
    canvas.drawRightString(letter[0] - inch, letter[1] - 0.6 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def p(st, text, style="APABody"):
    return Paragraph(text, st[style])


def h_table(st, rows):
    data = [[Paragraph(c, st["APATableCell"]) for c in row] for row in rows]
    t = Table(data, colWidths=[2.4 * inch, 4.0 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "TimesNewRoman-Bold"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, (0, 0, 0)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, (0, 0, 0)),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, (0, 0, 0)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build():
    st = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=2.54 * cm,
        rightMargin=2.54 * cm,
        topMargin=2.54 * cm,
        bottomMargin=2.54 * cm,
        title="Deuda técnica y el sistema de gestión de inventario",
        author="Esteban Amaya",
    )
    story = []

    # Portada
    story.append(Spacer(1, 2.0 * inch))
    story.append(p(st, "Deuda técnica y el sistema de gestión de inventario: diagnóstico, refactorización y validación comportamental", "APATitle"))
    story.append(p(st, "Esteban Amaya", "APACover"))
    story.append(p(st, "[código del estudiante]", "APACover"))
    story.append(p(st, "[programa académico]", "APACover"))
    story.append(p(st, "Mantenimiento de Sistemas de Software — Unidad 2", "APACover"))
    story.append(p(st, "[nombre del docente]", "APACover"))
    story.append(p(st, "17 de octubre de 2026", "APACover"))
    story.append(PageBreak())

    story.append(p(st, "Introducción", "APAHeading1"))
    story.append(p(st, "El presente estudio de caso analiza la deuda técnica de un módulo de gestión de inventario escrito en Python, la diagnostica con herramientas estáticas y dinámicas, aplica una refactorización que preserva el comportamiento observable y demuestra la equivalencia mediante pruebas automatizadas y un checksum de carga fija. El trabajo se alinea con las técnicas de mantenimiento evolutivo y perfectivo (Sommerville, 2016; Pressman &amp; Maxim, 2015) y con la calidad de mantenibilidad descrita en ISO/IEC 25010:2011."))
    story.append(p(st, "Cunningham (1992) definió la deuda técnica como el costo diferido de decisiones de diseño apresuradas. Fowler (2018) sistematizó los <i>bad smells</i> y las refactorizaciones. Martin (2008) enfatizó la limpieza del código como condición de evolución sostenible. Este informe aplica esas ideas al artefacto <i>gestion_inventario.py</i>."))

    story.append(p(st, "Módulo Seleccionado", "APAHeading1"))
    story.append(p(st, "Se seleccionó un sistema de gestión de inventario con la clase pública <i>SistemaGestionInventario</i> y el método <i>procesar_operacion_completa</i>, que concentraba las operaciones ENTRADA, SALIDA, AJUSTE y TRANSFERENCIA. La versión inicial, de 781 líneas según Radon (<i>raw</i>), se conserva en <i>codigo/evidencia/antes/gestion_inventario.py</i>. La API pública —incluidos <i>consultar_stock</i>, <i>valorizar</i>, <i>productos_bajo_minimo</i>, <i>obtener_movimientos</i> y <i>generar_informe_operativo</i>— permanece invariante tras la refactorización."))

    story.append(p(st, "Metodología", "APAHeading1"))
    story.append(p(st, "La metodología comprendió seis pasos. Primero, se construyó deliberadamente un módulo con deuda técnica (duplicación, método largo, código muerto, lista larga de parámetros y diccionarios en lugar de objetos). Segundo, se fijó el comportamiento con pruebas de caracterización en <i>pytest</i> y una carga fija con checksum SHA-256. Tercero, se diagnosticó con Pylint, Radon, Vulture y jscpd (análisis estático) y con <i>pytest</i> más <i>coverage</i>, <i>cProfile</i> y el módulo <i>trace</i> (análisis dinámico). Cuarto, se refactorizó sin cambiar la firma pública ni los mensajes o resultados. Quinto, se reejecutaron pruebas, checksum y reportes posteriores. Sexto, se gestionó el trabajo en Git con ramas <i>diagnostico</i>, <i>refactorizacion</i> y <i>validacion</i>, integradas mediante <i>git merge --no-ff</i>."))

    story.append(p(st, "Diagnóstico de los Bad Smells", "APAHeading1"))
    story.append(p(st, "Método Excesivamente Largo y Complejidad Ciclomática Alta", "APAHeading2"))
    story.append(p(st, "Radon reportó para <i>procesar_operacion_completa</i> una complejidad ciclomática <b>F (67)</b> y un promedio del módulo <b>B (9.93)</b> en la versión inicial. Un solo método concentraba validación y las cuatro operaciones, lo que dificulta pruebas focalizadas y la comprensión del flujo (Fowler, 2018)."))
    story.append(p(st, "Código Duplicado", "APAHeading2"))
    story.append(p(st, "La herramienta jscpd encontró <b>cinco clones</b> y <b>62 líneas duplicadas (7.94 %)</b> asociadas al armado repetido de movimientos y al formato de respuestas. La duplicación eleva el riesgo de correcciones inconsistentes entre operaciones."))
    story.append(p(st, "Código Muerto e Imports sin Uso", "APAHeading2"))
    story.append(p(st, "Vulture detectó imports no usados (<i>json</i>, <i>math</i>, <i>os</i>, <i>random</i>), funciones sin llamados (<i>aplicar_descuento_por_volumen</i>, <i>_formatear_moneda_fantasma</i>, <i>_normalizar_texto_legacy</i>) y atributos escritos pero no leídos (<i>_ultima_auditoria_interna</i>, <i>_cache_valorizacion_obsoleta</i>, <i>_flag_modo_debug_legacy</i>). Ese ruido reduce la legibilidad y genera falsas pistas durante el mantenimiento."))
    story.append(p(st, "Lista Larga de Parámetros", "APAHeading2"))
    story.append(p(st, "La firma pública expone catorce parámetros. Por contrato académico se conservó; internamente se introdujo el objeto de parámetros <i>SolicitudOperacion</i> (Fowler, 2018)."))

    story.append(p(st, "Implicaciones para la Mantenibilidad", "APAHeading1"))
    story.append(p(st, "Según ISO/IEC 25010:2011, la mantenibilidad incluye modularidad, reusabilidad, analizabilidad, modificabilidad y capacidad de ser probado. La deuda inicial degradaba especialmente la analizabilidad (método F(67)), la modificabilidad (cambios repetidos en bloques duplicados) y la capacidad de prueba (dificultad para aislar una operación)."))
    story.append(Spacer(1, 12))
    story.append(h_table(st, [
        ["Subcaracterística", "Efecto observado"],
        ["Analizabilidad", "Método F(67) y duplicación ocultan el flujo por operación"],
        ["Modificabilidad", "Un cambio en movimientos exige editar varios bloques"],
        ["Capacidad de prueba", "Difícil aislar ENTRADA frente a SALIDA"],
        ["Modularidad", "Diccionarios y dead code mezclan dominio con residuos"],
    ]))
    story.append(Paragraph("Tabla 1. Relación entre bad smells e ISO/IEC 25010:2011.", st["APABody0"]))

    story.append(p(st, "Refactorización", "APAHeading1"))
    story.append(p(st, "Se aplicaron, como mínimo, las siguientes técnicas sin alterar el comportamiento externo: extracción de métodos por operación; sustitución de literales mágicos por constantes de mensajes y tipos; introducción del objeto de parámetros <i>SolicitudOperacion</i>; extracción de las clases <i>Producto</i> y <i>Movimiento</i>; renombrado orientado a intención; y eliminación de código muerto. La evidencia del antes permanece en <i>evidencia/antes/</i> y el código vigente en <i>codigo/gestion_inventario.py</i>."))
    story.append(Spacer(1, 12))
    story.append(h_table(st, [
        ["Métrica", "Antes → Después"],
        ["Complejidad promedio (Radon CC)", "B (9.93) → A (4.03)"],
        ["Complejidad de procesar_operacion_completa", "F (67) → orquestación delegada (A)"],
        ["Cobertura (coverage)", "75 % → 90 %"],
        ["Clones jscpd / líneas duplicadas", "5 / 7.94 % → 1 / ≈2 %"],
        ["Checksum carga fija SHA-256", "Idéntico en ambos estados"],
    ]))
    story.append(Paragraph("Tabla 2. Comparación de métricas obtenidas con herramientas ejecutadas.", st["APABody0"]))

    story.append(p(st, "Herramientas Estáticas y Dinámicas", "APAHeading1"))
    story.append(p(st, "Como análisis estático se emplearon Pylint, Radon (complejidad ciclomática, índice de mantenibilidad y métricas raw), Vulture y jscpd. Como análisis dinámico se emplearon <i>pytest</i> con <i>coverage</i>, <i>cProfile</i> sobre la carga fija y el módulo <i>trace</i>. Los reportes se almacenaron en <i>codigo/analisis/antes/</i> y <i>codigo/analisis/despues/</i>. El script <i>codigo/scripts/regenerar_analisis.py</i> permite regenerarlos."))

    story.append(p(st, "Control de Versiones", "APAHeading1"))
    story.append(p(st, "El repositorio Git en <i>codigo/</i> utilizó ramas independientes <i>diagnostico</i>, <i>refactorizacion</i> y <i>validacion</i>, con commits atómicos y mensajes orientados al <i>porqué</i>. Cada rama se integró a <i>main</i> con <i>git merge --no-ff</i>. El archivo <i>codigo/historial_git.txt</i> documenta el grafo y los mensajes para entregas sin la carpeta <i>.git</i>."))

    story.append(p(st, "Pruebas Automatizadas", "APAHeading1"))
    story.append(p(st, "Diecisiete pruebas en <i>tests/test_comportamiento_fijo.py</i> cubren normalización, costo promedio (incluidos stock total en cero y stock negativo), mensajes exactos, el indicador <i>forzar</i>, copias defensivas y el límite de diez movimientos en el informe por bodega. Tras la refactorización el resultado fue <b>17 passed</b>. El checksum SHA-256 de la carga fija coincide antes y después: <i>5b6efe95e65dfd55fab1a73d0ba023c61c4d85418a7d0a569311b7721c379104</i>."))

    story.append(p(st, "Conclusiones", "APAHeading1"))
    story.append(p(st, "El módulo inicial acumulaba deuda que degradaba analizabilidad y modificabilidad. El diagnóstico con Radon, jscpd y Vulture fundamentó al menos tres <i>bad smells</i>. La refactorización aplicó técnicas clásicas de Fowler sin alterar la API ni los resultados. Las pruebas y el checksum demuestran equivalencia comportamental. El flujo Git documenta un ciclo completo de mantenimiento: diagnosticar, refactorizar y validar."))

    story.append(PageBreak())
    story.append(p(st, "Referencias", "APAHeading1"))
    refs = [
        "Cunningham, W. (1992). The WyCash portfolio management system. <i>ACM SIGPLAN OOPS Messenger, 4</i>(2), 29–30. https://doi.org/10.1145/157710.157715",
        "Fowler, M. (2018). <i>Refactoring: Improving the design of existing code</i> (2nd ed.). Addison-Wesley.",
        "International Organization for Standardization. (2011). <i>Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models</i> (ISO/IEC 25010:2011).",
        "Martin, R. C. (2008). <i>Clean code: A handbook of agile software craftsmanship</i>. Prentice Hall.",
        "Pressman, R. S., &amp; Maxim, B. R. (2015). <i>Software engineering: A practitioner’s approach</i> (8th ed.). McGraw-Hill.",
        "Sommerville, I. (2016). <i>Software engineering</i> (10th ed.). Pearson.",
    ]
    for r in refs:
        story.append(p(st, r, "APARef"))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print("PDF:", OUT)
    return OUT


if __name__ == "__main__":
    build()
