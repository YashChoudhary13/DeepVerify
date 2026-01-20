from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    membership_status = Column(String, default="Free")
    detections_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="owner")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, unique=True, index=True)
    file_path = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="jobs")
    results = relationship("ModelResult", back_populates="job")
    is_demo = Column(Boolean, default=False)


class ModelResult(Base):
    __tablename__ = "model_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    model_name = Column(String)
    confidence_real = Column(Float)
    confidence_fake = Column(Float)
    label = Column(String)
    heatmap_path = Column(String)

    job = relationship("Job", back_populates="results")


class Contribution(Base):
    """
    Community-contributed training data.
    Users upload images and label them as Real or Fake to help improve the model.
    """
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    label = Column(String, nullable=False)  # "real" or "fake"
    source = Column(String, nullable=False)  # "camera", "download", "ai_tool", "other"
    ai_tool_name = Column(String, nullable=True)  # e.g., "Midjourney", "DALL-E"
    description = Column(String, nullable=True)  # Optional note from user
    verified = Column(Boolean, default=False)  # Admin review status
    created_at = Column(DateTime, default=datetime.utcnow)

    contributor = relationship("User", backref="contributions")
