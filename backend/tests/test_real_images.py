import os
import io
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image
from app.main import app
from app.db.session import init_db

@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()

@pytest.mark.asyncio
async def test_real_ai_image_pipeline():
    """Tests the full pipeline on the real AI-generated test image."""
    real_ai_img_path = os.path.join("uploads", "4d87e7da-2750-4083-8864-f4c41b009883_raw.png")
    if not os.path.exists(real_ai_img_path):
        pytest.skip("Test image not present in uploads directory")

    with open(real_ai_img_path, "rb") as f:
        img_bytes = f.read()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/detect/analyze",
            files={"file": ("ai_portrait.png", img_bytes, "image/png")}
        )
        assert response.status_code == 200
        data = response.json()

        # Core assertions: must be identified as AI-GENERATED
        assert data["final_verdict"] == "AI-GENERATED"
        assert data["overall_confidence"] >= 0.70
        assert data["status"] == "COMPLETED"

        # Check that ML models evaluated
        assert "ml_evaluations" in data
        assert len(data["ml_evaluations"]) >= 1

        # Check Content DNA
        assert "content_dna" in data
        assert len(data["content_dna"]["sha256_hash"]) == 64

        # Check that C2PA manifest is recorded
        assert data["forensic_signals"]["c2pa_manifest_detected"] is True

        # Check PDF dossier can be generated
        pdf_res = await ac.get(f"/api/v1/report/{data['id']}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF-")

@pytest.mark.asyncio
async def test_low_res_edge_case():
    """Tests degraded/low-resolution edge case: must output limitations and inconclusive."""
    img = Image.new("RGB", (100, 100), color=(100, 100, 100))
    buffer = io.BytesIO()
    img.save(buffer, "JPEG")
    buffer.seek(0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/detect/analyze",
            files={"file": ("low_res.jpg", buffer.read(), "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Low resolution" in " ".join(data["limitations"])
