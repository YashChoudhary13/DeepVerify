import os
import sys
import requests
import uuid
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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

# Parse command line arguments
try:
    COUNT_PER_CLASS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
except ValueError:
    print("⚠️ Invalid number provided. Using default 100.")
    COUNT_PER_CLASS = 100

# Threading configuration
MAX_WORKERS = 10  # Number of parallel downloads (adjust based on your connection)
USER_ID = 1  # Assign to first user (usually admin)

# Thread-safe counters
download_lock = Lock()
success_count = {"fake": 0, "real": 0}
fail_count = {"fake": 0, "real": 0}


def setup_directories():
    os.makedirs(DATA_DIR, exist_ok=True)


def download_and_save(url, label, index, total):
    """Download a single image and return the result."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (DeepFakeDetector/1.0)'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            ext = ".jpg"
            image_id = uuid.uuid4().hex
            filename = f"{image_id}{ext}"
            save_path = os.path.join(DATA_DIR, filename)
            
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            return {"success": True, "path": save_path, "label": label, "index": index}
    except Exception as e:
        pass  # Silently fail, will be counted
    
    return {"success": False, "path": None, "label": label, "index": index}


def register_batch_in_db(results):
    """Register all successful downloads in the database."""
    db = SessionLocal()
    registered = 0
    
    try:
        for result in results:
            if result["success"] and result["path"] and os.path.exists(result["path"]):
                contrib = Contribution(
                    user_id=USER_ID,
                    image_path=result["path"],
                    label=result["label"],
                    source="auto_collection",
                    ai_tool_name="ThisPersonDoesNotExist" if result["label"] == "fake" else None,
                    description=f"Auto-collected {result['label']} image",
                    verified=True
                )
                db.add(contrib)
                registered += 1
        
        db.commit()
    except Exception as e:
        print(f"❌ DB Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    return registered


def fetch_images_parallel(label, count, url_generator):
    """Fetch images in parallel using ThreadPoolExecutor."""
    print(f"\n{'='*50}")
    print(f"📥 Downloading {count} {label.upper()} images with {MAX_WORKERS} threads...")
    print(f"{'='*50}")
    
    results = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all download tasks
        futures = {}
        for i in range(count):
            url = url_generator(i)
            future = executor.submit(download_and_save, url, label, i, count)
            futures[future] = i
        
        # Process completed downloads
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            # Progress update every 10 downloads or at end
            if completed % 10 == 0 or completed == count:
                success = sum(1 for r in results if r["success"])
                print(f"[{completed}/{count}] Downloaded: {success} ✅ | Failed: {completed - success} ❌")
    
    # Register successful downloads in DB
    successful_results = [r for r in results if r["success"]]
    registered = register_batch_in_db(successful_results)
    
    print(f"✅ {label.upper()}: {len(successful_results)} downloaded, {registered} registered in DB")
    return len(successful_results)


def main():
    print("🚀 Starting FAST Automated Data Collection...")
    print(f"📂 Storage: {DATA_DIR}")
    print(f"🎯 Target: {COUNT_PER_CLASS} Real + {COUNT_PER_CLASS} Fake")
    print(f"⚡ Threads: {MAX_WORKERS} parallel downloads")
    print("-" * 50)
    
    setup_directories()
    
    # URL generators
    def fake_url_generator(i):
        return "https://thispersondoesnotexist.com/"
    
    def real_url_generator(i):
        rand = random.randint(1, 1000000)
        return f"https://loremflickr.com/800/800/face,portrait/all?lock={rand}"
    
    # Fetch FAKE images
    fake_success = fetch_images_parallel("fake", COUNT_PER_CLASS, fake_url_generator)
    
    # Fetch REAL images
    real_success = fetch_images_parallel("real", COUNT_PER_CLASS, real_url_generator)
    
    print("\n" + "=" * 50)
    print("✨ Collection Complete!")
    print(f"   Fake: {fake_success}/{COUNT_PER_CLASS}")
    print(f"   Real: {real_success}/{COUNT_PER_CLASS}")
    print(f"   Total: {fake_success + real_success}/{COUNT_PER_CLASS * 2}")
    print("\n💡 Run train_model.py to train on this data.")


if __name__ == "__main__":
    main()
