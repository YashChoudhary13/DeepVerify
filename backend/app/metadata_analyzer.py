# app/metadata_analyzer.py
"""
Metadata Analyzer Module for DeepVerify Backend
================================================
Analyzes image metadata for AI generation indicators.
Integrates with the main models_interface pipeline.
"""

import io
import math
import os
import struct
import zlib
from collections import Counter
from typing import Dict, Any, List, Optional
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS


# ============================================================================
# AI SOFTWARE SIGNATURES
# ============================================================================
AI_SOFTWARE_SIGNATURES = [
    # OpenAI / DALL-E
    "dall-e", "dalle", "openai", "chatgpt",
    # Midjourney
    "midjourney", "mj",
    # Adobe
    "adobe firefly", "firefly", "adobe generative",
    # Stable Diffusion variants
    "stable diffusion", "stablediffusion", "automatic1111", "a1111",
    "comfyui", "invoke ai", "invokeai", "diffusers",
    # Other AI tools
    "leonardo.ai", "leonardo ai", "playground ai", "nightcafe",
    "dream studio", "dreamstudio", "bing image creator", "copilot",
    "imagen", "ideogram", "flux", "nanobanana", "nano banana",
]

# PNG text chunk keys that contain AI generation info
AI_PNG_KEYS = [
    "parameters", "prompt", "negative_prompt", "workflow",
    "comment", "description", "software", "source", "ai_generated", "dream", "sd-metadata",
]


# ============================================================================
# FORENSIC ENCODING + METADATA ANALYZER (JPEG-focused)
# ============================================================================

SUBSAMPLING_MAP = {
    0: "4:4:4",
    1: "4:2:2",
    2: "4:2:0",
    3: "4:1:1",
}


