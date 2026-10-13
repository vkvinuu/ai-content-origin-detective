import time
import logging
from typing import Dict, Any, List, Optional
from PIL import Image
from app.services.ml.model_manager import model_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

# Known architectural characteristics and training biases
MODEL_METADATA = {
    "Ateeqq/ai-vs-human-image-detector": {
        "version": "siglip-so400m-art-diffusion",
        "architecture": "SigLIP",
        "specialization": "Modern diffusion & digital art (Midjourney, DALL-E, SDXL, artistic renders)",
        "known_limitation": "May capture stylistic digital aesthetics; less sensitive to raw camera sensor compression."
    },
    "umm-maybe/AI-image-detector": {
        "version": "vit-base-patch16-diffusiondb",
        "architecture": "ViT",
        "specialization": "DiffusionDB baseline (Early Stable Diffusion 1.4/1.5 vs ImageNet)",
        "known_limitation": "Trained on early diffusion models; underperforms on modern high-resolution or photorealistic outputs."
    }
}

def map_model_label(raw_label: str, model_id: str = "") -> str:
    """
    Explicit, auditable label normalization across heterogeneous model vocabularies.
    Never assumes identical label indices or naming conventions.
    
    Verified mappings:
    - Ateeqq/ai-vs-human-image-detector: {0: 'ai', 1: 'hum'}
    - umm-maybe/AI-image-detector:       {0: 'artificial', 1: 'human'}
    """
    clean_label = raw_label.lower().strip()

    # 1. Model-specific exact overrides
    if "ateeqq" in model_id.lower():
        if clean_label == "ai":
            return "AI-GENERATED"
        if clean_label == "hum":
            return "REAL / HUMAN"

    if "umm-maybe" in model_id.lower():
        if clean_label in ("artificial", "artif"):
            return "AI-GENERATED"
        if clean_label in ("human", "hum"):
            return "REAL / HUMAN"

    # 2. Universal exact matches
    ai_synonyms = {"ai", "artificial", "fake", "synthetic", "deepfake", "generated", "sdxl"}
    human_synonyms = {"hum", "human", "real", "authentic", "photo", "pristine", "natural"}

    if clean_label in ai_synonyms:
        return "AI-GENERATED"
    if clean_label in human_synonyms:
        return "REAL / HUMAN"

    # 3. Substring matching as safe fallback
    if any(k in clean_label for k in ["artif", "fake", "synth", "gen"]):
        return "AI-GENERATED"
    if any(k in clean_label for k in ["human", "real", "photo", "auth"]):
        return "REAL / HUMAN"

    return "INCONCLUSIVE"


def extract_class_probabilities(
    raw_preds: List[Dict[str, Any]],
    model_id: str = "",
    temperature: Optional[float] = None
) -> Dict[str, float]:
    """
    Extracts calibrated {AI-GENERATED: float, REAL / HUMAN: float} probabilities from model output.
    Applies temperature scaling (Platt scaling on log-odds) to prevent deep vision transformer
    cross-entropy overconfidence saturation (0.9999 / 0.0001) while strictly preserving rank-order
    and relative uncertainty across ensemble constituents.
    """
    if temperature is None:
        temperature = getattr(settings, "ML_CALIBRATION_TEMPERATURE", 1.6)

    prob_ai = 0.5
    prob_human = 0.5

    for p in raw_preds:
        label = p.get("label", "")
        score = float(p.get("score", 0.0))
        mapped = map_model_label(label, model_id)
        if mapped == "AI-GENERATED":
            prob_ai = score
        elif mapped == "REAL / HUMAN":
            prob_human = score

    # Normalize raw distribution
    total = prob_ai + prob_human
    if total > 0:
        prob_ai = prob_ai / total
        prob_human = prob_human / total

    # Apply temperature calibration if temperature > 1.0
    if temperature and temperature > 1.0:
        p = min(max(prob_ai, 1e-5), 1.0 - 1e-5)
        inv_t = 1.0 / temperature
        p_pow = p ** inv_t
        q_pow = (1.0 - p) ** inv_t
        cal_ai = p_pow / (p_pow + q_pow)
        cal_human = 1.0 - cal_ai
        prob_ai = cal_ai
        prob_human = cal_human

    return {
        "AI-GENERATED": round(prob_ai, 4),
        "REAL / HUMAN": round(prob_human, 4)
    }


