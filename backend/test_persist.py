"""Quick integration test: upload a synthetic JPEG and verify persistence."""
import urllib.request
import urllib.error
import json
import io
import uuid
import traceback
from PIL import Image

# 1. Create a minimal valid JPEG test image
img = Image.new("RGB", (100, 100), color="blue")
buf = io.BytesIO()
img.save(buf, format="JPEG")
img_bytes = buf.getvalue()

# 2. Build multipart form data
boundary = uuid.uuid4().hex
lines = []
lines.append(("--" + boundary).encode())
lines.append(b'Content-Disposition: form-data; name="file"; filename="test_blue.jpg"')
lines.append(b"Content-Type: image/jpeg")
lines.append(b"")
lines.append(img_bytes)
lines.append(("--" + boundary + "--").encode())
body = b"\r\n".join(lines)

req = urllib.request.Request(
    "http://localhost:8000/api/v1/detect/analyze",
    data=body,
    headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
    method="POST",
)

try:
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read().decode())
    print("STATUS:", resp.status)
    print("VERDICT:", data.get("final_verdict"))
    print("CONFIDENCE:", data.get("overall_confidence"))
    print("STATUS_FIELD:", data.get("status"))
    print("USER_ID:", data.get("user_id"))
    print("ML_EVALS:", len(data.get("ml_evaluations", [])))
    print("HAS_FORENSICS:", data.get("forensic_signals") is not None)
    print("HAS_DNA:", data.get("content_dna") is not None)
    print("ANALYSIS_ID:", data.get("id"))
    aid = data.get("id")
    if aid:
        # Verify retrieval from DB
        r2 = urllib.request.urlopen(f"http://localhost:8000/api/v1/detect/result/{aid}", timeout=30)
        d2 = json.loads(r2.read().decode())
        print("\n--- RE-FETCH FROM DB ---")
        print("RE-FETCH STATUS:", d2.get("status"))
        print("RE-FETCH VERDICT:", d2.get("final_verdict"))
        print("RE-FETCH ML_EVALS:", len(d2.get("ml_evaluations", [])))
        print("RE-FETCH HAS_DNA:", d2.get("content_dna") is not None)
    print("\n=== TEST PASSED ===")
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print("HTTP ERROR:", e.code)
    print("HEADERS:", dict(e.headers))
    print("BODY:", error_body[:3000])
    # Try parse as JSON for detail
    try:
        detail = json.loads(error_body)
        print("DETAIL:", json.dumps(detail, indent=2))
    except Exception:
        pass
    print("\n=== TEST FAILED ===")
except Exception as ex:
    print("EXCEPTION:", ex)
    traceback.print_exc()
    print("\n=== TEST FAILED ===")
