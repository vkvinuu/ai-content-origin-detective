from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_db
from app.services.ml.model_manager import model_manager
from app.services.supabase_storage import supabase_storage

router = APIRouter(prefix="/health", tags=["System Health"])

@router.get("")
async def system_health(db: AsyncSession = Depends(get_db)):
    """System health check endpoint."""
    # Database check
    db_healthy = False
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "engine_name": settings.PROJECT_NAME,
        "engine_version": settings.ENGINE_VERSION,
        "database_connected": db_healthy,
        "database_backend": "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite",
        "supabase_storage_connected": supabase_storage.is_configured,
        "ml_model_loaded": model_manager.is_loaded,
        "ml_model_name": model_manager.model_name
    }