def _entropy(values: List[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return round(-sum((c / total) * math.log2(c / total) for c in counts.values() if c), 3)


def _summarize_quantization(image: Image.Image) -> Dict[str, Any]:
    qtables = getattr(image, "quantization", None)
    if not qtables:
        return {"present": False}

    tables = {}
    uniform_flags = []

    for idx, coeffs in qtables.items():
        coeff_list = list(coeffs)
        if not coeff_list:
            continue
        mean_val = sum(coeff_list) / len(coeff_list)
        variance = sum((c - mean_val) ** 2 for c in coeff_list) / len(coeff_list)
        std_dev = math.sqrt(variance)
        tables[str(idx)] = {
            "min": int(min(coeff_list)),
            "max": int(max(coeff_list)),
            "mean": round(mean_val, 2),
            "std": round(std_dev, 2),
            "entropy": _entropy(coeff_list),
        }
        uniform_flags.append(std_dev < 2.0)

    return {
        "present": True,
        "tables": tables,
        "all_uniform": bool(tables) and all(uniform_flags),
    }


def _parse_jpeg_segments(image_bytes: bytes) -> Dict[str, Any]:
    """Lightweight JPEG segment parser to identify container markers."""
    stream = io.BytesIO(image_bytes)
    header = stream.read(2)
    if header != b"\xff\xd8":
        return {"is_jpeg": False}

    segments = []
    found = {
        "jfif": False,
        "exif": False,
        "xmp": False,
        "icc": False,
    }
    sof_info = {}

    while True:
        marker_prefix = stream.read(1)
        if not marker_prefix:
            break
        if marker_prefix != b"\xff":
            continue
        marker_byte = stream.read(1)
        if not marker_byte:
            break
        marker = 0xFF00 | marker_byte[0]

        # Standalone markers without length
        if 0xFFD0 <= marker <= 0xFFD7 or marker == 0xFF01:
            segments.append(marker)
            continue

        length_bytes = stream.read(2)
        if len(length_bytes) < 2:
            break
        length = struct.unpack(">H", length_bytes)[0]
        payload = stream.read(max(length - 2, 0))

        if marker in range(0xFFE0, 0xFFEF + 1):  # APP0-APP15
            ident = payload[:10]
            if ident.startswith(b"JFIF"):
                found["jfif"] = True
            elif ident.startswith(b"Exif\x00\x00"):
                found["exif"] = True
            elif b"http://ns.adobe.com/xap/1.0/" in payload:
                found["xmp"] = True
            elif ident.startswith(b"ICC_PROFILE"):
                found["icc"] = True

        if marker in (0xFFC0, 0xFFC1, 0xFFC2, 0xFFC3):  # SOF markers
            try:
                precision = payload[0]
                height = struct.unpack(">H", payload[1:3])[0]
                width = struct.unpack(">H", payload[3:5])[0]
                components = payload[5]
                sof_info = {
                    "precision_bits": precision,
                    "width": width,
                    "height": height,
                    "components": components,
                    "progressive": marker == 0xFFC2,
                    "sof_marker": hex(marker),
                }
            except Exception:
                pass

        segments.append(marker)

        if marker == 0xFFD9:  # EOI
            break

    return {
        "is_jpeg": True,
        "segments": [hex(m) for m in segments],
        "presence": found,
        "sof": sof_info,
    }


def _extract_exif_from_image(image: Image.Image) -> Dict[str, Any]:
    try:
        # Prefer piexif if available
        try:
            import piexif
            exif_bytes = image.info.get("exif")
            if exif_bytes:
                exif_dict = piexif.load(exif_bytes)
                flat = {}
                for ifd in ("0th", "Exif", "GPS"):
                    for tag_id, value in exif_dict.get(ifd, {}).items():
                        tag_name = piexif.TAGS[ifd][tag_id]["name"]
                        flat[tag_name] = value if not isinstance(value, bytes) else value.decode("utf-8", "ignore")
                return flat
        except Exception:
            pass

        exif_data = image._getexif()
        if not exif_data:
            return {}
        result = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                try:
                    value = value.decode('utf-8', errors='ignore')
                except Exception:
                    value = str(value)
            result[str(tag_name)] = value
        return result
    except Exception:
        return {}


def _extract_xmp_from_bytes(image_bytes: bytes) -> Dict[str, Any]:
    xmp_data = {}
    try:
        content = image_bytes
        xmp_start = content.find(b"<x:xmpmeta")
        if xmp_start == -1:
            xmp_start = content.find(b"<?xpacket begin")

        if xmp_start != -1:
            xmp_end = content.find(b"</x:xmpmeta>", xmp_start)
            if xmp_end == -1:
                xmp_end = content.find(b"<?xpacket end", xmp_start)

            if xmp_end != -1:
                xmp_packet = content[xmp_start:xmp_end + 50].decode('utf-8', errors='ignore')

                import re

                match = re.search(r'<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>', xmp_packet)
                if match:
                    xmp_data['creator_tool'] = match.group(1)

                match = re.search(r'<tiff:Software>([^<]+)</tiff:Software>', xmp_packet)
                if match:
                    xmp_data['software'] = match.group(1)

                if 'c2pa' in xmp_packet.lower() or 'content credentials' in xmp_packet.lower():
                    xmp_data['c2pa_detected'] = True

                if 'ai_generated' in xmp_packet.lower() or 'generative' in xmp_packet.lower():
                    xmp_data['ai_marker_detected'] = True
    except Exception:
        pass
    return xmp_data


def _check_c2pa_bytes(image_bytes: bytes) -> Dict[str, Any]:
    c2pa_result = {"detected": False, "source": None, "details": []}
    try:
        content_lower = image_bytes.lower()
        c2pa_markers = [
            b'c2pa', b'content credentials', b'contentcredentials',
            b'cai_claim', b'cai:claim', b'jumb',
            b'c2pa.assertions', b'c2pa_manifest',
        ]
        for marker in c2pa_markers:
            if marker in content_lower:
                c2pa_result["detected"] = True
                c2pa_result["details"].append(f"Found marker: {marker.decode('utf-8', errors='ignore')}")

        if b'dall-e' in content_lower or b'dalle' in content_lower:
            c2pa_result["source"] = "DALL-E"
        elif b'openai' in content_lower:
            c2pa_result["source"] = "OpenAI"
        elif b'adobe firefly' in content_lower:
            c2pa_result["source"] = "Adobe Firefly"
        elif b'bing' in content_lower:
            c2pa_result["source"] = "Bing Image Creator"
    except Exception:
        pass
    return c2pa_result


def analyze_forensic_image_bytes(image_bytes: bytes, filename: str = "uploaded") -> Dict[str, Any]:
    """
    Combined EXIF + JPEG container/encoding analysis.
    Returns structured JSON plus human-readable forensic interpretation.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        return {
            "has_metadata": False,
            "message": f"Failed to open image: {exc}",
            "categories": {},
        }

    info = img.info or {}

    # Core captures
    basic = {
        "Filename": filename,
        "Format": img.format,
        "Dimensions": f"{img.width} × {img.height}",
        "Color Mode": img.mode,
        "DPI": str(info.get("dpi") or info.get("jfif_density") or "Not set"),
    }

    exif = _extract_exif_from_image(img)
    xmp = _extract_xmp_from_bytes(image_bytes)
    c2pa = _check_c2pa_bytes(image_bytes)

    jpeg_container_raw = {}
    encoding_display = {}
    quant_display = {}

    if img.format and img.format.upper() == "JPEG":
        jpeg_container_raw = _parse_jpeg_segments(image_bytes)
        subsampling = info.get("subsampling")
        
        # Build user-friendly encoding info
        encoding_display = {
            "Encoding Type": "Progressive JPEG" if info.get("progressive") else "Baseline JPEG",
            "Chroma Subsampling": SUBSAMPLING_MAP.get(subsampling, "Unknown" if subsampling is not None else "Not specified"),
            "Color Components": str(jpeg_container_raw.get("sof", {}).get("components", "Unknown")),
            "Bits Per Sample": str(jpeg_container_raw.get("sof", {}).get("precision_bits", 8)),
            "Color Space": info.get("color_space") or img.mode,
        }
        
        # Container segments present
        container_present = jpeg_container_raw.get("presence", {})
        encoding_display["JFIF Header"] = "Yes" if container_present.get("jfif") else "No"
        encoding_display["EXIF Segment"] = "Yes" if container_present.get("exif") else "No"
        encoding_display["XMP Segment"] = "Yes" if container_present.get("xmp") else "No"
        encoding_display["ICC Profile"] = "Yes" if container_present.get("icc") else "No"
        
        quant_raw = _summarize_quantization(img)
        if quant_raw.get("present"):
            tables = quant_raw.get("tables", {})
            if tables:
                # Show summary stats for all tables
                means = [t.get("mean", 0) for t in tables.values() if t.get("mean")]
                all_uniform = quant_raw.get("all_uniform")
                quant_display = {
                    "Tables Present": f"{len(tables)} quantization table(s)",
                    "Uniformity": "Extremely uniform (suspicious)" if all_uniform else "Normal variation",
                    "Mean Values": f"{min(means):.0f} - {max(means):.0f}" if means else "N/A",
                    "Pattern": "Typical for synthetic/edited images" if all_uniform else "Typical for camera captures",
                }

    # Forensic signals
    signals: List[Dict[str, Any]] = []
    evidence_capture: List[str] = []
    evidence_synth: List[str] = []
    inconclusive: List[str] = []

    exif_present = bool(exif)
    camera_make = exif.get("Make") or exif.get("CameraMake")
    camera_model = exif.get("Model") or exif.get("CameraModel")
    software_tag = exif.get("Software")

    if exif_present:
        if camera_make or camera_model:
            evidence_capture.append("✓ Camera make/model present in EXIF")
        if exif.get("GPSInfo"):
            evidence_capture.append("✓ GPS coordinates present (strong capture signal)")
        if exif.get("DateTimeOriginal") or exif.get("DateTime"):
            evidence_capture.append("✓ Capture timestamp present")
        if software_tag and not (camera_make or camera_model):
            signals.append({"type": "exif_inconsistency", "detail": "Software tag present without camera make/model", "severity": "warn", "weight": 0.25})
    else:
        signals.append({"type": "no_exif", "detail": "EXIF missing or stripped", "severity": "info", "weight": 0.2})
        evidence_synth.append("⚠ Missing EXIF (could be stripped or synthetic)")

    # DPI anomalies
    dpi = basic.get("DPI")
    if dpi in ("Not set", "1", "(1, 1)", "(0, 0)"):
        signals.append({"type": "dpi_anomaly", "detail": "DPI missing or anomalous (common in post-processing)", "severity": "info", "weight": 0.15})

    # JPEG-specific checks
    if jpeg_container_raw.get("is_jpeg"):
        if not jpeg_container_raw.get("presence", {}).get("exif"):
            signals.append({"type": "app1_missing", "detail": "JPEG APP1/EXIF segment absent (likely stripped)", "severity": "info", "weight": 0.15})
            evidence_synth.append("⚠ Missing EXIF segment in JPEG structure")

        if encoding_display.get("Chroma Subsampling") == "4:4:4" and not camera_make:
            signals.append({"type": "editing_indicator", "detail": "4:4:4 chroma subsampling without camera EXIF (often edited/exported)", "severity": "warn", "weight": 0.25})
            evidence_synth.append("⚠ 4:4:4 chroma + no camera EXIF suggests editing/re-export")

        if "Progressive" in encoding_display.get("Encoding Type", "") and not camera_make:
            signals.append({"type": "progressive_reencode", "detail": "Progressive JPEG without camera EXIF suggests re-encoding", "severity": "warn", "weight": 0.2})
            evidence_synth.append("⚠ Progressive encoding without camera metadata")

        if quant_display.get("Uniformity", "").startswith("Extremely"):
            signals.append({"type": "uniform_quantization", "detail": "Quantization tables are extremely uniform", "severity": "warn", "weight": 0.25})
            evidence_synth.append("⚠ Uniform quantization (synthetic/edited indicator)")

    # XMP / C2PA markers
    if xmp.get("ai_marker_detected"):
        evidence_synth.append("⚠ XMP indicates AI/generative tool use")
    if c2pa.get("detected"):
        evidence_capture.append("✓ C2PA content credentials present")

    # Build summary buckets
    if not evidence_capture and not evidence_synth:
        inconclusive.append("No strong forensic signals found; visual analysis recommended")

    forensic_summary = {
        "evidence_of_capture": evidence_capture if evidence_capture else ["No capture evidence detected"],
        "evidence_of_synthetic_or_post": evidence_synth if evidence_synth else ["No post-processing/synthetic indicators"],
        "inconclusive": inconclusive if inconclusive else ["Analysis inconclusive; further investigation may be needed"],
    }

    categories = {
        "Basic Information": basic,
        "Encoding & Container": encoding_display if encoding_display else {"note": "Not a JPEG file"},
        "Quantization Analysis": quant_display if quant_display else {"note": "No quantization data"},
        "EXIF Metadata": exif if exif else {"Status": "Missing or stripped"},
        "Forensic Assessment": {
            "Evidence of Capture": "\n".join(evidence_capture) if evidence_capture else "None detected",
            "Evidence of Synthetic/Post-Processing": "\n".join(evidence_synth) if evidence_synth else "None detected",
            "Inconclusive Signals": "\n".join(inconclusive) if inconclusive else "None",
        }
    }

    return {
        "has_metadata": True,
        "categories": categories,
        "forensic_summary": forensic_summary,
    }


# ============================================================================
# METADATA EXTRACTION FUNCTIONS
# ============================================================================

def extract_exif(image_path: str) -> Dict[str, Any]:
    """Extract EXIF metadata from image."""
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return {}
            
            result = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        value = str(value)
                result[str(tag_name)] = value
            return result
    except Exception as e:
        return {"error": str(e)}


def extract_png_text_chunks(image_path: str) -> Dict[str, str]:
    """Extract text chunks from PNG files."""
    chunks = {}
    
    try:
        with open(image_path, 'rb') as f:
            signature = f.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                return {}
            
            while True:
                length_data = f.read(4)
                if len(length_data) < 4:
                    break
                
                length = struct.unpack('>I', length_data)[0]
                chunk_type = f.read(4).decode('ascii', errors='ignore')
                
                if chunk_type == 'IEND':
                    break
                
                data = f.read(length)
                f.read(4)  # Skip CRC
                
                if chunk_type == 'tEXt':
                    null_pos = data.find(b'\x00')
                    if null_pos != -1:
                        key = data[:null_pos].decode('latin-1', errors='ignore')
                        value = data[null_pos+1:].decode('latin-1', errors='ignore')
                        chunks[key] = value
                
                elif chunk_type == 'iTXt':
                    try:
                        parts = data.split(b'\x00', 4)
                        if len(parts) >= 5:
                            key = parts[0].decode('utf-8', errors='ignore')
                            if len(parts[1]) > 0 and parts[1][0] == 1:
                                text = zlib.decompress(parts[4]).decode('utf-8', errors='ignore')
                            else:
                                text = parts[4].decode('utf-8', errors='ignore')
                            chunks[key] = text
                    except:
                        pass
                
                elif chunk_type == 'zTXt':
                    null_pos = data.find(b'\x00')
                    if null_pos != -1:
                        key = data[:null_pos].decode('latin-1', errors='ignore')
                        try:
                            text = zlib.decompress(data[null_pos+2:]).decode('utf-8', errors='ignore')
                            chunks[key] = text
                        except:
                            pass
    except Exception:
        pass
    
    return chunks


def extract_xmp(image_path: str) -> Dict[str, Any]:
    """Extract XMP metadata from image."""
    xmp_data = {}
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        xmp_start = content.find(b'<x:xmpmeta')
        if xmp_start == -1:
            xmp_start = content.find(b'<?xpacket begin')
        
        if xmp_start != -1:
            xmp_end = content.find(b'</x:xmpmeta>', xmp_start)
            if xmp_end == -1:
                xmp_end = content.find(b'<?xpacket end', xmp_start)
            
            if xmp_end != -1:
                xmp_packet = content[xmp_start:xmp_end + 50].decode('utf-8', errors='ignore')
                
                import re
                
                match = re.search(r'<xmp:CreatorTool>([^<]+)</xmp:CreatorTool>', xmp_packet)
                if match:
                    xmp_data['creator_tool'] = match.group(1)
                
                match = re.search(r'<tiff:Software>([^<]+)</tiff:Software>', xmp_packet)
                if match:
                    xmp_data['software'] = match.group(1)
                
                if 'c2pa' in xmp_packet.lower() or 'content credentials' in xmp_packet.lower():
                    xmp_data['c2pa_detected'] = True
                    
                if 'ai_generated' in xmp_packet.lower() or 'generative' in xmp_packet.lower():
                    xmp_data['ai_marker_detected'] = True
                    
    except Exception:
        pass
    
    return xmp_data


def check_c2pa_manifest(image_path: str) -> Dict[str, Any]:
    """Check for C2PA Content Credentials manifest."""
    c2pa_result = {
        "detected": False,
        "source": None,
        "details": []
    }
    
    try:
        with open(image_path, 'rb') as f:
            content = f.read()
        
        content_lower = content.lower()
        
        c2pa_markers = [
            b'c2pa', b'content credentials', b'contentcredentials',
            b'cai_claim', b'cai:claim', b'jumb',
            b'c2pa.assertions', b'c2pa_manifest',
        ]
        
        for marker in c2pa_markers:
            if marker in content_lower:
                c2pa_result["detected"] = True
                c2pa_result["details"].append(f"Found marker: {marker.decode('utf-8', errors='ignore')}")
        
        if b'dall-e' in content_lower or b'dalle' in content_lower:
            c2pa_result["source"] = "DALL-E"
        elif b'openai' in content_lower:
            c2pa_result["source"] = "OpenAI"
        elif b'adobe firefly' in content_lower:
            c2pa_result["source"] = "Adobe Firefly"
        elif b'bing' in content_lower:
            c2pa_result["source"] = "Bing Image Creator"
            
    except Exception:
        pass
    
    return c2pa_result


# ============================================================================
# RESOLUTION ANALYSIS
# ============================================================================
COMMON_AI_RESOLUTIONS = {
    (1024, 1024): "Square (DALL-E/Midjourney/SD)",
    (1024, 1792): "Portrait (Midjourney)",
    (1792, 1024): "Landscape (Midjourney)",
    (1024, 768): "Landscape (SDXL)",
    (768, 1024): "Portrait (SDXL)",
    (512, 512): "Square (Standard SD 1.5)",
}

def check_resolution_patterns(width: int, height: int) -> Optional[Dict[str, Any]]:
    """Check if image dimensions match common AI generation patterns."""
    if (width, height) in COMMON_AI_RESOLUTIONS:
        return {
            "type": "suspicious_resolution",
            "detail": f"Exact match for common AI resolution: {width}x{height} ({COMMON_AI_RESOLUTIONS[(width, height)]})",
            "weight": 0.15 # Low weight as resizing is common
        }
    return None

# ============================================================================
# AI DETECTION LOGIC
# ============================================================================

def analyze_for_ai_signatures(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze metadata for AI generation indicators."""
    indicators = []
    
    def check_value(value: str, source: str) -> Optional[Dict]:
        if not isinstance(value, str):
            return None
        value_lower = value.lower()
        for sig in AI_SOFTWARE_SIGNATURES:
            if sig in value_lower:
                return {
                    "type": "software_signature",
                    "source": source,
                    "signature": sig,
                    "value": value[:200],
                    "weight": 0.4
                }
        return None
    
    # Check EXIF
    exif = metadata.get("exif", {})
    for key, value in exif.items():
        if result := check_value(str(value), f"exif.{key}"):
            indicators.append(result)
    
    # Check XMP
    xmp = metadata.get("xmp", {})
    for key, value in xmp.items():
        if result := check_value(str(value), f"xmp.{key}"):
            indicators.append(result)
    
    # Check PNG chunks
    png_chunks = metadata.get("png_chunks", {})
    for key, value in png_chunks.items():
        if key.lower() in AI_PNG_KEYS:
            indicators.append({
                "type": "ai_png_chunk",
                "key": key,
                "value": value[:500] if len(value) > 500 else value,
                "weight": 0.35
            })
        if result := check_value(str(value), f"png.{key}"):
            indicators.append(result)

    # Check Resolution
    img_info = metadata.get("image_info", {})
    width = img_info.get("size", {}).get("width")
    height = img_info.get("size", {}).get("height")
    if width and height:
        if res_result := check_resolution_patterns(width, height):
            indicators.append(res_result)
    
    # Check for missing camera EXIF
    camera_fields = ["Make", "Model", "LensModel", "FocalLength", "ExposureTime", "FNumber", "ISOSpeedRatings"]
    has_camera_data = any(field in exif for field in camera_fields)
    
    if not has_camera_data and exif and not exif.get("error"):
        indicators.append({
            "type": "missing_camera_exif",
            "detail": "Image has EXIF but no camera data",
            "weight": 0.25
        })
    elif not exif or exif.get("error") or len(exif) == 0:
        indicators.append({
            "type": "no_exif",
            "detail": "No EXIF metadata found",
            "weight": 0.1
        })
        # Possible stripping
        indicators.append({
            "type": "possible_metadata_stripping",
            "detail": "Metadata absent - inconclusive without visual analysis",
            "weight": 0.0
        })
    
    # C2PA detection
    c2pa = metadata.get("c2pa", {})
    if c2pa.get("detected"):
        indicators.append({
            "type": "c2pa",
            "source": c2pa.get("source", "Unknown"),
            "details": c2pa.get("details", []),
            "weight": 0.5
        })
    
    # XMP AI markers
    if xmp.get("c2pa_detected"):
        indicators.append({
            "type": "xmp_c2pa",
            "detail": "XMP contains C2PA/Content Credentials reference",
            "weight": 0.45
        })
    
    if xmp.get("ai_marker_detected"):
        indicators.append({
            "type": "xmp_ai_marker",
            "detail": "XMP contains AI generation marker",
            "weight": 0.4
        })
    
    return indicators


def calculate_ai_confidence(indicators: List[Dict[str, Any]]) -> float:
    """Calculate overall AI generation confidence score."""
    if not indicators:
        return 0.0

    # Filter out 0-weight indicators
    active_indicators = [ind for ind in indicators if ind.get("weight", 0) > 0]
    
    if not active_indicators:
        return 0.0
    
    total_weight = sum(ind.get("weight", 0.1) for ind in active_indicators)
    confidence = min(total_weight, 1.0)
    
    # Helper for weak indicators
    only_weak = all(ind.get("weight", 0) <= 0.25 for ind in active_indicators)

    # Boost for strong indicators
    strong_indicators = [i for i in active_indicators if i.get("weight", 0) >= 0.4]
    if strong_indicators:
        confidence = max(confidence, 0.7)
    elif only_weak:
        confidence = min(confidence, 0.35)
    
    return round(confidence, 3)


def detect_ai_source(indicators: List[Dict[str, Any]]) -> List[str]:
    """Identify likely AI generation source."""
    sources = set()
    
    for ind in indicators:
        if ind.get("type") == "c2pa" and ind.get("source"):
            sources.add(ind["source"])
        
        if ind.get("type") == "software_signature":
            sig = ind.get("signature", "").lower()
            if "dall" in sig or "openai" in sig:
                sources.add("DALL-E/OpenAI")
            elif "midjourney" in sig:
                sources.add("Midjourney")
            elif "firefly" in sig:
                sources.add("Adobe Firefly")
            elif "stable" in sig or "diffusion" in sig or "a1111" in sig or "comfy" in sig:
                sources.add("Stable Diffusion")
            elif "leonardo" in sig:
                sources.add("Leonardo.AI")
            elif "nanobanana" in sig or "nano banana" in sig:
                sources.add("NanoBanana")
            else:
                sources.add("AI Generated")
    
    return list(sources)


# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

async def analyze_image_metadata(image_path: str) -> Dict[str, Any]:
    """
    Async-compatible metadata analysis for backend integration.
    
    Returns:
        Dict containing AI detection results from metadata analysis.
    """
    if not os.path.exists(image_path):
        return {
            "error": f"File not found: {image_path}",
            "is_ai_generated": False,
            "confidence": 0.0,
            "sources_detected": [],
            "indicators": []
        }
    
    # Extract all metadata
    metadata = {
        "exif": extract_exif(image_path),
        "xmp": extract_xmp(image_path),
        "c2pa": check_c2pa_manifest(image_path),
        "image_info": {}
    }
    
    # Get image format
    try:
        with Image.open(image_path) as img:
            metadata["image_info"]["format"] = img.format
            metadata["image_info"]["size"] = {"width": img.width, "height": img.height}
    except:
        pass
    
    # Check for PNG
    if image_path.lower().endswith('.png'):
        metadata["png_chunks"] = extract_png_text_chunks(image_path)
    
    # Analyze for AI indicators
    indicators = analyze_for_ai_signatures(metadata)
    
    # Calculate confidence
    confidence = calculate_ai_confidence(indicators)
    
    # Detect sources
    sources = detect_ai_source(indicators)
    
    # Determine if AI generated (threshold: 0.3)
    is_ai_generated = confidence >= 0.3
    
    # Prepare simplified indicators for API response
    simplified_indicators = []
    for ind in indicators:
        simplified_indicators.append({
            "type": ind.get("type", "unknown"),
            "detail": ind.get("detail") or ind.get("signature") or ind.get("source", ""),
            "weight": ind.get("weight", 0)
        })
    
    return {
        "is_ai_generated": is_ai_generated,
        "confidence": confidence,
        "sources_detected": sources,
        "indicators": simplified_indicators,
        "c2pa_detected": metadata.get("c2pa", {}).get("detected", False),
        "c2pa_source": metadata.get("c2pa", {}).get("source"),
        "has_camera_exif": any(
            field in metadata.get("exif", {}) 
            for field in ["Make", "Model", "LensModel"]
        )
    }


def analyze_image_metadata_sync(image_path: str) -> Dict[str, Any]:
    """
    Synchronous version for use in background tasks.
    """
    import asyncio
    
    # If we're already in an async context, just run directly
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, can't use run_until_complete
            # Just call the underlying sync code directly
            return _analyze_sync(image_path)
    except RuntimeError:
        pass
    
    return _analyze_sync(image_path)


def _analyze_sync(image_path: str) -> Dict[str, Any]:
    """Internal sync implementation."""
    if not os.path.exists(image_path):
        return {
            "error": f"File not found: {image_path}",
            "is_ai_generated": False,
            "confidence": 0.0,
            "sources_detected": [],
            "indicators": []
        }
    
    # Extract all metadata
    metadata = {
        "exif": extract_exif(image_path),
        "xmp": extract_xmp(image_path),
        "c2pa": check_c2pa_manifest(image_path),
        "image_info": {}
    }
    
    try:
        with Image.open(image_path) as img:
            metadata["image_info"]["format"] = img.format
            metadata["image_info"]["size"] = {"width": img.width, "height": img.height}
    except:
        pass
    
    if image_path.lower().endswith('.png'):
        metadata["png_chunks"] = extract_png_text_chunks(image_path)
    
    indicators = analyze_for_ai_signatures(metadata)
    confidence = calculate_ai_confidence(indicators)
    sources = detect_ai_source(indicators)
    is_ai_generated = confidence >= 0.3
    
    simplified_indicators = []
    for ind in indicators:
        simplified_indicators.append({
            "type": ind.get("type", "unknown"),
            "detail": ind.get("detail") or ind.get("signature") or ind.get("source", ""),
            "weight": ind.get("weight", 0)
        })
    
    return {
        "is_ai_generated": is_ai_generated,
        "confidence": confidence,
        "sources_detected": sources,
        "indicators": simplified_indicators,
        "c2pa_detected": metadata.get("c2pa", {}).get("detected", False),
        "c2pa_source": metadata.get("c2pa", {}).get("source"),
        "has_camera_exif": any(
            field in metadata.get("exif", {}) 
            for field in ["Make", "Model", "LensModel"]
        )
    }
