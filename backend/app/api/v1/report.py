import io
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Analysis
from app.core.auth import get_optional_current_user
from app.services.report_generator import generate_pdf_dossier
from app.services.supabase_storage import supabase_storage

router = APIRouter(prefix="/report", tags=["Forensic Reports"])

@router.get("/{analysis_id}/pdf")
async def download_pdf_report(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_optional_current_user)
):
    """
    Generates and downloads a formal forensic audit PDF dossier.
    Also caches the generated PDF to Supabase Storage if configured.
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
    analysis_record = result.scalar_one_or_none()

    if not analysis_record:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    # Ownership check
    if analysis_record.user_id and current_user:
        if current_user.get("id") != analysis_record.user_id and current_user.get("role") != "service_role":
            raise HTTPException(status_code=403, detail="Access denied to this forensic report.")

    pdf_stream = generate_pdf_dossier(analysis_record)
    pdf_bytes = pdf_stream.getvalue()
    filename = f"forensic_report_{analysis_id[:8]}.pdf"

    # Persist report path to Supabase storage asynchronously if storage is enabled
    if supabase_storage.is_configured and not analysis_record.report_storage_path:
        storage_dest = f"analyses/{analysis_id}/report_{filename}"
        supabase_path = supabase_storage.upload_bytes(pdf_bytes, storage_dest, content_type="application/pdf")
        if supabase_path:
            analysis_record.report_storage_path = supabase_path
            await db.commit()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
