import io
import uuid
import logging
from PIL import Image
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from config import settings
import yolo_model

# Configure logging
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api/detection", tags=["Object Detection"])

# COCO 80 classes mapping to DonateAI Categories and polished labels
COCO_CLASSES_MAP = {
    # Clothing & Personal
    "backpack": ("Household", "Backpack"),
    "umbrella": ("Household", "Umbrella"),
    "handbag": ("Household", "Handbag"),
    "tie": ("Clothing", "Tie"),
    "suitcase": ("Household", "Suitcase"),
    # Toys & Recreation
    "frisbee": ("Toys", "Frisbee"),
    "skis": ("Toys", "Skis"),
    "snowboard": ("Toys", "Snowboard"),
    "sports ball": ("Toys", "Sports Ball"),
    "kite": ("Toys", "Kite"),
    "baseball bat": ("Toys", "Baseball Bat"),
    "baseball glove": ("Toys", "Baseball Glove"),
    "skateboard": ("Toys", "Skateboard"),
    "surfboard": ("Toys", "Surfboard"),
    "tennis racket": ("Toys", "Tennis Racket"),
    "toy": ("Toys", "Toy"),
    "teddy bear": ("Toys", "Teddy Bear"),
    # Kitchen & Dining
    "bottle": ("Kitchen", "Bottle"),
    "wine glass": ("Kitchen", "Wine Glass"),
    "cup": ("Kitchen", "Cup"),
    "fork": ("Kitchen", "Fork"),
    "knife": ("Kitchen", "Knife"),
    "spoon": ("Kitchen", "Spoon"),
    "bowl": ("Kitchen", "Bowl"),
    # Furniture
    "chair": ("Furniture", "Chair"),
    "couch": ("Furniture", "Couch"),
    "potted plant": ("Household", "Potted Plant"),
    "bed": ("Furniture", "Bed"),
    "dining table": ("Furniture", "Dining Table"),
    "toilet": ("Household", "Toilet"),
    # Electronics
    "tv": ("Electronics", "Television"),
    "laptop": ("Electronics", "Laptop"),
    "mouse": ("Electronics", "Computer Mouse"),
    "remote": ("Electronics", "Remote Control"),
    "keyboard": ("Electronics", "Keyboard"),
    "cell phone": ("Electronics", "Mobile Phone"),
    "microwave": ("Electronics", "Microwave"),
    "oven": ("Kitchen", "Oven"),
    "toaster": ("Electronics", "Toaster"),
    "sink": ("Kitchen", "Sink"),
    "refrigerator": ("Electronics", "Refrigerator"),
    # Household & Utility
    "book": ("Books", "Book"),
    "clock": ("Household", "Clock"),
    "vase": ("Household", "Vase"),
    "scissors": ("Education", "Scissors"),
    "hair drier": ("Electronics", "Hair Drier"),
    "toothbrush": ("Hygiene", "Toothbrush"),
}

@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    # Verify YOLO model is loaded
    if yolo_model.yolo_instance is None:
        # Log the detailed load error privately on the backend (Correction 7)
        logger.error(f"YOLO model requested but unavailable. Error context: {yolo_model.yolo_error}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object detection service is currently unavailable. Please try again later."
        )

    # Validate image file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image format."
        )

    try:
        # Load image bytes
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
    except Exception as e:
        logger.error(f"Failed to decode uploaded image: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process image. The file may be corrupt."
        )

    try:
        # Run YOLOv8 model inference
        # The model accepts the PIL Image object directly
        results = yolo_model.yolo_instance(image, conf=settings.YOLO_CONFIDENCE_THRESHOLD)
        
        detections = []
        raw_detections = []
        result = results[0]
        boxes = result.boxes

        for box in boxes:
            xyxy = box.xyxy[0].tolist()  # absolute pixel coords: [x1, y1, x2, y2]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]

            x1, y1, x2, y2 = xyxy

            # Resolve category and polish label name (preserving exact identity)
            category, item_name = COCO_CLASSES_MAP.get(
                cls_name.lower(), 
                ("Other", cls_name.replace("_", " ").title())
            )

            det_id = f"det-{uuid.uuid4().hex[:6]}"
            raw_detections.append({
                "id": det_id,
                "class_id": cls_id,
                "item_name": item_name,
                "category": category,
                "confidence": conf,
                "bbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
            })

        # Group detections by item_name to calculate quantity and average confidence
        grouped = {}
        for det in raw_detections:
            name = det["item_name"]
            if name not in grouped:
                grouped[name] = {
                    "item_name": name,
                    "category": det["category"],
                    "count": 0,
                    "confidences": []
                }
            grouped[name]["count"] += 1
            grouped[name]["confidences"].append(det["confidence"])

        grouped_items = []
        for name, data in grouped.items():
            avg_conf = sum(data["confidences"]) / len(data["confidences"])
            grouped_items.append({
                "item_name": name,
                "category": data["category"],
                "quantity": data["count"],
                "confidence": avg_conf
            })

        return {
            "image_width": width,
            "image_height": height,
            "detections": raw_detections,
            "grouped_items": grouped_items
        }

    except Exception as e:
        logger.error(f"Error executing YOLOv8 model inference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred on the server during object detection."
        )
