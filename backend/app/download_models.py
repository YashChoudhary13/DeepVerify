# Model Download Script for Railway Deployment
# app/download_models.py
"""
Download ML models on Railway startup from R2 or GitHub.
This avoids including large model files in the Docker image.
"""
import os
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Model URLs - Reads from environment variables or uses R2_PUBLIC_URL as fallback
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev")

MODEL_URLS = {
    "efficientnet_b0_deepfake.h5": os.getenv(
        "MODEL_EFFICIENTNET_URL",
        f"{R2_PUBLIC_URL}/models/efficientnet_b0_deepfake.h5"
    ),
    "mobilenetv2_deepfake.h5": os.getenv(
        "MODEL_MOBILENET_URL", 
        f"{R2_PUBLIC_URL}/models/mobilenetv2_deepfake.h5"
    ),
    "resnet50_deepfake.h5": os.getenv(
        "MODEL_RESNET_URL",
        f"{R2_PUBLIC_URL}/models/resnet50_deepfake.h5"
    ),
    "xception_deepfake.h5": os.getenv(
        "MODEL_XCEPTION_URL",
        f"{R2_PUBLIC_URL}/models/xception_deepfake.h5"
    ),
    "deepverify_finetuned.pt": os.getenv(
        "MODEL_DEEPVERIFY_URL",
        f"{R2_PUBLIC_URL}/models/deepverify_finetuned.pt"
    ),
}

# Use absolute path to ensure models go to /app/models
MODELS_DIR = Path("/app/models")

def download_model(filename: str, url: str) -> bool:
    """Download a single model file."""
    filepath = MODELS_DIR / filename
    
    # Skip if already exists
    if filepath.exists():
        logger.info(f"✓ Model already exists: {filename}")
        return True
    
    try:
        logger.info(f"⬇️  Downloading {filename}...")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024 * 10) == 0:  # Log every 10MB
                            logger.info(f"   {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB)")
        
        logger.info(f"✅ Downloaded: {filename} ({total_size / 1024 / 1024:.1f}MB)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download {filename}: {e}")
        if filepath.exists():
            filepath.unlink()
        return False

def download_all_models() -> bool:
    """Download all required models."""
    MODELS_DIR.mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("MODEL DOWNLOAD STARTING")
    logger.info("=" * 60)
    
    success = True
    for filename, url in MODEL_URLS.items():
        if not download_model(filename, url):
            success = False
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ ALL MODELS READY")
        logger.info("=" * 60)
        
        # Verify files exist and list them
        logger.info(f"Verifying models in {MODELS_DIR}...")
        import os
        if MODELS_DIR.exists():
            files = list(MODELS_DIR.glob("*"))
            logger.info(f"Found {len(files)} files:")
            for f in files:
                logger.info(f"  ✓ {f.name} ({f.stat().st_size / 1024 / 1024:.1f}MB)")
        else:
            logger.error(f"❌ Models directory does not exist: {MODELS_DIR}")
    else:
        logger.warning("⚠️  Some models failed to download - app may not work correctly")
    
    return success

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_all_models()
