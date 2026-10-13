import io
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image
from app.main import app
from app.db.session import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    pass

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "engine_version" in data
        assert "database_connected" in data
        assert "database_backend" in data
        assert "supabase_storage_connected" in data

@pytest.mark.asyncio
async def test_upload_and_analyze_flow():
    # Create test JPEG in memory
    img = Image.new("RGB", (400, 400), color=(120, 180, 240))
    buffer = io.BytesIO()
    img.save(buffer, "JPEG")
    buffer.seek(0)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/detect/analyze",
            files={"file": ("test_sky.jpg", buffer.read(), "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "final_verdict" in data
        assert "overall_confidence" in data
        assert "content_dna" in data
        assert "forensic_signals" in data
        assert "blockchain_provenance" not in data
        
        analysis_id = data["id"]
        
        # Test retrieving result by ID
        get_res = await ac.get(f"/api/v1/detect/result/{analysis_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == analysis_id

        # Test history endpoint
        hist_res = await ac.get("/api/v1/detect/history")
        assert hist_res.status_code == 200
        assert isinstance(hist_res.json(), list)

        # Test PDF report download
        pdf_res = await ac.get(f"/api/v1/report/{analysis_id}/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
