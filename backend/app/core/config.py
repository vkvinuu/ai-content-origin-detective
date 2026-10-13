from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AI Content-Origin Detective"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENGINE_VERSION: str = "1.0.0"

    # Database: Supports Supabase PostgreSQL (e.g. postgresql+asyncpg://...) or SQLite fallback
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./detective.db")

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None           # anon or service_role key for backend storage/auth operations
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None # preferred for backend-to-storage admin operations
    SUPABASE_JWT_SECRET: Optional[str] = None    # used for verifying Supabase auth access tokens locally
    SUPABASE_STORAGE_BUCKET: str = "investigation-assets" # private storage bucket

    # Security & Storage Constraints
    MAX_UPLOAD_SIZE_BYTES: int = 26214400  # 25 MB
    MAX_IMAGE_PIXELS: int = 89478485      # PIL Decompression bomb protection (approx 9400x9400)
    UPLOAD_DIR: str = "uploads"
    ARTIFACT_DIR: str = "artifacts"
    ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "audio/mpeg",
        "audio/wav",
        "audio/flac",
        "audio/ogg"
    ]
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ML Models (Primary SigLIP detector for modern diffusion/art + ViT baseline)
    PRIMARY_ML_MODEL: str = "Ateeqq/ai-vs-human-image-detector"
    BASELINE_ML_MODEL: str = "umm-maybe/AI-image-detector"
    USE_CPU_ONLY: bool = True
    ML_UNCERTAINTY_MIN: float = 0.45
    ML_UNCERTAINTY_MAX: float = 0.55
    ML_CALIBRATION_TEMPERATURE: float = 1.6

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
