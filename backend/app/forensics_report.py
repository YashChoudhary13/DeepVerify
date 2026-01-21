# app/forensics_report.py
"""
Professional forensic metadata analysis PDF report generator.
Generates polished reports suitable for technical and forensic analysis.
"""

import hashlib
import io
from datetime import datetime
from typing import Dict, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def compute_file_hash(image_bytes: bytes) -> str:
    """Compute SHA-256 hash of image file."""
    return hashlib.sha256(image_bytes).hexdigest()


def generate_forensic_report(
    metadata_analysis: Dict[str, Any],
    image_bytes: bytes,
    filename: str,
    file_size: int,
) -> bytes:
    """
    Generate a professional forensic metadata analysis PDF report.
    
    Args:
        metadata_analysis: Output from analyze_forensic_image_bytes()
        image_bytes: Raw image file bytes
        filename: Original filename
        file_size: File size in bytes
        
    Returns:
        PDF file as bytes
    """
    # Compute file hash
    file_hash = compute_file_hash(image_bytes)
    
    # Create PDF buffer
    pdf_buffer = io.BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title="Image Metadata & Encoding Forensics Report",
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderPadding=6,
    )
    
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        leading=12,
        leftIndent=10,
        spaceAfter=8,
        fontName='Helvetica-Oblique',
    )
    
    # Build document
    story = []
    
    # ===== HEADER SECTION =====
    story.append(Paragraph("IMAGE METADATA &amp; ENCODING FORENSICS", title_style))
    story.append(Paragraph("DeepVerify Analysis Report", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Header info table
    header_data = [
        ["<b>File Name</b>", filename],
        ["<b>File Size</b>", f"{file_size:,} bytes"],
        ["<b>File Hash (SHA-256)</b>", file_hash[:32] + "<br/>" + file_hash[32:]],
        ["<b>Analysis Timestamp</b>", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["<b>Report Version</b>", "1.0 - Metadata-Only Analysis"],
    ]
    
    header_table = Table(header_data, colWidths=[2.0*inch, 4.0*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))
    
    # ===== EXECUTIVE SUMMARY =====
    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    
    categories = metadata_analysis.get('categories', {})
    forensic_summary = categories.get('Forensic Assessment', {})
    
    evidence_capture = forensic_summary.get('Evidence of Capture', 'None detected')
    evidence_synth = forensic_summary.get('Evidence of Synthetic/Post-Processing', 'None detected')
    inconclusive = forensic_summary.get('Inconclusive Signals', '')
    
    # Determine verdict
    if evidence_synth and evidence_synth != 'None detected':
        verdict_text = "Metadata suggests synthetic or post-processed origin"
        confidence = "Medium to High"
    elif evidence_capture and evidence_capture != 'None detected':
        verdict_text = "Metadata is consistent with camera-captured images"
        confidence = "Medium to High"
    else:
        verdict_text = "Metadata evidence is inconclusive"
        confidence = "Low"
    
    summary_text = f"""
    <b>Verdict:</b> {verdict_text}<br/>
    <b>Confidence Level:</b> {confidence}<br/>
    <br/>
    This analysis is based exclusively on metadata and encoding characteristics.
    It does not employ machine learning models or pixel-level analysis.
    <br/>
    """
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 6))
    
    # ===== CAPTURE METADATA (EXIF) ANALYSIS =====
    story.append(Paragraph("1. CAPTURE METADATA (EXIF) ANALYSIS", heading_style))
    
    exif_data = categories.get('EXIF Metadata', {})
    
    if exif_data.get('Status') == 'Missing or stripped':
        story.append(Paragraph("<b>EXIF Data:</b> Not Present", subheading_style))
        story.append(Paragraph(
            "Absence of capture metadata is common in AI-generated and re-shared images and is treated as a forensic signal. "
            "However, legitimate photographs also have EXIF stripped by many social media platforms, messaging apps, and cloud services.",
            note_style
        ))
    else:
        story.append(Paragraph("<b>EXIF Data:</b> Present", subheading_style))
        exif_table_data = [["<b>Field</b>", "<b>Value</b>"]]
        
        # Extract key EXIF fields
        key_fields = ['Make', 'Model', 'DateTime', 'DateTimeOriginal', 'Software', 'LensModel']
        for field in key_fields:
            if field in exif_data:
                value = str(exif_data[field])[:60]
                exif_table_data.append([field, value])
        
        if len(exif_table_data) > 1:
            exif_table = Table(exif_table_data, colWidths=[2.0*inch, 4.0*inch])
            exif_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0f2fe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0369a1')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(exif_table)
        else:
            story.append(Paragraph("No EXIF metadata fields detected.", note_style))
    
    story.append(Spacer(1, 12))
    
    # ===== JPEG CONTAINER & ENCODING ANALYSIS =====
    story.append(Paragraph("2. JPEG CONTAINER &amp; ENCODING ANALYSIS", heading_style))
    
    basic_info = categories.get('Basic Information', {})
    encoding_info = categories.get('Encoding & Container', {})
    
    encoding_text = f"""
    <b>Image Format:</b> {basic_info.get('Format', 'Unknown')}<br/>
    <b>Dimensions:</b> {basic_info.get('Dimensions', 'Unknown')}<br/>
    <b>Color Mode:</b> {basic_info.get('Color Mode', 'Unknown')}<br/>
    """
    story.append(Paragraph(encoding_text, body_style))
    
    if encoding_info:
        story.append(Paragraph("<b>Encoding Characteristics:</b>", subheading_style))
        
        enc_table_data = [["<b>Property</b>", "<b>Value</b>"]]
        for key, value in encoding_info.items():
            if value and str(value).strip() != 'Not specified':
                enc_table_data.append([key, str(value)])
        
        if len(enc_table_data) > 1:
            enc_table = Table(enc_table_data, colWidths=[2.2*inch, 3.8*inch])
            enc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f9ff')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(enc_table)
    
    story.append(Spacer(1, 8))
    
    # Encoding interpretation
    interpretation = _interpret_encoding(basic_info, encoding_info, exif_data)
    story.append(Paragraph("<b>Interpretation:</b>", subheading_style))
    story.append(Paragraph(interpretation, note_style))
    
    story.append(Spacer(1, 12))
    
    # ===== QUANTIZATION ANALYSIS =====
    quant_info = categories.get('Quantization Analysis', {})
    if quant_info and any(v for v in quant_info.values() if v != 'No quantization data'):
        story.append(Paragraph("3. QUANTIZATION ANALYSIS", heading_style))
        
        quant_table_data = [["<b>Parameter</b>", "<b>Value</b>"]]
        for key, value in quant_info.items():
            if value:
                quant_table_data.append([key, str(value)])
        
        if len(quant_table_data) > 1:
            quant_table = Table(quant_table_data, colWidths=[2.0*inch, 4.0*inch])
            quant_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#92400e')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fffbeb')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(quant_table)
        
        story.append(Spacer(1, 12))
    
    # ===== FORENSIC ASSESSMENT =====
    story.append(Paragraph("4. FORENSIC ASSESSMENT &amp; VERDICT", heading_style))
    
    story.append(Paragraph("<b>Evidence of Authentic Capture:</b>", subheading_style))
    capture_items = evidence_capture.split('\n') if evidence_capture else ['None detected']
    for item in capture_items:
        if item.strip():
            story.append(Paragraph(f"• {item.strip()}", body_style))
    
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>Evidence of Synthetic/Post-Processing:</b>", subheading_style))
    synth_items = evidence_synth.split('\n') if evidence_synth else ['None detected']
    for item in synth_items:
        if item.strip():
            story.append(Paragraph(f"• {item.strip()}", body_style))
    
    story.append(Spacer(1, 12))
    
    # Final verdict box
    verdict_box = f"""
    <b>METADATA-ONLY VERDICT:</b><br/>
    {verdict_text}<br/>
    <br/>
    <i>This verdict is based exclusively on metadata and encoding analysis. 
    It does not incorporate machine learning, pixel analysis, or statistical modeling.</i>
    """
    story.append(Paragraph(verdict_box, note_style))
    
    story.append(Spacer(1, 16))
    
    # ===== LIMITATIONS & SCOPE =====
    story.append(Paragraph("5. LIMITATIONS &amp; SCOPE", heading_style))
    
    limitations_text = """
    <b>Important Limitations:</b><br/>
    <br/>
    • Metadata can be stripped, altered, or mimicked using specialized tools<br/>
    • Absence of EXIF does not confirm image manipulation or synthetic origin<br/>
    • Quantization patterns alone cannot definitively identify AI-generated images<br/>
    • This tool is designed to complement, not replace, model-based forensic analysis<br/>
    • Metadata analysis should be used as one signal among many in a comprehensive forensic investigation<br/>
    <br/>
    <b>Scope:</b> This analysis focuses on container format, encoding characteristics, and metadata presence/absence only.
    """
    
    story.append(Paragraph(limitations_text, note_style))
    
    story.append(Spacer(1, 12))
    
    # ===== FOOTER =====
    story.append(Spacer(1, 12))
    footer_text = f"""
    <b>Report Integrity:</b> This report was generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}.<br/>
    File Hash: {file_hash}<br/>
    For verification, compute SHA-256 of the original image and compare with the hash above.
    """
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        leading=10,
        borderPadding=6,
    )
    
    story.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def _interpret_encoding(
    basic_info: Dict[str, Any],
    encoding_info: Dict[str, Any],
    exif_data: Dict[str, Any],
) -> str:
    """Generate human-readable interpretation of encoding characteristics."""
    
    interpretations = []
    
    # Chroma subsampling interpretation
    chroma = encoding_info.get('Chroma Subsampling', '')
    if '4:4:4' in str(chroma):
        interpretations.append(
            "4:4:4 chroma subsampling preserves full color information and is "
            "atypical for camera JPEGs, which typically use 4:2:0 or 4:2:2. "
            "This pattern is consistent with certain editing or synthesis workflows."
        )
    elif '4:2:0' in str(chroma):
        interpretations.append(
            "4:2:0 chroma subsampling is standard for camera-captured JPEG images, "
            "where color information is reduced without significant visual loss."
        )
    
    # EXIF segment presence
    exif_present = encoding_info.get('EXIF Segment', 'Unknown')
    if 'No' in str(exif_present):
        interpretations.append(
            "The JPEG APP1 segment (which contains EXIF metadata) is absent. "
            "This indicates either metadata stripping or synthesis without capture metadata."
        )
    
    # Quantization uniformity
    quant_uniformity = encoding_info.get('Quantization Uniformity', '')
    if 'uniform' in str(quant_uniformity).lower():
        interpretations.append(
            "Quantization tables exhibit extreme uniformity, which is atypical for camera captures. "
            "This pattern is consistent with synthetic generation or aggressive re-encoding."
        )
    
    # Camera EXIF presence
    has_exif = bool(exif_data) and exif_data.get('Status') != 'Missing or stripped'
    if has_exif and ('Make' in exif_data or 'Model' in exif_data):
        interpretations.append(
            "Presence of camera make and model in EXIF is consistent with authentic camera capture."
        )
    
    if not interpretations:
        interpretations.append(
            "Encoding characteristics do not present strong indicators of either synthetic origin or authentic capture."
        )
    
    return " ".join(interpretations)
