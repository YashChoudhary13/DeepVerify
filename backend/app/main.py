# app/main.py
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    BackgroundTasks,
    HTTPException,
)
import asyncio
import threading
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from datetime import timedelta
import os
import uuid
from dotenv import load_dotenv
import shutil
import boto3
from botocore.exceptions import ClientError

load_dotenv()

from .database import engine
from .models import Base, User
from . import crud
from .dependencies import get_db
from .tasks import run_analysis, run_analysis_sync, celery

# ---- LOCAL JWT AUTH (the good one) ----
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_user_by_username,
    get_user_by_email,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .schemas_auth import UserCreate, UserResponse, Token, LoginRequest, UserUpdate

from .support import router as support_router
from .payments import router as payments_router

# Initialize models at startup
try:
    from .models_interface import initialize_models
    initialize_models()
except Exception as e:
    print(f"Warning: Could not initialize models: {e}")


# -------------------------------------
# INIT
# -------------------------------------
Base.metadata.create_all(bind=engine)
app = FastAPI(title="DeepVerify API")

# Health check endpoint for deployment monitoring
@app.get("/health")
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "DeepVerify API"
    }

@app.get("/api/admin/storage-info")
def get_storage_info():
    """Get storage usage information (admin only)."""
    from .storage import StorageManager
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    
    info = {
        "uploads": StorageManager(
            os.path.join(backend_dir, "..", "data", "uploads")
        ).get_storage_info(),
        "heatmaps": StorageManager(
            os.path.join(backend_dir, "..", "data", "heatmaps")
        ).get_storage_info(),
        "reverse_images": StorageManager(
            os.path.join(backend_dir, "..", "data", "reverse-images")
        ).get_storage_info(),
    }
    
    total_size_gb = sum(d["total_size_gb"] for d in info.values())
    total_files = sum(d["file_count"] for d in info.values())
    
    return {
        "directories": info,
        "total": {
            "file_count": total_files,
            "total_size_gb": round(total_size_gb, 2),
            "total_size_mb": round(total_size_gb * 1024, 2),
        }
    }

@app.post("/api/admin/cleanup")
def trigger_cleanup():
    """Manually trigger cleanup of old files (admin only)."""
    from .storage import cleanup_all_temp_directories
    deleted, freed = cleanup_all_temp_directories()
    return {
        "success": True,
        "files_deleted": deleted,
        "space_freed_mb": round(freed / 1024 / 1024, 2),
        "space_freed_gb": round(freed / 1024 / 1024 / 1024, 2),
    }

# Startup event: cleanup old temporary files
@app.on_event("startup")
async def startup_cleanup():
    """Run cleanup on startup to free space."""
    try:
        from .storage import cleanup_all_temp_directories
        from .download_models import download_all_models
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Download models if needed (Railway deployment)
        logger.info("Checking models...")
        download_all_models()
        
        # Cleanup old files
        logger.info("Running startup cleanup...")
        deleted, freed = cleanup_all_temp_directories()
        logger.info(f"Startup cleanup complete: {deleted} files, {freed / 1024 / 1024:.2f} MB")
    except Exception as e:
        import logging
        logging.error(f"Startup tasks failed: {e}")


# -------------------------------------
# CORS
# -------------------------------------
# CORS - prefer explicit origins when using credentials
# Set FRONTEND_ORIGINS env var to a comma-separated list like "http://localhost:3000,http://example.com"
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000")
if FRONTEND_ORIGINS.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in FRONTEND_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# -------------------------------------
# FILE SETUP
# -------------------------------------
backend_dir = os.path.dirname(os.path.dirname(__file__))

