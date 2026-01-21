# app/exif_extractor.py
"""
EXIF Metadata Extractor for Display
Extracts and formats EXIF data from images for user viewing.
Does NOT analyze AI generation - that's handled by metadata_analyzer.py
"""

import io
from typing import Dict, Any
from PIL import Image

# Try to use piexif first (more reliable), fall back to PIL if not available
try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False
    from PIL.ExifTags import TAGS, GPSTAGS


def extract_exif_from_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract EXIF metadata from image bytes.
    
    Args:
        image_bytes: Raw image file bytes
        
    Returns:
        Dictionary containing extracted EXIF metadata
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Basic image info
        basic_info = {
            "format": image.format,
            "mode": image.mode,
            "size": {"width": image.width, "height": image.height}
        }
        
        # Try piexif first (more reliable)
        if HAS_PIEXIF:
            try:
                print(f"[exif_extractor] Attempting piexif extraction from {basic_info['format']} image")
                exif_dict = piexif.load(io.BytesIO(image_bytes))
                print(f"[exif_extractor] piexif found data: {list(exif_dict.keys())}")
                return _parse_piexif_data(exif_dict, basic_info)
            except Exception as e:
                print(f"[exif_extractor] piexif failed: {e}, trying PIL fallback")
        
        # Fall back to PIL
        print(f"[exif_extractor] Using PIL fallback for EXIF extraction")
        exif_data = image._getexif()
        print(f"[exif_extractor] PIL _getexif() result: {exif_data is not None}")
        
        if not exif_data:
            # Try alternative PIL method - getexif()
            try:
                exif_data = image.getexif()
                print(f"[exif_extractor] PIL getexif() result: {len(exif_data) if exif_data else 0} tags")
            except:
                pass
            
            if not exif_data:
                return {
                    "has_metadata": False,
                    "message": "No EXIF metadata found in this image",
                    "basic_info": basic_info
                }
        
        # Parse EXIF tags
        from PIL.ExifTags import TAGS, GPSTAGS
        exif_dict = {}
        gps_data = {}
        
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            
            # Handle GPS data separately
            if tag_name == "GPSInfo":
                try:
                    for gps_tag_id, gps_value in value.items():
                        gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_data[gps_tag_name] = str(gps_value)
                except:
                    pass
            else:
                # Convert values to string for JSON serialization
                try:
                    if isinstance(value, bytes):
                        exif_dict[tag_name] = value.decode('utf-8', errors='ignore')
                    else:
                        exif_dict[tag_name] = str(value)
                except:
                    exif_dict[tag_name] = str(value)
        
        result = {
            "has_metadata": True,
            "basic_info": basic_info,
            "exif": exif_dict
        }
        
        if gps_data:
            result["gps"] = gps_data
            
        # Extract commonly useful fields
        useful_fields = {}
        field_mapping = {
            "Make": "camera_make",
            "Model": "camera_model",
            "DateTime": "date_time",
            "DateTimeOriginal": "date_time_original",
            "Software": "software",
            "Orientation": "orientation",
            "XResolution": "x_resolution",
            "YResolution": "y_resolution",
            "ExposureTime": "exposure_time",
            "FNumber": "f_number",
            "ISOSpeedRatings": "iso",
            "Flash": "flash",
            "FocalLength": "focal_length"
        }
        
        for exif_key, useful_key in field_mapping.items():
            if exif_key in exif_dict:
                useful_fields[useful_key] = exif_dict[exif_key]
        
        if useful_fields:
            result["summary"] = useful_fields
            
        return result
        
    except Exception as e:
        import traceback
        print(f"[exif_extractor] Error: {e}")
        traceback.print_exc()
        return {
            "has_metadata": False,
            "error": f"Failed to extract metadata: {str(e)}"
        }


