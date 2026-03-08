import argparse
import os
from ultralytics import YOLO

def detect_checkboxes(source, model_path='models/best.pt', conf=0.1, classes=1):
    model = YOLO(model_path)
    results = model.predict(source=source, imgsz=2480, conf=conf, save=False, verbose=False)

    detection_data = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf_score = float(box.conf[0])
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            item = {
                "class": class_name,
                "conf": round(conf_score, 2),
                "box": [int(x1), int(y1), int(x2), int(y2)]
            }
            detection_data.append(item)

    return detection_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str, required=True)
    parser.add_argument('--model', type=str, default='models/best.pt')
    parser.add_argument('--conf', type=float, default=0.1)
    args = parser.parse_args()

    try:
        results = detect_checkboxes(args.source, args.model, args.conf)
        
        print(f"Found {len(results)} items:")
        for item in results:
            print(item)
    except Exception as e:
        print(e)
