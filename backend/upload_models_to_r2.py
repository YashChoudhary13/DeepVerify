"""
Upload ML models to Cloudflare R2 using boto3
Run this script once to upload models before Railway deployment
"""
import os
import boto3
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

# R2 Configuration
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

# S3 endpoint for R2
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Models directory
MODELS_DIR = Path("models")

# Model files to upload
MODEL_FILES = [
    "efficientnet_b0_deepfake.h5",
    "mobilenetv2_deepfake.h5",
    "resnet50_deepfake.h5",
    "xception_deepfake.h5",
    "deepverify_finetuned.pt"
]

def get_r2_client():
    """Create boto3 S3 client for R2"""
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name='auto'
    )

def upload_model_to_r2(client, filename: str) -> bool:
    """Upload a single model file to R2"""
    filepath = MODELS_DIR / filename
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        # Get file size
        file_size = filepath.stat().st_size
        size_mb = file_size / (1024 * 1024)
        
        print(f"\n📤 Uploading {filename} ({size_mb:.2f} MB)...")
        
        # Upload to R2 in the models/ folder
        s3_key = f"models/{filename}"
        
        # Upload with progress callback
        def progress_callback(bytes_transferred):
            progress = (bytes_transferred / file_size) * 100
            print(f"   Progress: {progress:.1f}%", end='\r')
        
        with open(filepath, 'rb') as file:
            client.upload_fileobj(
                file,
                R2_BUCKET_NAME,
                s3_key,
                Callback=progress_callback,
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )
        
        # Generate public URL
        public_url = f"{R2_PUBLIC_URL}/models/{filename}"
        
        print(f"\n✅ Uploaded successfully!")
        print(f"   URL: {public_url}")
        
        return True
        
    except ClientError as e:
        print(f"❌ Upload failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_r2_config():
    """Verify R2 configuration"""
    missing = []
    
    if not R2_ACCOUNT_ID:
        missing.append("R2_ACCOUNT_ID")
    if not R2_ACCESS_KEY_ID:
        missing.append("R2_ACCESS_KEY_ID")
    if not R2_SECRET_ACCESS_KEY:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not R2_BUCKET_NAME:
        missing.append("R2_BUCKET_NAME")
    if not R2_PUBLIC_URL:
        missing.append("R2_PUBLIC_URL")
    
    if missing:
        print("❌ Missing R2 configuration:")
        for var in missing:
            print(f"   - {var}")
        return False
    
    return True

def main():
    print("=" * 60)
    print("🚀 Upload Models to Cloudflare R2")
    print("=" * 60)
    
    # Verify configuration
    if not verify_r2_config():
        print("\n⚠️  Please check your .env file")
        return
    
    print(f"\n📦 Bucket: {R2_BUCKET_NAME}")
    print(f"🌐 Public URL: {R2_PUBLIC_URL}")
    print(f"📁 Models directory: {MODELS_DIR.absolute()}")
    
    # Check models directory
    if not MODELS_DIR.exists():
        print(f"\n❌ Models directory not found: {MODELS_DIR}")
        return
    
    # Create R2 client
    try:
        client = get_r2_client()
        print("\n✅ Connected to R2")
    except Exception as e:
        print(f"\n❌ Failed to connect to R2: {e}")
        return
    
    # Upload each model
    print(f"\n📋 Found {len(MODEL_FILES)} models to upload\n")
    
    success_count = 0
    failed_files = []
    
    for filename in MODEL_FILES:
        if upload_model_to_r2(client, filename):
            success_count += 1
        else:
            failed_files.append(filename)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print(f"✅ Successful: {success_count}/{len(MODEL_FILES)}")
    
    if failed_files:
        print(f"❌ Failed: {len(failed_files)}")
        for filename in failed_files:
            print(f"   - {filename}")
    
    if success_count == len(MODEL_FILES):
        print("\n🎉 All models uploaded successfully!")
        print("\n📝 Add these URLs to Railway environment variables:")
        print("-" * 60)
        for filename in MODEL_FILES:
            url = f"{R2_PUBLIC_URL}/models/{filename}"
            env_name = filename.replace("_deepfake.h5", "").replace("_", "").upper()
            print(f"MODEL_{env_name}_URL={url}")
        print("-" * 60)
        
        print("\n✨ You can now deploy to Railway!")
        print("   The models will be downloaded from these URLs on startup.")
    else:
        print("\n⚠️  Some uploads failed. Please check errors above.")

if __name__ == "__main__":
    main()
