# AI Content-Origin Detective 🕵️‍♂️🔍

A production-grade digital forensics platform and multi-signal machine learning ensemble with persistent PostgreSQL storage and private asset custody.

Accurately determines whether an uploaded media asset is:

- **`REAL / HUMAN`**
- **`AI-GENERATED`**
- **`AI-MODIFIED`**
- **`MANIPULATED`**
- **`INCONCLUSIVE — MODEL DISAGREEMENT`**
- **`UNKNOWN / INCONCLUSIVE`**

Combines multiple independent signals without fabricated scores or uncalibrated guesses, and generates an official, verifiable **Forensic Audit PDF Dossier**.

---

## 🚀 Key Architectural Upgrades

- **Blockchain Completely Removed:** Replaced unscalable on-chain lookups with persistent PostgreSQL records, private object storage, and cryptographic Content DNA (SHA-256, MD5, pHash, dHash, wHash).
- **Supabase PostgreSQL & Storage:** Production database schema with Row Level Security (RLS) policies, authenticated investigator profiles, and private storage buckets using time-limited signed URLs.
- **Persistent Investigation History:** Survives restarts and redeployments, recording full metadata, individual ML predictions, and forensic signals.
- **Multi-Format Media Support:** Supports JPEG, PNG, WebP, GIF, BMP, TIFF, AVIF, HEIC, and is architected for video/audio forensic extensions.

---

## 🗄️ Supabase Setup & Migration

### Step 1: Create Supabase Project

1. Log in to [Supabase](https://supabase.com) and create a new project.
2. Under **Project Settings -> Database**, copy your connection string (URI) or connection pooler string.
3. Under **Project Settings -> API**, copy your Project URL, `anon` public key, `service_role` secret key, and JWT Secret.

### Step 2: Apply the Database Schema & RLS Policies

Navigate to the **SQL Editor** in your Supabase dashboard and run the migration script:

```sql
-- Located at: backend/supabase_migration.sql
```

This script creates:

- `analyses`, `forensic_signals`, `ml_evaluations`, and `content_dna` tables.
- Foreign keys, cascading deletes, and performance indexes.
- Row Level Security (RLS) policies linking records to authenticated users (`auth.users`).
- The private `investigation-assets` storage bucket with access policies.

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env` in the backend and configure:

```env
# PostgreSQL connection (e.g. Supabase connection pooler or direct)
DATABASE_URL="postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Supabase Storage & Auth
SUPABASE_URL="https://[YOUR-PROJECT-REF].supabase.co"
SUPABASE_KEY="[YOUR-ANON-KEY]"
SUPABASE_SERVICE_ROLE_KEY="[YOUR-SERVICE-ROLE-KEY]"
SUPABASE_JWT_SECRET="[YOUR-SUPABASE-JWT-SECRET]"
SUPABASE_STORAGE_BUCKET="investigation-assets"
```

And in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL="http://localhost:8000"
NEXT_PUBLIC_SUPABASE_URL="https://[YOUR-PROJECT-REF].supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="[YOUR-ANON-KEY]"
```

_(Note: Never expose the `SUPABASE_SERVICE_ROLE_KEY` or database password in frontend code)._

---

## 🐧 Quick Start for Linux / WSL

In Windows Subsystem for Linux (WSL / Ubuntu), your `V:\` drive is mounted at `/mnt/v/`:

```bash
cd /mnt/v/ai-content-origin-detective
chmod +x *.sh
./setup_linux.sh
./run_all.sh
```

Or run services independently:

- **Terminal 1 (Backend):** `./run_backend.sh`
- **Terminal 2 (Frontend):** `./run_frontend.sh`

Access the application in your browser:

- **Frontend Web Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 🪟 Running on Windows

If running directly on Windows:

- **Backend:** Double-click `run_backend.bat`
- **Frontend:** Double-click `run_frontend.bat`

---

## 🧪 Run Automated Tests

To run the complete test suite (Security, Forensics, ML inference, and Synthesizer rules):

```bash
# In Linux / WSL:
cd backend && source .venv_linux/bin/activate && pytest -v

# In Windows:
cd backend && .\.venv\Scripts\pytest.exe -v
```

---

## 🧠 Multi-Model ML Ensemble & Forensic Stack

1. **Primary Detector**: [`Ateeqq/ai-vs-human-image-detector`](https://huggingface.co/Ateeqq/ai-vs-human-image-detector) (SigLIP Vision Transformer).
2. **Baseline Classifier**: [`umm-maybe/AI-image-detector`](https://huggingface.co/umm-maybe/AI-image-detector) (ViT-base on DiffusionDB).
3. **Forensic Signals:** Error Level Analysis (ELA), 2D Fourier (FFT) lattice harmonics, Poisson-Gaussian photon noise (PRNU), and EXIF/C2PA manifest verification.
4. **Calibrated Decision Synthesis:** Accounts for model disagreement, quality degradation, and out-of-distribution content without fabricating unvalidated softmax probabilities.
