from fastapi import APIRouter
from app.api.v1.detect import router as detect_router
from app.api.v1.report import router as report_router
from app.api.v1.health import router as health_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(detect_router)
api_v1_router.include_router(report_router)
api_v1_router.include_router(health_router)
