"""
체크박스 탐지 모듈
GetLocation 폴더의 detect.py를 참고하여 작성
"""
import os
from ultralytics import YOLO

def detect_checkboxes(source, model_path=None, conf=0.1, classes=1):
    """
    이미지에서 체크박스를 탐지하는 함수
    
    Args:
        source: 이미지 파일 경로 또는 이미지 배열
        model_path: YOLO 모델 파일 경로 (기본값: GetLocation/models/best.pt)
        conf: 신뢰도 임계값 (기본값: 0.1)
        classes: 탐지할 클래스 ID (기본값: 1 = checked)
    
    Returns:
        list: 탐지된 체크박스 정보 리스트
        [
            {
                "class": "checked",
                "conf": 0.95,
                "box": [x1, y1, x2, y2]
            },
            ...
        ]
    """
    # 모델 경로 설정 (기본값: GetLocation/models/best.pt)
    if model_path is None:
        # 현재 파일 기준으로 GetLocation 폴더 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'GetLocation', 'models', 'best.pt')
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
    
    # YOLO 모델 로드
    model = YOLO(model_path)
    
    # 예측 실행
    results = model.predict(
        source=source,
        imgsz=2480,
        conf=conf,
        save=False,
        verbose=False
    )
    
    # 탐지 결과 파싱
    detection_data = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf_score = float(box.conf[0])
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            
            # checked 클래스만 필터링 (classes=1)
            if cls_id == classes:
                item = {
                    "class": class_name,
                    "conf": round(conf_score, 2),
                    "box": [int(x1), int(y1), int(x2), int(y2)]
                }
                detection_data.append(item)
    
    return detection_data


def get_checked_checkboxes(source, model_path=None, conf=0.1):
    """
    체크된 체크박스만 반환하는 편의 함수
    
    Args:
        source: 이미지 파일 경로 또는 이미지 배열
        model_path: YOLO 모델 파일 경로
        conf: 신뢰도 임계값
    
    Returns:
        list: 체크된 체크박스 좌표 리스트
        [
            {"x1": 1948, "y1": 416, "x2": 1960, "y2": 427},
            ...
        ]
    """
    detection_data = detect_checkboxes(source, model_path, conf, classes=1)
    
    checkboxes = []
    for item in detection_data:
        if item["class"] == "checked":
            x1, y1, x2, y2 = item["box"]
            checkboxes.append({
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
                "conf": item["conf"]
            })
    
    return checkboxes


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='체크박스 탐지 테스트')
    parser.add_argument('--source', type=str, required=True, help='이미지 파일 경로')
    parser.add_argument('--model', type=str, default=None, help='모델 파일 경로')
    parser.add_argument('--conf', type=float, default=0.1, help='신뢰도 임계값')
    args = parser.parse_args()
    
    try:
        results = detect_checkboxes(args.source, args.model, args.conf)
        
        print(f"Found {len(results)} checked checkboxes:")
        for item in results:
            x1, y1, x2, y2 = item["box"]
            print(f"Found a checkbox! x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}")
    except Exception as e:
        print(f"Error: {e}")

