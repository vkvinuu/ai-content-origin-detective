import os
import pytest
from PIL import Image, PngImagePlugin
import numpy as np
from app.services.dna.hasher import compute_content_dna
from app.services.forensics.ela import perform_ela
from app.services.forensics.fourier import perform_fft_analysis
from app.services.forensics.noise import analyze_noise_residual
from app.services.forensics.exif_parser import parse_metadata

@pytest.fixture
def sample_test_image(tmp_path):
    """Creates a temporary test image with noise and gradients."""
    img_path = str(tmp_path / "test_sample.png")
    # Generate 512x512 gradient image with noise
    x = np.linspace(0, 1, 512)
    y = np.linspace(0, 1, 512)
    xx, yy = np.meshgrid(x, y)
    arr = (np.sin(xx * 10) * 127 + 128).astype(np.uint8)
    img = Image.fromarray(arr).convert("RGB")
    
    # Add metadata
    meta = PngImagePlugin.PngInfo()
    meta.add_text("parameters", "A high quality photo of a detective, Euler a, Steps: 25, Sampler: DPM++ 2M")
    img.save(img_path, "PNG", pnginfo=meta)
    return img_path

def test_content_dna_generation(sample_test_image):
    dna = compute_content_dna(sample_test_image)
    assert "sha256_hash" in dna
    assert len(dna["sha256_hash"]) == 64
    assert "perceptual_hash" in dna
    assert "difference_hash" in dna
    assert "wavelet_hash" in dna
    assert dna["dna_fingerprint_composite"].startswith("DNA:V1.0.0")

def test_exif_ai_signature_detection(sample_test_image):
    metadata = parse_metadata(sample_test_image)
    assert metadata["has_ai_metadata"] is True
    assert any("Sampler" in tag or "Steps" in tag for tag in metadata["ai_metadata_tags"])

def test_ela_execution(sample_test_image, tmp_path):
    artifact_dir = str(tmp_path / "artifacts")
    ela = perform_ela(sample_test_image, artifact_dir, "test1234")
    assert "ela_mean_discrepancy" in ela
    assert "ela_heatmap_url" in ela
    assert os.path.exists(os.path.join(artifact_dir, "ela_test1234.jpg"))

def test_fft_execution(sample_test_image, tmp_path):
    artifact_dir = str(tmp_path / "artifacts")
    fft_res = perform_fft_analysis(sample_test_image, artifact_dir, "test1234")
    assert "fft_peak_harmonic_ratio" in fft_res
    assert "fft_spectrum_url" in fft_res
    assert os.path.exists(os.path.join(artifact_dir, "fft_test1234.jpg"))

def test_noise_analysis(sample_test_image):
    noise = analyze_noise_residual(sample_test_image)
    assert "noise_variance" in noise
    assert "compression_quality_estimate" in noise
