"""
Quick end-to-end test: uploads a JPEG to the running backend analyze endpoint.
Run from the backend directory with the venv active.
"""
import sys
import json
import uuid
import urllib.request
import urllib.error

def upload_and_analyze(filepath: str, url: str = "http://localhost:8000/api/v1/detect/analyze"):
    boundary = f"testboundary{uuid.uuid4().hex}"
    with open(filepath, "rb") as f:
        file_data = f.read()

    import os
    filename = os.path.basename(filepath)
    ctype = "image/jpeg"
    if filepath.endswith(".png"):
        ctype = "image/png"
    elif filepath.endswith(".webp"):
        ctype = "image/webp"

    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    parts.append(file_data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
            print(f"STATUS CODE: {r.status}")
            print(f"PIPELINE STATUS: {resp.get('status')}")
            print(f"VERDICT:     {resp.get('final_verdict')}")
            print(f"CONFIDENCE:  {resp.get('overall_confidence')}")
            print(f"ML MODELS:   {len(resp.get('ml_evaluations', []))}")
            print(f"FORENSICS:   {resp.get('forensic_signals') is not None}")
            print(f"DNA:         {resp.get('content_dna') is not None}")
            print(f"REASONS:     {resp.get('verdict_reasons', [])[:3]}")
            if resp.get("error_message"):
                print(f"ERROR MSG:   {resp.get('error_message')}")
            if resp.get("limitations"):
                print(f"LIMITS:      {resp['limitations'][:2]}")
            for ml in resp.get("ml_evaluations", []):
                print(f"  MODEL: {ml['model_name']} -> {ml['predicted_label']} @ {ml['confidence']:.2%}")
            return resp
    except urllib.error.HTTPError as e:
        body_err = e.read().decode(errors="replace")
        print(f"HTTP ERROR {e.code}: {body_err}")
    except Exception as ex:
        import traceback
        print(f"REQUEST FAILED: {ex}")
        traceback.print_exc()
    return None

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "test_sample.jpg"
    upload_and_analyze(path)
