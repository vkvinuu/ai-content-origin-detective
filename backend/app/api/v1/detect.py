import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import sanitize_filename, validate_image_stream, verify_image_integrity, verify_media_integrity
from app.core.exceptions import SecurityValidationError
from app.core.auth import get_optional_current_user, get_current_user
from app.db.session import get_db
from app.db.models import Analysis, ForensicSignal, MLEvaluation, ContentDNA
from app.schemas.analysis import AnalysisResponseSchema, SignedUrlResponse
from app.services.dna.hasher import compute_content_dna
from app.services.forensics.exif_parser import parse_metadata
from app.services.forensics.ela import perform_ela
from app.services.forensics.fourier import perform_fft_analysis
from app.services.forensics.noise import analyze_noise_residual
from app.services.forensics.steganography import check_steganography_indicators
from app.services.ml.inference import run_ml_detection
from app.services.synthesizer.decision_engine import synthesize_analysis
from app.services.supabase_storage import supabase_storage

from app.services.forensics.video_analyzer import analyze_video_pipeline
from app.services.forensics.audio_analyzer import analyze_audio_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detect", tags=["Detection & Analysis"])


def attach_signed_urls(analysis: Analysis) -> None:
    """Populates transient signed URLs for private Supabase Storage assets."""
    if supabase_storage.is_configured:
        if analysis.storage_path:
            analysis.signed_image_url = supabase_storage.create_signed_url(analysis.storage_path, expires_in=3600)
        if analysis.report_storage_path:
            analysis.signed_report_url = supabase_storage.create_signed_url(analysis.report_storage_path, expires_in=3600)


