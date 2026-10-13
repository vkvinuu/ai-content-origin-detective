-- =========================================================================
-- AI Content‑Origin Detective – Supabase PostgreSQL Schema & Security DDL
-- Migration: 20261011_000001_init_supabase_schema.sql (secure version)
-- =========================================================================

-- -------------------------------------------------------------------------
-- 1. Enable required extensions (idempotent)
-- -------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -------------------------------------------------------------------------
-- 2. Core tables (preserve all original columns, indexes and FK relationships)
-- -------------------------------------------------------------------------

-- 2.1. Analyses (investigations)
CREATE TABLE IF NOT EXISTS public.analyses (
    id                 VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id            UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    image_sha256       VARCHAR(64) NOT NULL,
    image_phash        VARCHAR(64) NOT NULL,
    file_name          VARCHAR(255) NOT NULL,
    file_size_bytes    INTEGER NOT NULL,
    mime_type          VARCHAR(100) NOT NULL,
    dimensions_width   INTEGER NOT NULL,
    dimensions_height  INTEGER NOT NULL,
    storage_path       VARCHAR(512),
    report_storage_path VARCHAR(512),
    final_verdict      VARCHAR(64) NOT NULL DEFAULT 'UNKNOWN / INCONCLUSIVE',
    overall_confidence FLOAT NOT NULL DEFAULT 0.0,
    verdict_reasons    JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations        JSONB NOT NULL DEFAULT '[]'::jsonb,
    status             VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    error_message      TEXT,
    engine_version     VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_id    ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_sha256     ON public.analyses(image_sha256);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON public.analyses(created_at DESC);

-- 2.2. Forensic signals
CREATE TABLE IF NOT EXISTS public.forensic_signals (
    id                               VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    analysis_id                      VARCHAR(36) NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
    exif_metadata                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    has_ai_metadata                  BOOLEAN DEFAULT FALSE,
    ai_metadata_tags                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    c2pa_manifest_detected           BOOLEAN DEFAULT FALSE,
    ela_mean_discrepancy             FLOAT,
    ela_max_discrepancy              FLOAT,
    ela_anomaly_detected             BOOLEAN DEFAULT FALSE,
    ela_heatmap_url                  VARCHAR(255),
    ela_storage_path                 VARCHAR(512),
    fft_peak_harmonic_ratio          FLOAT,
    fft_lattice_anomaly_detected     BOOLEAN DEFAULT FALSE,
    fft_spectrum_url                 VARCHAR(255),
    fft_storage_path                 VARCHAR(512),
    noise_variance                   FLOAT,
    noise_uniformity_score           FLOAT,
    steganography_anomaly            BOOLEAN DEFAULT FALSE,
    compression_quality_estimate     INTEGER,
    forensic_summary                 TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_forensic_signals_analysis_id ON public.forensic_signals(analysis_id);

-- 2.3. Machine Learning evaluations
CREATE TABLE IF NOT EXISTS public.ml_evaluations (
    id                       VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    analysis_id              VARCHAR(36) NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
    model_name               VARCHAR(128) NOT NULL,
    model_version            VARCHAR(64) NOT NULL,
    architecture             VARCHAR(64),
    specialization           TEXT,
    known_limitation         TEXT,
    predicted_label          VARCHAR(64) NOT NULL,
    raw_probabilities        JSONB NOT NULL DEFAULT '{}'::jsonb,
    normalized_probabilities JSONB DEFAULT '{}'::jsonb,
    confidence               FLOAT NOT NULL,
    execution_time_ms        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ml_evaluations_analysis_id ON public.ml_evaluations(analysis_id);

-- 2.4. Content DNA
CREATE TABLE IF NOT EXISTS public.content_dna (
    id                VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    analysis_id       VARCHAR(36) NOT NULL REFERENCES public.analyses(id) ON DELETE CASCADE,
    sha256_hash       VARCHAR(64) NOT NULL,
    md5_hash          VARCHAR(32) NOT NULL,
    perceptual_hash   VARCHAR(64) NOT NULL,
    difference_hash   VARCHAR(64) NOT NULL,
    wavelet_hash      VARCHAR(64) NOT NULL,
    color_histogram_vector JSONB NOT NULL DEFAULT '[]'::jsonb,
    dna_fingerprint_composite TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_dna_analysis_id ON public.content_dna(analysis_id);
CREATE INDEX IF NOT EXISTS idx_content_dna_sha256      ON public.content_dna(sha256_hash);

-- -------------------------------------------------------------------------
-- 3. Row Level Security (RLS) Policies – drop legacy & current then recreate
-- -------------------------------------------------------------------------

-- Enable RLS on all tables
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forensic_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_dna ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- Drop any existing policies (legacy names and current names) to avoid
-- permissive leftovers.
-- ---------------------------------------------------------------------
-- Analyses
DROP POLICY IF EXISTS "Users can read their own analyses" ON public.analyses;
DROP POLICY IF EXISTS "Users can insert analyses"      ON public.analyses;
DROP POLICY IF EXISTS "Users can update their own analyses" ON public.analyses;
DROP POLICY IF EXISTS "Users can delete analyses" ON public.analyses;
DROP POLICY IF EXISTS analyses_select   ON public.analyses;
DROP POLICY IF EXISTS analyses_insert   ON public.analyses;
DROP POLICY IF EXISTS analyses_update   ON public.analyses;
DROP POLICY IF EXISTS analyses_delete   ON public.analyses;

-- Forensic signals
DROP POLICY IF EXISTS "Users can read child forensic_signals" ON public.forensic_signals;
DROP POLICY IF EXISTS "Users can insert forensic_signals"      ON public.forensic_signals;
DROP POLICY IF EXISTS "Users can update forensic_signals"      ON public.forensic_signals;
DROP POLICY IF EXISTS "Users can delete forensic_signals"      ON public.forensic_signals;
DROP POLICY IF EXISTS forensic_signals_select ON public.forensic_signals;
DROP POLICY IF EXISTS forensic_signals_insert ON public.forensic_signals;
DROP POLICY IF EXISTS forensic_signals_update ON public.forensic_signals;
DROP POLICY IF EXISTS forensic_signals_delete ON public.forensic_signals;

-- ML evaluations
DROP POLICY IF EXISTS "Users can read child ml_evaluations" ON public.ml_evaluations;
DROP POLICY IF EXISTS "Users can insert ml_evaluations"      ON public.ml_evaluations;
DROP POLICY IF EXISTS "Users can update ml_evaluations"      ON public.ml_evaluations;
DROP POLICY IF EXISTS "Users can delete ml_evaluations"      ON public.ml_evaluations;
DROP POLICY IF EXISTS ml_evaluations_select ON public.ml_evaluations;
DROP POLICY IF EXISTS ml_evaluations_insert ON public.ml_evaluations;
DROP POLICY IF EXISTS ml_evaluations_update ON public.ml_evaluations;
DROP POLICY IF EXISTS ml_evaluations_delete ON public.ml_evaluations;

-- Content DNA
DROP POLICY IF EXISTS "Users can read child content_dna" ON public.content_dna;
DROP POLICY IF EXISTS "Users can insert content_dna"      ON public.content_dna;
DROP POLICY IF EXISTS "Users can update content_dna"      ON public.content_dna;
DROP POLICY IF EXISTS "Users can delete content_dna"      ON public.content_dna;
DROP POLICY IF EXISTS content_dna_select ON public.content_dna;
DROP POLICY IF EXISTS content_dna_insert ON public.content_dna;
DROP POLICY IF EXISTS content_dna_update ON public.content_dna;
DROP POLICY IF EXISTS content_dna_delete ON public.content_dna;

-- Storage objects (possible previous policies)
DROP POLICY IF EXISTS "Users can upload their own investigation assets" ON storage.objects;
DROP POLICY IF EXISTS "Users can read their own investigation assets"   ON storage.objects;
DROP POLICY IF EXISTS storage_objects_insert ON storage.objects;
DROP POLICY IF EXISTS storage_objects_select ON storage.objects;
DROP POLICY IF EXISTS storage_objects_update ON storage.objects;
DROP POLICY IF EXISTS storage_objects_delete ON storage.objects;

-- ---------------------------------------------------------------------
-- 3.1 Analyses policies (ownership enforced, service_role allowed)
-- ---------------------------------------------------------------------
CREATE POLICY analyses_select ON public.analyses
    FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

CREATE POLICY analyses_insert ON public.analyses
    FOR INSERT WITH CHECK (auth.uid() = user_id AND user_id IS NOT NULL OR auth.role() = 'service_role');

CREATE POLICY analyses_update ON public.analyses
    FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role')
    WITH CHECK (auth.uid() = user_id AND user_id IS NOT NULL OR auth.role() = 'service_role');

CREATE POLICY analyses_delete ON public.analyses
    FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- ---------------------------------------------------------------------
-- 3.2 Child tables – enforce ownership via parent analysis
-- ---------------------------------------------------------------------
-- Forensic signals
CREATE POLICY forensic_signals_select ON public.forensic_signals
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = forensic_signals.analysis_id
              AND (a.user_id = auth.uid() OR a.user_id IS NULL OR auth.role() = 'service_role')
        )
    );

CREATE POLICY forensic_signals_insert ON public.forensic_signals
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY forensic_signals_update ON public.forensic_signals
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = forensic_signals.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY forensic_signals_delete ON public.forensic_signals
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = forensic_signals.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

-- ML evaluations
CREATE POLICY ml_evaluations_select ON public.ml_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = ml_evaluations.analysis_id
              AND (a.user_id = auth.uid() OR a.user_id IS NULL OR auth.role() = 'service_role')
        )
    );

