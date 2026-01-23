# backend/app/deepfake_model.py
"""
Advanced Deepfake Detection Model

This module implements a state-of-the-art deepfake detection architecture using:
- Vision Transformer (ViT) backbone for feature extraction
- Patch-based analysis for localized manipulation detection
- Attention-weighted pooling for focusing on relevant image regions

The model processes images by dividing them into patches, extracting features
from each patch independently, and using learned attention weights to combine
patch-level predictions into a final image-level decision.
"""

import torch
import torch.nn as nn
import numpy as np
import os
from PIL import Image
from typing import Tuple, Optional, Dict, Any

# Model configuration
BACKBONE_MODEL = "dima806/deepfake_vs_real_image_detection"


class AttentionPooling(nn.Module):
    """
    Attention-based pooling layer.
    
    Instead of simple averaging, this layer learns which patches are most
    important for the final prediction and weights them accordingly.
    """
    
    def __init__(self, feature_dim: int):
        super().__init__()
        self.attention_net = nn.Sequential(
            nn.Linear(feature_dim, feature_dim // 2),
            nn.Tanh(),
            nn.Linear(feature_dim // 2, 1)
        )
    
    def forward(self, patch_features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            patch_features: Tensor of shape (batch, num_patches, feature_dim)
            
        Returns:
            pooled: Weighted combination of patch features (batch, feature_dim)
            attention_weights: Attention scores for each patch (batch, num_patches, 1)
        """
        attention_scores = self.attention_net(patch_features)
        attention_weights = torch.softmax(attention_scores, dim=1)
        pooled = (attention_weights * patch_features).sum(dim=1)
        return pooled, attention_weights


class PatchBasedDetector(nn.Module):
    """
    Patch-based deepfake detection model.
    
    This architecture divides the input image into patches, processes each
    patch through a ViT backbone, and uses attention pooling to aggregate
    patch-level features into a final prediction.
    
    Benefits:
    - Can detect localized manipulations (e.g., face swaps)
    - Attention weights provide interpretability (which areas are suspicious)
    - More robust than whole-image analysis
    """
    
    def __init__(self):
        super().__init__()
        
        # Load pre-trained ViT backbone
        from transformers import AutoModelForImageClassification
        
        self.backbone = AutoModelForImageClassification.from_pretrained(
            BACKBONE_MODEL,
            num_labels=2,
            output_hidden_states=True,
        )
        
        # Freeze backbone weights (use as feature extractor)
        for param in self.backbone.parameters():
            param.requires_grad = False
        
        # Get hidden size from backbone config
        hidden_size = self.backbone.config.hidden_size
        
        # Attention pooling for patch aggregation
        self.attention_pool = AttentionPooling(hidden_size)
        
        # Final classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size // 2, 2)
        )
    
    def extract_patches(self, image: torch.Tensor, patch_size: int = 112) -> torch.Tensor:
        """
        Extract non-overlapping patches from input image.
        
        Args:
            image: Input tensor of shape (batch, channels, height, width)
            patch_size: Size of each square patch
            
        Returns:
            patches: Tensor of shape (batch, num_patches, channels, patch_size, patch_size)
        """
        B, C, H, W = image.shape
        
        # Calculate number of patches in each dimension
        h_patches = H // patch_size
        w_patches = W // patch_size
        
        # Reshape to extract patches
        patches = image.unfold(2, patch_size, patch_size).unfold(3, patch_size, patch_size)
        patches = patches.contiguous().view(B, C, -1, patch_size, patch_size)
        patches = patches.permute(0, 2, 1, 3, 4)  # (B, num_patches, C, H, W)
        
        return patches
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the model.
        
        Args:
            x: Input image tensor (batch, patches, channels, height, width)
               or (batch, channels, height, width) for single-patch mode
               
        Returns:
            Dictionary containing:
            - logits: Classification logits (batch, 2)
            - attention_weights: Patch attention weights (batch, num_patches)
            - probabilities: Softmax probabilities (batch, 2)
        """
        # Handle both patch and non-patch inputs
        if x.dim() == 4:
            # Single image input - extract patches
            x = self.extract_patches(x)
        
        B, P, C, H, W = x.shape
        
        # Flatten batch and patch dimensions for backbone processing
        x_flat = x.reshape(B * P, C, H, W)
        
        # Resize patches to 224x224 if they are smaller (ViT expects 224)
        if H != 224 or W != 224:
            x_flat = torch.nn.functional.interpolate(
                x_flat, 
                size=(224, 224), 
                mode='bilinear', 
                align_corners=False
            )
        
        # Extract features from backbone
        outputs = self.backbone.base_model(pixel_values=x_flat)
        
        # Get CLS token features (first token)
        features = outputs.last_hidden_state[:, 0]  # (B*P, hidden_size)
        
        # Reshape back to (batch, patches, features)
        features = features.reshape(B, P, -1)
        
        # Attention pooling across patches
        pooled_features, attention_weights = self.attention_pool(features)
        
        # Final classification
        logits = self.classifier(pooled_features)
        probabilities = torch.softmax(logits, dim=1)
        
        return {
            "logits": logits,
            "attention_weights": attention_weights.squeeze(-1),
            "probabilities": probabilities
        }


def create_detector() -> PatchBasedDetector:
    """Factory function to create a new detector instance."""
    model = PatchBasedDetector()
    
    # Load fine-tuned weights if available
    weights_path = os.path.join(os.path.dirname(__file__), "..", "models", "deepverify_finetuned.pt")
    weights_path = os.path.abspath(weights_path)
    print(f"[deepfake_model] Checking for weights at: {weights_path} | Exists: {os.path.exists(weights_path)}")
    if os.path.exists(weights_path):
        try:
            print(f"[deepfake_model] Loading fine-tuned weights from {weights_path}")
            model.load_state_dict(torch.load(weights_path, map_location="cpu"))
        except Exception as e:
            print(f"[deepfake_model] Failed to load weights: {e}")
    
    return model


def preprocess_image(image_path: str, target_size: int = 224) -> torch.Tensor:
    """
    Load and preprocess an image for the detector.
    
    Args:
        image_path: Path to the image file
        target_size: Target size for resizing (will be square)
        
    Returns:
        Preprocessed image tensor ready for the model
    """
    from torchvision import transforms
    
    transform = transforms.Compose([
        transforms.Resize((target_size, target_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
    
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0)  # Add batch dimension
    
    return tensor


def predict(model: PatchBasedDetector, image_path: str, device: str = "cpu") -> Dict[str, Any]:
    """
    Run prediction on a single image.
    
    Args:
        model: The detector model
        image_path: Path to the image
        device: Device to run inference on
        
    Returns:
        Dictionary with prediction results
    """
    model = model.to(device)
    model.eval()
    
    # Preprocess image
    image = preprocess_image(image_path).to(device)
    
    with torch.no_grad():
        outputs = model(image)
    
    probs = outputs["probabilities"][0].cpu().numpy()
    attention = outputs["attention_weights"][0].cpu().numpy()
    
    # Determine prediction (assuming index 0 = real, index 1 = fake)
    label = "fake" if probs[1] > probs[0] else "real"
    
    return {
        "label": label,
        "confidence_real": float(probs[0]),
        "confidence_fake": float(probs[1]),
        "attention_weights": attention.tolist(),
        "suspicious_patches": int(np.sum(attention > np.mean(attention) + np.std(attention)))
    }
