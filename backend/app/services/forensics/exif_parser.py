import os
import re
from typing import Dict, Any, List, Tuple
from PIL import Image, ExifTags
import piexif

AI_SIGNATURE_PATTERNS = [
    r"midjourney",
    r"stable\s*diffusion",
    r"stablediffusion",
    r"dall-?e",
    r"comfyui",
    r"novelai",
    r"invokeai",
    r"civitai",
    r"adobe\s*firefly",
    r"flux(\.1)?",
    r"sdxl",
    r"runway(ml)?",
    r"pika",
    r"sora",
    r"bing\s*image\s*creator",
    r"playground\s*ai",
    r"sampler:\s*[\w\+\-\s]+",
    r"steps:\s*\d+",
    r"cfg\s*scale:\s*[\d\.]+",
    r"model\s*hash:\s*[a-f0-9]+"
]

C2PA_PATTERNS = [
    b"urn:c2pa:",
    b"http://ns.adobe.com/c2pa",
    b"jumdc2pa",
    b"c2pa.claim",
    b"c2pa.signature",
    b"caBX"
]

def parse_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extracts and audits EXIF, IPTC, XMP, and PNG info metadata.
    Detects AI generation prompts, model parameters, and C2PA provenance manifests.
    """
    exif_data: Dict[str, Any] = {}
    found_ai_tags: List[str] = []
    c2pa_detected = False

    # Check for C2PA raw bytes in file header/tail
    try:
        with open(file_path, "rb") as f:
            raw_sample = f.read(131072) # Read first 128KB
            for pattern in C2PA_PATTERNS:
                if pattern in raw_sample.lower():
                    c2pa_detected = True
                    break
    except Exception:
        pass

    try:
        with Image.open(file_path) as img:
            # 1. Pillow Info (often holds PNG text chunks with Stable Diffusion prompts)
            if hasattr(img, "info") and img.info:
                for key, val in img.info.items():
                    val_str = str(val)
                    exif_data[f"info:{key}"] = val_str[:500] # Truncate very long prompt strings
                    # Scan for AI signatures
                    for pattern in AI_SIGNATURE_PATTERNS:
                        m = re.search(pattern, val_str, re.IGNORECASE)
                        if m:
                            found_ai_tags.append(f"PNG Text Chunk '{key}': Found '{m.group(0)}'")

            # 2. Standard EXIF
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    # Handle binary or non-serializable types
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="ignore").strip()
                        except Exception:
                            value = f"<binary {len(value)} bytes>"
                    
                    val_str = str(value)
                    exif_data[tag_name] = val_str[:500]

                    # Check for software / artist AI signatures
                    if tag_name.lower() in ["software", "artist", "imagedescription", "usercomment", "xpcomment"]:
                        for pattern in AI_SIGNATURE_PATTERNS:
                            m = re.search(pattern, val_str, re.IGNORECASE)
                            if m:
                                found_ai_tags.append(f"EXIF '{tag_name}': Found '{m.group(0)}'")

            # Check MakerNote / piexif if available
            try:
                piexif_dict = piexif.load(file_path)
                for ifd in ("0th", "Exif", "GPS", "1st"):
                    for tag in piexif_dict.get(ifd, {}):
                        tag_info = piexif.TAGS[ifd].get(tag, {"name": str(tag)})
                        tag_name = tag_info.get("name", str(tag))
                        raw_v = piexif_dict[ifd][tag]
                        if isinstance(raw_v, bytes):
                            text_v = raw_v.decode("utf-8", errors="ignore").strip()
                        else:
                            text_v = str(raw_v)
                        for pattern in AI_SIGNATURE_PATTERNS:
                            m = re.search(pattern, text_v, re.IGNORECASE)
                            if m:
                                tag_msg = f"EXIF/{ifd} '{tag_name}': Found '{m.group(0)}'"
                                if tag_msg not in found_ai_tags:
                                    found_ai_tags.append(tag_msg)
            except Exception:
                pass

    except Exception as e:
        exif_data["parse_error"] = str(e)

    # De-duplicate AI tags
    found_ai_tags = list(dict.fromkeys(found_ai_tags))

    return {
        "exif_metadata": exif_data,
        "has_ai_metadata": len(found_ai_tags) > 0,
        "ai_metadata_tags": found_ai_tags,
        "c2pa_manifest_detected": c2pa_detected
    }