async def execute_analysis_pipeline(
    analysis_id: str,
    raw_path: str,       # The original uploaded file (preserved for forensics)
    orig_filename: str,
    file_size: int,
    mime_type: str,
    width: int,
    height: int,
    db: AsyncSession,
    user_id: Optional[str] = None
) -> None:
    """Executes the complete multi-signal forensic and ML pipeline and persists results."""
    try:
        # 1. Content DNA from original raw file
        dna_data = compute_content_dna(raw_path, settings.ENGINE_VERSION)

        # Branch according to media modality
        if mime_type.startswith("video/"):
            video_res = analyze_video_pipeline(raw_path, settings.ARTIFACT_DIR)
            temp_metrics = video_res["temporal_metrics"]
            ml_results = video_res["frame_evaluations"]
            
            # Synthesize video verdict with D3 physical kinematics and keyframe ML
            verdict_reasons = [
                f"Video container analyzed ({video_res['video_metadata']['codec']}, {video_res['video_metadata']['fps']} FPS, {video_res['video_metadata']['duration_seconds']}s).",
                f"Evaluated {video_res['keyframes_evaluated']} keyframe(s) across temporal sequence."
            ]
            if temp_metrics["temporal_anomaly_detected"]:
                verdict_reasons.append(
                    f"D3 kinematic divergence & temporal flickering detected (jerk ratio: {temp_metrics.get('d3_jerk_ratio', 0.0)}, morphing index: {temp_metrics['morphing_index']})."
                )

            ai_score = video_res["aggregated_ai_score"]
            frame_scores = [ev.get("normalized_probabilities", {}).get("AI-GENERATED", 0.5) for ev in ml_results if "ateeqq" in ev.get("model_name", "").lower()]
            has_high_variance = (max(frame_scores) - min(frame_scores) > 0.55) if len(frame_scores) >= 2 else False

            # Categorization based on physical kinematics + spatial distribution:
            # 1. Full AI Generation (T2V / I2V): uniformly high synthetic keyframes + optical flow divergence
            if ai_score >= 0.75 and temp_metrics["temporal_anomaly_detected"]:
                final_verdict = "AI-GENERATED"
                overall_confidence = round(min(0.95, max(ai_score, 0.78)), 2)
                verdict_reasons.append("Sustained synthetic neural artifacts across all keyframes corroborated by Newtonian motion flow divergence (T2V/I2V generation footprint).")

            elif ai_score >= 0.70:
                final_verdict = "AI-GENERATED"
                overall_confidence = round(max(ai_score, 0.75), 2)
                verdict_reasons.append("Consistent algorithmic synthesis detected across video keyframe ensemble.")

            # 2. Mixed / Face-Swapped / AI-Modified: high variance across frames or temporal anomaly with moderate keyframe scores
            elif has_high_variance or (temp_metrics["temporal_anomaly_detected"] and 0.40 <= ai_score < 0.70):
                final_verdict = "AI-MODIFIED"
                overall_confidence = 0.72
                verdict_reasons.append("Localized temporal discontinuity or partial synthetic keyframe variation detected, consistent with facial manipulation, inpainting, or spliced AI footage.")

            # 3. Real Camera Recording: low AI scores without physical kinematic discontinuities
            elif ai_score <= 0.28 and not temp_metrics["temporal_anomaly_detected"]:
                final_verdict = "REAL / HUMAN"
                overall_confidence = round(1.0 - ai_score, 2)
                verdict_reasons.append("Continuous physical acceleration dynamics and authentic camera sensor characteristics observed across video stream.")

            # 4. Inconclusive: degraded video, ambiguous evidence, or unresolvable disagreement
            else:
                final_verdict = "UNKNOWN / INCONCLUSIVE"
                overall_confidence = 0.50
                verdict_reasons.append("Video frame quality, optical flow continuity, or neural classifier consensus is statistically indeterminate.")

            synthesis = {
                "final_verdict": final_verdict,
                "overall_confidence": overall_confidence,
                "verdict_reasons": verdict_reasons,
                "limitations": [
                    "Temporal video analysis evaluates uniform keyframe samples and Newtonian second-order optical flow.",
                    "Heavily compressed social media re-encodings can induce artificial motion artifacts."
                ]
            }
            metadata_findings = {"exif_metadata": {}, "has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
            ela_findings = {"ela_mean_discrepancy": 0.0, "ela_max_discrepancy": 0.0, "ela_anomaly_detected": False, "ela_heatmap_url": None}
            fft_findings = {"fft_peak_harmonic_ratio": 1.0, "fft_lattice_anomaly_detected": False, "fft_spectrum_url": None}
            noise_findings = {"noise_variance": 0.0, "noise_uniformity_score": 1.0, "compression_quality_estimate": 80}
            stego_findings = {"steganography_anomaly": False}
            ela_storage_path = None
            fft_storage_path = None

        elif mime_type.startswith("audio/"):
            audio_res = analyze_audio_pipeline(raw_path)
            ml_results = []
            final_verdict = audio_res["predicted_label"]
            overall_confidence = audio_res["confidence"]
            verdict_reasons = [
                f"Audio stream analyzed ({audio_res['sample_rate']} Hz, {audio_res['duration_seconds']}s).",
                audio_res["forensic_summary"]
            ]
            synthesis = {
                "final_verdict": final_verdict,
                "overall_confidence": overall_confidence,
                "verdict_reasons": verdict_reasons,
                "limitations": ["Audio evaluation based on STFT spectral envelope and neural vocoder residual physics."]
            }
            metadata_findings = {"exif_metadata": {}, "has_ai_metadata": False, "ai_metadata_tags": [], "c2pa_manifest_detected": False}
            ela_findings = {"ela_mean_discrepancy": 0.0, "ela_max_discrepancy": 0.0, "ela_anomaly_detected": False, "ela_heatmap_url": None}
            fft_findings = {"fft_peak_harmonic_ratio": 1.0, "fft_lattice_anomaly_detected": False, "fft_spectrum_url": None}
            noise_findings = {"noise_variance": 0.0, "noise_uniformity_score": 1.0, "compression_quality_estimate": 100}
            stego_findings = {"steganography_anomaly": False}
            ela_storage_path = None
            fft_storage_path = None

        else:
            # 2. Digital Forensics directly on original raw image
            metadata_findings = parse_metadata(raw_path)
            ela_findings = perform_ela(raw_path, settings.ARTIFACT_DIR, analysis_id)
            fft_findings = perform_fft_analysis(raw_path, settings.ARTIFACT_DIR, analysis_id)
            noise_findings = analyze_noise_residual(raw_path)
            stego_findings = check_steganography_indicators(raw_path)

            # 3. Machine Learning Ensemble directly on original raw file
            ml_results = run_ml_detection(raw_path)

            # 4. Multi-Signal Decision Synthesis
            synthesis = synthesize_analysis(
                metadata_findings=metadata_findings,
                ela_findings=ela_findings,
                fft_findings=fft_findings,
                noise_findings=noise_findings,
                stego_findings=stego_findings,
                ml_evaluations=ml_results,
                dimensions=(width, height)
            )

            # Upload ELA & FFT artifacts if available
            ela_local = os.path.join(settings.ARTIFACT_DIR, f"ela_{analysis_id}.jpg")
            fft_local = os.path.join(settings.ARTIFACT_DIR, f"fft_{analysis_id}.jpg")
            ela_dest = f"analyses/{analysis_id}/ela_heatmap.jpg"
            fft_dest = f"analyses/{analysis_id}/fft_spectrum.jpg"

            ela_storage_path = supabase_storage.upload_file(ela_local, ela_dest, content_type="image/jpeg") if os.path.exists(ela_local) else None
            fft_storage_path = supabase_storage.upload_file(fft_local, fft_dest, content_type="image/jpeg") if os.path.exists(fft_local) else None

        # 5. Upload original media to private Supabase Storage bucket
        storage_dest = f"analyses/{analysis_id}/original_{orig_filename}"
        supabase_img_path = supabase_storage.upload_file(raw_path, storage_dest, content_type=mime_type)

        # 6. Persist to database
        analysis = Analysis(
            id=analysis_id,
            user_id=user_id,
            image_sha256=dna_data["sha256_hash"],
            image_phash=dna_data["perceptual_hash"],
            file_name=orig_filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            dimensions_width=width,
            dimensions_height=height,
            storage_path=supabase_img_path or storage_dest,
            final_verdict=synthesis["final_verdict"],
            overall_confidence=synthesis["overall_confidence"],
            verdict_reasons=synthesis["verdict_reasons"],
            limitations=synthesis["limitations"],
            status="COMPLETED",
            engine_version=settings.ENGINE_VERSION,
            completed_at=datetime.now(timezone.utc)
        )

        forensic_signal = ForensicSignal(
            analysis_id=analysis_id,
            exif_metadata=metadata_findings["exif_metadata"],
            has_ai_metadata=metadata_findings["has_ai_metadata"],
            ai_metadata_tags=metadata_findings["ai_metadata_tags"],
            c2pa_manifest_detected=metadata_findings["c2pa_manifest_detected"],
            ela_mean_discrepancy=ela_findings["ela_mean_discrepancy"],
            ela_max_discrepancy=ela_findings["ela_max_discrepancy"],
            ela_anomaly_detected=ela_findings["ela_anomaly_detected"],
            ela_heatmap_url=ela_findings["ela_heatmap_url"],
            ela_storage_path=ela_storage_path,
            fft_peak_harmonic_ratio=fft_findings["fft_peak_harmonic_ratio"],
            fft_lattice_anomaly_detected=fft_findings["fft_lattice_anomaly_detected"],
            fft_spectrum_url=fft_findings["fft_spectrum_url"],
            fft_storage_path=fft_storage_path,
            noise_variance=noise_findings["noise_variance"],
            noise_uniformity_score=noise_findings["noise_uniformity_score"],
            steganography_anomaly=stego_findings["steganography_anomaly"],
            compression_quality_estimate=noise_findings["compression_quality_estimate"],
            forensic_summary="; ".join(synthesis["verdict_reasons"][:3])
        )

        content_dna = ContentDNA(
            analysis_id=analysis_id,
            sha256_hash=dna_data["sha256_hash"],
            md5_hash=dna_data["md5_hash"],
            perceptual_hash=dna_data["perceptual_hash"],
            difference_hash=dna_data["difference_hash"],
            wavelet_hash=dna_data["wavelet_hash"],
            color_histogram_vector=dna_data["color_histogram_vector"],
            dna_fingerprint_composite=dna_data["dna_fingerprint_composite"]
        )

        db.add(analysis)
        db.add(forensic_signal)
        db.add(content_dna)

        for ml_item in ml_results:
            db.add(MLEvaluation(
                analysis_id=analysis_id,
                model_name=ml_item["model_name"],
                model_version=ml_item["model_version"],
                architecture=ml_item.get("architecture"),
                specialization=ml_item.get("specialization"),
                known_limitation=ml_item.get("known_limitation"),
                predicted_label=ml_item["predicted_label"],
                raw_probabilities=ml_item["raw_probabilities"],
                normalized_probabilities=ml_item.get("normalized_probabilities", {}),
                confidence=ml_item["confidence"],
                execution_time_ms=ml_item["execution_time_ms"]
            ))

        await db.commit()
        logger.info(f"Analysis {analysis_id} completed: {synthesis['final_verdict']}")

    except Exception as e:
        logger.error(f"Pipeline error for {analysis_id}: {e}", exc_info=True)
        await db.rollback()

        # Attempt to persist a failure record so the investigation isn't lost.
        # Wrap in its own try/except so we never swallow the original error.
        try:
            # Convert user_id to a proper UUID string if present, or None
            safe_user_id = None
            if user_id:
                try:
                    import uuid as _uuid_mod
                    safe_user_id = str(_uuid_mod.UUID(str(user_id)))
                except (ValueError, AttributeError):
                    safe_user_id = None

            failed_record = Analysis(
                id=analysis_id,
                user_id=safe_user_id,
                image_sha256="unknown",
                image_phash="unknown",
                file_name=orig_filename,
                file_size_bytes=file_size,
                mime_type=mime_type,
                dimensions_width=width,
                dimensions_height=height,
                final_verdict="UNKNOWN / INCONCLUSIVE",
                overall_confidence=0.0,
                verdict_reasons=["Pipeline execution encountered an unexpected error."],
                limitations=[str(e)],
                status="FAILED",
                error_message=str(e)[:2000],
                engine_version=settings.ENGINE_VERSION
            )
            db.add(failed_record)
            await db.commit()
        except Exception as persist_err:
            logger.error(f"Failed to persist error record for {analysis_id}: {persist_err}", exc_info=True)
            await db.rollback()


@router.post("/analyze", response_model=AnalysisResponseSchema)
async def analyze_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Accepts any image format, enforces security checks, runs the full
    forensics + ML + DNA pipeline, uploads to private storage, and returns the evidence dossier.
    Associates the investigation with authenticated user ID if provided.
    """
    # --- Step 1: Read entire file into memory once ---
    contents: bytes = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise SecurityValidationError("Uploaded file is empty.")

    # Read first 16 bytes for magic byte detection
    header_bytes = contents[:16]

    # --- Step 2: Magic-byte validation & size check ---
    mime_type, ext = validate_image_stream(header_bytes, file_size)

    # --- Step 3: Save uploaded file with safe name ---
    safe_name = sanitize_filename(file.filename or "upload")
    analysis_id = str(uuid.uuid4())
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.ARTIFACT_DIR, exist_ok=True)

    # Preserve original format in raw path
    raw_ext = os.path.splitext(safe_name)[1].lower() or ext
    raw_filename = f"{analysis_id}_raw{raw_ext}"
    raw_filepath = os.path.join(settings.UPLOAD_DIR, raw_filename)

    with open(raw_filepath, "wb") as f:
        f.write(contents)

    # --- Step 4: Integrity check & dimension extraction ---
    width, height = verify_media_integrity(raw_filepath, mime_type)

    # --- Step 5: Full analysis pipeline on authentic uploaded file ---
    user_id = None
    if current_user:
        raw_uid = current_user.get("id")
        if raw_uid:
            try:
                user_id = str(uuid.UUID(str(raw_uid)))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid user ID from token, ignoring: {raw_uid}")
                user_id = None

    await execute_analysis_pipeline(
        analysis_id=analysis_id,
        raw_path=raw_filepath,
        orig_filename=safe_name,
        file_size=file_size,
        mime_type=mime_type,
        width=width,
        height=height,
        db=db,
        user_id=user_id
    )

    # --- Step 6: Return completed record ---
    stmt = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(
            selectinload(Analysis.forensic_signals),
            selectinload(Analysis.ml_evaluations),
            selectinload(Analysis.content_dna)
        )
    )
    result = await db.execute(stmt)
    analysis_record = result.scalar_one_or_none()

    if not analysis_record:
        raise HTTPException(status_code=500, detail="Failed to retrieve completed analysis record.")

    attach_signed_urls(analysis_record)
    return analysis_record


@router.get("/result/{analysis_id}", response_model=AnalysisResponseSchema)
async def get_analysis_result(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Retrieves full analysis record by ID.
    Enforces user ownership check if user_id is set on the investigation.
    """
    stmt = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(
            selectinload(Analysis.forensic_signals),
            selectinload(Analysis.ml_evaluations),
            selectinload(Analysis.content_dna)
        )
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found.")

    # Ownership check: If recorded with a user_id, ensure requesting user matches
    if record.user_id and current_user:
        if current_user.get("id") != record.user_id and current_user.get("role") != "service_role":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this investigation record.")

    attach_signed_urls(record)
    return record


@router.get("/history", response_model=List[AnalysisResponseSchema])
async def list_recent_analyses(
    limit: int = 50,
    user_only: bool = Query(False, description="Filter solely to authenticated user's records"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Returns investigation history.
    If authenticated, returns the user's investigation records or global history.
    """
    stmt = select(Analysis).order_by(Analysis.created_at.desc())

    if user_only and current_user:
        stmt = stmt.where(Analysis.user_id == current_user["id"])
    elif user_only and not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required to filter user history.")

    stmt = stmt.limit(min(limit, 100)).options(
        selectinload(Analysis.forensic_signals),
        selectinload(Analysis.ml_evaluations),
        selectinload(Analysis.content_dna)
    )

    result = await db.execute(stmt)
    records = result.scalars().all()
    for rec in records:
        attach_signed_urls(rec)
    return records


@router.get("/{analysis_id}/signed-url", response_model=SignedUrlResponse)
async def get_asset_signed_url(
    analysis_id: str,
    file_type: str = Query("image", pattern="^(image|report|ela|fft)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Returns a fresh, short-lived signed URL for an authorized private file download.
    """
    stmt = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(selectinload(Analysis.forensic_signals))
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    if record.user_id and current_user and current_user.get("id") != record.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    target_path = None
    if file_type == "image":
        target_path = record.storage_path
    elif file_type == "report":
        target_path = record.report_storage_path
    elif file_type == "ela" and record.forensic_signals:
        target_path = record.forensic_signals.ela_storage_path
    elif file_type == "fft" and record.forensic_signals:
        target_path = record.forensic_signals.fft_storage_path

    if not target_path:
        raise HTTPException(status_code=404, detail=f"No stored asset found for type '{file_type}'.")

    signed_url = supabase_storage.create_signed_url(target_path, expires_in=3600)
    if not signed_url:
        # Fallback to local artifact URL if Supabase storage is unconfigured
        if file_type == "image":
            signed_url = f"/uploads/{os.path.basename(target_path)}"
        else:
            signed_url = f"/artifacts/{os.path.basename(target_path)}"

    return SignedUrlResponse(
        file_type=file_type,
        signed_url=signed_url,
        expires_in=3600
    )
