import os
import sys
import requests
import time
import uuid
import random
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path to import app modules
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

# Load environment variables (for DB connection)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.database import SessionLocal
from app.models import Contribution

# Configuration
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "contributions"))
# Default: 100 per class (200 total) if no arg provided
try:
    COUNT_PER_CLASS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
except ValueError:
    print("⚠️ Invalid number provided. Using default 100.")
    COUNT_PER_CLASS = 100

USER_ID = 1  # Assign to first user (usually admin)

def setup_directories():
    os.makedirs(DATA_DIR, exist_ok=True)

def download_file(url, label, source_type):
    try:
        # Request with timeout and user agent
        headers = {'User-Agent': 'Mozilla/5.0 (DeepFakeDetector/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Generate unique filename
            ext = ".jpg"
            image_id = uuid.uuid4().hex
            filename = f"{image_id}{ext}"
            save_path = os.path.join(DATA_DIR, filename)
            
            # Save image
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            return save_path
    except Exception as e:
        print(f"❌ Error downloading: {e}")
    return None

def register_in_db(db, image_path, label):
    try:
        # Check if file exists first
        if not os.path.exists(image_path):
            return False
            
        contrib = Contribution(
            user_id=USER_ID,
            image_path=image_path,
            label=label,
            source="auto_collection",
            ai_tool_name="ThisPersonDoesNotExist" if label == "fake" else None,
            description=f"Auto-collected {label} image",
            verified=True  # Auto-verify since we know the source
        )
        db.add(contrib)
        db.commit()
        print(f"   └── Registered in DB (ID: {contrib.id})")
        return True
    except Exception as e:
        print(f"   └── ❌ DB Error: {e}")
        db.rollback()
        return False

def main():
    print("🚀 Starting Automated Data Collection...")
    print(f"📂 Storage: {DATA_DIR}")
    print(f"🎯 Target: {COUNT_PER_CLASS} Real + {COUNT_PER_CLASS} Fake")
    print("-" * 50)
    
    setup_directories()
    db = SessionLocal()
    
    # 1. Fetch FAKE images
    print("\n[1/2] Fetching FAKE images (ThisPersonDoesNotExist)...")
    for i in range(COUNT_PER_CLASS):
        print(f"[{i+1}/{COUNT_PER_CLASS}] Downloading Fake...", end=" ", flush=True)
        # Add random delay to be polite
        time.sleep(1.0 + random.random()) 
        
        url = "https://thispersondoesnotexist.com/"  # Direct image
        path = download_file(url, "fake", "ai_tool")
        
        if path:
            print("✅ Saved.", end=" ")
            register_in_db(db, path, "fake")
        else:
            print("❌ Failed.")

    # 2. Fetch REAL images
    print("\n[2/2] Fetching REAL images (LoremFlickr Faces)...")
    for i in range(COUNT_PER_CLASS):
        print(f"[{i+1}/{COUNT_PER_CLASS}] Downloading Real...", end=" ", flush=True)
        time.sleep(0.5)
        
        # LoremFlickr or similar
        # Using a random lock to prevent caching same image
        rand = random.randint(1, 100000)
        url = f"https://loremflickr.com/800/800/face,portrait/all?lock={rand}"
        path = download_file(url, "real", "camera")
        
        if path:
            print("✅ Saved.", end=" ")
            register_in_db(db, path, "real")
        else:
            print("❌ Failed.")
            
    db.close()
    print("\n" + "="*50)
    print("✨ Collection Complete! Run train_model.py to use this data.")

if __name__ == "__main__":
    main()
