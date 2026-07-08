import sys
import os
import io
from PIL import Image

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from config import settings
import yolo_model

def run_yolo26_tests():
    print("=== STARTING YOLO26s DETECTION SERVICE UNIT TESTS ===")
    
    # Instantiate client and run tests inside context to trigger startup events
    with TestClient(app) as client:
        # 1. Test model loaded successfully
        print("\n[Test 1] Verifying YOLO model is loaded globally...")
        assert yolo_model.yolo_instance is not None, "YOLO model is not loaded! Check main startup logs."
        model_name = settings.YOLO_MODEL_PATH if settings.YOLO_MODEL_PATH else settings.YOLO_MODEL_NAME
        print(f"Success! Model instance is active, configured model: {model_name}")
        assert settings.YOLO_MODEL_NAME == "yolo26s.pt", f"Expected settings.YOLO_MODEL_NAME to be yolo26s.pt, got {settings.YOLO_MODEL_NAME}"

        # 2. Test info health endpoint
        print("\n[Test 2] Testing health info endpoint /api/detection/info...")
        res_info = client.get("/api/detection/info")
        assert res_info.status_code == 200, f"Expected 200, got {res_info.status_code}"
        info_data = res_info.json()
        print(f"Info endpoint response: {info_data}")
        assert info_data["model_family"] == "YOLO26", f"Expected YOLO26 family, got {info_data['model_family']}"
        assert info_data["status"] == "loaded", "Model should be loaded"
        assert info_data["model_name"] == "yolo26s.pt", f"Expected yolo26s.pt, got {info_data['model_name']}"

        # 3. Test HTTP 503 behavior when model is not available
        print("\n[Test 3] Testing HTTP 503 behavior if model is unavailable...")
        # Temporarily set yolo_instance to None
        orig_instance = yolo_model.yolo_instance
        try:
            yolo_model.yolo_instance = None
            # Create a small dummy image in memory
            img = Image.new('RGB', (100, 100), color = 'red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            res_503 = client.post("/api/detection/analyze", files={"file": ("test.jpg", img_bytes, "image/jpeg")})
            print(f"Unavailable endpoint response code: {res_503.status_code}")
            assert res_503.status_code == 503, f"Expected 503, got {res_503.status_code}"
        finally:
            # Restore instance
            yolo_model.yolo_instance = orig_instance
            
        # 4. Test image upload inference works with real model
        print("\n[Test 4] Testing upload of a real test image...")
        # Create a small dummy image in memory
        img = Image.new('RGB', (640, 480), color = 'blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        res_analyze = client.post("/api/detection/analyze", files={"file": ("test.jpg", img_bytes, "image/jpeg")})
        assert res_analyze.status_code == 200, f"Expected 200, got {res_analyze.status_code}: {res_analyze.text}"
        data = res_analyze.json()
        print("Success! Inference response keys parsed:")
        print(data.keys())
        
        # 5. Verify response contract keys and shapes
        print("\n[Test 5] Verifying API response contract...")
        assert "image_width" in data, "Missing image_width key"
        assert "image_height" in data, "Missing image_height key"
        assert "detections" in data, "Missing detections key"
        assert "grouped_items" in data, "Missing grouped_items key"
        
        assert data["image_width"] == 640
        assert data["image_height"] == 480
        assert isinstance(data["detections"], list)
        assert isinstance(data["grouped_items"], list)
        print("Response contract keys validated successfully.")
        
        # 6. Verify webcam Blob / multipart formats (PNG, JPEG, corrupt)
        print("\n[Test 6] Testing PNG format upload...")
        img_png = Image.new('RGB', (320, 240), color = 'green')
        png_bytes = io.BytesIO()
        img_png.save(png_bytes, format='PNG')
        png_bytes.seek(0)
        res_png = client.post("/api/detection/analyze", files={"file": ("webcam.png", png_bytes, "image/png")})
        assert res_png.status_code == 200, f"Expected 200 for PNG, got {res_png.status_code}"
        
        print("\n[Test 7] Testing empty / corrupt image reject behavior...")
        corrupt_bytes = io.BytesIO(b"corrupt image data string here")
        res_corrupt = client.post("/api/detection/analyze", files={"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")})
        print(f"Corrupt upload response code: {res_corrupt.status_code} (Expected: 400)")
        assert res_corrupt.status_code == 400
        
        print("\n[Test 8] Testing non-image file type rejection...")
        text_bytes = io.BytesIO(b"hello world")
        res_txt = client.post("/api/detection/analyze", files={"file": ("test.txt", text_bytes, "text/plain")})
        print(f"Non-image upload response code: {res_txt.status_code} (Expected: 400)")
        assert res_txt.status_code == 400

        # 7. Verify quantity grouping, confidence ranges, bounding boxes
        print("\n[Test 9] Verifying coordinate bounding box boundaries and confidence properties...")
        if len(data["detections"]) > 0:
            for det in data["detections"]:
                # Confidence in [0.0, 1.0]
                assert 0.0 <= det["confidence"] <= 1.0, f"Confidence {det['confidence']} out of range!"
                
                # Coordinates within image boundaries
                bbox = det["bbox"]
                assert 0.0 <= bbox["x1"] <= 640
                assert 0.0 <= bbox["x2"] <= 640
                assert 0.0 <= bbox["y1"] <= 480
                assert 0.0 <= bbox["y2"] <= 480
                
                print(f"Checked box: {det['item_name']} ({det['category']}) conf={det['confidence']:.2f}")
        else:
            print("Note: No objects detected in dummy solid-color test image (this is expected for standard models).")
            
        print("\n=== ALL YOLO26s UNIT TESTS PASSED ===")

if __name__ == "__main__":
    run_yolo26_tests()
