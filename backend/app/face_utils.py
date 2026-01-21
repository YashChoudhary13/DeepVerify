import torch
from facenet_pytorch import MTCNN
from PIL import Image

# Initialize MTCNN for face detection
# keep_all=True: detect multiple faces (we usually pick the biggest)
# device='cpu': safer for background tasks, fast enough for cropping
mtcnn = MTCNN(keep_all=True, device="cpu")

def get_face_boxes(pil_img):
    """
    Detect faces in a PIL image.
    Returns a list of bounding boxes [x1, y1, x2, y2].
    """
    try:
        # Convert to RGB if needed
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
            
        boxes, _ = mtcnn.detect(pil_img)
        if boxes is None:
            return []
        return boxes.astype(int).tolist()
    except Exception as e:
        print(f"Face detection error: {e}")
        return []

def crop_face_region(pil_img, box, margin=0.3):
    """
    Crops the face from the image with some margin/context.
    
    Args:
        pil_img: Source image
        box: [x1, y1, x2, y2]
        margin: Percentage of extra context to add (0.3 = 30%)
    """
    w, h = pil_img.size
    x1, y1, x2, y2 = box

    bw, bh = x2 - x1, y2 - y1
    mx, my = int(bw * margin), int(bh * margin)

    x1 = max(0, x1 - mx)
    y1 = max(0, y1 - my)
    x2 = min(w, x2 + mx)
    y2 = min(h, y2 + my)

    return pil_img.crop((x1, y1, x2, y2))
