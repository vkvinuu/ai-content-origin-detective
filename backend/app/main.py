import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import DetectiveBaseException, SecurityValidationError
from app.db.session import init_db
from app.api.v1.router import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Ensure critical directories exist at module load time ---
# (StaticFiles mount fails if the directory doesn't exist yet)
_ARTIFACT_DIR = os.path.abspath(settings.ARTIFACT_DIR)
_UPLOAD_DIR = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(_ARTIFACT_DIR, exist_ok=True)
os.makedirs(_UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Content-Origin Detective...")
    await init_db()
    logger.info("Database schema initialized.")
    yield
    logger.info("Shutting down AI Content-Origin Detective.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.ENGINE_VERSION,
    description=(
        "Production-grade digital forensics and machine learning engine for detecting "
        "AI-generated, manipulated, and human-origin visual media."
    ),
    lifespan=lifespan
)

# CORS — allow all origins in development so frontend can reach backend freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount artifacts for serving ELA heatmaps and FFT spectra
app.mount("/artifacts", StaticFiles(directory=_ARTIFACT_DIR), name="artifacts")

@app.exception_handler(SecurityValidationError)
async def security_validation_handler(request: Request, exc: SecurityValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": "SecurityValidationError"}
    )

@app.exception_handler(DetectiveBaseException)
async def detective_exception_handler(request: Request, exc: DetectiveBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": type(exc).__name__}
    )

app.include_router(api_v1_router)

@app.get("/")
async def root():
    return {
        "engine": settings.PROJECT_NAME,
        "version": settings.ENGINE_VERSION,
        "docs_url": "/docs",
        "api_v1": "/api/v1"
    }
