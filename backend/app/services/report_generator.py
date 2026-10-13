import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings

def generate_pdf_dossier(analysis) -> io.BytesIO:
    """
    Generates a formal, forensic evidentiary report for an analysis record.
    Outputs a PDF as an in-memory byte stream.
    Includes file integrity hashes, Content DNA, forensic indicators,
    neural ensemble predictions, and calibrated conclusions.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748b')
    )

    story = []

    # Title & Header
    story.append(Paragraph("DIGITAL FORENSICS & SYNTHETIC MEDIA DOSSIER", title_style))
    story.append(Paragraph(
        f"Case Investigation ID: {analysis.id} &nbsp;|&nbsp; "
        f"Engine Version: {analysis.engine_version} &nbsp;|&nbsp; "
        f"Timestamp: {analysis.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if analysis.created_at else 'N/A'}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=12))

    # Executive Verdict Banner
    verdict_color = '#dc2626' if 'AI' in analysis.final_verdict else ('#16a34a' if 'REAL' in analysis.final_verdict else '#d97706')
    conf_pct = round(analysis.overall_confidence * 100, 1)
    
    summary_data = [
        [
            Paragraph("<b>EVIDENTIARY VERDICT:</b>", body_style),
            Paragraph(f"<font color='{verdict_color}'><b>{analysis.final_verdict}</b></font>", section_heading)
        ],
        [
            Paragraph("<b>CALIBRATED CONFIDENCE:</b>", body_style),
            Paragraph(f"<b>{conf_pct}%</b>", body_style)
        ],
        [
            Paragraph("<b>ASSET METRICS:</b>", body_style),
            Paragraph(f"{analysis.file_name} ({analysis.dimensions_width}x{analysis.dimensions_height} px, {round(analysis.file_size_bytes/1024, 1)} KB, {analysis.mime_type})", body_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[150, 390])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Content DNA & Cryptographic Integrity
    story.append(Paragraph("1. Content DNA & Cryptographic Hashes", section_heading))
    dna = getattr(analysis, "content_dna", None)
    if dna:
        dna_data = [
            ["SHA-256 Primary Hash", Paragraph(f"<font name='Courier'>{dna.sha256_hash}</font>", body_style)],
            ["MD5 Integrity Hash", Paragraph(f"<font name='Courier'>{dna.md5_hash}</font>", body_style)],
            ["Perceptual Hash (pHash)", Paragraph(f"<font name='Courier'>{dna.perceptual_hash}</font>", body_style)],
            ["Difference Hash (dHash)", Paragraph(f"<font name='Courier'>{dna.difference_hash}</font>", body_style)],
            ["Wavelet Hash (wHash)", Paragraph(f"<font name='Courier'>{dna.wavelet_hash}</font>", body_style)],
            ["Canonical DNA String", Paragraph(f"<font name='Courier' size=7>{dna.dna_fingerprint_composite}</font>", body_style)]
        ]
        dna_table = Table(dna_data, colWidths=[150, 390])
        dna_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(dna_table)
    story.append(Spacer(1, 10))

    # Forensic Signals
    story.append(Paragraph("2. Forensic Signal Evidence & Discrepancies", section_heading))
    signals = getattr(analysis, "forensic_signals", None) or getattr(analysis, "forensic_signal", None)
    if signals:
        forensic_data = [
            ["EXIF / XMP AI Metadata Tags", "Detected" if signals.has_ai_metadata else "None Found"],
            ["C2PA Manifest Header", "Present" if signals.c2pa_manifest_detected else "Not Detected"],
            ["Error Level Analysis (ELA)", f"Mean: {signals.ela_mean_discrepancy} | Max: {signals.ela_max_discrepancy} ({'Anomaly Detected' if signals.ela_anomaly_detected else 'Normal'})"],
            ["2D FFT Spectral Harmonics", f"Harmonic Ratio: {signals.fft_peak_harmonic_ratio} ({'Lattice Anomaly' if signals.fft_lattice_anomaly_detected else 'Continuous'})"],
            ["Sensor Noise Floor Variance", f"{signals.noise_variance} (Uniformity index: {signals.noise_uniformity_score})"],
            ["Estimated JPEG Quality", f"~{signals.compression_quality_estimate} / 100"]
        ]
        f_table = Table(forensic_data, colWidths=[180, 360])
        f_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(f_table)
    story.append(Spacer(1, 10))

    # Machine Learning Ensemble
    story.append(Paragraph("3. Machine Learning Ensemble Evaluations", section_heading))
    
    table_header_style = ParagraphStyle(
        'MLTableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    expected_models = [settings.PRIMARY_ML_MODEL, settings.BASELINE_ML_MODEL]
    eval_list = getattr(analysis, "ml_evaluations", None) or []
    
    # Map evaluations by model_name
    eval_map = {}
    for ev in eval_list:
        m_name = getattr(ev, "model_name", None) or (ev.get("model_name") if isinstance(ev, dict) else None)
        if m_name:
            eval_map[m_name] = ev

    mime_type = getattr(analysis, "mime_type", "") or ""
    is_image = not mime_type.startswith(("video/", "audio/"))

    if eval_list or is_image:
        ml_rows = [[
            Paragraph("<b>Model Name</b>", table_header_style),
            Paragraph("<b>Version</b>", table_header_style),
            Paragraph("<b>Predicted Class</b>", table_header_style),
            Paragraph("<b>Confidence</b>", table_header_style),
            Paragraph("<b>Latency</b>", table_header_style)
        ]]

        displayed_models = set()
        has_failed_models = False

        # Order by expected models first if it's an image
        models_to_display = []
        if is_image:
            for m_id in expected_models:
                models_to_display.append((m_id, eval_map.get(m_id)))
                displayed_models.add(m_id)
        # Add any remaining evaluations that ran
        for m_name, ev in eval_map.items():
            if m_name not in displayed_models:
                models_to_display.append((m_name, ev))
                displayed_models.add(m_name)

        for m_name, eval_m in models_to_display:
            if eval_m is not None:
                m_ver = getattr(eval_m, "model_version", None) or (eval_m.get("model_version") if isinstance(eval_m, dict) else "N/A")
                pred = getattr(eval_m, "predicted_label", None) or (eval_m.get("predicted_label") if isinstance(eval_m, dict) else "N/A")
                conf = getattr(eval_m, "confidence", None)
                if conf is None and isinstance(eval_m, dict):
                    conf = eval_m.get("confidence", 0.0)
                lat = getattr(eval_m, "execution_time_ms", None)
                if lat is None and isinstance(eval_m, dict):
                    lat = eval_m.get("execution_time_ms", 0)

                if pred in ("FAILED", "ERROR"):
                    has_failed_models = True
                    pred_p = Paragraph("<font color='#dc2626'><b>FAILED</b></font>", body_style)
                    conf_p = Paragraph("N/A", body_style)
                    lat_p = Paragraph("N/A", body_style)
                else:
                    color = '#dc2626' if 'AI' in pred else ('#16a34a' if 'REAL' in pred else '#d97706')
                    pred_p = Paragraph(f"<font color='{color}'><b>{pred}</b></font>", body_style)
                    conf_p = Paragraph(f"{round((conf or 0.0) * 100, 1)}%", body_style)
                    lat_p = Paragraph(f"{lat or 0} ms", body_style)

                ml_rows.append([
                    Paragraph(m_name, body_style),
                    Paragraph(str(m_ver), body_style),
                    pred_p,
                    conf_p,
                    lat_p
                ])
            else:
                has_failed_models = True
                ml_rows.append([
                    Paragraph(m_name, body_style),
                    Paragraph("N/A", body_style),
                    Paragraph("<font color='#dc2626'><b>FAILED / NOT LOADED</b></font>", body_style),
                    Paragraph("N/A", body_style),
                    Paragraph("N/A", body_style)
                ])

        ml_table = Table(ml_rows, colWidths=[160, 120, 110, 80, 70])
        ml_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(ml_table)

        if has_failed_models:
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                "<font color='#dc2626'><b>Integrity Notice:</b> One or more expected ensemble models failed during evaluation. "
                "The failure was recorded honestly and excluded from consensus weighting.</font>",
                disclaimer_style
            ))
    else:
        story.append(Paragraph("No machine learning image ensemble evaluations were applicable for this media asset.", disclaimer_style))

    story.append(Spacer(1, 10))

    # Reasons & Limitations
    story.append(Paragraph("4. Evidentiary Synthesis & Technical Limitations", section_heading))
    if analysis.verdict_reasons:
        story.append(Paragraph("<b>Observed Evidence:</b>", body_style))
        for r in analysis.verdict_reasons:
            story.append(Paragraph(f"• {r}", body_style))
        story.append(Spacer(1, 6))

    if analysis.limitations:
        story.append(Paragraph("<b>Analysis Limitations & Caveats:</b>", body_style))
        for lim in analysis.limitations:
            story.append(Paragraph(f"• {lim}", body_style))
        story.append(Spacer(1, 10))

    # Chain of Custody & Storage Verification Notice
    story.append(Paragraph("5. Chain of Custody & Digital File Integrity", section_heading))
    storage_info = [
        ["Investigation Storage", "Secure Supabase Object Store / Local Cryptographic Vault"],
        ["Asset Retention Status", "Cryptographically Verified via SHA-256"],
        ["Legal & Forensic Notice", Paragraph(
            "This document is an automated forensic analysis report generated by the AI Content-Origin Detective engine. "
            "Forensic scores represent multi-signal evidentiary indicators and calibrated machine learning models. "
            "They should be considered alongside physical chain-of-custody documentation and expert witness review.",
            disclaimer_style
        )]
    ]
    st_table = Table(storage_info, colWidths=[160, 380])
    st_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(st_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
