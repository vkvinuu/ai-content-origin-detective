from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ForensicSignalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exif_metadata: Dict[str, Any] = Field(default_factory=dict)
    has_ai_metadata: bool = False
    ai_metadata_tags: List[str] = Field(default_factory=list)
    c2pa_manifest_detected: bool = False
    ela_mean_discrepancy: Optional[float] = None
    ela_max_discrepancy: Optional[float] = None
    ela_anomaly_detected: bool = False
    ela_heatmap_url: Optional[str] = None
    ela_storage_path: Optional[str] = None
    fft_peak_harmonic_ratio: Optional[float] = None
    fft_lattice_anomaly_detected: bool = False
    fft_spectrum_url: Optional[str] = None
    fft_storage_path: Optional[str] = None
    noise_variance: Optional[float] = None
    noise_uniformity_score: Optional[float] = None
    steganography_anomaly: bool = False
    compression_quality_estimate: Optional[int] = None
    forensic_summary: str = ""

class MLEvaluationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_name: str
    model_version: str
    architecture: Optional[str] = None
    specialization: Optional[str] = None
    known_limitation: Optional[str] = None
    predicted_label: str
    raw_probabilities: Dict[str, float]
    normalized_probabilities: Optional[Dict[str, float]] = None
    confidence: float
    execution_time_ms: int

class ContentDNASchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sha256_hash: str
    md5_hash: str
    perceptual_hash: str
    difference_hash: str
    wavelet_hash: str
    color_histogram_vector: List[float] = Field(default_factory=list)
    dna_fingerprint_composite: str

class SignedUrlResponse(BaseModel):
    file_type: str
    signed_url: str
    expires_in: int = 3600

class AnalysisResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    image_sha256: str
    image_phash: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    dimensions_width: int
    dimensions_height: int
    storage_path: Optional[str] = None
    report_storage_path: Optional[str] = None
    signed_image_url: Optional[str] = None
    signed_report_url: Optional[str] = None
    final_verdict: str  # REAL / HUMAN, AI-GENERATED, AI-MODIFIED, MANIPULATED, UNKNOWN / INCONCLUSIVE
    overall_confidence: float
    verdict_reasons: List[str]
    limitations: List[str]
    status: str
    error_message: Optional[str] = None
    engine_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    forensic_signals: Optional[ForensicSignalSchema] = None
    ml_evaluations: List[MLEvaluationSchema] = Field(default_factory=list)
    content_dna: Optional[ContentDNASchema] = None

class AnalysisStatusResponse(BaseModel):
    id: str
    status: str
    progress_percentage: int
    current_stage: str
    error_message: Optional[str] = None

class UserProfileSchema(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = "authenticated"