def run_ml_detection(image_path: str) -> List[Dict[str, Any]]:
    """
    Executes multi-model ML synthetic content detection.
    Runs vision transformer and diffusion detector models in ensemble.
    Returns per-model predictions with versions, raw probabilities, calibrated normalized scores,
    and architectural limitations.
    """
    results: List[Dict[str, Any]] = []

    # Ensure models are loaded
    if not model_manager.is_loaded or len(model_manager.classifiers) < len(model_manager.models_config):
        model_manager.load_models()

    # Open and convert image once for inference
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
    except Exception as e:
        logger.error(f"Failed to open image for ML inference: {e}")
        return results

    # Run inference across configured models
    for m_cfg in model_manager.models_config:
        m_id = m_cfg["id"]
        meta = MODEL_METADATA.get(m_id, {
            "version": "v1.0",
            "architecture": "Transformer",
            "specialization": "Visual classification",
            "known_limitation": "Standard vision classifier limitation."
        })

        clf = model_manager.get_classifier(m_id)
        if clf is None:
            # Attempt on-demand load if classifier was not loaded
            model_manager.load_model(m_id)
            clf = model_manager.get_classifier(m_id)

        if clf is None:
            load_err = model_manager.load_errors.get(m_id, "Model failed to load or initialize.")
            logger.warning(f"ML model '{m_id}' is unavailable: {load_err}")
            results.append({
                "model_name": m_id,
                "model_version": meta["version"],
                "architecture": meta["architecture"],
                "specialization": meta["specialization"],
                "known_limitation": f"Model initialization failed: {load_err}",
                "predicted_label": "FAILED",
                "raw_probabilities": {},
                "normalized_probabilities": {"AI-GENERATED": 0.0, "REAL / HUMAN": 0.0},
                "confidence": 0.0,
                "execution_time_ms": 0,
                "error": str(load_err)
            })
            continue

        start_time = time.time()
        try:
            # Inference via Hugging Face pipeline
            raw_preds = clf(rgb_img)
            exec_time = int((time.time() - start_time) * 1000)

            # Store exact untouched raw probabilities
            raw_prob_dict = {p["label"]: round(float(p["score"]), 4) for p in raw_preds}

            # Map normalized probabilities
            norm_probs = extract_class_probabilities(raw_preds, m_id)
            ai_score = norm_probs["AI-GENERATED"]
            human_score = norm_probs["REAL / HUMAN"]

            # Determine dominant prediction
            if ai_score > human_score:
                predicted_label = "AI-GENERATED"
                confidence = ai_score
            else:
                predicted_label = "REAL / HUMAN"
                confidence = human_score

            # Check uncertainty band
            if settings.ML_UNCERTAINTY_MIN <= confidence <= settings.ML_UNCERTAINTY_MAX:
                predicted_label = "INCONCLUSIVE"

            results.append({
                "model_name": m_id,
                "model_version": meta["version"],
                "architecture": meta["architecture"],
                "specialization": meta["specialization"],
                "known_limitation": meta["known_limitation"],
                "predicted_label": predicted_label,
                "raw_probabilities": raw_prob_dict,
                "normalized_probabilities": norm_probs,
                "confidence": round(confidence, 4),
                "execution_time_ms": exec_time
            })

        except Exception as e:
            logger.warning(f"Inference error for model '{m_id}': {e}")
            results.append({
                "model_name": m_id,
                "model_version": meta["version"],
                "architecture": meta["architecture"],
                "specialization": meta["specialization"],
                "known_limitation": f"Inference execution error: {e}",
                "predicted_label": "FAILED",
                "raw_probabilities": {},
                "normalized_probabilities": {"AI-GENERATED": 0.0, "REAL / HUMAN": 0.0},
                "confidence": 0.0,
                "execution_time_ms": 0,
                "error": str(e)
            })

    if not results:
        logger.warning(f"No neural ML models succeeded for '{image_path}'. Returning empty ML evaluations without unvalidated fallbacks.")

    return results
