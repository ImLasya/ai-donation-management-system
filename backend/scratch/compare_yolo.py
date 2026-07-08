import sys
import os
import time
from PIL import Image
import io

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def compare_models():
    print("=== YOLOv8s vs YOLO26s COMPILATION BENCHMARK ===")
    
    yolov8_path = "yolov8s.pt"
    yolo26_path = "yolo26s.pt"
    
    # Check model files exist
    yolov8_exists = os.path.exists(yolov8_path)
    yolo26_exists = os.path.exists(yolo26_path)
    
    print(f"yolov8s.pt exists: {yolov8_exists}")
    print(f"yolo26s.pt exists: {yolo26_exists}")
    
    if not (yolov8_exists and yolo26_exists):
        print("Error: Both model files must exist in backend/ to run comparison!")
        return

    # Import ultralytics
    print("\nImporting Ultralytics...")
    from ultralytics import YOLO
    
    # Measure load latency
    print("\n[Loading Models]")
    t0 = time.perf_counter()
    model_v8 = YOLO(yolov8_path)
    t1 = time.perf_counter()
    v8_load_time = t1 - t0
    print(f"YOLOv8s load latency: {v8_load_time:.4f} seconds")
    
    t0 = time.perf_counter()
    model_26 = YOLO(yolo26_path)
    t1 = time.perf_counter()
    v26_load_time = t1 - t0
    print(f"YOLO26s load latency: {v26_load_time:.4f} seconds")
    
    # Create test image (size 640x480)
    # We can create a simple checkerboard patterns image in memory to simulate structured classes
    img = Image.new('RGB', (640, 480), color = 'white')
    # Save to buffer
    img_buf = io.BytesIO()
    img.save(img_buf, format='JPEG')
    img_buf.seek(0)
    test_img = Image.open(img_buf)

    print("\n[Running Inference (Single Image Benchmarking)]")
    # YOLOv8s inference
    t0 = time.perf_counter()
    results_v8 = model_v8(test_img, verbose=False)
    t1 = time.perf_counter()
    v8_inf_time = t1 - t0
    boxes_v8 = results_v8[0].boxes
    print(f"YOLOv8s Inference Latency: {v8_inf_time:.4f} seconds")
    print(f"YOLOv8s Boxes Detected: {len(boxes_v8)}")
    for i, box in enumerate(boxes_v8):
        cls_name = results_v8[0].names[int(box.cls[0])]
        conf = float(box.conf[0])
        print(f"  Box {i+1}: Class='{cls_name}' Conf={conf:.4f}")
        
    # YOLO26s inference
    t0 = time.perf_counter()
    results_26 = model_26(test_img, verbose=False)
    t1 = time.perf_counter()
    v26_inf_time = t1 - t0
    boxes_26 = results_26[0].boxes
    print(f"YOLO26s Inference Latency: {v26_inf_time:.4f} seconds")
    print(f"YOLO26s Boxes Detected: {len(boxes_26)}")
    for i, box in enumerate(boxes_26):
        cls_name = results_26[0].names[int(box.cls[0])]
        conf = float(box.conf[0])
        print(f"  Box {i+1}: Class='{cls_name}' Conf={conf:.4f}")

    print("\n[Accuracy Metrics Statement]")
    print("NOTE: Ground-truth labeled validation dataset is not present in local workspace.")
    print("Therefore, standard validation metrics such as precision, recall, false positive/negative rate,")
    print("mAP50, and mAP50-95 cannot be computed and remain unverified at this stage.")
    print("Future fine-tuning on a labeled donation dataset is recommended for accurate performance stats.")

if __name__ == "__main__":
    compare_models()
