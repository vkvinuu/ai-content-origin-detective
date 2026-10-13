from typing import Dict, Any
from PIL import Image
import numpy as np
import cv2

def analyze_noise_residual(image_path: str) -> Dict[str, Any]:
    """
    Extracts sensor noise residual and analyzes spatial uniformity.
    Works on any Pillow-readable format by normalizing to RGB first.
    """
    try:
        with Image.open(image_path) as img:
            rgb = np.array(img.convert("RGB"), dtype=np.float32)

        h_px, w_px, _ = rgb.shape
        gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)

        # Noise residual = Original - Median-filtered (denoised)
        denoised = cv2.medianBlur(gray.astype(np.uint8), 3).astype(np.float32)
        residual = gray - denoised
        noise_variance = float(np.var(residual))

        # Block-wise spatial uniformity
        block_size = 32
        block_vars = []
        for y in range(0, h_px - block_size + 1, block_size):
            for x in range(0, w_px - block_size + 1, block_size):
                block_vars.append(float(np.var(residual[y:y+block_size, x:x+block_size])))

        if block_vars:
            mean_bv = float(np.mean(block_vars))
            std_bv = float(np.std(block_vars))
            uniformity_score = round(std_bv / (mean_bv + 1e-5), 3)
        else:
            uniformity_score = 1.0

        # Compression quality heuristic from Laplacian sharpness
        laplacian_var = float(cv2.Laplacian(gray.astype(np.uint8), cv2.CV_64F).var())
        estimated_quality = min(100, max(20, int(35 + np.log1p(laplacian_var) * 8)))

    except Exception:
        noise_variance = 0.0
        uniformity_score = 1.0
        estimated_quality = 50

    return {
        "noise_variance": round(noise_variance, 3),
        "noise_uniformity_score": uniformity_score,
        "compression_quality_estimate": estimated_quality
    }
