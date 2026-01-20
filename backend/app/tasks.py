# app/tasks.py
import traceback
import asyncio
import os
from .database import SessionLocal
from . import crud
from . import models
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, USE_CELERY
from .models_interface import run_models_on_image, HEATMAP_DIR  # must return {"models": [...], "consensus": {...}}
from datetime import datetime

# Try to initialize Celery, fallback to None if Redis unavailable
celery = None
try:
    if USE_CELERY == "false":
        celery = None
    elif USE_CELERY == "true":
        try:
            from celery import Celery
            celery = Celery(
                "tasks",
                broker=CELERY_BROKER_URL,
                backend=CELERY_RESULT_BACKEND,
            )
            # Quick health check; may raise if Redis not reachable
            celery.control.inspect(timeout=1).active()
        except Exception as e:
            print(f"Warning: Celery/Redis not available: {e}. Using sync mode.")
            celery = None
    else:
        # auto mode: try to use Celery but don't crash
        try:
            from celery import Celery
            test_celery = Celery(
                "tasks",
                broker=CELERY_BROKER_URL,
                backend=CELERY_RESULT_BACKEND,
            )
            test_celery.control.inspect(timeout=1).active()
            celery = test_celery
        except Exception:
            celery = None
except Exception as e:
    print(f"Warning: Could not initialize Celery: {e}. Using sync mode.")
    celery = None


def _get_db():
    return SessionLocal()


def run_analysis_sync(job_id: int, file_path: str):
    """
    Synchronous worker for local dev. This:
      1. marks job 'processing'
      2. runs models via run_models_on_image (async -> run with asyncio.run)
      3. saves each model result via crud.add_model_result
      4. marks job 'completed' (or 'failed' on error)
    """
    db = _get_db()
    try:
        print(f"[tasks] Starting analysis job_id={job_id}, file={file_path}")
        # 1) mark job processing
        crud.update_job_status(job_id, "processing", db)
        db.commit()  # Ensure status is saved

        # 2) run the model pipeline (models_interface returns structured results)
        try:
            results = asyncio.run(run_models_on_image(file_path, job_id)) \
                if callable(run_models_on_image) else asyncio.run(run_models_on_image(file_path))
        except TypeError:
            # fallback if run_models_on_image signature is (file_path,) not (file_path, job_id)
            results = asyncio.run(run_models_on_image(file_path))
        except Exception as e:
            print(f"[tasks] Error running models: {e}")
            traceback.print_exc()
            raise

        if not results:
            raise RuntimeError("Model runner returned None")
        
        if "models" not in results:
            raise RuntimeError("Model runner returned unexpected result structure")

        # 3) persist per-model results
        model_count = 0
        print(f"[tasks] Processing {len(results.get('models', []))} model results")
        if results.get("models"):
            for m in results["models"]:
                # expect m contains keys: name, version, confidence_real, confidence_fake, label, time_ms, heatmap_path
                try:
                    # Skip error results
                    if m.get("label") == "error":
                        print(f"[tasks] Skipping error result from model: {m.get('name', 'unknown')}")
                        continue
                    
                    model_name = m.get("name") or m.get("model_name") or "unknown"
                    confidence_real = float(m.get("confidence_real", 0.0))
                    confidence_fake = float(m.get("confidence_fake", 0.0))
                    label = m.get("label", "unknown")
                    heatmap_path = m.get("heatmap_path", "N/A")
                    heatmap_bytes = None
                    # If heatmap was written to disk by models_interface, read its bytes to store in DB
                    try:
                        if heatmap_path and heatmap_path != "N/A":
                            heat_fp = os.path.join(HEATMAP_DIR, heatmap_path)
                            if os.path.exists(heat_fp):
                                with open(heat_fp, "rb") as hf:
                                    heatmap_bytes = hf.read()
                    except Exception as e:
                        print(f"[tasks] Warning: could not read heatmap bytes for {heatmap_path}: {e}")
                    
                    print(f"[tasks] Saving result: model={model_name}, real={confidence_real:.4f}, fake={confidence_fake:.4f}, label={label}")
                    
                    crud.add_model_result(
                        job_id=job_id,
                        model_name=model_name,
                        confidence_real=confidence_real,
                        confidence_fake=confidence_fake,
                        label=label,
                        heatmap_path=heatmap_path,
                        db=db,
                        heatmap_bytes=heatmap_bytes,
                    )
                    model_count += 1
                    print(f"[tasks] ✓ Saved result for model: {model_name}")
                except Exception as e:
                    print(f"[tasks] ✗ Error saving model result: {e}")
                    traceback.print_exc()
        
        if model_count == 0:
            print(f"[tasks] ⚠ Warning: No successful model results for job_id={job_id}")
            print(f"[tasks] Results structure: {results}")
        else:
            print(f"[tasks] ✓ Successfully saved {model_count} model results")

        # 4) mark job completed (even if no models worked)
        crud.update_job_status(job_id, "completed", db)
        db.commit()
        
        # Verify results were saved
        db.refresh(db.query(models.Job).filter(models.Job.id == job_id).first())
        saved_results = db.query(models.ModelResult).filter(models.ModelResult.job_id == job_id).count()
        print(f"[tasks] ✓ Completed job_id={job_id} with {model_count} model results (verified: {saved_results} in DB)")

    except Exception as e:
        # log and mark failed
        print(f"[tasks] Error processing job_id={job_id}: {e}")
        traceback.print_exc()
        try:
            crud.update_job_status(job_id, "failed", db)
            db.commit()
        except Exception as db_error:
            print(f"[tasks] Error updating job status to failed: {db_error}")
    finally:
        db.close()


# Celery task wrapper (keeps same function signature). If celery is None we still define run_analysis as alias.
if celery:
    @celery.task(bind=True, name="run_analysis")
    def run_analysis(self, job_id: int, file_path: str):
        return run_analysis_sync(job_id, file_path)
else:
    def run_analysis(job_id: int, file_path: str):
        return run_analysis_sync(job_id, file_path)
