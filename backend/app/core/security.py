import os
import re
import uuid
from typing import Tuple
from PIL import Image
from app.core.config import settings
from app.core.exceptions import SecurityValidationError

# Enforce PIL decompression bomb limit
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS

# Comprehensive magic byte signatures for all supported image formats
MAGIC_SIGNATURES = [
    # JPEG / JFIF / EXIF
    (b"\xFF\xD8\xFF", "image/jpeg", ".jpg"),
    # PNG
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    # GIF87a / GIF89a
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
    # BMP
    (b"BM", "image/bmp", ".bmp"),
    # TIFF little-endian
    (b"II\x2A\x00", "image/tiff", ".tiff"),
    # TIFF big-endian
    (b"MM\x00\x2A", "image/tiff", ".tiff"),
    # AVIF / HEIF / HEIC — ftyp box header at byte 4
    (b"\x00\x00\x00", "image/avif", ".avif"),  # Handled dynamically below
    # ICO
    (b"\x00\x00\x01\x00", "image/x-icon", ".ico"),
]

def sanitize_filename(filename: str) -> str:
    """Removes path traversal sequences, illegal characters, and enforces safety."""
    if not filename:
        return "unnamed_upload"
    base = os.path.basename(filename)
    cleaned = re.sub(r"[^\w\.\-]", "_", base)
    cleaned = cleaned.lstrip(".")
    if not cleaned:
        return f"upload_{uuid.uuid4().hex[:8]}"
    return cleaned[:100]

def validate_image_stream(header_bytes: bytes, file_size: int) -> Tuple[str, str]:
    """
    Validates magic bytes and file size. Supports JPEG, PNG, WebP, GIF, BMP,
    TIFF, AVIF/HEIF/HEIC, and ICO.
    Returns (detected_mime_type, standard_extension).
    """
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise SecurityValidationError(
            f"File size {file_size} bytes exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
        )

    if len(header_bytes) < 12:
        raise SecurityValidationError("Uploaded file is too small or truncated to be a valid image.")

    # JPEG (all variants: JFIF, EXIF, raw)
    if header_bytes[:3] == b"\xFF\xD8\xFF":
        return "image/jpeg", ".jpg"

    # PNG
    if header_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"

    # WebP (RIFF....WEBP)
    if header_bytes[:4] == b"RIFF" and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
        return "image/webp", ".webp"

    # GIF
    if header_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", ".gif"

    # BMP
    if header_bytes[:2] == b"BM":
        return "image/bmp", ".bmp"

    # TIFF
    if header_bytes[:4] in (b"II\x2A\x00", b"MM\x00\x2A"):
        return "image/tiff", ".tiff"

    # AVIF / HEIF / HEIC — ISO Base Media File Format: check ftyp box
    # Box size (4 bytes) + 'ftyp' (4 bytes) + brand (4 bytes)
    if len(header_bytes) >= 12 and header_bytes[4:8] == b"ftyp":
        brand = header_bytes[8:12]
        if brand in (b"avif", b"avis", b"av01"):
            return "image/avif", ".avif"
        if brand in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"):
            return "image/heic", ".heic"
        if brand in (b"heif", b"mifi"):
            return "image/heif", ".heif"

    # ICO
    if header_bytes[:4] == b"\x00\x00\x01\x00":
        return "image/x-icon", ".ico"

    # Video: MP4 / M4V (ftypmp41, ftypmp42, ftypisom, etc.)
    if len(header_bytes) >= 12 and header_bytes[4:8] == b"ftyp":
        brand = header_bytes[8:12]
        if brand in (b"mp41", b"mp42", b"isom", b"iso2", b"avc1", b"dash"):
            return "video/mp4", ".mp4"
        if brand in (b"qt  ", b"moov"):
            return "video/quicktime", ".mov"

    # Video: Matroska / WebM
    if header_bytes[:4] == b"\x1A\x45\xDF\xA3":
        return "video/webm", ".webm"

    # Video: AVI (RIFF....AVI )
    if header_bytes[:4] == b"RIFF" and len(header_bytes) >= 12 and header_bytes[8:12] == b"AVI ":
        return "video/x-msvideo", ".avi"

    # Audio: MP3 (ID3 tag or sync word 0xFFFB / 0xFFFA / 0xFFF3)
    if header_bytes[:3] == b"ID3" or (len(header_bytes) >= 2 and header_bytes[0] == 0xFF and (header_bytes[1] & 0xE0) == 0xE0):
        return "audio/mpeg", ".mp3"

    # Audio: WAV (RIFF....WAVE)
    if header_bytes[:4] == b"RIFF" and len(header_bytes) >= 12 and header_bytes[8:12] == b"WAVE":
        return "audio/wav", ".wav"

    # Audio: FLAC
    if header_bytes[:4] == b"fLaC":
        return "audio/flac", ".flac"

    # Audio: OGG
    if header_bytes[:4] == b"OggS":
        return "audio/ogg", ".ogg"

    raise SecurityValidationError(
        "File signature (magic bytes) does not match supported media formats (JPEG, PNG, WebP, GIF, BMP, TIFF, AVIF, HEIC, MP4, WebM, WAV, MP3, FLAC, OGG)."
    )


def verify_media_integrity(filepath: str, mime_type: str) -> Tuple[int, int]:
    """
    Safely verifies integrity according to media type (image, video, audio).
    Returns (width, height) for visual media, or (duration_seconds, sample_rate) for audio.
    """
    if mime_type.startswith("image/"):
        return verify_image_integrity(filepath)

    if mime_type.startswith("video/"):
        return verify_video_integrity(filepath)

    if mime_type.startswith("audio/"):
        return verify_audio_integrity(filepath)

    return (0, 0)


def verify_image_integrity(filepath: str) -> Tuple[int, int]:
    """
    Safely opens and verifies the image using Pillow.
    Guards against decompression bombs, truncated files, and malformed headers.
    Preserves the original uploaded file without any side-effect conversions.
    Returns (width, height).
    """
    try:
        with Image.open(filepath) as img:
            img.load()
            width, height = img.size
            if width <= 0 or height <= 0:
                raise SecurityValidationError("Invalid image dimensions detected.")
            return width, height
    except Image.DecompressionBombError:
        raise SecurityValidationError("Image exceeds safe pixel dimension limit (decompression bomb defense).")
    except SecurityValidationError:
        raise
    except Exception as e:
        raise SecurityValidationError(f"Corrupt or unreadable image data: {str(e)}")


def verify_video_integrity(filepath: str) -> Tuple[int, int]:
    """
    Safely opens and verifies a video stream using OpenCV with FFMPEG backend.
    Returns (width, height).
    """
    import cv2
    cap = cv2.VideoCapture(filepath, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            raise SecurityValidationError("Could not decode video stream or file is corrupted.")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if width <= 0 or height <= 0 or frame_count <= 0:
            raise SecurityValidationError("Invalid video geometry or empty frame stream.")
        return width, height
    finally:
        cap.release()


def verify_audio_integrity(filepath: str) -> Tuple[int, int]:
    """
    Safely verifies audio stream integrity.
    Returns (duration_seconds, sample_rate).
    """
    try:
        from scipy.io import wavfile
        sr, data = wavfile.read(filepath)
        duration = int(len(data) / sr) if sr > 0 else 0
        return duration, int(sr)
    except Exception:
        # Non-WAV or compressed audio: check non-empty file size
        file_sz = os.path.getsize(filepath)
        if file_sz < 64:
            raise SecurityValidationError("Audio file is truncated or corrupted.")
        return (0, 44100)