def _parse_piexif_data(exif_dict: Dict, basic_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse exif dictionary from piexif library.
    
    Args:
        exif_dict: Dictionary returned by piexif.load()
        basic_info: Basic image information
        
    Returns:
        Formatted metadata dictionary
    """
    from PIL.ExifTags import TAGS
    
    if not exif_dict or not any(exif_dict.get(ifd_name, {}) for ifd_name in ["0th", "Exif", "GPS"]):
        return {
            "has_metadata": False,
            "message": "No EXIF metadata found in this image",
            "basic_info": basic_info
        }
    
    exif_data = {}
    gps_data = {}
    
    # Parse 0th IFD (main EXIF data)
    if "0th" in exif_dict:
        for tag_id, value in exif_dict["0th"].items():
            try:
                tag_name = piexif.TAGS["0th"][tag_id]["name"].decode('utf-8') if isinstance(piexif.TAGS["0th"][tag_id]["name"], bytes) else piexif.TAGS["0th"][tag_id]["name"]
                if isinstance(value, bytes):
                    exif_data[tag_name] = value.decode('utf-8', errors='ignore')
                else:
                    exif_data[tag_name] = str(value)
            except:
                pass
    
    # Parse Exif IFD
    if "Exif" in exif_dict:
        for tag_id, value in exif_dict["Exif"].items():
            try:
                tag_name = piexif.TAGS["Exif"][tag_id]["name"].decode('utf-8') if isinstance(piexif.TAGS["Exif"][tag_id]["name"], bytes) else piexif.TAGS["Exif"][tag_id]["name"]
                if isinstance(value, bytes):
                    exif_data[tag_name] = value.decode('utf-8', errors='ignore')
                else:
                    exif_data[tag_name] = str(value)
            except:
                pass
    
    # Parse GPS IFD
    if "GPS" in exif_dict:
        for tag_id, value in exif_dict["GPS"].items():
            try:
                tag_name = piexif.TAGS["GPS"][tag_id]["name"].decode('utf-8') if isinstance(piexif.TAGS["GPS"][tag_id]["name"], bytes) else piexif.TAGS["GPS"][tag_id]["name"]
                if isinstance(value, bytes):
                    gps_data[tag_name] = value.decode('utf-8', errors='ignore')
                else:
                    gps_data[tag_name] = str(value)
            except:
                pass
    
    result = {
        "has_metadata": True,
        "basic_info": basic_info,
        "exif": exif_data
    }
    
    if gps_data:
        result["gps"] = gps_data
    
    # Extract commonly useful fields
    useful_fields = {}
    field_mapping = {
        "Make": "camera_make",
        "Model": "camera_model",
        "DateTime": "date_time",
        "DateTimeOriginal": "date_time_original",
        "Software": "software",
        "Orientation": "orientation",
        "XResolution": "x_resolution",
        "YResolution": "y_resolution",
        "ExposureTime": "exposure_time",
        "FNumber": "f_number",
        "ISOSpeedRatings": "iso",
        "Flash": "flash",
        "FocalLength": "focal_length"
    }
    
    for exif_key, useful_key in field_mapping.items():
        if exif_key in exif_data:
            useful_fields[useful_key] = exif_data[exif_key]
    
    if useful_fields:
        result["summary"] = useful_fields
    
    return result



def format_metadata_for_display(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format metadata into organized categories for frontend display.
    
    Args:
        metadata: Raw metadata dictionary from extract_exif_from_bytes
        
    Returns:
        Formatted metadata with organized categories
    """
    if not metadata.get("has_metadata"):
        return metadata
    
    # Organize data into categories
    display_data = {
        "has_metadata": True,
        "categories": {}
    }
    
    # Basic Info
    if "basic_info" in metadata:
        display_data["categories"]["Basic Information"] = metadata["basic_info"]
    
    # Summary (most useful fields)
    if "summary" in metadata:
        display_data["categories"]["Camera & Settings"] = metadata["summary"]
    
    # GPS Location
    if "gps" in metadata:
        display_data["categories"]["GPS Location"] = metadata["gps"]
    
    # Full EXIF (optional, can be collapsed)
    if "exif" in metadata:
        display_data["categories"]["Full EXIF Data"] = metadata["exif"]
    
    return display_data
