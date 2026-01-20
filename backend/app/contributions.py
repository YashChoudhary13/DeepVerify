# backend/app/contributions.py
"""
Community Training Data Contribution API

Endpoints for users to upload labeled images to help improve the detection model.
Images are stored for future training (not processed immediately).
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime
from typing import Optional

from .database import SessionLocal
from .models import Contribution, User
from .auth import get_current_active_user
from .dependencies import get_db

router = APIRouter()

# Directory for storing contributed images
CONTRIBUTIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "contributions")
)
os.makedirs(CONTRIBUTIONS_DIR, exist_ok=True)


@router.post("/contribute")
async def contribute_image(
    file: UploadFile = File(...),
    label: str = Form(...),  # "real" or "fake"
    source: str = Form(...),  # "camera", "download", "ai_tool", "other"
    ai_tool_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Submit a labeled image for training data collection.
    
    Parameters:
    - file: The image file
    - label: "real" or "fake"
    - source: Where the image came from
    - ai_tool_name: If label is "fake" and source is "ai_tool", specify which tool
    - description: Optional notes about the image
    """
    # Validate label
    if label not in ["real", "fake"]:
        raise HTTPException(status_code=400, detail="Label must be 'real' or 'fake'")
    
    # Validate source
    valid_sources = ["camera", "download", "ai_tool", "other"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Source must be one of: {valid_sources}")
    
    # If fake and from AI tool, require tool name
    if label == "fake" and source == "ai_tool" and not ai_tool_name:
        raise HTTPException(status_code=400, detail="Please specify which AI tool generated this image")
    
    try:
        # Generate unique filename
        filename = file.filename or "contribution"
        ext = os.path.splitext(filename)[1] or ".jpg"
        image_id = uuid.uuid4().hex
        save_path = os.path.join(CONTRIBUTIONS_DIR, f"{image_id}{ext}")
        
        # Save file
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        
        # Create contribution record
        contribution = Contribution(
            user_id=current_user.id,
            image_path=save_path,
            label=label,
            source=source,
            ai_tool_name=ai_tool_name,
            description=description,
            verified=False,
        )
        
        db.add(contribution)
        db.commit()
        db.refresh(contribution)
        
        return {
            "success": True,
            "message": "Thank you for your contribution!",
            "contribution_id": contribution.id,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save contribution: {str(e)}")


@router.get("/contributions/stats")
def get_contribution_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get contribution statistics for the current user.
    """
    # User's contributions
    user_total = db.query(Contribution).filter(Contribution.user_id == current_user.id).count()
    user_real = db.query(Contribution).filter(
        Contribution.user_id == current_user.id,
        Contribution.label == "real"
    ).count()
    user_fake = db.query(Contribution).filter(
        Contribution.user_id == current_user.id,
        Contribution.label == "fake"
    ).count()
    
    # Global stats
    global_total = db.query(Contribution).count()
    global_real = db.query(Contribution).filter(Contribution.label == "real").count()
    global_fake = db.query(Contribution).filter(Contribution.label == "fake").count()
    
    return {
        "user": {
            "total": user_total,
            "real": user_real,
            "fake": user_fake,
        },
        "global": {
            "total": global_total,
            "real": global_real,
            "fake": global_fake,
        }
    }


@router.get("/contributions/my")
def get_my_contributions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """
    Get the current user's recent contributions.
    """
    contributions = (
        db.query(Contribution)
        .filter(Contribution.user_id == current_user.id)
        .order_by(Contribution.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": c.id,
            "label": c.label,
            "source": c.source,
            "ai_tool_name": c.ai_tool_name,
            "verified": c.verified,
            "created_at": c.created_at.isoformat(),
        }
        for c in contributions
    ]
