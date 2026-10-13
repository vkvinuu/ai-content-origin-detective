import os
from typing import Dict, Any
from PIL import Image
import numpy as np
import cv2

def perform_fft_analysis(
    image_path: str,
    output_dir: str,
    analysis_id: str
) -> Dict[str, Any]:
    """
    Computes 2D FFT power spectrum to detect periodic lattice harmonics from
    neural upsampling/deconvolution. Handles any Pillow-readable image format.
    """
    os.makedirs(output_dir, exist_ok=True)
    spectrum_filename = f"fft_{analysis_id}.jpg"
    spectrum_path = os.path.join(output_dir, spectrum_filename)

    try:
        with Image.open(image_path) as img:
            # Convert to grayscale via RGB to handle palette/RGBA/L etc.
            gray = np.array(img.convert("L"), dtype=np.float32)

        # 2D FFT
        dft = np.fft.fft2(gray)
        dft_shift = np.fft.fftshift(dft)
        magnitude_spectrum = np.log(np.abs(dft_shift) + 1.0)

        # Normalize to uint8
        min_val, max_val = np.min(magnitude_spectrum), np.max(magnitude_spectrum)
        if max_val - min_val > 1e-5:
            norm_spectrum = ((magnitude_spectrum - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
        else:
            norm_spectrum = np.zeros_like(magnitude_spectrum, dtype=np.uint8)

        # Mask central DC component, measure high-frequency peaks
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        r = min(h, w) // 10
        y_idx, x_idx = np.ogrid[:h, :w]
        mask = (x_idx - center_x) ** 2 + (y_idx - center_y) ** 2 <= r ** 2

        hf_spectrum = magnitude_spectrum.copy()
        hf_spectrum[mask] = 0.0

        non_zero = hf_spectrum[hf_spectrum > 0]
        if len(non_zero) > 0:
            peak_hf = float(np.max(non_zero))
            median_hf = float(np.median(non_zero))
            peak_harmonic_ratio = round(peak_hf / (median_hf + 1e-5), 3)
        else:
            peak_harmonic_ratio = 1.0

        lattice_anomaly_detected = peak_harmonic_ratio > 3.2

        # Save colorized spectrum
        colored = cv2.applyColorMap(norm_spectrum, cv2.COLORMAP_VIRIDIS)
        cv2.imwrite(spectrum_path, colored)

    except Exception as e:
        # Create a blank spectrum on failure
        blank = np.zeros((512, 512), dtype=np.uint8)
        cv2.imwrite(spectrum_path, cv2.applyColorMap(blank, cv2.COLORMAP_VIRIDIS))
        return {
            "fft_peak_harmonic_ratio": 1.0,
            "fft_lattice_anomaly_detected": False,
            "fft_spectrum_url": f"/artifacts/{spectrum_filename}"
        }

    return {
        "fft_peak_harmonic_ratio": peak_harmonic_ratio,
        "fft_lattice_anomaly_detected": lattice_anomaly_detected,
        "fft_spectrum_url": f"/artifacts/{spectrum_filename}"
    }
