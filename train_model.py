#!/usr/bin/env python3
"""
Training Script for DeepVerify Model

This script fine-tunes the PatchBasedDetector model using community-contributed
labeled images from the database.

Usage:
    python train_model.py [--epochs 10] [--batch-size 16] [--lr 1e-5]
    
The script will:
1. Load all verified contributions from the database
2. Split into train/validation sets
3. Fine-tune the model
4. Save the new weights to backend/models/deepverify_finetuned.pt
"""

import os
import sys
import argparse
from datetime import datetime

# Add backend to path
# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Load environment variables explicitly from backend/.env for Supabase
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# FORCE ABSOLUTE DATABASE PATH for regeneration (Commented out)
# db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend", "deepfake.db"))
# os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms
from PIL import Image
from tqdm import tqdm

# Import database connection
from app.database import SessionLocal
from app.models import Contribution


# ============================================================================
# Configuration
# ============================================================================
MODELS_DIR = os.path.join(os.path.dirname(__file__), "backend", "models")
WEIGHTS_PATH = os.path.join(MODELS_DIR, "deepverify_finetuned.pt")
os.makedirs(MODELS_DIR, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================================
# Dataset
# ============================================================================
# Import face utils from backend
try:
    from app.face_utils import get_face_boxes, crop_face_region
    FACE_UTILS_AVAILABLE = True
    print("✅ Smart Face Training enabled (MTCNN)")
except ImportError:
    FACE_UTILS_AVAILABLE = False
    print("⚠️  face_utils not found, falling back to simple resize")

class ContributionDataset(Dataset):
    """Dataset for loading community-contributed images."""
    
    def __init__(self, contributions, transform=None):
        self.contributions = contributions
        self.transform = transform or transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def __len__(self):
        return len(self.contributions)
    
    def __getitem__(self, idx):
        contrib = self.contributions[idx]
        
        # Load image
        try:
            image = Image.open(contrib.image_path).convert("RGB")
            
            # --- SMART FACE CROP ---
            if FACE_UTILS_AVAILABLE:
                boxes = get_face_boxes(image)
                if boxes:
                    # Crop the first face found
                    image = crop_face_region(image, boxes[0])
            # -----------------------
            
            image = self.transform(image)
        except Exception as e:
            print(f"Error loading image {contrib.image_path}: {e}")
            # Return a blank image if failed
            image = torch.zeros(3, 224, 224)
        
        # Label: 0 = real, 1 = fake
        label = 1 if contrib.label == "fake" else 0
        
        return image, label


# ============================================================================
# Model (simplified for fine-tuning)
# ============================================================================
def load_model_for_training():
    """Load the PatchBasedDetector model for fine-tuning."""
    # Import from backend
    try:
        from app.deepfake_model import PatchBasedDetector
    except ImportError:
        # Fallback if running from root
        sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
        from app.deepfake_model import PatchBasedDetector
    
    print(f"Loading PatchBasedDetector (ViT + Attention Pooling)")
    model = PatchBasedDetector()
    
    # Freeze backbone weights
    for param in model.backbone.parameters():
        param.requires_grad = False
        
    # Unfreeze attention pooling and classifier
    for param in model.attention_pool.parameters():
        param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
        
    return model


# ============================================================================
# Training Functions
# ============================================================================
def train_epoch(model, dataloader, optimizer, criterion, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    for images, labels in tqdm(dataloader, desc="Training"):
        images = images.to(device)
        labels = labels.to(device)
        
        optimizer.zero_grad()
        
        # Forward pass
        outputs = model(images)
        
        # Handle dict output from PatchBasedDetector
        if isinstance(outputs, dict):
            logits = outputs["logits"]
        elif hasattr(outputs, "logits"):
            logits = outputs.logits
        else:
            logits = outputs
        
        loss = criterion(logits, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)
    
    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total
    return avg_loss, accuracy


def validate(model, dataloader, criterion, device):
    """Validate the model."""
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="Validation"):
            images = images.to(device)
            labels = labels.to(device)
            
            outputs = model(images)
            if isinstance(outputs, dict):
                logits = outputs["logits"]
            elif hasattr(outputs, "logits"):
                logits = outputs.logits
            else:
                logits = outputs
            
            loss = criterion(logits, labels)
            
            total_loss += loss.item()
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    
    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total
    return avg_loss, accuracy


# ============================================================================
# Main Training Loop
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Train DeepVerify model with contributed data")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--verified-only", action="store_true", help="Use only verified contributions")
    args = parser.parse_args()
    
    print("=" * 60)
    print("DeepVerify Model Training")
    print("=" * 60)
    print(f"Device: {DEVICE}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print()
    
    # -------------------------------------------------------------------------
    # Step 1: Load contributions from database
    # -------------------------------------------------------------------------
    print("Loading contributions from database...")
    db = SessionLocal()
    
    query = db.query(Contribution)
    if args.verified_only:
        query = query.filter(Contribution.verified == True)
    
    contributions = query.all()
    db.close()
    
    # Filter to only existing files
    valid_contributions = [c for c in contributions if os.path.exists(c.image_path)]
    
    print(f"Total contributions: {len(contributions)}")
    print(f"Valid (file exists): {len(valid_contributions)}")
    
    if len(valid_contributions) < 5:
        print("\n⚠️  Not enough data for training! Need at least 5 images.")
        print("Please collect more contributions before training.")
        sys.exit(1)
    
    # Count labels
    real_count = sum(1 for c in valid_contributions if c.label == "real")
    fake_count = sum(1 for c in valid_contributions if c.label == "fake")
    print(f"Real images: {real_count}")
    print(f"Fake images: {fake_count}")
    print()
    
    # -------------------------------------------------------------------------
    # Step 2: Create datasets
    # -------------------------------------------------------------------------
    print("Creating datasets...")
    dataset = ContributionDataset(valid_contributions)
    
    # Split into train/val
    val_size = int(len(dataset) * args.val_split)
    train_size = len(dataset) - val_size
    
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)
    
    print(f"Training samples: {train_size}")
    print(f"Validation samples: {val_size}")
    print()
    
    # -------------------------------------------------------------------------
    # Step 3: Load model
    # -------------------------------------------------------------------------
    print("Loading model...")
    model = load_model_for_training()
    model = model.to(DEVICE)
    
    # -------------------------------------------------------------------------
    # Step 4: Training setup
    # -------------------------------------------------------------------------
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr,
        weight_decay=1e-4
    )
    
    best_val_acc = 0.0
    
    # -------------------------------------------------------------------------
    # Step 5: Training loop
    # -------------------------------------------------------------------------
    print("\nStarting training...")
    print("-" * 60)
    
    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")
        
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion, DEVICE)
        val_loss, val_acc = validate(model, val_loader, criterion, DEVICE)
        
        print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f}")
        print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  ✅ Saved best model! (Acc: {val_acc:.4f})")
    
    # -------------------------------------------------------------------------
    # Step 6: Done
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"Best validation accuracy: {best_val_acc:.4f}")
    print(f"Weights saved to: {WEIGHTS_PATH}")
    print()
    print("To use the new weights, restart the backend server.")
    print("The model will automatically load the fine-tuned weights if available.")


if __name__ == "__main__":
    main()
