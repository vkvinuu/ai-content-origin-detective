"""
Integration tests for dedicated video and audio forensic pipelines.
Verifies temporal optical flow, spectral Nyquist cutoffs, and multi-modal handling.
"""

import os
import io
import pytest
import numpy as np
from scipy.io import wavfile
import cv2
from app.services.forensics.video_analyzer import analyze_temporal_consistency, extract_video_keyframes
from app.services.forensics.audio_analyzer import analyze_spectral_footprint, analyze_audio_pipeline
from app.core.security import validate_image_stream, verify_media_integrity


def test_magic_byte_media_validation():
    # Video MP4 magic bytes
    mp4_header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00"
    mime, ext = validate_image_stream(mp4_header, 1024)
    assert mime == "video/mp4"
    assert ext == ".mp4"

    # Audio WAV magic bytes
    wav_header = b"RIFF\x24\x08\x00\x00WAVEfmt "
    mime, ext = validate_image_stream(wav_header, 1024)
    assert mime == "audio/wav"
    assert ext == ".wav"

    # Audio MP3 magic bytes
    mp3_header = b"ID3\x04\x00\x00\x00\x00\x00\x21\x00\x00\x00\x00\x00\x00"
    mime, ext = validate_image_stream(mp3_header, 1024)
    assert mime == "audio/mpeg"
    assert ext == ".mp3"


def test_synthetic_audio_spectral_analysis(tmp_path):
    # Create synthetic WAV with sharp 12kHz cutoff (simulating neural vocoder)
    sample_rate = 44100
    t = np.linspace(0, 2.0, int(sample_rate * 2.0), endpoint=False)
    # Fundamental harmonic + 5kHz + 11kHz, zero content above 12kHz
    sig = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 5000 * t) + 0.2 * np.sin(2 * np.pi * 11000 * t)
    sig_int16 = (sig * 32767).astype(np.int16)

    test_wav = str(tmp_path / "test_neural_cutoff.wav")
    wavfile.write(test_wav, sample_rate, sig_int16)

    res = analyze_audio_pipeline(test_wav)
    assert res["media_type"] == "audio"
    assert res["sample_rate"] == 44100
    assert "cutoff_frequency_hz" in res["spectral_metrics"]
    assert res["confidence"] >= 0.70


def test_synthetic_video_flow_analysis(tmp_path):
    # Create small synthetic test video (10 frames of 64x64)
    test_avi = str(tmp_path / "test_motion.avi")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(test_avi, fourcc, 10.0, (64, 64), isColor=True)

    for i in range(10):
        # Create translating circle
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        cv2.circle(frame, (10 + i * 4, 32), 8, (255, 255, 255), -1)
        out.write(frame)
    out.release()

    keyframes, meta = extract_video_keyframes(test_avi, max_frames=5)
    assert len(keyframes) > 0
    assert meta["width"] == 64
    assert meta["height"] == 64

    temp_res = analyze_temporal_consistency(test_avi)
    assert "mean_optical_flow" in temp_res
    assert temp_res["evaluated_frame_pairs"] > 0
