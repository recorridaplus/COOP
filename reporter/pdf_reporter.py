"""
pdf_reporter.py — Generador de reportes ejecutivos en PDF.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

DATA_DIR = Path(__file__).parent.parent / "data"
REPORT_JSON_PATH = DATA_DIR / "latest_comparison_report.json"

def export_to_pdf(json_path: Path = REPORT_JSON_PATH, output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = DATA_DIR / "reporte_diferencias_conaprole.pdf"

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#2F225B'),
        alignment=0,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=20
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )

    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10
    )

    story = []

    # Encabezado
    story.append(Paragraph("COOP — Reporte de Diferencias de Productos Conaprole", title_style))
    scraped_time = data.get("generated_at", "")[:19].replace("T", " ")
    story.append(Paragraph(f"Fecha de reporte: {scraped_time} | Productos analizados: {data.get('total_official_products', 0)}", subtitle_style))

    # Tabla de resumen por supermercado
    summary_data = [["Supermercado", "Coincidencias", "Discrepancias"]]
    for sp_name, counts in data.get("matches_summary", {}).items():
        summary_data.append([sp_name, str(counts.get("matches", 0)), str(counts.get("discrepancies", 0))])

    summary_table = Table(summary_data, colWidths=[200, 100, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2F225B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Tabla de hallazgos / discrepancias
    discrepancies = data.get("discrepancies", [])
    if discrepancies:
        story.append(Paragraph(f"<b>Detalle de Discrepancias ({len(discrepancies)})</b>", styles['Heading2']))
        story.append(Spacer(1, 10))

        table_data = [["Alerta", "Supermercado", "Producto Conaprole", "Publicado en Supermercado", "Similitud Nombre"]]

        for item in discrepancies[:40]:  # Limitar a las primeras 40 para el PDF de muestra
            alert = item.get("alert_level", "YELLOW")
            alert_text = "APÓCRIFA" if alert == "RED" else "DIFERENTE"
            sp_name = item.get("supermarket", "")
            off_name = item.get("conaprole_product", {}).get("name", "")
            sp_name_pub = item.get("supermarket_product", {}).get("name", "")
            sim = item.get("name_comparison", {}).get("similarity_score", 0)

            table_data.append([
                Paragraph(f"<b>{alert_text}</b>", cell_bold),
                Paragraph(sp_name, cell_style),
                Paragraph(off_name, cell_style),
                Paragraph(sp_name_pub, cell_style),
                Paragraph(f"{sim}%", cell_style)
            ])

        disc_table = Table(table_data, colWidths=[65, 85, 170, 170, 60])
        disc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4A3B7E')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,0), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(disc_table)

    doc.build(story)
    return output_path

if __name__ == "__main__":
    export_to_pdf()
