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

from services.donation_eligibility_service import DonationEligibilityService

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
        # Run YOLO26s model inference
        # The model accepts the PIL Image object directly
        results = yolo_model.yolo_instance(image, conf=settings.YOLO_CONFIDENCE_THRESHOLD)
        
        raw_detections = []
        donatable_detections = []
        rejected_detections = []
        result = results[0]
        boxes = result.boxes

        for box in boxes:
            xyxy = box.xyxy[0].tolist()  # absolute pixel coords: [x1, y1, x2, y2]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]

            x1, y1, x2, y2 = xyxy

            # Normalize label
            normalized_label = DonationEligibilityService.normalize_label(cls_name)
            eligibility_status = DonationEligibilityService.classify_detection(cls_name)
            display_label = DonationEligibilityService.get_display_label(cls_name)
            donation_category = DonationEligibilityService.get_donation_category(cls_name)
            rejection_reason = DonationEligibilityService.get_rejection_reason(cls_name)

            det_id = f"det-{uuid.uuid4().hex[:6]}"
            det_data = {
                "id": det_id,
                "class_id": cls_id,
                "label": display_label,
                "normalized_label": normalized_label,
                "confidence": conf,
                "bbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                },
                "eligibility_status": eligibility_status,
                "donation_category": donation_category,
                "rejection_reason": rejection_reason
            }

            raw_detections.append(det_data)
            if eligibility_status == "DONATABLE":
                donatable_detections.append(det_data)
            else:
                rejected_detections.append(det_data)

        # Group detections by label to calculate quantity and average confidence ONLY for donatable detections
        grouped = {}
        for det in donatable_detections:
            name = det["label"]
            if name not in grouped:
                grouped[name] = {
                    "item_name": name,
                    "category": det["donation_category"],
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
            "raw_detections": raw_detections,
            "donatable_detections": donatable_detections,
            "rejected_detections": rejected_detections,
            "grouped_items": grouped_items,
            # Backward compatibility key
            "detections": raw_detections
        }

    except Exception as e:
        logger.error(f"Error executing YOLO26s model inference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred on the server during object detection."
        )

@router.get("/info", response_model=dict)
async def get_detection_info():
    import os
    status_str = "loaded" if yolo_model.yolo_instance is not None else "unavailable"
    model_name = settings.YOLO_MODEL_PATH if settings.YOLO_MODEL_PATH else settings.YOLO_MODEL_NAME
    model_display_name = os.path.basename(model_name) if model_name else "unknown"
    return {
        "model_name": model_display_name,
        "model_family": "YOLO26",
        "status": status_str
    }
