import hashlib
from typing import Dict, Any
from PIL import Image
import imagehash
import numpy as np

def compute_content_dna(file_path: str, engine_version: str = "1.0.0") -> Dict[str, Any]:
    """
    Generates a cryptographic + perceptual Content DNA profile.
    Works on any Pillow-supported image format.
    """
    # 1. Cryptographic hashes from raw bytes
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256_hash.update(chunk)
            md5_hash.update(chunk)

    sha256_hex = sha256_hash.hexdigest()
    md5_hex = md5_hash.hexdigest()

    # 2. Perceptual hashes (require RGB PIL image)
    try:
        with Image.open(file_path) as img:
            rgb_img = img.convert("RGB")
            phash_val = str(imagehash.phash(rgb_img))
            dhash_val = str(imagehash.dhash(rgb_img))
            whash_val = str(imagehash.whash(rgb_img))

            # 3. Compact 24-bin color histogram signature
            np_img = np.array(rgb_img)
            hist_r, _ = np.histogram(np_img[:, :, 0], bins=8, range=(0, 256), density=True)
            hist_g, _ = np.histogram(np_img[:, :, 1], bins=8, range=(0, 256), density=True)
            hist_b, _ = np.histogram(np_img[:, :, 2], bins=8, range=(0, 256), density=True)
            color_vector = [round(float(v), 5) for v in np.concatenate([hist_r, hist_g, hist_b])]
    except Exception:
        phash_val = "0" * 16
        dhash_val = "0" * 16
        whash_val = "0" * 16
        color_vector = [0.0] * 24

    dna_composite = (
        f"DNA:V{engine_version}:SHA256={sha256_hex[:16]}"
        f":PHASH={phash_val}:DHASH={dhash_val}:WHASH={whash_val}"
    )

    return {
        "sha256_hash": sha256_hex,
        "md5_hash": md5_hex,
        "perceptual_hash": phash_val,
        "difference_hash": dhash_val,
        "wavelet_hash": whash_val,
        "color_histogram_vector": color_vector,
        "dna_fingerprint_composite": dna_composite
    }
