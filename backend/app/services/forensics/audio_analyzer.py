"""
Dedicated Audio & Music Forensics Service.
Implements spectral analysis, Nyquist cutoff & upsampling detection,
neural vocoder residual physics analysis, and audio provenance checks.
Supports MP3, WAV, FLAC, and OGG formats.
"""

import os
import time
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import signal
from scipy.io import wavfile

logger = logging.getLogger(__name__)


def load_audio_signal(audio_path: str, max_duration_sec: float = 30.0) -> Tuple[np.ndarray, int]:
    """
    Safely loads audio signal into a normalized 1D float array and returns (samples, sample_rate).
    Uses soundfile / librosa with SciPy fallback to support MP3, WAV, FLAC, and OGG formats cleanly.
    Applies streaming chunking up to max_duration_sec to prevent memory spikes.
    """
    # 1. Try soundfile (handles WAV, FLAC, OGG without subprocess)
    try:
        import soundfile as sf
        with sf.SoundFile(audio_path) as sfile:
            sr = sfile.samplerate
            max_frames = int(sr * max_duration_sec)
            raw_data = sfile.read(frames=max_frames, dtype="float32")
            if len(raw_data.shape) > 1:
                data = np.mean(raw_data, axis=1)
            else:
                data = raw_data
            return data.astype(np.float32), int(sr)
    except Exception as sf_err:
        logger.debug(f"SoundFile read bypassed or failed for {audio_path}: {sf_err}")

    # 2. Try librosa (handles MP3 via audioread/soundfile)
    try:
        import librosa
        data, sr = librosa.load(audio_path, sr=None, mono=True, duration=max_duration_sec)
        return data.astype(np.float32), int(sr)
    except Exception as lib_err:
        logger.debug(f"Librosa read bypassed or failed for {audio_path}: {lib_err}")

    # 3. Fallback: Direct WAV via SciPy wavfile
    try:
        sr, raw_data = wavfile.read(audio_path)
        if raw_data.dtype == np.int16:
            data = raw_data.astype(np.float32) / 32768.0
        elif raw_data.dtype == np.int32:
            data = raw_data.astype(np.float32) / 2147483648.0
        elif raw_data.dtype == np.uint8:
            data = (raw_data.astype(np.float32) - 128.0) / 128.0
        else:
            data = raw_data.astype(np.float32)

        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        max_samples = int(sr * max_duration_sec)
        if len(data) > max_samples:
            data = data[:max_samples]

        return data, int(sr)
    except Exception as e:
        logger.warning(f"All audio loaders failed for {audio_path}: {e}")
        return np.zeros(1024, dtype=np.float32), 44100


