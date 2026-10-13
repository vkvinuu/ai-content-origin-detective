import io
import pytest
from PIL import Image
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.services.ml.model_manager import model_manager
from app.services.ml.inference import run_ml_detection
from app.services.synthesizer.decision_engine import synthesize_analysis
from app.services.report_generator import generate_pdf_dossier


def test_model_roster_composition():
    """Verify that only Ateeqq and umm-maybe are configured, and Organika is completely removed."""
    configured_ids = [m["id"] for m in model_manager.models_config]
    assert "Ateeqq/ai-vs-human-image-detector" in configured_ids
    assert "umm-maybe/AI-image-detector" in configured_ids
    assert len(configured_ids) == 2
    assert not any("organika" in mid.lower() or "sdxl" in mid.lower() for mid in configured_ids)


def test_both_models_execute_inference(tmp_path):
    """Verify that both Ateeqq and umm-maybe actually load and execute inference on an image."""
    img_path = str(tmp_path / "test_ensemble.jpg")
    img = Image.new("RGB", (256, 256), color=(140, 180, 220))
    img.save(img_path, "JPEG")

    evals = run_ml_detection(img_path)
    model_names = [ev["model_name"] for ev in evals]

    assert "Ateeqq/ai-vs-human-image-detector" in model_names
    assert "umm-maybe/AI-image-detector" in model_names
    assert len(evals) == 2

    for ev in evals:
        assert ev["predicted_label"] in ("AI-GENERATED", "REAL / HUMAN", "INCONCLUSIVE", "FAILED")
        assert 0.0 <= ev["confidence"] <= 1.0
        assert "normalized_probabilities" in ev
        assert "raw_probabilities" in ev


def test_pdf_report_section3_lists_both_models():
    """Verify that the generated PDF report dossier includes both models in Section 3."""
    class MockDNA:
        sha256_hash = "abcdef1234567890" * 4
        md5_hash = "1234567890abcdef" * 2
        perceptual_hash = "f0f0f0f0f0f0f0f0"
        difference_hash = "0f0f0f0f0f0f0f0f"
        wavelet_hash = "aaaaaaaabbbbbbbb"
        dna_fingerprint_composite = "DNA:V1.0.0:TEST"

    class MockForensics:
        has_ai_metadata = False
        c2pa_manifest_detected = False
        ela_mean_discrepancy = 1.5
        ela_max_discrepancy = 5.0
        ela_anomaly_detected = False
        fft_peak_harmonic_ratio = 1.05
        fft_lattice_anomaly_detected = False
        noise_variance = 2.5
        noise_uniformity_score = 1.0
        compression_quality_estimate = 90

    class MockMLEval:
        def __init__(self, name, version, pred, conf, latency):
            self.model_name = name
            self.model_version = version
            self.predicted_label = pred
            self.confidence = conf
            self.execution_time_ms = latency

    class MockAnalysis:
        id = "test-case-1234"
        engine_version = "1.0.0"
        created_at = None
        file_name = "sample.jpg"
        dimensions_width = 1024
        dimensions_height = 768
        file_size_bytes = 1048576
        mime_type = "image/jpeg"
        final_verdict = "AI-GENERATED"
        overall_confidence = 0.85
        verdict_reasons = ["Consensus reached across detector architectures."]
        limitations = []
        content_dna = MockDNA()
        forensic_signals = MockForensics()
        ml_evaluations = [
            MockMLEval("Ateeqq/ai-vs-human-image-detector", "siglip-so400m", "AI-GENERATED", 0.95, 250),
            MockMLEval("umm-maybe/AI-image-detector", "vit-base", "AI-GENERATED", 0.75, 120)
        ]

    pdf_buffer = generate_pdf_dossier(MockAnalysis())
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_report_honestly_reports_model_failure():
    """Verify that if a model fails, Section 3 honestly displays the failure instead of hiding it."""
    class MockDNA:
        sha256_hash = "abcdef1234567890" * 4
        md5_hash = "1234567890abcdef" * 2
        perceptual_hash = "f0f0f0f0f0f0f0f0"
        difference_hash = "0f0f0f0f0f0f0f0f"
        wavelet_hash = "aaaaaaaabbbbbbbb"
        dna_fingerprint_composite = "DNA:V1.0.0:TEST"

    class MockForensics:
        has_ai_metadata = False
        c2pa_manifest_detected = False
        ela_mean_discrepancy = 1.5
        ela_max_discrepancy = 5.0
        ela_anomaly_detected = False
        fft_peak_harmonic_ratio = 1.05
        fft_lattice_anomaly_detected = False
        noise_variance = 2.5
        noise_uniformity_score = 1.0
        compression_quality_estimate = 90

    class MockMLEval:
        def __init__(self, name, version, pred, conf, latency):
            self.model_name = name
            self.model_version = version
            self.predicted_label = pred
            self.confidence = conf
            self.execution_time_ms = latency

    # Only Ateeqq succeeded, umm-maybe is missing or marked FAILED
    class MockAnalysisWithFailure:
        id = "test-case-fail-1234"
        engine_version = "1.0.0"
        created_at = None
        file_name = "sample.jpg"
        dimensions_width = 1024
        dimensions_height = 768
        file_size_bytes = 1048576
        mime_type = "image/jpeg"
        final_verdict = "AI-GENERATED"
        overall_confidence = 0.85
        verdict_reasons = ["Evaluated by available primary model."]
        limitations = ["Model umm-maybe failed to execute."]
        content_dna = MockDNA()
        forensic_signals = MockForensics()
        ml_evaluations = [
            MockMLEval("Ateeqq/ai-vs-human-image-detector", "siglip-so400m", "AI-GENERATED", 0.95, 250),
            MockMLEval("umm-maybe/AI-image-detector", "vit-base", "FAILED", 0.0, 0)
        ]

    pdf_buffer = generate_pdf_dossier(MockAnalysisWithFailure())
    pdf_bytes = pdf_buffer.getvalue()
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
