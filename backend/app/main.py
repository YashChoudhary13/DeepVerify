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
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import timedelta
import os
import uuid
from dotenv import load_dotenv

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


# -------------------------------------
# CORS
# -------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in production
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
@app.post("/upload")
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
# JOB TRANSFORM
# =================================================================

def transform_job_for_frontend(job):
    consensus = None

    if job.results:
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
            if job.file_path and os.path.exists(job.file_path):
                fname = os.path.basename(job.file_path)
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
        image = {"thumbnail_url": f"{BASE_URL}/api/uploads/{fname}"}

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
@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = crud.get_job(job_id, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return transform_job_for_frontend(job)


# =================================================================
# DASHBOARD (AUTH REQUIRED)
# =================================================================

@app.get("/api/dashboard")
@app.get("/dashboard")
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
def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/api/heatmaps/{filename}")
def get_heatmap_file(filename: str):
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


app.include_router(support_router)
app.include_router(payments_router)
