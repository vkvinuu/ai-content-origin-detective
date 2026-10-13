"""
Dedicated AI-Video Detection & Temporal Consistency Analysis Service.
Performs keyframe extraction, inter-frame temporal flow analysis,
flickering/morphing detection, video metadata parsing, and per-frame ML inference.
"""

import os
import time
import logging
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_video_keyframes(
    video_path: str,
    max_frames: int = 8,
    target_fps: float = 1.0
) -> Tuple[List[Image.Image], Dict[str, Any]]:
    """
    Safely extracts keyframes from a video file at a target rate (default 1 FPS)
    up to max_frames for detailed frame analysis.
    Returns (list of PIL RGB frames, video_metadata_dict).
    """
    cap = cv2.VideoCapture(video_path)
    frames: List[Image.Image] = []
    metadata: Dict[str, Any] = {
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "total_frames": 0,
        "duration_seconds": 0.0,
        "codec": "unknown"
    }

    if not os.path.exists(video_path):
        logger.warning(f"Video file does not exist: {video_path}")
        return frames, metadata

    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logger.warning(f"Unable to open video: {video_path}")
        return frames, metadata

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

        duration = (total_frames / fps) if fps > 0 else 0.0

        metadata.update({
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "duration_seconds": round(duration, 2),
            "codec": codec_str or "H264/MPEG4"
        })

        if total_frames <= 0 or fps <= 0:
            return frames, metadata

        # Calculate sampling interval (frames to skip)
        step = max(1, int(fps / target_fps))
        frame_idx = 0

        while cap.isOpened() and len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                # Convert BGR (OpenCV) to RGB (Pillow)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                frames.append(pil_img)

            frame_idx += 1

    finally:
        cap.release()

    return frames, metadata


def analyze_temporal_consistency(video_path: str, max_check_frames: int = 30) -> Dict[str, Any]:
    """
    Measures optical flow differences, high-frequency temporal flickering,
    and texture morphing between consecutive frames.
    AI video generators (Sora, Kling, Gen-2, Pika) exhibit distinct
    temporal coherence failure modes: high-frequency texture morphing,
    unphysical optical flow divergence, and boundary flickering.
    """
    if not os.path.exists(video_path):
        return {
            "temporal_anomaly_detected": False,
            "mean_optical_flow": 0.0,
            "temporal_flicker_score": 0.0,
            "morphing_index": 0.0,
            "evaluated_frame_pairs": 0
        }

    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return {
            "temporal_anomaly_detected": False,
            "mean_optical_flow": 0.0,
            "temporal_flicker_score": 0.0,
            "morphing_index": 0.0,
            "evaluated_frame_pairs": 0
        }

    prev_gray = None
    prev_flow = None
    flow_magnitudes: List[float] = []
    second_order_accels: List[float] = []
    flicker_diffs: List[float] = []
    frame_count = 0

    try:
        while cap.isOpened() and frame_count < max_check_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Resize to standardized dimension for fast, consistent optical flow (320x240)
            small = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None:
                # 1. First-order velocity field (Farneback Optical Flow)
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0
                )
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                flow_magnitudes.append(float(np.mean(mag)))

                # 2. D3: Second-Order Difference-of-Differences (Kinematic Acceleration Consistency)
                # Physical cameras follow Newtonian continuity; AI generators introduce sudden velocity divergences
                if prev_flow is not None:
                    flow_diff = flow - prev_flow
                    accel_mag, _ = cv2.cartToPolar(flow_diff[..., 0], flow_diff[..., 1])
                    second_order_accels.append(float(np.mean(accel_mag)))

                prev_flow = flow

                # 3. Pixel difference (flicker metric)
                diff = np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32))
                flicker_diffs.append(float(np.mean(diff)))

            prev_gray = gray
            frame_count += 1

    finally:
        cap.release()

    if not flow_magnitudes:
        return {
            "temporal_anomaly_detected": False,
            "mean_optical_flow": 0.0,
            "d3_second_order_acceleration": 0.0,
            "temporal_flicker_score": 0.0,
            "morphing_index": 0.0,
            "evaluated_frame_pairs": 0,
            "video_classification_hint": "INCONCLUSIVE"
        }

    mean_flow = float(np.mean(flow_magnitudes))
    std_flow = float(np.std(flow_magnitudes))
    mean_flicker = float(np.mean(flicker_diffs))
    mean_d3_accel = float(np.mean(second_order_accels)) if second_order_accels else 0.0
    
    # AI video temporal anomalies:
    # 1. Morphing index: high variance in flow with unnatural localized texture flicker
    morphing_index = round(std_flow / (mean_flow + 1e-5), 4)
    # 2. D3 acceleration jerk: sudden discontinuous vector jumps between consecutive frame flows
    d3_jerk_ratio = round(mean_d3_accel / (mean_flow + 1e-5), 4) if mean_flow > 0.05 else 0.0
    
    temporal_anomaly = bool(morphing_index > 0.85 or mean_flicker > 25.0 or d3_jerk_ratio > 1.25)

    return {
        "temporal_anomaly_detected": temporal_anomaly,
        "mean_optical_flow": round(mean_flow, 4),
        "d3_second_order_acceleration": round(mean_d3_accel, 4),
        "d3_jerk_ratio": d3_jerk_ratio,
        "temporal_flicker_score": round(mean_flicker, 4),
        "morphing_index": morphing_index,
        "evaluated_frame_pairs": len(flow_magnitudes)
    }