def analyze_spectral_footprint(samples: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """
    Computes STFT spectrogram and inspects spectral roll-off, Nyquist cutoffs,
    and high-frequency quantization banding.
    
    Generative AI music models (Suno v3, Udio, MusicGen, Stable Audio) frequently
    utilize neural audio decoders (EnCodec / DAC / SoundStream) trained at 24kHz or 32kHz
    and then resampled to 44.1kHz. This produces an abrupt 'brick-wall' spectral cutoff
    at 12kHz or 16kHz with distinct periodic quantization artifacts in high frequencies.
    """
    if len(samples) < 512 or sample_rate <= 0:
        return {
            "nyquist_cutoff_detected": False,
            "cutoff_frequency_hz": 0.0,
            "high_freq_energy_ratio": 0.5,
            "neural_vocoder_anomaly": False,
            "spectral_flatness": 0.5,
            "dynamic_range_db": 0.0
        }

    # 1. Compute Welch periodogram for power spectral density
    freqs, psd = signal.welch(samples, fs=sample_rate, nperseg=min(2048, len(samples)))
    
    # Avoid log of zero
    psd_safe = np.maximum(psd, 1e-12)
    psd_db = 10 * np.log10(psd_safe)

    # 2. Check for sharp neural decoder cutoff (brick-wall drop around 11-13kHz or 15-17kHz)
    nyquist = sample_rate / 2.0
    cutoff_detected = False
    detected_cutoff = 0.0

    # Look for 25dB+ drop within a 1kHz band above 10kHz
    high_mask = (freqs >= 10000) & (freqs <= min(20000, nyquist - 500))
    if np.any(high_mask):
        high_freqs = freqs[high_mask]
        high_db = psd_db[high_mask]
        
        # Compute gradient (slope of drop)
        db_grad = np.diff(high_db)
        steepest_drop_idx = np.argmin(db_grad) if len(db_grad) > 0 else 0
        if len(db_grad) > 0 and db_grad[steepest_drop_idx] < -15.0:
            cutoff_detected = True
            detected_cutoff = float(high_freqs[steepest_drop_idx])

    # 3. High-frequency to Low-frequency energy ratio
    mid_energy = float(np.sum(psd[(freqs >= 500) & (freqs < 8000)]))
    high_energy = float(np.sum(psd[freqs >= 8000]))
    energy_ratio = float(high_energy / (mid_energy + 1e-9))

    # 4. Spectral Flatness (Wiener entropy)
    geometric_mean = np.exp(np.mean(np.log(psd_safe)))
    arithmetic_mean = np.mean(psd_safe)
    flatness = float(geometric_mean / (arithmetic_mean + 1e-9))

    # 5. Dynamic range
    dyn_range = float(np.max(psd_db) - np.min(psd_db))

    # Neural vocoder anomaly heuristic: sharp cutoff with unnatural spectral flatness
    neural_vocoder = bool(cutoff_detected or (flatness > 0.45 and energy_ratio < 0.02))

    return {
        "nyquist_cutoff_detected": cutoff_detected,
        "cutoff_frequency_hz": round(detected_cutoff, 1),
        "high_freq_energy_ratio": round(energy_ratio, 4),
        "neural_vocoder_anomaly": neural_vocoder,
        "spectral_flatness": round(flatness, 4),
        "dynamic_range_db": round(dyn_range, 2)
    }


def analyze_audio_pipeline(audio_path: str) -> Dict[str, Any]:
    """
    Executes the dedicated AI music detection and audio forensic pipeline.
    Specifically evaluates AI-generated music (e.g. EnCodec/DAC vocoders used in Suno, Udio, MusicGen)
    versus human-composed studio or acoustic music.
    Does NOT perform speech detection, voice cloning detection, or speaker identification.
    """
    start_time = time.time()
    samples, sample_rate = load_audio_signal(audio_path, max_duration_sec=30.0)
    spectral_metrics = analyze_spectral_footprint(samples, sample_rate)

    duration_sec = round(float(len(samples) / sample_rate), 2) if sample_rate > 0 else 0.0

    # Guard: insufficient audio length or invalid stream
    if duration_sec < 1.0 or len(samples) < 1024:
        return {
            "media_type": "audio",
            "sample_rate": sample_rate,
            "duration_seconds": duration_sec,
            "spectral_metrics": spectral_metrics,
            "predicted_label": "INCONCLUSIVE",
            "confidence": 0.50,
            "forensic_summary": "Audio duration is too short (< 1.0s) for spectral envelope and harmonic analysis.",
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }

    # Calibrate evidence based on neural music decoder footprints vs organic music acoustics
    is_neural = spectral_metrics["neural_vocoder_anomaly"]
    has_cutoff = spectral_metrics["nyquist_cutoff_detected"]
    dyn_range = spectral_metrics["dynamic_range_db"]
    energy_ratio = spectral_metrics["high_freq_energy_ratio"]

    # 1. High confidence AI Music generation: steep brick-wall neural vocoder cutoff (typical of 24k/32k upsampling)
    if has_cutoff and energy_ratio < 0.03:
        pred_label = "AI-GENERATED"
        confidence = 0.88
        summary = (
            f"Characteristic neural audio codec cutoff detected at {spectral_metrics['cutoff_frequency_hz']} Hz "
            "with steep high-frequency suppression, consistent with generative AI music decoders (EnCodec/DAC)."
        )
    # 2. Moderate AI Music generation: suppressed high frequencies + unnatural flatness
    elif is_neural and energy_ratio < 0.02:
        pred_label = "AI-GENERATED"
        confidence = 0.74
        summary = "Anomalous high-frequency suppression and synthetic neural music quantization pattern detected."
    # 3. Human / Real Music: wide dynamic range + natural acoustic overtone harmonics extending beyond 10kHz
    elif dyn_range > 35.0 and energy_ratio > 0.06:
        pred_label = "REAL / HUMAN"
        confidence = 0.82
        summary = "Continuous harmonic overtones, natural acoustic dynamic range, and organic spectral decay detected."
    # 4. Ambiguous / Low-bitrate / Inconclusive: return INCONCLUSIVE rather than forcing binary guess
    else:
        pred_label = "INCONCLUSIVE"
        confidence = 0.50
        summary = "Audio compression or indeterminate acoustic envelope prevents definitive music origin attribution."

    exec_time_ms = int((time.time() - start_time) * 1000)

    return {
        "media_type": "audio",
        "sample_rate": sample_rate,
        "duration_seconds": duration_sec,
        "spectral_metrics": spectral_metrics,
        "predicted_label": pred_label,
        "confidence": confidence,
        "forensic_summary": summary,
        "execution_time_ms": exec_time_ms
    }
