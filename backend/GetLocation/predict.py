import argparse
import os
from ultralytics import YOLO

def main():
    # 1. Setup Arguments
    parser = argparse.ArgumentParser(description='YOLOv11 Checkbox Detector')
    
    # --source: Path to the input image (Required)
    parser.add_argument('--source', type=str, required=True, help='Path to the image file to analyze')
    
    # --model: Path to the trained model (Update the default path if needed)
    parser.add_argument('--model', type=str, default='models/best.pt', help='Path to the .pt model file')

    args = parser.parse_args()

    # Check if files exist
    if not os.path.exists(args.model):
        print(f"Error: Model file not found at: {args.model}")
        return
    if not os.path.exists(args.source):
        print(f"Error: Image file not found at: {args.source}")
        return

    # 2. Load Model
    print(f"Loading model: {args.model}")
    model = YOLO(args.model)

    # 3. Run Prediction (Resolution set to 1920)
    print(f"Analyzing image: {args.source}")
    results = model.predict(source=args.source, imgsz=2480, conf=0.01, classes=1, save=True)

    # 4. Print Results (Coordinates)
    print("\n" + "="*30)
    print("Detection Results")
    print("="*30)
    
    found_count = 0
    for result in results:
        for box in result.boxes:
            found_count += 1
            
            # Extract Information
            x1, y1, x2, y2 = box.xyxy[0].tolist() # Top-Left, Bottom-Right Coordinates
            conf = float(box.conf[0])             # Confidence Score
            cls_id = int(box.cls[0])              # Class ID
            class_name = model.names[cls_id]      # Class Name (checked/unchecked)

            # Print Output
            print(f"[{class_name.upper()}] Conf: {conf:.2f}")
            print(f" - Coords: {int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}")
            
    if found_count == 0:
        print("No checkboxes detected.")
    else:
        print("="*30)
        print(f"Total {found_count} objects found")
    
    # Show where the result image is saved (if available)
    if hasattr(result, 'save_dir'):
        print(f"\n Result saved at: {result.save_dir}")

if __name__ == '__main__':
    main()
