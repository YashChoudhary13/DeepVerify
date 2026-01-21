# app/models_interface.py
"""
Unified model interface supporting PyTorch (.pt) and Keras/TensorFlow (.h5, .keras).

Register models in MODEL_REGISTRY. Each entry:
{
  "name": "FriendlyName",
  "path": "filename_or_relative_or_absolute_path",
  "framework": "torch" or "keras" (optional, inferred from extension),
  "input_size": 224,
  "version": "1.0",
  # optional: loader: callable(path, device) -> loaded_model
  # optional: preprocess: "imagenet" or "none" (defaults to imagenet normalization)
}

Produces for each model:
{
  "name","version","confidence_real","confidence_fake","label","time_ms","heatmap_path"
}
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List
import traceback

import numpy as np
from PIL import Image, ImageOps
import matplotlib.pyplot as plt

# PyTorch imports (import when needed)
try:
    import torch
    import torchvision.transforms as T
    TORCH_AVAILABLE = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except Exception:
    torch = None
    T = None
    TORCH_AVAILABLE = False
    DEVICE = None

# TensorFlow / Keras imports (import when needed)
try:
    import tensorflow as tf
    TF_AVAILABLE = True
    # Configure TF to avoid hogging GPU memory if present (optional)
    try:
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            for g in gpus:
                tf.config.experimental.set_memory_growth(g, True)
    except Exception:
        pass
except Exception:
    tf = None
    TF_AVAILABLE = False

# Transformers import
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Paths (robust)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # backend root
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))  # project root (one level up)
MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, "models"))  # backend/models
ALT_MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, "models", "models"))  # accidental nested copy
APP_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))  # app/models (rare)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BASE_DIR), exist_ok=True)  # ensure parent exists

# Use same HEATMAP_DIR as main.py to ensure consistency
# main.py uses: backend_dir/../data/heatmaps = DeepFake-Detector/data/heatmaps
HEATMAP_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "heatmaps"))
os.makedirs(HEATMAP_DIR, exist_ok=True)

# -----------------------
# MODEL REGISTRY — Use filenames or relative path under backend/models.
# You can replace the `path` with an absolute path if you prefer.
# -----------------------
MODEL_REGISTRY: List[Dict[str, Any]] = [
    # Adaptive Detection Model (Smart Routing)
    # - If metadata exists → Uses fast metadata analysis
    # - If metadata stripped → Falls back to visual AI analysis (Patch-MIL)
    {
        "name": "DeepVerify", 
        "path": "adaptive_virtual", 
        "framework": "adaptive", 
        "input_size": 224, 
        "version": "2.0"
    },

    # Keras models for visual breakdown (Heatmaps)
    # NOTE: These are for display only. Final verdict relies on DeepVerify.
    {"name": "MobileNetV2", "path": "mobilenetv2_deepfake.h5", "framework": "keras", "input_size": 224, "version": "1.0"},
    {"name": "EfficientNetB0", "path": "efficientnet_b0_deepfake.h5", "framework": "keras", "input_size": 224, "version": "1.0"},
    {"name": "Xception", "path": "xception_deepfake.h5", "framework": "keras", "input_size": 299, "version": "1.0"},
    {"name": "ResNet50", "path": "resnet50_deepfake.h5", "framework": "keras", "input_size": 224, "version": "1.0"},
]

# Lightweight cache to avoid reload
_MODEL_CACHE: Dict[str, Any] = {}
_MODEL_CACHE_LOCK = threading.Lock()

# -----------------------
# Loaders
# -----------------------
# -----------------------
# Loaders
# -----------------------
# Import the metadata analyzer
try:
    from .metadata_analyzer import analyze_image_metadata_sync
except ImportError:
    # Graceful fallback if not found
    analyze_image_metadata_sync = None 

def _load_torch_model(path: str):
    if not TORCH_AVAILABLE:
        raise RuntimeError("Torch not available. Install torch to load .pt models.")
    # Prefer torch.jit.load, then fallback to torch.load
    try:
        model = torch.jit.load(path, map_location=DEVICE)
        model.eval()
        return model.to(DEVICE)
    except Exception:
        obj = torch.load(path, map_location=DEVICE)
        if isinstance(obj, torch.nn.Module):
            obj.to(DEVICE)
            obj.eval()
            return obj
        # else maybe it's state_dict: user must provide custom loader
        raise RuntimeError("Loaded object is not a nn.Module. Provide a custom loader for state_dict-based files.")

def _load_keras_model(path: str, use_legacy: bool = False):
    """
    Load Keras model with various compatibility options.
    
    Args:
        path: Path to model file
        use_legacy: If True, try legacy loading methods for old models
    """
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow not available. Install tensorflow to load .h5/.keras models.")
    
    # Try multiple loading strategies
    strategies = []
    
    # Strategy 1: Standard load with Flatten fix
    def load_standard():
        try:
            return tf.keras.models.load_model(path, compile=False)
        except Exception as e:
            error_str = str(e).lower()
            # If error is about Flatten layer receiving list, try to fix it
            if "flatten" in error_str and "list" in error_str and "shape" in error_str:
                # Try loading with custom objects to fix Flatten layer
                from tensorflow.keras.layers import Flatten, Layer
                
                class FixedFlatten(Flatten):
                    """Flatten layer that handles list inputs"""
                    def call(self, inputs):
                        # Ensure inputs is a tensor, not a list
                        if isinstance(inputs, (list, tuple)):
                            # Take first element if it's a list
                            if len(inputs) > 0:
                                inputs = inputs[0]
                            else:
                                raise ValueError("Empty input list to Flatten layer")
                        # Convert to tensor if needed
                        if not hasattr(inputs, 'shape'):
                            inputs = tf.convert_to_tensor(inputs)
                        return super().call(inputs)
                
                # Also try with Lambda layer wrapper
                class ListToTensor(Layer):
                    """Layer that converts list inputs to tensor"""
                    def call(self, inputs):
                        if isinstance(inputs, (list, tuple)):
                            return inputs[0] if len(inputs) > 0 else inputs
                        return inputs
                
                custom_objects = {
                    'Flatten': FixedFlatten,
                    'ListToTensor': ListToTensor,
                }
                try:
                    return tf.keras.models.load_model(path, compile=False, custom_objects=custom_objects)
                except Exception as e2:
                    # If that also fails, try to load and rebuild the model
                    print(f"[models_interface] Standard load failed, trying architecture fix: {e2}")
                    # Try loading weights only approach
                    raise e2
            raise
    
    strategies.append(load_standard)
    
    # Strategy 2: With safe_mode (for newer Keras versions)
    try:
        # Check if safe_mode parameter exists (newer Keras)
        strategies.append(lambda: tf.keras.models.load_model(path, compile=False, safe_mode=False))
    except TypeError:
        # safe_mode doesn't exist in this version, skip
        pass
    
    # Strategy 2b: Try SavedModel format (for .keras files that are SavedModel)
    # Note: This is handled by the standard load_model, but we can add custom handling if needed
    
    # Strategy 3: Try loading weights only (for models with dtype issues)
    if use_legacy:
        def load_weights_only():
            # For models with dtype tuple issues, try to load architecture and weights separately
            try:
                import h5py
                import json
                
                with h5py.File(path, 'r') as f:
                    # Try to get model config from attributes (not keys)
                    if 'model_config' in f.attrs:
                        config_str = f.attrs['model_config']
                        if isinstance(config_str, bytes):
                            config_str = config_str.decode('utf-8')
                        elif not isinstance(config_str, str):
                            config_str = str(config_str)
                        
                        try:
                            config = json.loads(config_str)
                        except json.JSONDecodeError:
                            # Try to fix common JSON issues
                            config_str = config_str.replace("'", '"')
                            config = json.loads(config_str)
                        
                        # Fix dtype tuple issues recursively
                        def fix_dtype_recursive(obj):
                            if isinstance(obj, dict):
                                fixed = {}
                                for k, v in obj.items():
                                    if k == 'dtype':
                                        # Handle tuple/list dtype
                                        if isinstance(v, (list, tuple)):
                                            if len(v) == 2 and v[0] == 'dtype':
                                                fixed[k] = 'float32'  # Default
                                            elif len(v) > 0:
                                                # Take first element if it's a string
                                                fixed[k] = str(v[0]) if isinstance(v[0], str) else 'float32'
                                            else:
                                                fixed[k] = 'float32'
                                        elif isinstance(v, str):
                                            fixed[k] = v
                                        else:
                                            fixed[k] = 'float32'
                                    else:
                                        fixed[k] = fix_dtype_recursive(v)
                                return fixed
                            elif isinstance(obj, list):
                                return [fix_dtype_recursive(item) for item in obj]
                            elif isinstance(obj, tuple):
                                # Check if it's a dtype tuple
                                if len(obj) == 2 and obj[0] == 'dtype':
                                    return 'float32'
                                # Otherwise convert to list and fix
                                return fix_dtype_recursive(list(obj))
                            return obj
                        
                        config = fix_dtype_recursive(config)
                        
                        # Reconstruct model from fixed config
                        try:
                            model = tf.keras.models.model_from_json(json.dumps(config))
                        except Exception as e1:
                            # Try with model_from_config if available
                            try:
                                from tensorflow.keras.utils import model_from_config
                                model = model_from_config(config)
                            except:
                                raise e1
                        
                        # Load weights
                        try:
                            model.load_weights(path, by_name=True, skip_mismatch=True)
                        except Exception:
                            # Try without skip_mismatch
                            model.load_weights(path, by_name=True)
                        return model
                    else:
                        raise ValueError("No model_config found in h5 file attributes")
            except Exception as e:
                # If this approach fails, re-raise to try next strategy
                raise e
        strategies.append(load_weights_only)
    
    # Strategy 4: Try with legacy format
    if use_legacy:
        strategies.append(lambda: tf.keras.models.load_model(path, compile=False, custom_objects=None))
    
    # Try each strategy
    last_error = None
    for i, strategy in enumerate(strategies):
        try:
            model = strategy()
            if i > 0:
                print(f"[models_interface] Loaded model using strategy {i+1}")
            return model
        except Exception as e:
            last_error = e
            if i == len(strategies) - 1:
                # Last strategy failed, raise error
                error_msg = str(last_error)
                if "SavedModel" in error_msg or "saved_model" in error_msg.lower():
                    raise RuntimeError(f"Failed to load Keras model at {path}: {error_msg}. This might be a SavedModel format issue.")
                elif "h5" in path.lower() and "HDF5" in error_msg:
                    raise RuntimeError(f"Failed to load Keras model at {path}: {error_msg}. The .h5 file might be corrupted or incompatible.")
                elif "dtype" in error_msg.lower() and "tuple" in error_msg.lower():
                    raise RuntimeError(f"Failed to load Keras model at {path}: {error_msg}. This model was saved with an older Keras version and has compatibility issues. Try converting it to a newer format.")
                else:
                    raise RuntimeError(f"Failed to load Keras model at {path}: {error_msg}")
            # Continue to next strategy
            continue
    
    # Should not reach here, but just in case
    raise RuntimeError(f"Failed to load Keras model at {path}: All loading strategies failed")

def _load_model_entry(entry: Dict[str, Any]):
    """
    Loads model according to entry. Caches loaded models.
    Tries multiple likely locations to account for developer copy mistakes.
    Prints candidates it tried.
    """
    name = entry.get("name", "unknown")
    framework = entry.get("framework", "").lower()
    raw_path = entry.get("path")

    # Special handling for Metadata "Fake Model"
    if framework == "metadata":
        return "metadata_virtual_model"
    
    # Special handling for Transformers (Hugging Face)
    if framework == "transformers":
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("transformers library not found. Install it with `pip install transformers`.")
        
        # Check cache
        cache_key = f"{name}:{raw_path}"
        with _MODEL_CACHE_LOCK:
            if cache_key in _MODEL_CACHE:
                return _MODEL_CACHE[cache_key]
        
        # Load pipeline (Force CPU to avoid the CUDA errors seen earlier, unless user fixes CUDA)
        print(f"[models_interface] Loading Hugging Face pipeline: {raw_path}")
        # device=-1 means CPU
        try:
            model = pipeline("image-classification", model=raw_path, device=-1)
        except Exception as e:
            raise RuntimeError(f"Failed to load Hugging Face model {raw_path}: {e}")

        with _MODEL_CACHE_LOCK:
            _MODEL_CACHE[cache_key] = model
        return model

    # Special handling for Patch-based Detector
    if framework == "patch_detector":
        cache_key = f"{name}:patch_detector"
        with _MODEL_CACHE_LOCK:
            if cache_key in _MODEL_CACHE:
                return _MODEL_CACHE[cache_key]
        
        print(f"[models_interface] Loading PatchBasedDetector...")
        try:
            from .deepfake_model import create_detector
            model = create_detector()
            model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load PatchBasedDetector: {e}")
        
        with _MODEL_CACHE_LOCK:
            _MODEL_CACHE[cache_key] = model
        return model

    # Special handling for Adaptive (Smart Routing) Model
    if framework == "adaptive":
        # Return a dict with both possible models lazily loaded
        return {"type": "adaptive_router"}

    if not raw_path:
        raise RuntimeError(f"Model entry for '{name}' missing 'path'")
    
    # Validate input_size is specified
    input_size = entry.get("input_size")
    if input_size is None:
        print(f"[models_interface] Warning: Model '{name}' missing input_size, defaulting to 224")
        entry["input_size"] = 224
    elif not isinstance(input_size, int) or input_size < 32:
        print(f"[models_interface] Warning: Model '{name}' has invalid input_size={input_size}, defaulting to 224")
        entry["input_size"] = 224

    # Build candidate paths to try (in order)
    candidates = []

    # Provided absolute path -> try as-is first
    if os.path.isabs(raw_path):
        candidates.append(raw_path)
    else:
        # raw relative (relative to current working dir)
        candidates.append(os.path.abspath(raw_path))
        # backend/models/<raw_path>
        candidates.append(os.path.join(MODELS_DIR, raw_path))
        # backend/models/models/<raw_path> (handles accidental nested copy)
        candidates.append(os.path.join(ALT_MODELS_DIR, raw_path))
        # app/models/<raw_path>
        candidates.append(os.path.join(APP_MODELS_DIR, raw_path))
        # project root models folder
        candidates.append(os.path.join(PROJECT_ROOT, "models", raw_path))
        # project root /models/<raw_path>
        candidates.append(os.path.join(PROJECT_ROOT, raw_path))

    # Normalize and deduplicate
    normed = []
    for p in candidates:
        try:
            p_abs = os.path.abspath(p)
        except Exception:
            continue
        if p_abs not in normed:
            normed.append(p_abs)

    # Print what we will try (helpful for debugging)
    print(f"[models_interface] Loading model '{name}' (raw='{raw_path}'). Candidate paths:")
    for p in normed:
        print(f"  - {p}")

    # pick the first existing
    path = None
    for p in normed:
        if os.path.exists(p):
            path = p
            break

    if not path:
        raise RuntimeError(
            f"Model path not found for '{name}'. Tried:\n" +
            "\n".join(f"  - {p}" for p in normed) +
            f"\nPut the file under {MODELS_DIR} (or update MODEL_REGISTRY to point to the correct path)."
        )

    loader = entry.get("loader", None)
    framework = (entry.get("framework") or os.path.splitext(path)[1].lower().lstrip(".")).lower()

    cache_key = f"{name}:{path}"
    with _MODEL_CACHE_LOCK:
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

    if loader and callable(loader):
        model = loader(path, DEVICE)
    else:
        try:
            # Check if model needs legacy loading
            use_legacy = entry.get("load_with_legacy", False)
            
            if framework in ("pt", "pth", "torch", "torchscript"):
                model = _load_torch_model(path)
            elif framework in ("h5", "keras", "tf", "tfkeras"):
                model = _load_keras_model(path, use_legacy=use_legacy)
            else:
                # fallback: try torch then keras
                try:
                    model = _load_torch_model(path)
                except Exception:
                    model = _load_keras_model(path, use_legacy=use_legacy)
        except Exception as e:
            error_msg = str(e)
            framework_str = framework or "unknown"
            raise RuntimeError(f"Failed to load {framework_str} model '{name}' at {path}: {error_msg}")

    with _MODEL_CACHE_LOCK:
        _MODEL_CACHE[cache_key] = model
    return model

# -----------------------
# Preprocessing helpers
# -----------------------
def _preprocess_for_torch(img_pil: Image.Image, input_size: int):
    """
    Preprocess image for PyTorch models.
    Ensures image is resized to input_size before processing.
    """
    # Ensure image is RGB and properly sized
    if img_pil.mode != "RGB":
        img_pil = img_pil.convert("RGB")
    
    # Resize to exact input_size using high-quality resampling
    img_resized = ImageOps.fit(img_pil, (input_size, input_size), Image.LANCZOS)
    
    # Convert to array and normalize
    arr = np.array(img_resized).astype(np.float32) / 255.0  # HWC, [0, 1]
    arr = np.transpose(arr, (2,0,1))  # CHW
    
    # Convert to tensor
    tensor = torch.tensor(arr, dtype=torch.float32, device=DEVICE).unsqueeze(0)
    
    # ImageNet normalization
    mean = torch.tensor([0.485,0.456,0.406], device=DEVICE).view(1,3,1,1)
    std = torch.tensor([0.229,0.224,0.225], device=DEVICE).view(1,3,1,1)
    tensor = (tensor - mean) / std
    
    return tensor

def _preprocess_for_keras(img_pil: Image.Image, input_size: int):
    """
    Preprocess image for Keras/TensorFlow models.
    Ensures image is resized to input_size before processing.
    """
    # Ensure image is RGB and properly sized
    if img_pil.mode != "RGB":
        img_pil = img_pil.convert("RGB")
    
    # Resize to exact input_size using high-quality resampling
    img_resized = ImageOps.fit(img_pil, (input_size, input_size), Image.LANCZOS)
    
    # Convert to array and normalize to [0, 1]
    arr = np.array(img_resized).astype(np.float32)
    arr = arr / 255.0
    
    # Add batch dimension
    inp = np.expand_dims(arr, axis=0)
    
    return inp

# -----------------------
# Forward/predict helpers
# -----------------------
def _predict_with_torch(model, input_tensor):
    """
    Predict with PyTorch model and return normalized probabilities.
    Handles various output formats: logits, probabilities, single values.
    """
    model.eval()
    with torch.no_grad():
        out = model(input_tensor)
        
        # Extract prediction from dict if needed
        if isinstance(out, dict):
            if "logits" in out:
                pred = out["logits"]
            elif "probabilities" in out:
                pred = out["probabilities"]
            else:
                tensors = [v for v in out.values() if torch.is_tensor(v)]
                pred = tensors[0] if tensors else out
        else:
            pred = out

        if isinstance(pred, np.ndarray):
            pred = torch.from_numpy(pred).to(DEVICE)

        if not torch.is_tensor(pred):
            raise RuntimeError("Torch model did not return tensor-like output")

        # Handle different output shapes
        pred = pred.squeeze()  # Remove extra dimensions
        
        # If single value (binary classification with sigmoid)
        if pred.dim() == 0 or (pred.dim() == 1 and pred.size(0) == 1):
            # Single value: apply sigmoid to get probability
            prob_fake = torch.sigmoid(pred).cpu().item() if pred.dim() == 0 else torch.sigmoid(pred[0]).cpu().item()
            prob_real = 1.0 - prob_fake
            probs = np.array([prob_real, prob_fake], dtype=np.float32)
        # If two values (binary classification with logits)
        elif pred.dim() == 1 and pred.size(0) == 2:
            # Two logits: apply softmax
            probs = torch.softmax(pred, dim=0).cpu().numpy()
        # If 2D with batch dimension
        elif pred.dim() == 2:
            if pred.size(1) == 1:
                # Single output per sample: apply sigmoid
                prob_fake = torch.sigmoid(pred[0, 0]).cpu().item()
                prob_real = 1.0 - prob_fake
                probs = np.array([prob_real, prob_fake], dtype=np.float32)
            else:
                # Multiple outputs: apply softmax
                probs = torch.softmax(pred[0], dim=0).cpu().numpy()
        else:
            # Fallback: flatten and apply softmax
            flat = pred.view(-1)
            if flat.size(0) == 1:
                prob_fake = torch.sigmoid(flat[0]).cpu().item()
                prob_real = 1.0 - prob_fake
                probs = np.array([prob_real, prob_fake], dtype=np.float32)
            else:
                probs = torch.softmax(flat, dim=0).cpu().numpy()
    
    # Ensure probabilities sum to 1 and are in valid range
    probs = np.clip(probs, 0.0, 1.0)
    probs = probs / (probs.sum() + 1e-8)  # Normalize
    
    return probs

def _predict_with_keras(model, input_np):
    """
    Predict with Keras/TensorFlow model and return normalized probabilities.
    Handles various output formats: logits, probabilities, single values.
    """
    pred = model.predict(input_np, verbose=0)
    pred = np.asarray(pred)
    
    # Flatten to 1D if needed
    if pred.ndim == 2 and pred.shape[0] == 1:
        probs = pred[0]
    elif pred.ndim == 1:
        probs = pred
    elif pred.ndim == 0:
        # Scalar output
        probs = np.array([pred.item()])
    else:
        # Flatten multi-dimensional output
        probs = pred.reshape(-1)
    
    # Handle logits (values outside [0, 1] range)
    # If single value and outside [0, 1], it's likely a logit
    if probs.size == 1:
        val = float(probs[0])
        if val < 0 or val > 1:
            # Apply sigmoid for binary classification
            prob_fake = 1.0 / (1.0 + np.exp(-val))
            prob_real = 1.0 - prob_fake
            probs = np.array([prob_real, prob_fake], dtype=np.float32)
        else:
            # Already a probability, assume it's fake probability
            prob_fake = val
            prob_real = 1.0 - prob_fake
            probs = np.array([prob_real, prob_fake], dtype=np.float32)
    # If two values, check if they need normalization
    elif probs.size == 2:
        # Check if values are logits (outside [0, 1] or don't sum to ~1)
        if np.any(probs < 0) or np.any(probs > 1) or abs(probs.sum() - 1.0) > 0.1:
            # Apply softmax
            exp = np.exp(probs - np.max(probs))
            probs = exp / (exp.sum() + 1e-8)
        else:
            # Already probabilities, just normalize to ensure they sum to 1
            probs = probs / (probs.sum() + 1e-8)
    else:
        # Multiple outputs: apply softmax
        if np.any(probs < 0) or np.any(probs > 1):
            exp = np.exp(probs - np.max(probs))
            probs = exp / (exp.sum() + 1e-8)
        else:
            probs = probs / (probs.sum() + 1e-8)
    
    # Ensure probabilities are in valid range
    probs = np.clip(probs, 0.0, 1.0)
    probs = probs / (probs.sum() + 1e-8)  # Normalize again to ensure sum = 1
    
    return probs

# -----------------------
# Heatmap generation using Grad-CAM (for Keras) and occlusion (fallback)
# -----------------------
def _generate_gradcam_heatmap_keras(model, img_pil: Image.Image, input_size: int, target_class_idx: int = 1):
    """
    Generate heatmap using Grad-CAM for Keras models.
    Much faster and more accurate than occlusion-based methods.
    """
    if not TF_AVAILABLE:
        return None
    
    try:
        import tensorflow as tf
        from tensorflow import keras
        
        # Preprocess image
        img_resized = ImageOps.fit(img_pil.convert("RGB"), (input_size, input_size), Image.LANCZOS)
        img_array = np.array(img_resized).astype(np.float32)
        
        # Normalize for ImageNet models
        img_array = img_array / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        # Find the last convolutional layer
        last_conv_layer = None
        for layer in reversed(model.layers):
            if isinstance(layer, (keras.layers.Conv2D, keras.layers.SeparableConv2D, 
                                keras.layers.DepthwiseConv2D)):
                last_conv_layer = layer
                break
        
        if last_conv_layer is None:
            # Try to find any layer with spatial dimensions
            for layer in reversed(model.layers):
                if hasattr(layer, 'output_shape') and len(layer.output_shape) == 4:
                    last_conv_layer = layer
                    break
        
        if last_conv_layer is None:
            return None
        
        # Create a model that outputs both the last conv layer and the final predictions
        grad_model = keras.Model(
            inputs=model.input,
            outputs=[last_conv_layer.output, model.output]
        )
        
        # Compute gradients
        with tf.GradientTape() as tape:
            outputs = grad_model(img_array)
            # Handle both tuple and single output
            if isinstance(outputs, (list, tuple)):
                conv_outputs, predictions = outputs[0], outputs[1]
            else:
                # If only one output, try to get predictions from model directly
                conv_outputs = outputs
                predictions = model(img_array)
            
            # Ensure predictions is a tensor
            if not isinstance(predictions, tf.Tensor):
                predictions = tf.convert_to_tensor(predictions)
            
            # Get target class loss
            # Handle different prediction shapes
            if len(predictions.shape) == 0:
                # Scalar output
                loss = predictions
            elif len(predictions.shape) == 1:
                # 1D output - could be single value or 2-class
                if predictions.shape[0] > target_class_idx:
                    loss = predictions[target_class_idx]
                else:
                    loss = predictions[0]
            else:
                # 2D+ output - batch dimension first
                if predictions.shape[-1] > target_class_idx:
                    loss = predictions[:, target_class_idx] if len(predictions.shape) > 1 else predictions[target_class_idx]
                else:
                    loss = predictions[:, 0] if len(predictions.shape) > 1 else predictions[0]
        
        # Get gradients
        grads = tape.gradient(loss, conv_outputs)
        
        # Global average pooling of gradients
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        # Weight the feature maps by gradients
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        
        # Normalize heatmap
        heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
        heatmap = heatmap.numpy()
        
        # Resize to input size (use PIL if cv2 not available)
        try:
            import cv2
            heatmap = cv2.resize(heatmap, (input_size, input_size))
        except ImportError:
            # Fallback to PIL resize
            from PIL import Image as PILImage
            heatmap_pil = PILImage.fromarray((heatmap * 255).astype(np.uint8))
            heatmap_pil = heatmap_pil.resize((input_size, input_size), Image.BILINEAR)
            heatmap = np.array(heatmap_pil).astype(np.float32) / 255.0
        heatmap = np.clip(heatmap, 0, 1)
        
        return heatmap
        
    except Exception as e:
        print(f"[models_interface] Grad-CAM failed: {e}")
        return None

def _overlay_heatmap_on_image(img_pil: Image.Image, heatmap: np.ndarray, alpha: float = 0.5):
    """
    Overlay heatmap on original image with transparency.
    """
    w, h = img_pil.size
    
    # Resize heatmap to original image size
    from PIL import Image as PILImage
    heatmap_resized = PILImage.fromarray((heatmap * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    heatmap_array = np.array(heatmap_resized).astype(np.float32) / 255.0
    
    # Apply colormap
    cmap = plt.get_cmap("jet")
    colored = cmap(heatmap_array)[:, :, :3]
    colored = (colored * 255).astype(np.uint8)
    heatmap_rgb = PILImage.fromarray(colored)
    
    # Blend with original image
    img_rgb = img_pil.convert("RGB")
    blended = PILImage.blend(img_rgb, heatmap_rgb, alpha)
    
    return blended

def _generate_occlusion_heatmap_improved(predict_fn, img_pil: Image.Image, input_size: int, 
                                         target_class_idx: int = 1, patch_size: int = 16, stride: int = 8):
    """
    Improved occlusion-based heatmap generation (faster with better quality).
    """
    w, h = img_pil.size
    img_resized = ImageOps.fit(img_pil.convert("RGB"), (input_size, input_size), Image.LANCZOS)
    base_pred = predict_fn(img_resized)
    base_target = float(base_pred[target_class_idx]) if target_class_idx < len(base_pred) else float(base_pred[0])
    
    # Adaptive patch size based on input size
    ps = max(8, int(patch_size * input_size / 224))
    st = max(4, int(stride * input_size / 224))
    
    heatmap = np.zeros((input_size, input_size), dtype=np.float32)
    counts = np.zeros_like(heatmap)
    
    # Use mean color of image for occlusion
    img_array = np.array(img_resized)
    mean_color = tuple(map(int, img_array.mean(axis=(0, 1))))
    
    # Process in batches for better performance
    for y in range(0, input_size - ps + 1, st):
        for x in range(0, input_size - ps + 1, st):
            occluded = img_resized.copy()
            patch = Image.new("RGB", (ps, ps), mean_color)
            occluded.paste(patch, (x, y))
            pred = predict_fn(occluded)
            target_prob = float(pred[target_class_idx]) if target_class_idx < len(pred) else float(pred[0])
            drop = base_target - target_prob
            heatmap[y:y+ps, x:x+ps] += max(0.0, drop)
            counts[y:y+ps, x:x+ps] += 1.0
    
    # Normalize
    counts[counts == 0] = 1.0
    heatmap = heatmap / counts
    heatmap = np.clip(heatmap, 0.0, None)
    
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    return heatmap

def _generate_heatmap(model, img_pil: Image.Image, input_size: int, framework: str, 
                     target_class_idx: int = 1, predict_fn=None):
    """
    Generate heatmap using the best available method for the model.
    Tries Grad-CAM for Keras models, falls back to occlusion.
    """
    w, h = img_pil.size
    
    # Try Grad-CAM for Keras models
    if framework in ("keras", "h5", "tf", "tfkeras") and TF_AVAILABLE:
        heatmap = _generate_gradcam_heatmap_keras(model, img_pil, input_size, target_class_idx)
        if heatmap is not None:
            # Overlay on original image
            result = _overlay_heatmap_on_image(img_pil, heatmap, alpha=0.5)
            return result
    
    # Fallback to occlusion method
    if predict_fn is None:
        def predict_fn_local(pil_img):
            if framework in ("pt", "pth", "torch", "torchscript"):
                inp_t = _preprocess_for_torch(pil_img, input_size)
                return _predict_with_torch(model, inp_t)
            else:
                inp_np = _preprocess_for_keras(pil_img, input_size)
                return _predict_with_keras(model, inp_np)
        predict_fn = predict_fn_local
    
    heatmap = _generate_occlusion_heatmap_improved(predict_fn, img_pil, input_size, target_class_idx)
    
    # Overlay on original image
    result = _overlay_heatmap_on_image(img_pil, heatmap, alpha=0.5)
    return result

# -----------------------
# Runner for single model
# -----------------------
def _run_single_model(entry: Dict[str, Any], file_path: str, job_id: Optional[int] = None) -> Dict[str, Any]:
    name = entry.get("name", "unknown")
    version = entry.get("version", "1.0")
    input_size = int(entry.get("input_size", 224))
    framework = entry.get("framework", None)
    
    # -------------------------------------------------------------------------
    # ADAPTIVE (SMART ROUTING) LOGIC
    # Step 1: Check metadata first
    # Step 2: If metadata stripped → use visual AI (PatchBasedDetector)
    # Step 3: If metadata exists → use metadata result
    # -------------------------------------------------------------------------
    if framework == "adaptive":
        t0 = time.time()
        try:
            print(f"[models_interface] Running Adaptive Analysis for {name}...")
            
            # Step 1: Run Visual Model (ALWAYS) to get Heatmap
            from .deepfake_model import create_detector, predict
            
            # Load or get cached detector
            cache_key = "DeepVerify:patch_detector"
            with _MODEL_CACHE_LOCK:
                if cache_key in _MODEL_CACHE:
                    detector = _MODEL_CACHE[cache_key]
                else:
                    detector = create_detector()
                    detector.eval()
                    _MODEL_CACHE[cache_key] = detector
            
            # Run visual prediction
            vis_result = predict(detector, file_path, device="cpu")
            detector_label = vis_result["label"]
            
            # Generate Heatmap from Attention Weights
            heatmap_path = "N/A"
            try:
                att_weights = vis_result.get("attention_weights", [])
                if att_weights and len(att_weights) == 4:
                    # Reshape 4 weights into 2x2 grid
                    att_grid = np.array(att_weights).reshape(2, 2).astype(np.float32)
                    
                    # Normalize to 0-1 for heatmap
                    att_min, att_max = att_grid.min(), att_grid.max()
                    if att_max > att_min:
                        att_norm = (att_grid - att_min) / (att_max - att_min)
                    else:
                        att_norm = att_grid # Uniform attention
                        
                    # Overlay
                    img_pil = Image.open(file_path).convert("RGB")
                    heatmap_img = _overlay_heatmap_on_image(img_pil, att_norm, alpha=0.6)
                    
                    # Save
                    fname = f"heatmap_{name}_{int(time.time()*1000)}_{os.getpid()}.png"
                    heatpath = os.path.join(HEATMAP_DIR, fname)
                    heatmap_img.save(heatpath, "PNG", optimize=True)
                    heatmap_path = fname
                    print(f"[models_interface] ✓ Attention heatmap generated: {heatmap_path}")
            except Exception as h_err:
                print(f"[models_interface] Heatmap generation failed: {h_err}")

            # Step 2: Analyze metadata
            if not analyze_image_metadata_sync:
                raise ImportError("metadata_analyzer module not found")
            
            meta_res = analyze_image_metadata_sync(file_path)
            indicators = meta_res.get("indicators", [])
            is_stripped = any(ind.get("type") == "possible_metadata_stripping" for ind in indicators)
            is_ai = meta_res.get("is_ai_generated", False)
            
            # Step 3: Route based on metadata availability
            # FIX: If AI is detected (e.g. C2PA), use it even if EXIF is missing (stripped)
            if is_stripped and not is_ai:
                # Metadata stripped → Use visual AI scores
                print(f"[models_interface] Metadata stripped, using visual analysis score...")
                confidence_real = vis_result["confidence_real"]
                confidence_fake = vis_result["confidence_fake"]
                label = vis_result["label"]
                mode = "visual_ai"
            else:
                # Metadata exists → Use metadata result for SCORE
                print(f"[models_interface] Metadata found, using metadata score...")
                
                if is_ai:
                    confidence_raw = meta_res.get("confidence", 0.0)
                    confidence_fake = max(confidence_raw, 0.6)
                    confidence_real = 1.0 - confidence_fake
                    label = "fake"
                else:
                    # If metadata says authentic, we trust it high
                    confidence_real = 0.95
                    confidence_fake = 0.05
                    label = "real"
                mode = "metadata"
            
            return {
                "name": name,
                "version": version,
                "confidence_real": float(confidence_real),
                "confidence_fake": float(confidence_fake),
                "label": label,
                "time_ms": int((time.time() - t0) * 1000),
                "heatmap_path": heatmap_path,
                "analysis_mode": mode,
            }
                
        except Exception as e:
            print(f"[models_interface] Error in adaptive analysis: {e}")
            import traceback
            traceback.print_exc()
            return {
                "name": name,
                "version": version,
                "confidence_real": 0.5,
                "confidence_fake": 0.5,
                "label": "error",
                "time_ms": 0.0,
                "heatmap_path": "N/A",
            }

    # -------------------------------------------------------------------------
    # METADATA "FAKE MODEL" LOGIC
    # -------------------------------------------------------------------------
    if framework == "metadata":
        try:
            print(f"[models_interface] Running Metadata Analyzer (masked as model)...")
            if not analyze_image_metadata_sync:
                raise ImportError("metadata_analyzer module not found")
                
            meta_res = analyze_image_metadata_sync(file_path)
            
            is_ai = meta_res.get("is_ai_generated", False)
            confidence_raw = meta_res.get("confidence", 0.0)
            
            # Map metadata result to "Real vs Fake" probabilities
            # Indicators check
            indicators = meta_res.get("indicators", [])
            is_stripped = any(ind.get("type") == "possible_metadata_stripping" for ind in indicators)
            
            if is_ai:
                # AI Detected!
                confidence_fake = max(confidence_raw, 0.6) # Ensure at least 60% if flagged as AI
                confidence_real = 1.0 - confidence_fake
                label = "fake"
            elif is_stripped:
                # Stripped metadata -> Leaning real but lower confidence
                confidence_real = 0.55
                confidence_fake = 0.45
                label = "real"
            else:
                # Truly no AI signs found (and had metadata) -> Likely Real
                confidence_real = 0.95
                confidence_fake = 0.05
                label = "real"

            # Fake delay for 10 seconds (User Request)
            print(f"[models_interface] Simulating 10s analysis delay for Native model...")
            time.sleep(10)

            return {
                "name": name,
                "version": version,
                "confidence_real": confidence_real,
                "confidence_fake": confidence_fake,
                "label": label,
                "time_ms": 150.0, # Fake timing
                "heatmap_path": "N/A", # No heatmap for metadata
            }

        except Exception as e:
            traceback.print_exc()
            return {
                "name": name,
                "version": version,
                "confidence_real": 0.5,
                "confidence_fake": 0.5,
                "label": "error",
                "time_ms": 0.0,
                "heatmap_path": "N/A",
            }

    # -------------------------------------------------------------------------
    # TRANSFORMERS LOGIC
    # -------------------------------------------------------------------------
    if framework == "transformers":
        try:
            model = _load_model_entry(entry)
            print(f"[models_interface] Running Hugging Face prediction for {name}...")
            
            # Pipeline accepts path directly
            # Returns list of dicts: [{'label': 'Fake', 'score': 0.99}, {'label': 'Real', 'score': 0.01}]
            results = model(file_path)
            
            # Parse results
            # We need to map labels to Real/Fake confidence
            confidence_real = 0.0
            confidence_fake = 0.0
            
            for res in results:
                lbl = res['label'].lower()
                score = res['score']
                
                if "real" in lbl:
                    confidence_real = score
                elif "fake" in lbl or "deepfake" in lbl:
                    confidence_fake = score
            
            # Normalize if needed (pipeline usually softmaxes them already)
            label = "fake" if confidence_fake > confidence_real else "real"
            
            return {
                "name": name,
                "version": version,
                "confidence_real": confidence_real,
                "confidence_fake": confidence_fake,
                "label": label,
                "time_ms": int((time.time() - t0) * 1000),
                "heatmap_path": "N/A", # Heatmap not implemented for HF pipeline yet
            }
            
        except Exception as e:
            traceback.print_exc()
            return {
                "name": name,
                "version": version,
                "confidence_real": 0.5,
                "confidence_fake": 0.5,
                "label": "error",
                "time_ms": 0.0,
                "heatmap_path": "N/A",
            }

        except Exception as e:
            traceback.print_exc()
            return {
                "name": name,
                "version": version,
                "heatmap_path": "N/A",
            }

    # -------------------------------------------------------------------------
    # PATCH-BASED DETECTOR LOGIC
    # -------------------------------------------------------------------------
    if framework == "patch_detector":
        t0 = time.time()
        try:
            model = _load_model_entry(entry)
            print(f"[models_interface] Running PatchBasedDetector for {name}...")
            
            from .deepfake_model import predict
            result = predict(model, file_path, device="cpu")
            
            return {
                "name": name,
                "version": version,
                "confidence_real": result["confidence_real"],
                "confidence_fake": result["confidence_fake"],
                "label": result["label"],
                "time_ms": int((time.time() - t0) * 1000),
                "heatmap_path": "N/A",
            }
            
        except Exception as e:
            traceback.print_exc()
            return {
                "name": name,
                "version": version,
                "confidence_real": 0.5,
                "confidence_fake": 0.5,
                "label": "error",
                "time_ms": 0.0,
                "heatmap_path": "N/A",
            }
    # -------------------------------------------------------------------------
    # STANDARD MODEL LOGIC
    # -------------------------------------------------------------------------
    try:
        model = _load_model_entry(entry)
    except Exception as e:
        traceback.print_exc()
        return {
            "name": name,
            "version": version,
            "confidence_real": 0.5,
            "confidence_fake": 0.5,
            "label": "error",
            "time_ms": 0.0,
            "heatmap_path": "N/A",
        }

    t0 = time.time()
    
    # Load and validate image
    try:
        img = Image.open(file_path)
        # Ensure image is RGB and has valid dimensions
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Validate image dimensions
        if img.size[0] < 32 or img.size[1] < 32:
            raise ValueError(f"Image too small: {img.size}. Minimum size is 32x32 pixels.")
        
        # Verify image is not corrupted
        img.verify()
        # Reopen after verify (verify closes the image)
        img = Image.open(file_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
    except Exception as e:
        raise RuntimeError(f"Failed to load or validate image: {str(e)}")
    
    try:
        ext = (framework or os.path.splitext(entry.get("path",""))[1].lower()).lstrip(".")
        if ext in ("pt","pth","torch","torchscript"):
            if not TORCH_AVAILABLE:
                raise RuntimeError("Torch not installed on server")
            inp = _preprocess_for_torch(img, input_size)
            probs = _predict_with_torch(model, inp)
        else:
            if not TF_AVAILABLE:
                raise RuntimeError("TensorFlow not installed on server")
            inp_np = _preprocess_for_keras(img, input_size)
            probs = _predict_with_keras(model, inp_np)

        probs = np.asarray(probs).astype(np.float32)
        
        # Normalize probabilities to ensure they sum to 1
        probs = probs / (probs.sum() + 1e-8)
        probs = np.clip(probs, 0.0, 1.0)
        probs = probs / (probs.sum() + 1e-8)  # Normalize again
        
        # Interpret probabilities based on size
        # Check if model has explicit output_format configuration
        output_format = entry.get("output_format", "standard")  # "standard" = [real, fake], "reversed" = [fake, real]
        
        if probs.size >= 2:
            # Two or more values: check output format
            val0, val1 = float(probs[0]), float(probs[1])
            
            if output_format == "reversed":
                # Model outputs [fake, real]
                confidence_real = val1
                confidence_fake = val0
            else:
                # Standard: [real, fake]
                confidence_real = val0
                confidence_fake = val1
            
            # Sanity check: if probabilities are extremely skewed (>95% one way) and we haven't
            # explicitly configured the format, try the alternative interpretation
            # This helps catch models that output in reversed format
            if output_format == "standard" and (confidence_fake > 0.95 or confidence_fake < 0.05):
                # Try reversed interpretation
                confidence_real_alt = val1
                confidence_fake_alt = val0
                # If reversed gives more balanced results, use it
                if 0.1 < confidence_fake_alt < 0.9:
                    print(f"[models_interface] Model '{name}' output appears reversed, using alternative interpretation")
                    confidence_real = confidence_real_alt
                    confidence_fake = confidence_fake_alt
        else:
            # Single value: could be fake probability or real probability
            # Most binary classifiers output fake probability with sigmoid
            val = float(probs[0])
            if val > 0.5:
                # Likely fake probability
                confidence_fake = val
                confidence_real = 1.0 - val
            else:
                # Could be real probability, or low fake probability
                # Assume it's fake probability (common in binary classifiers)
                confidence_fake = val
                confidence_real = 1.0 - val
        
        # Ensure probabilities are valid
        confidence_real = max(0.0, min(1.0, confidence_real))
        confidence_fake = max(0.0, min(1.0, confidence_fake))
        
        # Normalize to ensure they sum to 1
        total = confidence_real + confidence_fake
        if total > 0:
            confidence_real = confidence_real / total
            confidence_fake = confidence_fake / total
        else:
            confidence_real = 0.5
            confidence_fake = 0.5
        
        # Determine label
        label = "fake" if confidence_fake > confidence_real else "real"
        target_idx = 1 if label == "fake" else 0
        
        # Debug output
        print(f"[models_interface] Model '{name}': real={confidence_real:.4f}, fake={confidence_fake:.4f}, label={label}")

        heatmap_path = "N/A"
        try:
            def predict_fn_for_heat(pil_img):
                ext_local = (framework or os.path.splitext(entry.get("path",""))[1].lower()).lstrip(".")
                if ext_local in ("pt","pth","torch","torchscript"):
                    inp_t = _preprocess_for_torch(pil_img, input_size)
                    return _predict_with_torch(model, inp_t)
                else:
                    inp_np_local = _preprocess_for_keras(pil_img, input_size)
                    return _predict_with_keras(model, inp_np_local)

            # Use improved heatmap generation
            ext_local = (framework or os.path.splitext(entry.get("path",""))[1].lower()).lstrip(".")
            heat_img = _generate_heatmap(model, img, input_size, ext_local, 
                                         target_class_idx=target_idx, 
                                         predict_fn=predict_fn_for_heat)
            
            fname = f"heatmap_{name}_{int(time.time()*1000)}_{os.getpid()}.png"
            heatpath = os.path.join(HEATMAP_DIR, fname)
            # Save with optimization to reduce file size
            heat_img.save(heatpath, "PNG", optimize=True)
            # Store just filename for API access (API will prepend HEATMAP_DIR)
            heatmap_path = fname
            print(f"[models_interface] ✓ Heatmap saved: {heatpath} (stored as: {heatmap_path})")
        except Exception as e:
            print(f"[models_interface] ✗ Heatmap generation failed for '{name}': {str(e)}")
            import traceback
            traceback.print_exc()
            heatmap_path = "N/A"

        t1 = time.time()
        time_ms = (t1 - t0) * 1000.0
        return {
            "name": name,
            "version": version,
            "confidence_real": round(float(confidence_real), 6),
            "confidence_fake": round(float(confidence_fake), 6),
            "label": label,
            "time_ms": round(time_ms, 2),
            "heatmap_path": heatmap_path,
        }
    except Exception as e:
        print(f"[models_interface] ✗ Model '{name}' prediction failed: {str(e)}")
        traceback.print_exc()
        return {
            "name": name,
            "version": version,
            "confidence_real": 0.5,
            "confidence_fake": 0.5,
            "label": "error",
            "time_ms": 0.0,
            "heatmap_path": "N/A",
            "error": str(e),  # Include error message for debugging
        }

# -----------------------
# Model availability tracking
# -----------------------
# Track which models have been tested and whether they work
_MODEL_AVAILABILITY: Dict[str, bool] = {}  # model name -> is_available
_MODEL_AVAILABILITY_LOCK = threading.Lock()

def clear_model_cache():
    """Clear model availability and cache - useful when model config changes"""
    global _MODEL_AVAILABILITY, _MODEL_CACHE
    with _MODEL_AVAILABILITY_LOCK:
        _MODEL_AVAILABILITY.clear()
        _MODEL_CACHE.clear()
        print("[models_interface] Model cache cleared")

def _check_model_availability(entry: Dict[str, Any]) -> bool:
    """Check if a model can be loaded. Caches the result."""
    name = entry.get("name", "unknown")
    
    with _MODEL_AVAILABILITY_LOCK:
        if name in _MODEL_AVAILABILITY:
            return _MODEL_AVAILABILITY[name]
        
        # Try to load the model
        try:
            _load_model_entry(entry)
            _MODEL_AVAILABILITY[name] = True
            print(f"[models_interface] ✓ Model '{name}' is available")
            return True
        except Exception as e:
            _MODEL_AVAILABILITY[name] = False
            print(f"[models_interface] ✗ Model '{name}' failed to load: {str(e)}")
            return False

def _get_working_models() -> List[Dict[str, Any]]:
    """Return only models that can be loaded successfully (lazy check)"""
    working = []
    for entry in MODEL_REGISTRY:
        if _check_model_availability(entry):
            working.append(entry)
    return working

def initialize_models():
    """
    Initialize and verify all models at startup.
    This will cache working models and print status.
    Call this at application startup for better error messages.
    """
    print("[models_interface] Initializing models...")
    working = _get_working_models()
    print(f"[models_interface] {len(working)}/{len(MODEL_REGISTRY)} models are available")
    return working

# -----------------------
# Async runner used by tasks.py
# -----------------------
async def run_models_on_image(file_path: str, job_id: Optional[int] = None) -> Dict[str, Any]:
    """Run all working models on an image and return results"""
    print(f"[models_interface] run_models_on_image called for file: {file_path}, job_id: {job_id}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")
    
    working_models = _get_working_models()
    
    if not working_models:
        print("[models_interface] WARNING: No working models available!")
        # Return empty results instead of raising error, so job can complete
        return {
            "models": [],
            "consensus": {
                "decision": "ERROR",
                "score": 0.0,
                "explanation": ["No working models available"]
            }
        }
    
    print(f"[models_interface] Running {len(working_models)} working models")
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(4, len(working_models))) as ex:
        futures = [ex.submit(_run_single_model, entry, file_path, job_id) for entry in working_models]
        for fut in as_completed(futures):
            try:
                r = fut.result()
                # Only include results that are not errors
                if r.get("label") != "error":
                    results.append(r)
                else:
                    print(f"[models_interface] Skipping error result from model: {r.get('name', 'unknown')}")
            except Exception as e:
                traceback.print_exc()
                print(f"[models_interface] Model execution failed: {str(e)}")
                # Skip failed models - don't add error results

    # consensus - only based on working model results
    # consensus - only based on valid DeepVerify result
    try:
        if not results:
            consensus = {
                "decision": "ERROR",
                "score": 0.0,
                "explanation": ["No models were able to process the image"]
            }
        else:
            # STRICT LOGIC (User Request):
            # 1. Find DeepVerify (Master Model)
            # 2. Ignore all others for the "Final Decision", but keep them in 'results' for the UI breakdown.
            
            deepverify = next((r for r in results if r.get("name") == "DeepVerify"), None)
            
            if deepverify:
                # Use DeepVerify's verdict explicitly
                decision = deepverify.get("label", "unknown").upper()
                
                # Get the relevant confidence score based on the label
                if decision == "FAKE":
                    score = deepverify.get("confidence_fake", 0.0)
                else:
                    score = deepverify.get("confidence_real", 0.0)
                
                # Check if it used metadata
                mode = deepverify.get("analysis_mode", "visual")
                explanation = f"Verdict by DeepVerify ({mode} analysis)"
                
            else:
                # Fallback if DeepVerify crashed but others worked (unlikely)
                # Just take the first available result
                fallback = results[0]
                decision = fallback.get("label", "unknown").upper()
                score = fallback.get("confidence_fake", 0.0) if decision == "FAKE" else fallback.get("confidence_real", 0.0)
                explanation = "DeepVerify unavailable, using fallback model"

            consensus = {
                "decision": decision,
                "score": float(score),
                "explanation": [explanation]
            }
    except Exception as e:
        print(f"[models_interface] Error calculating consensus: {str(e)}")
        consensus = {"decision": "PENDING", "score": 0.0, "explanation": []}

    return {"models": results, "consensus": consensus}
