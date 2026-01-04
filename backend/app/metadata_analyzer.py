# app/metadata_analyzer.py
"""
Metadata Analyzer Module for DeepVerify Backend
================================================
Analyzes image metadata for AI generation indicators.
Integrates with the main models_interface pipeline.
"""

import os
import struct
import zlib
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