CREATE POLICY ml_evaluations_insert ON public.ml_evaluations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY ml_evaluations_update ON public.ml_evaluations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = ml_evaluations.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY ml_evaluations_delete ON public.ml_evaluations
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = ml_evaluations.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

-- Content DNA
CREATE POLICY content_dna_select ON public.content_dna
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = content_dna.analysis_id
              AND (a.user_id = auth.uid() OR a.user_id IS NULL OR auth.role() = 'service_role')
        )
    );

CREATE POLICY content_dna_insert ON public.content_dna
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY content_dna_update ON public.content_dna
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = content_dna.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

CREATE POLICY content_dna_delete ON public.content_dna
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = content_dna.analysis_id
              AND (a.user_id = auth.uid() OR auth.role() = 'service_role')
        )
    );

-- ---------------------------------------------------------------------
-- 4. Supabase Storage bucket (private) and strict RLS policies
-- ---------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'investigation-assets',
    'investigation-assets',
    false,
    26214400, -- 25 MB
    ARRAY['image/jpeg','image/png','image/webp','image/gif','application/pdf','video/mp4']
) ON CONFLICT (id) DO NOTHING;

-- Storage objects policies – enforce UUID‑prefixed folders
CREATE POLICY storage_objects_insert ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'investigation-assets'
        AND auth.role() IN ('authenticated','service_role')
        AND (
            auth.role() = 'service_role'
            OR split_part(name, '/', 1) = auth.uid()::text
        )
    );

CREATE POLICY storage_objects_select ON storage.objects
    FOR SELECT USING (
        bucket_id = 'investigation-assets'
        AND (
            auth.role() = 'service_role'
            OR split_part(name, '/', 1) = auth.uid()::text
        )
    );

CREATE POLICY storage_objects_update ON storage.objects
    FOR UPDATE USING (
        bucket_id = 'investigation-assets'
        AND (
            auth.role() = 'service_role'
            OR split_part(name, '/', 1) = auth.uid()::text
        )
    ) WITH CHECK (
        bucket_id = 'investigation-assets'
        AND (
            auth.role() = 'service_role'
            OR split_part(name, '/', 1) = auth.uid()::text
        )
    );

CREATE POLICY storage_objects_delete ON storage.objects
    FOR DELETE USING (
        bucket_id = 'investigation-assets'
        AND (
            auth.role() = 'service_role'
            OR split_part(name, '/', 1) = auth.uid()::text
        )
    );

-- End of migration