def analyze_video_pipeline(video_path: str, temp_dir: str = "artifacts") -> Dict[str, Any]:
    """
    Executes the complete dedicated video forensic and temporal ML analysis.
    Combines:
    1. Stream & container metadata validation
    2. Temporal consistency & optical flow analysis
    3. Multi-frame ML inference across keyframes
    4. Correlated frame aggregation (does NOT treat frames as independent votes)
    """
    start_time = time.time()
    keyframes, metadata = extract_video_keyframes(video_path, max_frames=6, target_fps=1.0)
    temporal_metrics = analyze_temporal_consistency(video_path, max_check_frames=24)

    # Run ML detector on sampled keyframes
    frame_scores: List[float] = []
    frame_preds: List[str] = []
    frame_evaluations: List[Dict[str, Any]] = []

    for i, frame in enumerate(keyframes):
        # Save temporary frame to disk for inference
        frame_tmp = os.path.join(temp_dir, f"vframe_{os.path.basename(video_path)}_{i}.jpg")
        try:
            frame.save(frame_tmp, format="JPEG", quality=95)
            from app.services.ml.inference import run_ml_detection
            evals = run_ml_detection(frame_tmp)
            if evals:
                frame_evaluations.extend(evals)
                # Primary model AI score
                for ev in evals:
                    if "ateeqq" in ev.get("model_name", "").lower():
                        norm = ev.get("normalized_probabilities", {})
                        frame_scores.append(norm.get("AI-GENERATED", 0.5))
                        frame_preds.append(ev.get("predicted_label", "INCONCLUSIVE"))
        finally:
            if os.path.exists(frame_tmp):
                try:
                    os.remove(frame_tmp)
                except OSError:
                    pass

    # Aggregated consensus: do NOT treat correlated frames as independent binomial trials
    # Use trimmed mean / robust median to avoid single-frame outliers
    if frame_scores:
        aggregated_ai_score = round(float(np.median(frame_scores)), 4)
    else:
        aggregated_ai_score = 0.5

    exec_time_ms = int((time.time() - start_time) * 1000)

    return {
        "media_type": "video",
        "video_metadata": metadata,
        "temporal_metrics": temporal_metrics,
        "keyframes_evaluated": len(keyframes),
        "aggregated_ai_score": aggregated_ai_score,
        "frame_evaluations": frame_evaluations,
        "execution_time_ms": exec_time_ms
    }
