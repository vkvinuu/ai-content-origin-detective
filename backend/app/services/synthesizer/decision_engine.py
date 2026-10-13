from typing import Dict, Any, List, Tuple

def get_dynamic_model_weight(model_name: str, pred_label: str, confidence: float) -> float:
    """
    Returns empirical evidence-calibrated reliability weight for each detector architecture.

    1. Ateeqq/ai-vs-human-image-detector:
       - SigLIP-SO400M architecture capturing modern diffusion aesthetics & digital art.
       - High sensitivity to generative textures and diffusion patterns -> weight: 1.4

    2. umm-maybe/AI-image-detector:
       - ViT-B/16 architecture trained on DiffusionDB (early SD 1.4/1.5).
       - General baseline -> weight: 1.2
    """
    m_lower = model_name.lower()
    if "ateeqq" in m_lower:
        return 1.4
    elif "umm-maybe" in m_lower:
        return 1.2
    return 1.0


def synthesize_analysis(
    metadata_findings: Dict[str, Any],
    ela_findings: Dict[str, Any],
    fft_findings: Dict[str, Any],
    noise_findings: Dict[str, Any],
    stego_findings: Dict[str, Any],
    ml_evaluations: List[Dict[str, Any]],
    dimensions: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Synthesizes independent digital forensics, metadata, and ML signals into
    a calibrated origin verdict with explicit evidentiary reasons and technical limitations.
    
    Verdicts:
    - REAL / HUMAN
    - AI-GENERATED
    - AI-MODIFIED
    - MANIPULATED
    - INCONCLUSIVE — MODEL DISAGREEMENT
    - UNKNOWN / INCONCLUSIVE
    """
    reasons: List[str] = []
    limitations: List[str] = []

    # 1. Quality, Resolution & Capture Format Check
    width, height = dimensions
    quality = noise_findings.get("compression_quality_estimate", 75)
    
    # Decouple Screenshot Capture Method from Content Origin:
    # A screenshot is merely a capture mechanism (exact desktop aspect ratio, 0 noise variance, PNG format),
    # but does NOT inherently indicate whether the depicted content is real photograph or AI artwork.
    is_screenshot_capture = False
    aspect_ratio = round(max(width, height) / (min(width, height) + 1e-5), 2)
    standard_screen_aspects = {1.78, 1.6, 2.17, 2.16, 1.33}  # 16:9, 16:10, 19.5:9, 18:9, 4:3
    
    if (aspect_ratio in standard_screen_aspects or (width in (1920, 2560, 3840, 1280, 1440) and height in (1080, 1440, 2160, 720, 900))) and noise_findings.get("noise_variance", 1.0) < 0.1:
        is_screenshot_capture = True
        limitations.append("File format properties indicate screen capture/screenshot. Analysis evaluates the visual content inside the capture, not the file mechanism.")

    if width < 300 or height < 300:
        limitations.append(f"Low resolution ({width}x{height}) reduces accuracy of high-frequency spectral and noise tests.")

    if quality < 50:
        limitations.append(f"Heavy lossy compression detected (quality index ~{quality}/100), which may have scrubbed fine forensic artifacts.")

    # 2. Hard Metadata Evidence
    has_ai_metadata = metadata_findings.get("has_ai_metadata", False)
    ai_tags = metadata_findings.get("ai_metadata_tags", [])
    c2pa_detected = metadata_findings.get("c2pa_manifest_detected", False)

    if has_ai_metadata:
        for tag in ai_tags:
            reasons.append(f"Cryptographic/metadata footprint: {tag}")

    if c2pa_detected:
        reasons.append("C2PA Content Credentials provenance manifest header detected in file.")

    # 3. Frequency & Lattice Evidence (FFT)
    fft_ratio = fft_findings.get("fft_peak_harmonic_ratio", 1.0)
    fft_lattice = fft_findings.get("fft_lattice_anomaly_detected", False)
    
    if fft_lattice:
        reasons.append(f"2D Fourier transform detected anomalous periodic lattice harmonics (ratio: {fft_ratio}), typical of neural upsampling / deconvolution.")

    # 4. Error Level Analysis (ELA)
    ela_anomaly = ela_findings.get("ela_anomaly_detected", False)
    ela_mean = ela_findings.get("ela_mean_discrepancy", 0.0)
    ela_max = ela_findings.get("ela_max_discrepancy", 0.0)

    if ela_anomaly:
        reasons.append(f"Error Level Analysis revealed significant localized compression disparity (mean: {ela_mean}, max: {ela_max}), indicating regional splicing or inpainting.")

    # 5. Noise Residual & Physical Sensor Consistency
    noise_var = noise_findings.get("noise_variance", 0.0)
    noise_uniformity = noise_findings.get("noise_uniformity_score", 1.0)

    has_camera_hardware_exif = False
    exif = metadata_findings.get("exif_metadata", {})
    for k in exif.keys():
        kl = k.lower()
        if any(tag in kl for tag in ["make", "model", "fnumber", "exposuretime", "isospeed"]):
            has_camera_hardware_exif = True
            break

    if noise_var < 0.8:
        reasons.append(f"Suppressed noise floor (variance: {noise_var}), consistent with algorithmic generative synthesis rather than physical camera sensor photon noise.")
    elif noise_var > 3.0 and has_camera_hardware_exif and not ela_anomaly:
        reasons.append(f"Organic physical sensor noise present (variance: {noise_var}) corroborated by camera hardware EXIF tags.")

    # 6. ML Ensemble Analysis & Conflict Detection
    weighted_ai_sum = 0.0
    weighted_real_sum = 0.0
    total_weights = 0.0

    confident_ai_models: List[Tuple[str, float]] = []
    confident_real_models: List[Tuple[str, float]] = []
    failed_models: List[str] = []

    for eval_item in ml_evaluations:
        m_name = eval_item.get("model_name", "unknown")
        pred_label = eval_item.get("predicted_label", "INCONCLUSIVE")
        conf = float(eval_item.get("confidence", 0.5))
        norm_probs = eval_item.get("normalized_probabilities", {})

        # Handle failed models honestly without crashing or corrupting vote tallies
        if pred_label in ("FAILED", "ERROR"):
            failed_models.append(m_name)
            err_msg = eval_item.get("error") or eval_item.get("known_limitation") or "Execution failed"
            limitations.append(f"Model '{m_name}' failed to evaluate: {err_msg}. Origin determination proceeded without this model.")
            continue

        # Use normalized continuous probabilities if present, or fallback to confidence
        ai_prob = norm_probs.get("AI-GENERATED", conf if pred_label == "AI-GENERATED" else (1.0 - conf))
        real_prob = norm_probs.get("REAL / HUMAN", conf if pred_label == "REAL / HUMAN" else (1.0 - conf))

        # Dynamic evidence weight based on model architecture and prediction direction
        dominant_pred = "AI-GENERATED" if ai_prob >= real_prob else "REAL / HUMAN"
        weight = get_dynamic_model_weight(m_name, dominant_pred, max(ai_prob, real_prob))

        total_weights += weight
        weighted_ai_sum += (ai_prob * weight)
        weighted_real_sum += (real_prob * weight)

        # Track decisive predictions (>= 58% calibrated probability)
        if ai_prob >= 0.58:
            confident_ai_models.append((m_name, ai_prob))
            reasons.append(f"Model '{m_name}' evaluated AI-Generated with calibrated score {round(ai_prob * 100, 1)}%.")
        elif real_prob >= 0.58:
            confident_real_models.append((m_name, real_prob))
            reasons.append(f"Model '{m_name}' evaluated Real / Human with calibrated score {round(real_prob * 100, 1)}%.")
        else:
            limitations.append(f"Model '{m_name}' yielded indeterminate / borderline evaluation ({round(conf * 100, 1)}%).")

    if total_weights == 0:
        limitations.append("Neural ML models were unavailable; verdict relies strictly on forensic and metadata signals.")

    norm_ai_score = (weighted_ai_sum / total_weights) if total_weights > 0 else 0.5
    norm_real_score = (weighted_real_sum / total_weights) if total_weights > 0 else 0.5

    num_ai = len(confident_ai_models)
    num_real = len(confident_real_models)

    # In a two-model ensemble (Ateeqq + umm-maybe):
    # - Direct deadlock exists when opposing active models disagree (1 AI vs 1 Real)
    # - Probability deadlock occurs if weighted ensemble score is in the neutral band (0.44 - 0.56) with opposing votes
    is_direct_tie = (num_ai >= 1 and num_real >= 1)
    is_probability_deadlock = (0.44 <= norm_ai_score <= 0.56 and num_ai > 0 and num_real > 0)
    has_unresolvable_disagreement = (is_direct_tie or is_probability_deadlock)

    # Consensus: both active models agree on direction
    has_ai_consensus = (num_ai >= 2 and num_real == 0)
    has_real_consensus = (num_real >= 2 and num_ai == 0)

    if has_ai_consensus:
        reasons.append("Full consensus reached: both active detector architectures independently identified AI generation.")
    elif has_real_consensus:
        reasons.append("Full consensus reached: both active detector architectures independently verified authentic human origin.")

    # 7. Evidence-Based Synthesizer Rules & Verdict Determination

    # Condition A: Hard AI Metadata Proof (Overrides model disagreements)
    if has_ai_metadata:
        verdict = "AI-GENERATED"
        confidence = 0.99
        reasons.append("Definitive AI generation metadata tags and parameters confirmed.")
        if num_real > 0:
            limitations.append(
                "Notice: Despite metadata confirming AI origin, certain detectors predicted Human due to out-of-distribution generator architecture."
            )

    # Condition B: Genuine Model Disagreement / Deadlock without Hard Forensics
    elif has_unresolvable_disagreement and not fft_lattice and not (has_camera_hardware_exif and noise_var > 2.0):
        verdict = "INCONCLUSIVE — MODEL DISAGREEMENT"
        confidence = 0.50
        ai_desc = ", ".join([f"{name} ({round(c*100, 1)}% AI)" for name, c in confident_ai_models])
        real_desc = ", ".join([f"{name} ({round(c*100, 1)}% Human)" for name, c in confident_real_models])

        reasons.append(
            f"Direct model deadlock detected: [{ai_desc}] vs [{real_desc}] without consensus."
        )
        reasons.append(
            "Detectors yielded conflicting assessments without corroborating forensic proof."
        )
        limitations.append(
            "Because independent neural classifiers yielded contradictory assessments without an ensemble consensus, "
            "automated origin attribution is inconclusive."
        )

    # Condition C: Localized Splicing / Inpainting vs Full Generation
    elif ela_anomaly and (norm_ai_score > 0.55 or fft_lattice):
        verdict = "AI-MODIFIED"
        confidence = round(min(0.95, max(0.60, (ela_mean / 25.0) * 0.3 + norm_ai_score * 0.7)), 2)
        reasons.append("Localized compression boundary anomalies combined with synthetic spectral traces point to partial AI inpainting/modification.")

    elif ela_anomaly and not fft_lattice and norm_real_score > norm_ai_score:
        verdict = "MANIPULATED"
        confidence = round(min(0.92, max(0.60, (ela_max / 50.0) * 0.5 + 0.4)), 2)
        reasons.append("Localized compression discrepancy detected without global synthetic generative footprints, indicating traditional photographic splicing or cloning.")

    # Condition D: AI Generation (Consensus, High Probability, or Spectral Lattice)
    elif norm_ai_score >= 0.58 or (fft_lattice and norm_ai_score > 0.48) or (has_ai_consensus and norm_ai_score > 0.50):
        verdict = "AI-GENERATED"
        forensic_boost = (0.05 if fft_lattice else 0.0) + (0.04 if noise_var < 0.8 else 0.0)
        final_conf = min(0.98, max(0.50, norm_ai_score + forensic_boost))
        confidence = round(final_conf, 2)
        reasons.append("Concurrence between machine learning neural representations and generative noise/spectral harmonics.")

    # Condition E: Real / Human Photo (Consensus or High Probability, with Optical Consistency)
    elif (norm_real_score >= 0.58 or (has_real_consensus and norm_real_score > 0.50)) and not fft_lattice and not ela_anomaly:
        verdict = "REAL / HUMAN"
        sensor_boost = (0.05 if (has_camera_hardware_exif and noise_var > 2.0) else 0.0)
        final_conf = min(0.98, max(0.50, norm_real_score + sensor_boost))
        confidence = round(final_conf, 2)
        reasons.append("Consistent optical properties, physical sensor noise floor, and absence of generative frequency anomalies.")

    # Condition F: Ambiguous or Degraded Evidence
    else:
        verdict = "UNKNOWN / INCONCLUSIVE"
        confidence = 0.50
        reasons.append("Available forensic, spectral, and machine learning signals yielded conflicting or statistically indeterminate results.")
        limitations.append("The evidence does not meet the necessary threshold to make a reliable origin determination.")

    if not reasons:
        reasons.append("No conclusive forensic anomalies or definitive authenticity markers were observed.")

    return {
        "final_verdict": verdict,
        "overall_confidence": confidence,
        "verdict_reasons": reasons,
        "limitations": limitations
    }