UPLOAD_DIR = os.path.abspath(os.path.join(backend_dir, "..", "data", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

HEATMAP_DIR = os.path.abspath(os.path.join(backend_dir, "..", "data", "heatmaps"))
os.makedirs(HEATMAP_DIR, exist_ok=True)

REVERSE_IMAGE_DIR = os.path.abspath(os.path.join(backend_dir, "..", "data", "reverse-images"))
os.makedirs(REVERSE_IMAGE_DIR, exist_ok=True)

# Mount static files for reverse images
from fastapi.staticfiles import StaticFiles
app.mount("/public/reverse-images", StaticFiles(directory=REVERSE_IMAGE_DIR), name="reverse-images")


@app.get("/")
def root():
    return {"message": "DeepVerify backend running"}


# =================================================================
# AUTHENTICATION — LOCAL FASTAPI JWT SYSTEM (CORRECT + CLEAN)
# =================================================================

@app.post("/api/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")

    if get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = crud.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        db=db,
    )
    return user


@app.post("/api/auth/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            membership_status=user.membership_status,
            detections_used=user.detections_used,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    }


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.put("/api/auth/me", response_model=UserResponse)
def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Re-fetch user to ensure it's attached to the current session
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.email is not None:
        # Check if email is taken by another user
        existing = get_user_by_email(db, user_update.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_update.email
    
    db.commit()
    db.refresh(user)
    return user


# =================================================================
# UPLOAD — MUST BE LOGGED IN
# =================================================================

@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        filename = file.filename or "upload"
        ext = os.path.splitext(filename)[1] or ".jpg"

        image_id = uuid.uuid4().hex
        save_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")

        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        # Check usage limits
        if current_user.membership_status != "Pro":
            if current_user.detections_used >= 10:
                raise HTTPException(status_code=403, detail="Usage limit exceeded")

        job = crud.create_job(
            img_id=image_id,
            filename=save_path,
            db=db,
            user_id=current_user.id,
            image_data=content,
        )

        # Increment usage count
        current_user.detections_used += 1
        db.commit()

        # Prefer Celery if available
        if celery:
            try:
                print(f"[main] Using Celery for job_id={job.id}")
                run_analysis.delay(job.id, save_path)
            except Exception as e:
                print(f"[main] Celery failed, falling back to threading: {e}")
                # Run in background thread
                def run_task():
                    try:
                        run_analysis_sync(job.id, save_path)
                    except Exception as err:
                        print(f"[main] Background task error for job {job.id}: {err}")
                        import traceback
                        traceback.print_exc()
                
                thread = threading.Thread(target=run_task, daemon=False)  # Not daemon
                thread.start()
        else:
            print(f"[main] Using background thread for job_id={job.id}")
            # Run in background thread - NOT daemon so it completes
            def run_task():
                try:
                    run_analysis_sync(job.id, save_path)
                except Exception as e:
                    print(f"[main] Background task error for job {job.id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            thread = threading.Thread(target=run_task, daemon=False)  # Not daemon - ensures completion
            thread.start()

        print(f"[main] Job {job.id} created, analysis task scheduled in thread")
        return {"jobId": job.id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


# =================================================================
# METADATA ANALYZER — MUST BE LOGGED IN
# =================================================================

@app.post("/api/analyze/metadata")
async def analyze_metadata(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    Extract and analyze image metadata & encoding characteristics.
    Returns structured forensic analysis data.
    """
    try:
        import hashlib
        from .metadata_analyzer import analyze_forensic_image_bytes
        
        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(
                status_code=400, 
                detail="Only JPEG and PNG images are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size (max 10MB)
        if len(content) > 10_000_000:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Compute file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Forensic metadata + encoding analysis
        metadata_result = analyze_forensic_image_bytes(content, file.filename)

        return {
            "success": True,
            "filename": file.filename,
            "file_size": len(content),
            "file_hash": file_hash,
            "metadata": metadata_result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Metadata extraction failed: {str(e)}"
        )


@app.post("/api/analyze/metadata/download-report")
async def download_metadata_report(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate and return a professional PDF forensic report.
    """
    try:
        from .metadata_analyzer import analyze_forensic_image_bytes
        from .forensics_report import generate_forensic_report
        
        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(
                status_code=400, 
                detail="Only JPEG and PNG images are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size (max 10MB)
        if len(content) > 10_000_000:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Run forensic analysis
        metadata_result = analyze_forensic_image_bytes(content, file.filename)
        
        # Generate PDF report
        pdf_bytes = generate_forensic_report(
            metadata_analysis=metadata_result,
            image_bytes=content,
            filename=file.filename,
            file_size=len(content),
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "report_available": True,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Report generation failed: {str(e)}"
        )


# =================================================================
# REVERSE IMAGE SEARCH
# =================================================================

@app.post("/api/tools/reverse-image")
async def upload_reverse_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload an image for reverse image search to Cloudflare R2.
    Returns a publicly accessible image URL.
    """
    try:
        # Validate file type
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(
                status_code=400, 
                detail="Only JPEG and PNG images are supported"
            )
        
        # Validate file size (max 10MB)
        content = await file.read()
        if len(content) > 10_000_000:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.jpg"
        
        # Check if R2 is configured
        r2_account_id = os.getenv("R2_ACCOUNT_ID")
        r2_access_key = os.getenv("R2_ACCESS_KEY_ID")
        r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        r2_bucket = os.getenv("R2_BUCKET_NAME")
        r2_public_url = os.getenv("R2_PUBLIC_URL")
        
        if all([r2_account_id, r2_access_key, r2_secret_key, r2_bucket, r2_public_url]):
            # Upload to Cloudflare R2
            try:
                s3_client = boto3.client(
                    's3',
                    endpoint_url=f'https://{r2_account_id}.r2.cloudflarestorage.com',
                    aws_access_key_id=r2_access_key,
                    aws_secret_access_key=r2_secret_key,
                    region_name='auto'
                )
                
                # Upload the file
                s3_client.put_object(
                    Bucket=r2_bucket,
                    Key=f"reverse-images/{filename}",
                    Body=content,
                    ContentType=file.content_type,
                )
                
                # Construct public URL
                image_url = f"{r2_public_url}/reverse-images/{filename}"
                
                return {
                    "success": True,
                    "imageUrl": image_url,
                    "filename": filename,
                    "storage": "r2"
                }
                
            except ClientError as e:
                print(f"R2 upload failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload to R2: {str(e)}"
                )
        else:
            # Fallback to local storage if R2 not configured
            filepath = os.path.join(REVERSE_IMAGE_DIR, filename)
            
            # Save file to disk
            with open(filepath, "wb") as f:
                f.write(content)
            
            # Use local URL
            base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
            image_url = f"{base_url}/public/reverse-images/{filename}"
            
            return {
                "success": True,
                "imageUrl": image_url,
                "filename": filename,
                "storage": "local"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Image upload failed: {str(e)}"
        )


# =================================================================
# JOB TRANSFORM
# =================================================================

def transform_job_for_frontend(job):
    consensus = None

    if job.results:
        # STRICT LOGIC (User Request):
        # 1. Find DeepVerify (Master Model)
        # 2. Use its result for the "Final Decision" card.
        
        deepverify = next((r for r in job.results if r.model_name == "DeepVerify"), None)
        
        if deepverify:
            # Use DeepVerify's verdict explicitly
            decision = deepverify.label.upper() # "REAL" or "FAKE"
            
            # Get the relevant confidence score
            if decision == "FAKE":
                score = deepverify.confidence_fake
            else:
                score = deepverify.confidence_real
                
            consensus = {
                "decision": decision,
                "score": float(score),
                "explanation": [
                    f"Analyzed by {len(job.results)} model(s)",
                    f"Verdict Source: DeepVerify (Priority Model)",
                ],
            }
        else:
            # Fallback legacy logic (Majority Vote) if DeepVerify missing
            labels = [r.label for r in job.results]
            fake_count = labels.count("fake")
            real_count = labels.count("real")

            if fake_count > real_count:
                decision = "FAKE"
                avg_conf = sum(r.confidence_fake for r in job.results) / len(job.results)
            elif real_count > fake_count:
                decision = "REAL"
                avg_conf = sum(r.confidence_real for r in job.results) / len(job.results)
            else:
                decision = "UNCERTAIN"
                avg_conf = 0.5

            consensus = {
                "decision": decision,
                "score": avg_conf,
                "explanation": [
                    f"{len(job.results)} model(s) analyzed",
                    f"Majority vote: {decision.lower()}",
                ],
            }
    else:
        consensus = {
            "decision": "PENDING",
            "score": 0.0,
            "explanation": ["Analysis in progress..."],
        }

    models = []
    if job.results:
        for result in job.results:
            score = (
                result.confidence_fake
                if result.label == "fake"
                else result.confidence_real
            )

            BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
            heatmap_url = None
            if result.heatmap_path and result.heatmap_path != "N/A":
                # heatmap_path might be just filename or full path
                fname = os.path.basename(result.heatmap_path) if os.path.sep in result.heatmap_path else result.heatmap_path
                heatmap_file_path = os.path.join(HEATMAP_DIR, fname)
                if os.path.exists(heatmap_file_path):
                    heatmap_url = f"{BASE_URL}/api/heatmaps/{fname}"


            img_url = None
            # Prefer file path when available, otherwise use image_data stored in DB
            if job.file_path and os.path.exists(job.file_path):
                fname = os.path.basename(job.file_path)
                img_url = f"{BASE_URL}/api/uploads/{fname}"
            elif getattr(job, "image_data", None):
                # construct a filename from image_id (use .jpg by default)
                fname = f"{getattr(job, 'image_id', 'image')}.jpg"
                img_url = f"{BASE_URL}/api/uploads/{fname}"

            models.append(
                {
                    "model_name": result.model_name,
                    "version": "1.0",
                    "score": score,
                    "heatmap_url": heatmap_url,
                    "image_url": img_url,
                    "labels": {
                        "confidence_real": result.confidence_real,
                        "confidence_fake": result.confidence_fake,
                        "label": result.label,
                    },
                }
            )

    image = None
    if job.file_path and os.path.exists(job.file_path):
        fname = os.path.basename(job.file_path)
        image = {"thumbnail_url": f"/api/uploads/{fname}"}
    elif getattr(job, "image_data", None):
        image = {"thumbnail_url": f"/api/uploads/{getattr(job, 'image_id', 'image')}.jpg"}

    return {
        "job_id": job.id,
        "id": job.id,
        "image_id": getattr(job, "image_id", None),
        "file_path": job.file_path,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "models": models,
        "consensus": consensus,
        "image": image,
    }


# =================================================================
# GET JOB
# =================================================================

@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return transform_job_for_frontend(job)


# =================================================================
# DASHBOARD (AUTH REQUIRED)
# =================================================================

@app.get("/api/dashboard")
def dashboard(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    jobs = crud.get_recent_jobs(db, user_id=current_user.id)
    
    # Get total count of user's jobs to calculate analysis numbers
    from . import models
    total_count = db.query(models.Job).filter(models.Job.user_id == current_user.id).count()
    
    # Transform jobs and add user-specific analysis number
    transformed = []
    for idx, job in enumerate(jobs):
        job_data = transform_job_for_frontend(job)
        # Calculate analysis number (most recent = highest number)
        # Since jobs are ordered by created_at DESC, first job is the latest
        analysis_number = total_count - idx
        job_data["analysis_number"] = analysis_number
        job_data["display_name"] = f"Analysis #{analysis_number}"
        transformed.append(job_data)
    
    return transformed


# =================================================================
# FILE SERVING
# =================================================================

@app.get("/api/uploads/{filename}")
def get_uploaded_file(filename: str, db: Session = Depends(get_db)):
    # Try to serve from DB blob first. Support three cases:
    # 1) job.file_path contains the filename
    # 2) filename equals <image_id>.ext (we strip ext and match image_id)
    # 3) job.image_data exists even if file_path is None
    try:
        from . import models

        # 1) match by file_path containing filename
        job = db.query(models.Job).filter(models.Job.file_path.like(f"%{filename}")).first()
        if job and getattr(job, "image_data", None):
            ext = os.path.splitext(filename)[1].lower()
            media = "image/png" if ext == ".png" else "image/jpeg"
            return Response(content=job.image_data, media_type=media)

        # 2) match by image_id (filename may be <image_id>.jpg)
        base = os.path.splitext(filename)[0]
        job_by_id = db.query(models.Job).filter(models.Job.image_id == base).first()
        if job_by_id and getattr(job_by_id, "image_data", None):
            # choose media type from requested filename
            ext = os.path.splitext(filename)[1].lower()
            media = "image/png" if ext == ".png" else "image/jpeg"
            return Response(content=job_by_id.image_data, media_type=media)

        # 3) as fallback, if any job has image_data with matching basename
        # (covers cases where file_path is absolute and not matched by like())
        jobs = db.query(models.Job).all()
        for j in jobs:
            if getattr(j, "image_data", None):
                # attempt to match by basename of file_path
                if j.file_path and os.path.basename(j.file_path) == filename:
                    ext = os.path.splitext(filename)[1].lower()
                    media = "image/png" if ext == ".png" else "image/jpeg"
                    return Response(content=j.image_data, media_type=media)
    except Exception:
        # ignore DB errors and fallback to disk
        pass

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/api/heatmaps/{filename}")
def get_heatmap_file(filename: str, db: Session = Depends(get_db)):
    # Try to serve from DB blob first
    try:
        from . import models
        res = db.query(models.ModelResult).filter(models.ModelResult.heatmap_path == filename).first()
        if res and getattr(res, "heatmap_data", None):
            return Response(content=res.heatmap_data, media_type="image/png")
    except Exception:
        # ignore DB errors and fallback
        pass

    file_path = os.path.join(HEATMAP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Heatmap not found")
    return FileResponse(file_path)


# =================================================================
# TEST/DEBUG ENDPOINTS
# =================================================================
@app.post("/api/jobs/{job_id}/rerun")
@app.post("/api/rerun/{job_id}")
async def rerun_analysis(
    job_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Re-run analysis for an existing job"""
    job = crud.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user owns this job (allow if no user_id or user matches)
    if job.user_id is not None and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to re-run this job")
    
    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Delete existing results
    deleted_count = crud.delete_job_results(job_id, db)
    print(f"[main] Deleted {deleted_count} existing results for job {job_id}")
    
    # Reset job status to pending (this will trigger frontend refresh)
    crud.update_job_status(job_id, "pending", db)
    db.commit()  # Ensure status is committed before returning
    
    # Run analysis in background
    import threading
    
    def run_task():
        try:
            print(f"[main] Starting background re-analysis for job {job_id}")
            run_analysis_sync(job_id, job.file_path)
            print(f"[main] Completed re-analysis for job {job_id}")
        except Exception as e:
            print(f"[main] Re-run analysis error for job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            # Mark job as failed
            try:
                from .database import SessionLocal
                db_retry = SessionLocal()
                crud.update_job_status(job_id, "failed", db_retry)
                db_retry.commit()
                db_retry.close()
            except Exception as db_err:
                print(f"[main] Error updating job status to failed: {db_err}")
    
    thread = threading.Thread(target=run_task, daemon=False)
    thread.start()
    
    # Return updated job status
    db.refresh(job)
    return {
        "message": f"Re-analysis started for job {job_id}", 
        "job_id": job_id,
        "status": job.status
    }


@app.post("/api/test/analyze/{job_id}")
async def test_analyze(job_id: int, db: Session = Depends(get_db)):
    """Test endpoint to manually trigger analysis for a job"""
    job = crud.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.file_path or not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # Run analysis synchronously for testing
    try:
        run_analysis_sync(job_id, job.file_path)
        return {"message": f"Analysis completed for job {job_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/debug/job/{job_id}")
def debug_job(job_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to check job status and results"""
    job = crud.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    results_count = len(job.results) if job.results else 0
    results_detail = []
    if job.results:
        for r in job.results:
            results_detail.append({
                "model_name": r.model_name,
                "label": r.label,
                "confidence_real": r.confidence_real,
                "confidence_fake": r.confidence_fake,
            })
    
    return {
        "job_id": job.id,
        "status": job.status,
        "file_path": job.file_path,
        "file_exists": os.path.exists(job.file_path) if job.file_path else False,
        "results_count": results_count,
        "results": results_detail,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@app.get("/api/debug/job_blobs/{job_id}")
def debug_job_blobs(job_id: int, db: Session = Depends(get_db)):
    """Return diagnostics about presence of image/heatmap blobs for a job.
    Useful for debugging why images might not render.
    """
    from . import models

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    info = {
        "job_id": job.id,
        "image_id": getattr(job, "image_id", None),
        "file_path": job.file_path,
        "has_image_data": bool(getattr(job, "image_data", None)),
        "image_size": len(job.image_data) if getattr(job, "image_data", None) else 0,
        "results": []
    }

    results = db.query(models.ModelResult).filter(models.ModelResult.job_id == job_id).all()
    for r in results:
        info["results"].append({
            "model_name": r.model_name,
            "heatmap_path": r.heatmap_path,
            "has_heatmap_data": bool(getattr(r, "heatmap_data", None)),
            "heatmap_size": len(r.heatmap_data) if getattr(r, "heatmap_data", None) else 0,
        })

    return info

@app.post("/api/jobs/demo")
def create_demo_job(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a demo analysis job using a predefined image.
    Demo jobs:
    - do not count toward usage
    - do not appear in dashboard
    """

    SAMPLE_IMAGE = "sample-face.jpg"
    sample_src = os.path.join(os.path.dirname(__file__), "sample_assets", SAMPLE_IMAGE)

    if not os.path.exists(sample_src):
        raise HTTPException(status_code=500, detail="Sample image missing")

    # Copy image into uploads
    image_id = uuid.uuid4().hex
    dest_path = os.path.join(UPLOAD_DIR, f"{image_id}.jpg")
    shutil.copy(sample_src, dest_path)

    # Read the sample bytes and store in DB as well
    sample_bytes = None
    try:
        with open(dest_path, "rb") as sf:
            sample_bytes = sf.read()
    except Exception:
        sample_bytes = None

    # Create job EXACTLY like normal upload (store bytes in DB)
    job = crud.create_job(
        img_id=image_id,
        filename=dest_path,
        db=db,
        user_id=current_user.id,
        image_data=sample_bytes,
    )

    # IMPORTANT: mark job as demo (dynamic attribute)
    setattr(job, "is_demo", True)
    db.commit()

    # Run analysis (same as upload)
    if celery:
        run_analysis.delay(job.id, dest_path)
    else:
        threading.Thread(
            target=run_analysis_sync,
            args=(job.id, dest_path),
            daemon=False,
        ).start()

    return {"job_id": job.id}



app.include_router(support_router, prefix="/api")
app.include_router(payments_router, prefix="/api")

# Community contributions
from .contributions import router as contributions_router
app.include_router(contributions_router, prefix="/api")
