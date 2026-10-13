import pytest
from app.services.synthesizer.decision_engine import synthesize_analysis

def test_synthesizer_ai_metadata_override():
    # If explicit AI prompt tags are found in metadata, verdict must be AI-GENERATED
    meta = {"has_ai_metadata": True, "ai_metadata_tags": ["parameters: Stable Diffusion prompt"], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 2.0, "ela_max_discrepancy": 10.0}
    fft = {"fft_peak_harmonic_ratio": 1.2, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 3.0, "noise_uniformity_score": 1.1, "compression_quality_estimate": 90}
    stego = {"steganography_anomaly": False}
    ml = [{"model_name": "test_model", "predicted_label": "REAL / HUMAN", "confidence": 0.65}]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "AI-GENERATED"
    assert res["overall_confidence"] >= 0.95

def test_synthesizer_spliced_manipulation():
    # If localized ELA anomaly is high, but not AI-generated
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": True, "ela_mean_discrepancy": 12.0, "ela_max_discrepancy": 45.0}
    fft = {"fft_peak_harmonic_ratio": 1.1, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 5.0, "noise_uniformity_score": 3.5, "compression_quality_estimate": 85}
    stego = {"steganography_anomaly": False}
    ml = [{"model_name": "test_model", "predicted_label": "REAL / HUMAN", "confidence": 0.80}]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "MANIPULATED"

def test_synthesizer_real_camera_agreement():
    # Physical sensor noise, no ELA anomaly, no FFT lattice, ML says Real
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.8, "ela_max_discrepancy": 8.0}
    fft = {"fft_peak_harmonic_ratio": 1.05, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 4.5, "noise_uniformity_score": 1.0, "compression_quality_estimate": 95}
    stego = {"steganography_anomaly": False}
    ml = [{"model_name": "test_model", "predicted_label": "REAL / HUMAN", "confidence": 0.88}]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1920, 1080))
    assert res["final_verdict"] == "REAL / HUMAN"
    assert res["overall_confidence"] >= 0.70

def test_synthesizer_inconclusive_low_quality():
    # Low quality, contradictory/neutral signals
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.0, "ela_max_discrepancy": 5.0}
    fft = {"fft_peak_harmonic_ratio": 1.0, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 1.5, "noise_uniformity_score": 1.0, "compression_quality_estimate": 35}
    stego = {"steganography_anomaly": False}
    ml = [{"model_name": "test_model", "predicted_label": "INCONCLUSIVE", "confidence": 0.50}]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (200, 200))
    assert res["final_verdict"] == "UNKNOWN / INCONCLUSIVE"
    assert any("Low resolution" in lim for lim in res["limitations"])


def test_synthesizer_concurrence_resolves_ai():
    """
    Test concurrence:
    AI-generated image where Ateeqq predicts AI (98%) and umm-maybe predicts AI (65%).
    Ensemble must resolve to AI-GENERATED.
    """
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.5, "ela_max_discrepancy": 6.0}
    fft = {"fft_peak_harmonic_ratio": 1.1, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 0.5, "noise_uniformity_score": 1.0, "compression_quality_estimate": 90}
    stego = {"steganography_anomaly": False}
    ml = [
        {
            "model_name": "Ateeqq/ai-vs-human-image-detector",
            "predicted_label": "AI-GENERATED",
            "confidence": 0.98,
            "normalized_probabilities": {"AI-GENERATED": 0.98, "REAL / HUMAN": 0.02}
        },
        {
            "model_name": "umm-maybe/AI-image-detector",
            "predicted_label": "AI-GENERATED",
            "confidence": 0.65,
            "normalized_probabilities": {"AI-GENERATED": 0.65, "REAL / HUMAN": 0.35}
        }
    ]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "AI-GENERATED"
    assert res["overall_confidence"] >= 0.65


def test_synthesizer_real_camera_evidence_corroborates_human():
    """
    Real photograph where umm-maybe (95% Real) and camera hardware EXIF + organic noise
    corroborate authenticity.
    """
    meta = {
        "has_ai_metadata": False,
        "ai_metadata_tags": [],
        "c2pa_manifest_detected": False,
        "exif_metadata": {"Make": "Canon", "Model": "EOS R5", "FNumber": 2.8}
    }
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.2, "ela_max_discrepancy": 5.0}
    fft = {"fft_peak_harmonic_ratio": 1.02, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 4.2, "noise_uniformity_score": 1.0, "compression_quality_estimate": 95}
    stego = {"steganography_anomaly": False}
    ml = [
        {
            "model_name": "Ateeqq/ai-vs-human-image-detector",
            "predicted_label": "REAL / HUMAN",
            "confidence": 0.92,
            "normalized_probabilities": {"AI-GENERATED": 0.08, "REAL / HUMAN": 0.92}
        },
        {
            "model_name": "umm-maybe/AI-image-detector",
            "predicted_label": "REAL / HUMAN",
            "confidence": 0.95,
            "normalized_probabilities": {"AI-GENERATED": 0.05, "REAL / HUMAN": 0.95}
        }
    ]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (2048, 1536))
    assert res["final_verdict"] == "REAL / HUMAN"
    assert res["overall_confidence"] >= 0.70


