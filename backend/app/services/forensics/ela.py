import os
import io
from typing import Dict, Any
from PIL import Image, ImageChops, ImageEnhance
import numpy as np

def perform_ela(
    image_path: str,
    output_dir: str,
    analysis_id: str,
    quality_baseline: int = 95,
    amplification_factor: float = 12.0
) -> Dict[str, Any]:
    """
    Computes Error Level Analysis (ELA).
    Works on any Pillow-readable format by normalizing to RGB first.
    The heatmap is always saved as JPEG for efficient serving.
    """
    os.makedirs(output_dir, exist_ok=True)
    heatmap_filename = f"ela_{analysis_id}.jpg"
    heatmap_path = os.path.join(output_dir, heatmap_filename)

    try:
        with Image.open(image_path) as orig_img:
            # Convert to RGB regardless of source format
            orig_rgb = orig_img.convert("RGB")

            # Re-encode at fixed JPEG quality baseline to measure compression decay
            temp_buffer = io.BytesIO()
            orig_rgb.save(temp_buffer, "JPEG", quality=quality_baseline, subsampling=0)
            temp_buffer.seek(0)

            with Image.open(temp_buffer) as resaved_img:
                resaved_rgb = resaved_img.convert("RGB")

                # Absolute pixel-level difference map
                diff = ImageChops.difference(orig_rgb, resaved_rgb)
                diff_np = np.array(diff, dtype=np.float32)

                mean_diff = float(np.mean(diff_np))
                max_diff = float(np.max(diff_np))
                std_diff = float(np.std(diff_np))

                # Anomaly: isolated high-discrepancy region (splicing/inpainting)
                # or uniformly high mean (heavily edited/generated)
                anomaly_detected = (max_diff > 35.0 and std_diff > 4.5) or (mean_diff > 18.0)

                # Amplify for visualization
                enhancer = ImageEnhance.Brightness(diff)
                amplified = enhancer.enhance(amplification_factor)
                amplified.save(heatmap_path, "JPEG", quality=90)

    except Exception as e:
        # Create a blank heatmap on failure to avoid downstream errors
        blank = Image.new("RGB", (512, 512), (20, 20, 30))
        blank.save(heatmap_path, "JPEG")
        return {
            "ela_mean_discrepancy": 0.0,
            "ela_max_discrepancy": 0.0,
            "ela_anomaly_detected": False,
            "ela_heatmap_url": f"/artifacts/{heatmap_filename}"
        }

    return {
        "ela_mean_discrepancy": round(mean_diff, 3),
        "ela_max_discrepancy": round(max_diff, 3),
        "ela_anomaly_detected": anomaly_detected,
        "ela_heatmap_url": f"/artifacts/{heatmap_filename}"
    }
