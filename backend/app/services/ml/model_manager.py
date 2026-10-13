import logging
from typing import Optional, Dict, Any, List
from transformers import pipeline
import torch
from app.core.config import settings

logger = logging.getLogger(__name__)

class ModelManager:
    _instance: Optional["ModelManager"] = None
    
    def __init__(self):
        self.models_config = [
            {
                "id": settings.PRIMARY_ML_MODEL,
                "role": "primary",
                "label_map": {"ai": "AI-GENERATED", "hum": "REAL / HUMAN"}
            },
            {
                "id": settings.BASELINE_ML_MODEL,
                "role": "baseline",
                "label_map": {"artificial": "AI-GENERATED", "human": "REAL / HUMAN"}
            }
        ]
        self.classifiers: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self.load_errors: Dict[str, str] = {}

    @property
    def model_name(self) -> str:
        return f"{settings.PRIMARY_ML_MODEL} + {settings.BASELINE_ML_MODEL}"

    @classmethod
    def get_instance(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self, model_id: str) -> bool:
        """
        Loads a single transformer pipeline model into memory.
        Falls back to local cache if HF Hub request encounters network or authentication issues.
        """
        if model_id in self.classifiers:
            return True

        try:
            logger.info(f"Loading ML detector model: {model_id}...")
            clf = pipeline(
                "image-classification",
                model=model_id,
                device="cpu",
                dtype=torch.float32
            )
            self.classifiers[model_id] = clf
            self.load_errors.pop(model_id, None)
            logger.info(f"Successfully loaded {model_id}")
            return True
        except Exception as e:
            # Fallback to local cache if online check fails
            try:
                logger.info(f"Attempting local_files_only load for {model_id}...")
                clf = pipeline(
                    "image-classification",
                    model=model_id,
                    device="cpu",
                    dtype=torch.float32,
                    model_kwargs={"local_files_only": True}
                )
                self.classifiers[model_id] = clf
                self.load_errors.pop(model_id, None)
                logger.info(f"Successfully loaded {model_id} from local cache")
                return True
            except Exception as local_err:
                logger.warning(f"Could not load Hugging Face model '{model_id}': {e} (local fallback error: {local_err})")
                self.load_errors[model_id] = str(e)
                return False

    def load_models(self) -> bool:
        """
        Loads all configured Hugging Face transformer models for CPU inference.
        Caches models in memory to avoid reload latency.
        """
        success_count = 0
        for m_cfg in self.models_config:
            m_id = m_cfg["id"]
            if self.load_model(m_id):
                success_count += 1

        self.is_loaded = success_count > 0
        return self.is_loaded

    def get_classifier(self, model_id: str) -> Optional[Any]:
        return self.classifiers.get(model_id)

model_manager = ModelManager.get_instance()
