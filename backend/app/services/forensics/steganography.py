from typing import Dict, Any
from PIL import Image
import numpy as np

def check_steganography_indicators(image_path: str) -> Dict[str, Any]:
    """
    Analyzes LSB plane entropy to detect abnormal info density or watermarking.
    Works on any Pillow-readable format.
    """
    try:
        with Image.open(image_path) as img:
            rgb = np.array(img.convert("RGB"), dtype=np.uint8)

        lsb_plane = rgb & 1

        def entropy(plane: np.ndarray) -> float:
            counts = np.bincount(plane.flatten(), minlength=2)
            probs = counts / (np.sum(counts) + 1e-10)
            probs = probs[probs > 0]
            return float(-np.sum(probs * np.log2(probs + 1e-10)))

        r_e = entropy(lsb_plane[:, :, 0])
        g_e = entropy(lsb_plane[:, :, 1])
        b_e = entropy(lsb_plane[:, :, 2])
        avg_entropy = (r_e + g_e + b_e) / 3.0

        is_anomaly = avg_entropy > 0.9995

    except Exception:
        avg_entropy = 0.0
        is_anomaly = False

    return {
        "steganography_anomaly": is_anomaly,
        "lsb_avg_entropy": round(avg_entropy, 4)
    }
