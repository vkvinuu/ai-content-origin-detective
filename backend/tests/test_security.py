import pytest
from app.core.security import sanitize_filename, validate_image_stream
from app.core.exceptions import SecurityValidationError

def test_sanitize_filename_traversal():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\boot.ini") == "boot.ini"
    assert sanitize_filename("normal_photo.jpg") == "normal_photo.jpg"
    assert sanitize_filename("") == "unnamed_upload"
    assert sanitize_filename(".hidden_malware.png") == "hidden_malware.png"

def test_validate_image_stream_magic_bytes():
    # Valid JPEG magic
    jpeg_header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01"
    mime, ext = validate_image_stream(jpeg_header, 1024)
    assert mime == "image/jpeg"
    assert ext == ".jpg"

    # Valid PNG magic
    png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    mime, ext = validate_image_stream(png_header, 2048)
    assert mime == "image/png"
    assert ext == ".png"

    # Invalid executable header (MZ)
    exe_header = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00"
    with pytest.raises(SecurityValidationError):
        validate_image_stream(exe_header, 5000)

def test_validate_image_stream_size_limit():
    jpeg_header = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01"
    huge_size = 50 * 1024 * 1024 # 50 MB (exceeds 25MB limit)
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_image_stream(jpeg_header, huge_size)
    assert "exceeds maximum allowed limit" in str(exc_info.value)