def test_synthesizer_genuine_deadlock_returns_inconclusive():
    """
    True 1-vs-1 tie between models with equal evidence and no majority quorum.
    Must honestly return INCONCLUSIVE — MODEL DISAGREEMENT without fabricating certainty.
    """
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 2.0, "ela_max_discrepancy": 8.0}
    fft = {"fft_peak_harmonic_ratio": 1.05, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 1.5, "noise_uniformity_score": 1.0, "compression_quality_estimate": 80}
    stego = {"steganography_anomaly": False}
    # Two opposing models, 1-vs-1 tie
    ml = [
        {
            "model_name": "model_alpha",
            "predicted_label": "AI-GENERATED",
            "confidence": 0.85,
            "normalized_probabilities": {"AI-GENERATED": 0.85, "REAL / HUMAN": 0.15}
        },
        {
            "model_name": "model_beta",
            "predicted_label": "REAL / HUMAN",
            "confidence": 0.85,
            "normalized_probabilities": {"AI-GENERATED": 0.15, "REAL / HUMAN": 0.85}
        }
    ]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "INCONCLUSIVE — MODEL DISAGREEMENT"
    assert res["overall_confidence"] == 0.50
    assert any("deadlock" in r.lower() or "disagreement" in r.lower() for r in res["verdict_reasons"])


def test_synthesizer_ateeqq_and_umm_maybe_disagreement():
    """
    Direct disagreement between Ateeqq (predicting AI) and umm-maybe (predicting Real)
    without corroborating forensic proof must yield INCONCLUSIVE — MODEL DISAGREEMENT.
    """
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.5, "ela_max_discrepancy": 5.0}
    fft = {"fft_peak_harmonic_ratio": 1.0, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 1.2, "noise_uniformity_score": 1.0, "compression_quality_estimate": 85}
    stego = {"steganography_anomaly": False}
    ml = [
        {
            "model_name": "Ateeqq/ai-vs-human-image-detector",
            "predicted_label": "AI-GENERATED",
            "confidence": 0.88,
            "normalized_probabilities": {"AI-GENERATED": 0.88, "REAL / HUMAN": 0.12}
        },
        {
            "model_name": "umm-maybe/AI-image-detector",
            "predicted_label": "REAL / HUMAN",
            "confidence": 0.80,
            "normalized_probabilities": {"AI-GENERATED": 0.20, "REAL / HUMAN": 0.80}
        }
    ]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "INCONCLUSIVE — MODEL DISAGREEMENT"
    assert res["overall_confidence"] == 0.50
    assert any("deadlock" in r.lower() or "disagreement" in r.lower() for r in res["verdict_reasons"])


def test_synthesizer_model_failure_handled_honestly():
    """
    When one model fails (e.g. umm-maybe raises an error or fails to load),
    the failure is honestly recorded in limitations, and the decision engine proceeds
    without crashing or falsifying votes.
    """
    meta = {"has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
    ela = {"ela_anomaly_detected": False, "ela_mean_discrepancy": 1.0, "ela_max_discrepancy": 4.0}
    fft = {"fft_peak_harmonic_ratio": 1.0, "fft_lattice_anomaly_detected": False}
    noise = {"noise_variance": 0.5, "noise_uniformity_score": 1.0, "compression_quality_estimate": 90}
    stego = {"steganography_anomaly": False}
    ml = [
        {
            "model_name": "Ateeqq/ai-vs-human-image-detector",
            "predicted_label": "AI-GENERATED",
            "confidence": 0.94,
            "normalized_probabilities": {"AI-GENERATED": 0.94, "REAL / HUMAN": 0.06}
        },
        {
            "model_name": "umm-maybe/AI-image-detector",
            "predicted_label": "FAILED",
            "confidence": 0.0,
            "normalized_probabilities": {"AI-GENERATED": 0.0, "REAL / HUMAN": 0.0},
            "error": "CUDA out of memory or connection timeout"
        }
    ]

    res = synthesize_analysis(meta, ela, fft, noise, stego, ml, (1024, 1024))
    assert res["final_verdict"] == "AI-GENERATED"
    assert any("failed to evaluate" in lim for lim in res["limitations"])
    assert any("umm-maybe" in lim for lim in res["limitations"])


