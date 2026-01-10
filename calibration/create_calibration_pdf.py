"""
Calibration PDF Generator for Jan Document Plugin

Creates a test PDF with known content to verify extraction is working correctly.
The PDF contains specific test patterns that can be validated after extraction.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Check for reportlab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
except ImportError:
    print("Installing reportlab for PDF generation...")
    os.system(f"{sys.executable} -m pip install reportlab")
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors


# ============================================================================
# Calibration Content - Known Values for Verification
# ============================================================================

CALIBRATION_DATA = {
    "magic_string": "JANDOC_CALIBRATION_V1_VERIFIED",
    "test_numbers": [42, 137, 256, 1024, 2048],
    "test_phrase": "The quick brown fox jumps over the lazy dog",
    "technical_terms": [
        "ChromaDB vector embeddings",
        "sentence-transformers all-MiniLM-L6-v2",
        "Tesseract OCR engine",
        "FastAPI uvicorn server"
    ],
    "qa_pairs": [
        ("What is the calibration magic string?", "JANDOC_CALIBRATION_V1_VERIFIED"),
        ("What embedding model does this plugin use?", "all-MiniLM-L6-v2"),
        ("What is the sum of test numbers?", "3507"),
        ("What port does the proxy run on?", "1338"),
    ],
    "version": "1.2.0",
    "timestamp_format": "%Y-%m-%d %H:%M:%S"
}


def create_calibration_pdf(output_path: str = None) -> str:
    """
    Create a calibration PDF with known, verifiable content.

    Returns the path to the created PDF.
    """
    if output_path is None:
        output_path = Path(__file__).parent / "JanDocPlugin_Calibration.pdf"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue
    )

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.darkgreen
    )

    code_style = ParagraphStyle(
        'Code',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=10,
        backColor=colors.lightgrey,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10
    )

    story = []

    # Title
    story.append(Paragraph("Jan Document Plugin - Calibration Document", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime(CALIBRATION_DATA['timestamp_format'])}",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))

    # Purpose section
    story.append(Paragraph("Purpose", section_style))
    story.append(Paragraph(
        "This document is used to verify that the Jan Document Plugin is correctly "
        "extracting and indexing PDF content. After uploading this document, you can "
        "ask specific questions to confirm the system is working properly.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    # Magic String section
    story.append(Paragraph("Calibration Magic String", section_style))
    story.append(Paragraph(
        f"The unique calibration identifier is: <b>{CALIBRATION_DATA['magic_string']}</b>",
        styles['Normal']
    ))
    story.append(Paragraph(
        "If the AI can tell you this exact string, PDF extraction is working correctly.",
        styles['Italic']
    ))
    story.append(Spacer(1, 10))

    # Test Numbers section
    story.append(Paragraph("Test Numbers", section_style))
    numbers_str = ", ".join(str(n) for n in CALIBRATION_DATA['test_numbers'])
    total = sum(CALIBRATION_DATA['test_numbers'])
    story.append(Paragraph(
        f"The test numbers are: {numbers_str}",
        styles['Normal']
    ))
    story.append(Paragraph(
        f"The sum of these numbers is: <b>{total}</b>",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    # Technical Terms section
    story.append(Paragraph("Technical Components", section_style))
    story.append(Paragraph(
        "This plugin uses the following technologies:",
        styles['Normal']
    ))
    for term in CALIBRATION_DATA['technical_terms']:
        story.append(Paragraph(f"• {term}", styles['Normal']))
    story.append(Spacer(1, 10))

    # Configuration section
    story.append(Paragraph("Default Configuration", section_style))
    config_data = [
        ["Setting", "Value"],
        ["Proxy Port", "1338"],
        ["Jan Port", "1337"],
        ["Embedding Model", "all-MiniLM-L6-v2"],
        ["Vector Store", "ChromaDB"],
        ["Auto-inject Context", "True"],
        ["Max Context Tokens", "8000"],
    ]

    config_table = Table(config_data, colWidths=[2.5*inch, 3*inch])
    config_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
    ]))
    story.append(config_table)
    story.append(Spacer(1, 20))

    # Verification Questions section
    story.append(Paragraph("Verification Questions", section_style))
    story.append(Paragraph(
        "After uploading this document, ask the AI these questions to verify extraction:",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    qa_data = [["Question", "Expected Answer"]]
    for q, a in CALIBRATION_DATA['qa_pairs']:
        qa_data.append([q, a])

    qa_table = Table(qa_data, colWidths=[3.5*inch, 2.5*inch])
    qa_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(qa_table)
    story.append(Spacer(1, 20))

    # Pangram section (tests character extraction)
    story.append(Paragraph("Character Extraction Test", section_style))
    story.append(Paragraph(
        f"Pangram: <i>{CALIBRATION_DATA['test_phrase']}</i>",
        styles['Normal']
    ))
    story.append(Paragraph(
        "This sentence contains every letter of the alphabet and tests character extraction.",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))

    # Footer
    story.append(Paragraph("━" * 60, styles['Normal']))
    story.append(Paragraph(
        f"<b>Jan Document Plugin v{CALIBRATION_DATA['version']}</b> | "
        "Built for AVACHATTER by Anywave Creations",
        styles['Normal']
    ))

    # Build PDF
    doc.build(story)

    print(f"[OK] Calibration PDF created: {output_path}")
    return str(output_path)


def get_verification_data() -> dict:
    """
    Return the calibration data for verification scripts.
    """
    return CALIBRATION_DATA.copy()


if __name__ == "__main__":
    pdf_path = create_calibration_pdf()
    print(f"\nCalibration PDF ready at: {pdf_path}")
    print("\nTo verify extraction:")
    print("1. Upload this PDF to Jan Document Plugin")
    print("2. Ask: 'What is the calibration magic string?'")
    print(f"3. Expected answer: {CALIBRATION_DATA['magic_string']}")
