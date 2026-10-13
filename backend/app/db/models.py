import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)


class PortableUUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's native UUID column on Postgres and CHAR(36) on SQLite.
    Accepts and returns Python uuid.UUID objects or their string representation.
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, _uuid.UUID) else _uuid.UUID(str(value))
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, _uuid.UUID):
            return value
        return _uuid.UUID(str(value))


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    # Authenticated User Association (matches Supabase auth.users.id UUID)
    user_id = Column(PortableUUID(), nullable=True, index=True)

    image_sha256 = Column(String(64), nullable=False, index=True)
    image_phash = Column(String(64), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    dimensions_width = Column(Integer, nullable=False)
    dimensions_height = Column(Integer, nullable=False)
    
    # Storage paths in private Supabase Storage bucket
    storage_path = Column(String(512), nullable=True) # e.g. "analyses/{id}/original.jpg"
    report_storage_path = Column(String(512), nullable=True) # e.g. "analyses/{id}/report.pdf"

    # Verdict: REAL / HUMAN, AI-GENERATED, AI-MODIFIED, MANIPULATED, UNKNOWN / INCONCLUSIVE, INCONCLUSIVE — MODEL DISAGREEMENT
    final_verdict = Column(String(64), nullable=False, default="UNKNOWN / INCONCLUSIVE")
    overall_confidence = Column(Float, nullable=False, default=0.0)
    verdict_reasons = Column(JSON, nullable=False, default=list)
    limitations = Column(JSON, nullable=False, default=list)
    
    # Processing Status: PENDING, PROCESSING, COMPLETED, FAILED
    status = Column(String(32), nullable=False, default="PENDING")
    error_message = Column(Text, nullable=True)
    engine_version = Column(String(32), nullable=False, default="1.0.0")
    
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    forensic_signals = relationship("ForensicSignal", back_populates="analysis", uselist=False, cascade="all, delete-orphan")
    ml_evaluations = relationship("MLEvaluation", back_populates="analysis", cascade="all, delete-orphan")
    content_dna = relationship("ContentDNA", back_populates="analysis", uselist=False, cascade="all, delete-orphan")

    @property
    def forensic_signal(self):
        return self.forensic_signals

    @forensic_signal.setter
    def forensic_signal(self, value):
        self.forensic_signals = value

class ForensicSignal(Base):
    __tablename__ = "forensic_signals"

    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Metadata findings
    exif_metadata = Column(JSON, nullable=False, default=dict)
    has_ai_metadata = Column(Boolean, default=False)
    ai_metadata_tags = Column(JSON, nullable=False, default=list)
    c2pa_manifest_detected = Column(Boolean, default=False)
    
    # Error Level Analysis
    ela_mean_discrepancy = Column(Float, nullable=True)
    ela_max_discrepancy = Column(Float, nullable=True)
    ela_anomaly_detected = Column(Boolean, default=False)
    ela_heatmap_url = Column(String(255), nullable=True) # signed URL or path
    ela_storage_path = Column(String(512), nullable=True) # Supabase storage object path

    # Fourier / Frequency Analysis
    fft_peak_harmonic_ratio = Column(Float, nullable=True)
    fft_lattice_anomaly_detected = Column(Boolean, default=False)
    fft_spectrum_url = Column(String(255), nullable=True) # signed URL or path
    fft_storage_path = Column(String(512), nullable=True) # Supabase storage object path

    # Noise Residual & Consistency
    noise_variance = Column(Float, nullable=True)
    noise_uniformity_score = Column(Float, nullable=True)
    steganography_anomaly = Column(Boolean, default=False)
    compression_quality_estimate = Column(Integer, nullable=True)
    
    forensic_summary = Column(Text, nullable=False, default="")

    analysis = relationship("Analysis", back_populates="forensic_signals")

class MLEvaluation(Base):
    __tablename__ = "ml_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    model_name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=False)
    architecture = Column(String(64), nullable=True)
    specialization = Column(Text, nullable=True)
    known_limitation = Column(Text, nullable=True)
    predicted_label = Column(String(64), nullable=False)
    raw_probabilities = Column(JSON, nullable=False, default=dict)
    normalized_probabilities = Column(JSON, nullable=True, default=dict)
    confidence = Column(Float, nullable=False)
    execution_time_ms = Column(Integer, nullable=False, default=0)

    analysis = relationship("Analysis", back_populates="ml_evaluations")

class ContentDNA(Base):
    __tablename__ = "content_dna"

    id = Column(String(36), primary_key=True, default=lambda: str(_uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sha256_hash = Column(String(64), nullable=False, index=True)
    md5_hash = Column(String(32), nullable=False)
    perceptual_hash = Column(String(64), nullable=False)
    difference_hash = Column(String(64), nullable=False)
    wavelet_hash = Column(String(64), nullable=False)
    color_histogram_vector = Column(JSON, nullable=False, default=list)
    dna_fingerprint_composite = Column(Text, nullable=False)

    analysis = relationship("Analysis", back_populates="content_dna")
