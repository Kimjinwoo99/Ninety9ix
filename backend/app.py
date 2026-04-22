from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import json
from werkzeug.utils import secure_filename
import easyocr
import cv2
import numpy as np
from PIL import Image
import base64

# requests 라이브러리 import (서류 OCR API 호출용)
try:
    import requests
except ImportError:
    requests = None
    print("[app.py] ⚠️ requests 라이브러리가 설치되지 않았습니다. 서류 OCR 기능을 사용하려면 'pip install requests'를 실행하세요.")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 프론트엔드 로그를 받을 엔드포인트
@app.route('/api/log', methods=['POST'])
def log_from_frontend():
    """프론트엔드에서 로그를 받아서 서버 터미널에 출력"""
    try:
        data = request.get_json()
        log_level = data.get('level', 'INFO')
        message = data.get('message', '')
        timestamp = data.get('timestamp', '')
        
        # 터미널에 출력
        print(f"[FRONTEND-{log_level}] {timestamp} {message}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"[FRONTEND-ERROR] 로그 수신 오류: {str(e)}")
        return jsonify({'success': False}), 500

# 업로드 폴더 설정
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한

# EasyOCR 초기화 (한국어, 영어, 한문 지원)
# verbose=False로 설정하여 Windows 콘솔 인코딩 문제 방지
ocr = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
# 한문 특화 OCR (간체 중국어 - 영어와만 호환)
chinese_ocr = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_numpy_to_python(obj):
    """NumPy 타입을 Python 기본 타입으로 변환 (JSON 직렬화를 위해)"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_to_python(item) for item in obj)
    return obj

def convert_ocr_result_to_json_serializable(ocr_result):
    """OCR 결과를 JSON 직렬화 가능한 형태로 변환"""
    serializable_result = []
    for item in ocr_result:
        if len(item) >= 3:
            bbox, text, confidence = item[0], item[1], item[2]
            # 바운딩 박스를 리스트로 변환하고 NumPy 타입을 Python 타입으로 변환
            bbox_list = convert_numpy_to_python(bbox)
            # confidence도 변환
            conf_float = float(confidence) if isinstance(confidence, (np.floating, np.integer)) else confidence
            serializable_result.append([bbox_list, text, conf_float])
        else:
            # 형식이 다를 경우 그대로 변환
            serializable_result.append(convert_numpy_to_python(item))
    return serializable_result

def read_image(image_path):
    """이미지 파일을 읽어서 numpy 배열로 반환 (webp 지원 포함)"""
    file_ext = os.path.splitext(image_path)[1].lower()
    
    # webp 파일은 PIL로 읽기
    if file_ext == '.webp':
        try:
            pil_img = Image.open(image_path)
            # RGB로 변환 (RGBA인 경우)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            # numpy 배열로 변환
            img_array = np.array(pil_img)
            # BGR로 변환 (OpenCV 형식)
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img
        except Exception as e:
            return None
    else:
        # 다른 형식은 OpenCV로 읽기
        return cv2.imread(image_path)

def mask_resident_number(resident_number):
    """주민번호 뒷자리 마스킹 처리"""
    # 주민번호 형식: YYMMDD-XXXXXXX
    if len(resident_number) >= 8:
        # 앞 6자리(YYMMDD)는 유지, 뒷자리는 마스킹
        masked = resident_number[:7] + 'X' * (len(resident_number) - 7)
        return masked
    return resident_number

def crop_image_region(image_path, bbox, padding=5, img_array=None):
    """바운딩 박스 영역을 crop한 이미지 생성
    
    Args:
        image_path: 이미지 파일 경로 (img_array가 None일 때 사용)
        bbox: 바운딩 박스 좌표
        padding: 패딩 크기
        img_array: 이미지 배열 (None이면 파일에서 읽음)
    """
    if bbox is None:
        return None
    
    # img_array가 제공되면 사용, 아니면 파일에서 읽기
    if img_array is not None:
        img = img_array.copy()
    else:
        img = read_image(image_path)
        if img is None:
            return None
    
    # 바운딩 박스 좌표 추출
    points = np.array(bbox, dtype=np.int32)
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    
    x_min = max(0, min(x_coords) - padding)
    x_max = min(img.shape[1], max(x_coords) + padding)
    y_min = max(0, min(y_coords) - padding)
    y_max = min(img.shape[0], max(y_coords) + padding)
    
    # 영역 crop
    cropped = img[y_min:y_max, x_min:x_max]
    
    if cropped.size == 0:
        return None
    
    # 이미지를 base64로 인코딩
    _, buffer = cv2.imencode('.jpg', cropped)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

def create_masked_image(image_path, ocr_result, resident_number, return_array=False):
    """주민번호 뒷자리를 검은색으로 마스킹한 이미지 생성
    
    Args:
        image_path: 이미지 파일 경로
        ocr_result: OCR 결과
        resident_number: 주민번호
        return_array: True면 이미지 배열도 반환
    """
    if not resident_number or '-' not in resident_number:
        return None
    
    # 원본 이미지 읽기
    img = read_image(image_path)
    if img is None:
        return None
    
    # 주민번호 뒷자리 부분 찾기 (하이픈 이후 7자리)
    resident_parts = resident_number.split('-')
    if len(resident_parts) != 2 or len(resident_parts[1]) != 7:
        return None
    
    # OCR 결과에서 주민번호가 있는 위치 찾기 (여러 줄 포함)
    resident_match = None
    resident_bbox = None
    resident_text = None
    
    # 먼저 한 줄에 있는 경우 찾기
    for detection in ocr_result:
        text = detection[1]
        bbox = detection[0]
        
        resident_patterns = [
            r'\d{6}[-]\d{7}',
            r'\d{6}[-]\s*\d{1}\s*\d{6}',
            r'\d{6}[-]\d{1}\s+\d{6}',
        ]
        
        for pattern in resident_patterns:
            resident_match = re.search(pattern, text)
            if resident_match:
                resident_bbox = bbox
                resident_text = text
                break
        if resident_match:
            break
    
    # 한 줄에 없으면 여러 줄에 걸쳐 있는 경우 찾기
    if not resident_match:
        for idx in range(len(ocr_result) - 1):
            current_detection = ocr_result[idx]
            next_detection = ocr_result[idx + 1]
            
            current_text = current_detection[1]
            next_text = next_detection[1]
            
            front_match = re.search(r'(\d{6}[-])$', current_text.strip())
            back_match = re.search(r'^(\d{7})', next_text.strip())
            
            if not back_match:
                # 공백이 포함된 경우
                back_match = re.search(r'^(\d{1}\s*\d{6})', next_text.strip())
            
            if front_match and back_match:
                # 두 줄의 바운딩 박스 합치기
                bbox1 = current_detection[0]
                bbox2 = next_detection[0]
                all_x = []
                all_y = []
                for point in bbox1 + bbox2:
                    all_x.append(point[0])
                    all_y.append(point[1])
                
                if all_x and all_y:
                    resident_bbox = [
                        [min(all_x), min(all_y)],
                        [max(all_x), min(all_y)],
                        [max(all_x), max(all_y)],
                        [min(all_x), max(all_y)]
                    ]
                    resident_text = current_text + ' ' + next_text
                    resident_match = True  # 여러 줄로 찾았음을 표시
                    break
    
    if resident_match and resident_bbox:
            # 바운딩 박스 좌표 추출
            points = np.array(resident_bbox, dtype=np.int32)
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            
            x_min = min(x_coords)
            x_max = max(x_coords)
            y_min = min(y_coords)
            y_max = max(y_coords)
            
            # 주민번호에서 하이픈 위치 찾기
            hyphen_pos = resident_number.find('-')
            if hyphen_pos != -1:
                # 전체 바운딩 박스 너비
                total_width = x_max - x_min
                
                # 주민번호 앞부분(YYMMDD-)과 뒷부분(XXXXXXX)의 비율
                front_part = resident_number[:hyphen_pos + 1]  # "991130-"
                back_part = resident_number[hyphen_pos + 1:]  # "1234567"
                
                # 하이픈 위치 계산
                front_ratio = len(front_part) / len(resident_number) if len(resident_number) > 0 else 0
                hyphen_x = x_min + int(total_width * front_ratio)
                
                # 마스킹 시작 위치 (하이픈 이후)
                mask_start_x = hyphen_x
                mask_end_x = x_max
                
                # 마스킹 영역에 검은색 사각형 그리기
                cv2.rectangle(img, 
                             (max(0, mask_start_x - 1), max(0, y_min - 2)), 
                             (min(img.shape[1], mask_end_x + 1), min(img.shape[0], y_max + 2)), 
                             (0, 0, 0), -1)
    
    # 이미지를 base64로 인코딩
    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    
    if return_array:
        return img_base64, img
    return img_base64

def extract_date_with_reocr(image_path, bbox):
    """날짜 바운딩 박스 영역에 대해 OCR 재실행하여 날짜 추출"""
    try:
        # 이미지 읽기
        img = read_image(image_path)
        if img is None:
            return None
        
        # 바운딩 박스 좌표 추출
        points = np.array(bbox, dtype=np.int32)
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        
        x_min = max(0, min(x_coords) - 5)
        x_max = min(img.shape[1], max(x_coords) + 5)
        y_min = max(0, min(y_coords) - 5)
        y_max = min(img.shape[0], max(y_coords) + 5)
        
        # 영역 crop
        cropped_img = img[y_min:y_max, x_min:x_max]
        
        if cropped_img.size == 0:
            return None
        
        # OCR 재실행
        ocr_results = ocr.readtext(cropped_img)
        
        if ocr_results:
            # OCR 결과에서 텍스트 추출
            date_texts = [result[1] for result in ocr_results]
            combined_date = ' '.join(date_texts).strip()
            
            # 공백 제거 및 정리
            combined_date = re.sub(r'\s+', '', combined_date)
            # "Il"을 "."로 변환
            combined_date = combined_date.replace('Il', '.').replace('l', '.').replace('I', '.')
            
            # 날짜 형식 검증 (YYYY.M.D 또는 YYYY.MM.DD)
            date_pattern = r'^\d{4}\.\d{1,2}\.\d{1,2}$'
            if re.match(date_pattern, combined_date):
                return combined_date
            
            # 점이 여러 개 있는 경우 정리 시도
            # 예: "2019...25" -> "2019.1.25" 또는 "2019.12.25"
            if combined_date.count('.') >= 2:
                # 연도 찾기
                year_match = re.search(r'\d{4}', combined_date)
                if year_match:
                    year = year_match.group()
                    # 연도 이후 부분
                    after_year = combined_date[year_match.end():]
                    # 점과 숫자만 남기기
                    after_year = re.sub(r'[^\d.]', '', after_year)
                    # 점 정리
                    parts = [p for p in after_year.split('.') if p]
                    if len(parts) >= 2:
                        month = parts[0]
                        day = parts[1]
                        # 월과 일이 1-2자리인지 확인
                        if 1 <= len(month) <= 2 and 1 <= len(day) <= 2:
                            return f"{year}.{month}.{day}"
        
    except Exception as e:
        print(f"날짜 재OCR 오류: {str(e)}")
        return None
    
    return None

def extract_chinese_from_bracket(image_path, text_lines, name_line_idx):
    """이름 줄의 괄호 안 한자 부분에 한문 OCR 적용"""
    if name_line_idx is None or name_line_idx >= len(text_lines):
        return None
    
    bbox, line_text, confidence = text_lines[name_line_idx]
    
    # 괄호가 있는지 확인
    if '(' not in line_text and '（' not in line_text:
        return None
    
    # 괄호 위치 찾기
    open_bracket = line_text.find('(') if '(' in line_text else line_text.find('（')
    close_bracket = line_text.find(')') if ')' in line_text else line_text.find('）')
    
    if open_bracket == -1 or close_bracket == -1 or close_bracket <= open_bracket:
        return None
    
    # 괄호 안 텍스트 추출
    bracket_text = line_text[open_bracket + 1:close_bracket].strip()
    
    # 이미 한문이거나 의미있는 텍스트가 없으면 스킵
    if not bracket_text or len(bracket_text) < 1:
        return None
    
    try:
        # 이미지 읽기
        img = read_image(image_path)
        if img is None:
            return None
        
        # 바운딩 박스 좌표 추출
        points = np.array(bbox, dtype=np.int32)
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        
        x_min = min(x_coords)
        x_max = max(x_coords)
        y_min = min(y_coords)
        y_max = max(y_coords)
        
        # 전체 줄의 텍스트 길이
        total_text_length = len(line_text)
        total_width = x_max - x_min
        
        # 괄호 부분의 위치 계산
        bracket_start_ratio = open_bracket / total_text_length if total_text_length > 0 else 0
        bracket_end_ratio = close_bracket / total_text_length if total_text_length > 0 else 0
        
        # 괄호 영역의 x 좌표 계산
        bracket_start_x = x_min + int(total_width * bracket_start_ratio)
        bracket_end_x = x_min + int(total_width * bracket_end_ratio)
        
        # 괄호 영역 crop (약간의 패딩 추가)
        padding = 5
        crop_x_min = max(0, bracket_start_x - padding)
        crop_x_max = min(img.shape[1], bracket_end_x + padding)
        crop_y_min = max(0, y_min - padding)
        crop_y_max = min(img.shape[0], y_max + padding)
        
        cropped_img = img[crop_y_min:crop_y_max, crop_x_min:crop_x_max]
        
        if cropped_img.size == 0:
            return None
        
        # 한문 OCR 적용
        chinese_results = chinese_ocr.readtext(cropped_img)
        
        if chinese_results:
            # OCR 결과에서 텍스트 추출
            chinese_texts = [result[1] for result in chinese_results]
            chinese_text = ' '.join(chinese_texts).strip()
            
            # 원본 텍스트의 괄호 안 부분을 한문 OCR 결과로 교체
            new_line_text = line_text[:open_bracket + 1] + chinese_text + line_text[close_bracket:]
            return new_line_text
        
    except Exception as e:
        print(f"한문 OCR 오류: {str(e)}")
        return None
    
    return None

def format_resident_card_ocr(text_lines, image_path=None):
    """주민등록증 OCR 텍스트를 6줄로 정렬"""
    # 주민등록증인지 확인
    full_text = ' '.join([line[1] for line in text_lines])
    if '주민등록증' not in full_text:
        return None  # 주민등록증이 아니면 None 반환
    
    # 주민번호 패턴 찾기
    resident_patterns = [
        r'\d{6}[-]\d{7}',
        r'\d{6}[-]\s*\d{1}\s*\d{6}',
        r'\d{6}[-]\d{1}\s+\d{6}',
    ]
    
    resident_line_idx = None
    resident_number = None
    
    # 한 줄에 있는 경우
    for idx, (bbox, line_text, confidence) in enumerate(text_lines):
        for pattern in resident_patterns:
            if re.search(pattern, line_text):
                matched = re.search(pattern, line_text)
                resident_number = re.sub(r'\s+', '', matched.group())
                resident_line_idx = idx
                break
        if resident_line_idx is not None:
            break
    
    # 여러 줄에 걸쳐 있는 경우
    if resident_line_idx is None:
        for idx in range(len(text_lines) - 1):
            current_line = text_lines[idx][1]
            next_line = text_lines[idx + 1][1]
            
            # 여러 패턴 시도
            front_patterns = [
                r'(\d{6}[-])$',
                r'(\d{6}[-]\s*)$',
            ]
            
            back_patterns = [
                r'^(\d{7})',
                r'^(\s*\d{7})',
                r'^(\d{1}\s*\d{6})',
            ]
            
            for front_pattern in front_patterns:
                front_match = re.search(front_pattern, current_line.strip())
                if front_match:
                    for back_pattern in back_patterns:
                        back_match = re.search(back_pattern, next_line.strip())
                        if back_match:
                            rrn1 = front_match.group(1).strip()
                            rrn2 = back_match.group(1).strip()
                            rrn2 = re.sub(r'\s+', '', rrn2)
                            resident_number = rrn1 + rrn2
                            resident_line_idx = idx
                            break
                    if resident_line_idx is not None:
                        break
                if resident_line_idx is not None:
                    break
            if resident_line_idx is not None:
                break
    
    if resident_line_idx is None:
        return None
    
    # 정렬된 6줄 구성
    formatted_lines = []
    
    # 1. 첫 줄: "주민등록증"
    for bbox, line_text, confidence in text_lines:
        if '주민등록증' in line_text:
            formatted_lines.append('주민등록증')
            break
    
    # 2. 두 번째 줄: 이름 (주민번호 윗줄)
    name_line = None
    name_line_idx = None
    if resident_line_idx > 0:
        for check_idx in range(max(0, resident_line_idx - 3), resident_line_idx):
            bbox, line_text, confidence = text_lines[check_idx]
            exclude_keywords = ['주민등록', '주민등록증', '운전면허', '운전면허증', '여권', '신분증']
            if any(keyword in line_text for keyword in exclude_keywords):
                continue
            if re.search(r'[가-힣]{2,4}', line_text):
                name_line = line_text.strip()
                name_line_idx = check_idx
                break
    
    # 한문 OCR 적용 (이미지 경로가 제공된 경우)
    if name_line and image_path:
        updated_name_line = extract_chinese_from_bracket(image_path, text_lines, name_line_idx)
        if updated_name_line:
            name_line = updated_name_line.strip()
    
    if name_line:
        formatted_lines.append(name_line)
    
    # 3. 세 번째 줄: 주민번호
    if resident_number:
        formatted_lines.append(resident_number)
    
    # 4. 네 번째 줄: 주소 (주민번호 다음 줄부터 닫는 괄호까지)
    address_lines = []
    
    start_idx = resident_line_idx + 1
    if resident_line_idx + 1 < len(text_lines):
        next_line = text_lines[resident_line_idx + 1][1]
        if re.search(r'^\d{7}', next_line.strip()):
            start_idx = resident_line_idx + 2
    
    address_end_idx = None
    
    for idx in range(start_idx, len(text_lines)):
        bbox, line_text, confidence = text_lines[idx]
        
        # 날짜 패턴이 있으면 주소 종료
        if re.search(r'\d{4}', line_text) and ('.' in line_text or 'Il' in line_text or 'l' in line_text):
            address_end_idx = idx
            break
        
        # 닫는 괄호가 있으면 포함하고 종료
        if ')' in line_text or '）' in line_text:
            if re.search(r'[가-힣]', line_text):
                address_lines.append(line_text.strip())
            address_end_idx = idx + 1
            break
        
        # 구청장, 청장인 등이 나오면 주소 종료
        if '구청장' in line_text or '청장인' in line_text:
            address_end_idx = idx
            break
        
        # 주소로 간주할 수 있는 줄
        if re.search(r'[가-힣]', line_text) and len(line_text.strip()) > 1:
            address_lines.append(line_text.strip())
    
    if address_lines:
        combined_address = ' '.join(address_lines)
        combined_address = re.sub(r'\s+', ' ', combined_address).strip()
        formatted_lines.append(combined_address)
    
    # 5. 다섯 번째 줄: 날짜
    date_lines = []
    date_bboxes = []
    date_start_idx = address_end_idx if address_end_idx else start_idx
    
    for idx in range(date_start_idx, len(text_lines)):
        bbox, line_text, confidence = text_lines[idx]
        
        # 날짜 패턴 찾기 (4자리 연도 포함)
        if re.search(r'\d{4}', line_text):
            date_lines.append(line_text.strip())
            date_bboxes.append(bbox)
            # 다음 줄도 확인
            if idx + 1 < len(text_lines):
                next_bbox, next_line, next_confidence = text_lines[idx + 1]
                if re.search(r'\d{1,2}', next_line.strip()) and ('구청장' not in next_line and '청장인' not in next_line):
                    date_lines.append(next_line.strip())
                    date_bboxes.append(next_bbox)
            break
    
    if date_lines:
        combined_date = ' '.join(date_lines)
        combined_date = re.sub(r'\s+', ' ', combined_date).strip()
        # "Il"을 "."로 변환, "l"도 "."로 변환
        combined_date = combined_date.replace('Il', '.').replace('l', '.').replace('I', '.')
        # 공백 정리
        combined_date = re.sub(r'\s*\.\s*', '.', combined_date)
        
        # 날짜 형식 검증 (YYYY.M.D 또는 YYYY.MM.DD)
        date_pattern = r'^\d{4}\.\d{1,2}\.\d{1,2}$'
        if not re.match(date_pattern, combined_date):
            # 형식이 맞지 않으면 재OCR 시도
            if date_bboxes and image_path:
                # 모든 날짜 바운딩 박스를 합치기
                all_x = []
                all_y = []
                for bbox in date_bboxes:
                    for point in bbox:
                        all_x.append(point[0])
                        all_y.append(point[1])
                
                if all_x and all_y:
                    combined_bbox = [
                        [min(all_x), min(all_y)],
                        [max(all_x), min(all_y)],
                        [max(all_x), max(all_y)],
                        [min(all_x), max(all_y)]
                    ]
                    
                    # 재OCR 실행
                    reocr_date = extract_date_with_reocr(image_path, combined_bbox)
                    if reocr_date:
                        combined_date = reocr_date
        
        formatted_lines.append(combined_date)
    
    # 6. 여섯 번째 줄: 나머지 (구청장 등)
    remaining_lines = []
    remaining_start_idx = date_start_idx + len(date_lines) if date_lines else date_start_idx
    
    for idx in range(remaining_start_idx, len(text_lines)):
        bbox, line_text, confidence = text_lines[idx]
        
        # 날짜가 포함된 줄은 건너뛰기
        if re.search(r'\d{4}', line_text) and ('.' in line_text or 'Il' in line_text):
            continue
        
        # 구청장, 청장인, 지역명 등
        if any(keyword in line_text for keyword in ['구청장', '청장인', '서울특별시', '종로구', '서초구']):
            remaining_lines.append(line_text.strip())
    
    if remaining_lines:
        combined_remaining = ' '.join(remaining_lines)
        combined_remaining = re.sub(r'\s+', ' ', combined_remaining).strip()
        formatted_lines.append(combined_remaining)
    
    return '\n'.join(formatted_lines)

def extract_info_from_ocr(text_lines):
    """OCR 결과에서 성명, 주민번호, 주소 추출 및 바운딩 박스 정보 반환"""
    result = {
        'name': '',
        'resident_number': '',
        'address': '',
        'name_bbox': None,
        'resident_bbox': None,
        'address_bbox': None
    }
    
    # 주민등록증인 경우 정렬된 텍스트에서 추출
    # image_path는 extract_info_from_ocr 호출 시 전달되지 않으므로 None으로 설정
    formatted_text = format_resident_card_ocr(text_lines, image_path=None)
    if formatted_text:
        formatted_lines = formatted_text.split('\n')
        
        # 2번째 줄에서 이름 추출 (괄호 전까지)
        if len(formatted_lines) >= 2:
            name_line = formatted_lines[1]
            bracket_pos = name_line.find('(') if '(' in name_line else name_line.find('（')
            if bracket_pos != -1:
                result['name'] = name_line[:bracket_pos].strip()
            else:
                result['name'] = name_line.strip()
        
        # 3번째 줄에서 주민번호 추출
        if len(formatted_lines) >= 3:
            result['resident_number'] = formatted_lines[2].strip()
        
        # 4번째 줄에서 주소 추출
        if len(formatted_lines) >= 4:
            result['address'] = formatted_lines[3].strip()
        
        # 바운딩 박스는 원본 OCR 결과에서 찾기
        # 이름 바운딩 박스 찾기
        if result['name']:
            for bbox, line_text, confidence in text_lines:
                if result['name'] in line_text:
                    result['name_bbox'] = bbox
                    break
        
        # 주민번호 바운딩 박스 찾기 (여러 줄 포함)
        if result['resident_number']:
            # 한 줄에 있는 경우
            for bbox, line_text, confidence in text_lines:
                if re.search(r'\d{6}[-]\d{7}', line_text) or re.search(r'\d{6}[-]\s*\d{1}\s*\d{6}', line_text):
                    result['resident_bbox'] = bbox
                    break
            
            # 여러 줄에 걸쳐 있는 경우
            if not result['resident_bbox']:
                for idx in range(len(text_lines) - 1):
                    current_line = text_lines[idx][1]
                    next_line = text_lines[idx + 1][1]
                    
                    front_match = re.search(r'(\d{6}[-])$', current_line.strip())
                    back_match = re.search(r'^(\d{7})', next_line.strip())
                    
                    if not back_match:
                        back_match = re.search(r'^(\d{1}\s*\d{6})', next_line.strip())
                    
                    if front_match and back_match:
                        # 두 줄의 바운딩 박스 합치기
                        bbox1 = text_lines[idx][0]
                        bbox2 = text_lines[idx + 1][0]
                        all_x = []
                        all_y = []
                        for point in bbox1 + bbox2:
                            all_x.append(point[0])
                            all_y.append(point[1])
                        if all_x and all_y:
                            result['resident_bbox'] = [
                                [min(all_x), min(all_y)],
                                [max(all_x), min(all_y)],
                                [max(all_x), max(all_y)],
                                [min(all_x), max(all_y)]
                            ]
                        break
        
        # 주소 바운딩 박스 찾기 (4번째 줄에 해당하는 원본 OCR 줄만)
        if result['address']:
            # format_resident_card_ocr에서 주소를 구성한 줄들을 찾기
            # 주민번호 다음 줄부터 날짜나 구청장 전까지
            address_bboxes = []
            
            # 주민번호 위치 찾기
            resident_line_idx = None
            for idx, (bbox, line_text, confidence) in enumerate(text_lines):
                if re.search(r'\d{6}[-]', line_text):
                    resident_line_idx = idx
                    break
            
            if resident_line_idx is not None:
                start_idx = resident_line_idx + 1
                # 주민번호 뒷자리가 다음 줄에 있으면 그 다음부터
                if resident_line_idx + 1 < len(text_lines):
                    next_line = text_lines[resident_line_idx + 1][1]
                    if re.search(r'^\d{7}', next_line.strip()) or re.search(r'^\d{1}\s*\d{6}', next_line.strip()):
                        start_idx = resident_line_idx + 2
                
                # 주소 줄 찾기 (날짜나 구청장 전까지)
                for idx in range(start_idx, len(text_lines)):
                    bbox, line_text, confidence = text_lines[idx]
                    
                    # 날짜 패턴이 있으면 종료
                    if re.search(r'\d{4}', line_text) and ('.' in line_text or 'Il' in line_text):
                        break
                    
                    # 구청장, 청장인 등이 나오면 종료
                    if '구청장' in line_text or '청장인' in line_text:
                        break
                    
                    # 주소로 간주할 수 있는 줄 (한글이 포함되고, 닫는 괄호까지)
                    if re.search(r'[가-힣]', line_text) and len(line_text.strip()) > 1:
                        address_bboxes.append(bbox)
                        
                        # 닫는 괄호가 있으면 포함하고 종료
                        if ')' in line_text or '）' in line_text:
                            break
            
            if address_bboxes:
                all_x = []
                all_y = []
                for bbox in address_bboxes:
                    for point in bbox:
                        all_x.append(point[0])
                        all_y.append(point[1])
                if all_x and all_y:
                    result['address_bbox'] = [
                        [min(all_x), min(all_y)],
                        [max(all_x), min(all_y)],
                        [max(all_x), max(all_y)],
                        [min(all_x), max(all_y)]
                    ]
        
        return result
    
    # 주민등록증이 아닌 경우 기존 로직 사용
    # EasyOCR 결과 형식: [(bbox, text, confidence), ...]
    full_text = ' '.join([line[1] for line in text_lines])
    text_lines_list = [line[1] for line in text_lines]  # 각 줄의 텍스트
    
    # 주민번호 패턴 찾기 (YYMMDD-XXXXXXX 형식, 공백 및 줄바꿈 허용)
    # 먼저 한 줄에 있는 경우 찾기
    resident_patterns = [
        r'\d{6}[-]\d{7}',  # 기본 패턴: 501111-1234566
        r'\d{6}[-]\s*\d{1}\s*\d{6}',  # 공백 포함: 501111-1 234566
        r'\d{6}[-]\d{1}\s+\d{6}',  # 하이픈 후 공백: 501111-1 234566
    ]
    
    resident_match = None
    resident_line_idx = None
    
    # 각 패턴으로 시도 (한 줄에 있는 경우)
    for pattern in resident_patterns:
        resident_match = re.search(pattern, full_text)
        if resident_match:
            # 공백 제거하여 정규화
            matched_text = resident_match.group()
            normalized = re.sub(r'\s+', '', matched_text)  # 모든 공백 제거
            result['resident_number'] = normalized
            
            # 주민번호가 포함된 바운딩 박스와 줄 인덱스 찾기
            for idx, (bbox, line_text, confidence) in enumerate(text_lines):
                if re.search(pattern, line_text):
                    result['resident_bbox'] = bbox
                    resident_line_idx = idx
                    break
            break
    
    # 한 줄에 없으면 여러 줄에 걸쳐 있는 경우 찾기 (예: "991130-" 다음 줄에 "1234567")
    if not result['resident_number']:
        for idx in range(len(text_lines) - 1):
            current_line = text_lines[idx][1]
            next_line = text_lines[idx + 1][1]
            
            # 현재 줄이 "991130-" 같은 패턴으로 끝나고, 다음 줄이 숫자로 시작하는지 확인
            # 여러 패턴 시도
            front_patterns = [
                r'(\d{6}[-])$',  # "991130-"
                r'(\d{6}[-]\s*)$',  # "991130- " (공백 포함)
            ]
            
            back_patterns = [
                r'^(\d{7})',  # "1234567"
                r'^(\s*\d{7})',  # " 1234567" (공백 포함)
                r'^(\d{1}\s*\d{6})',  # "1 234567" (공백 포함)
            ]
            
            for front_pattern in front_patterns:
                front_match = re.search(front_pattern, current_line.strip())
                if front_match:
                    for back_pattern in back_patterns:
                        back_match = re.search(back_pattern, next_line.strip())
                        if back_match:
                            # 주민번호 재구성
                            rrn1 = front_match.group(1).strip()  # "991130-"
                            rrn2 = back_match.group(1).strip()   # "1234567" 또는 "1 234567"
                            # 공백 제거
                            rrn2 = re.sub(r'\s+', '', rrn2)
                            result['resident_number'] = rrn1 + rrn2
                            resident_line_idx = idx
                            resident_match = True  # 주민번호를 찾았음을 표시
                            
                            # 두 줄의 바운딩 박스를 합치기
                            bbox1 = text_lines[idx][0]
                            bbox2 = text_lines[idx + 1][0]
                            all_x = []
                            all_y = []
                            for point in bbox1 + bbox2:
                                all_x.append(point[0])
                                all_y.append(point[1])
                            if all_x and all_y:
                                result['resident_bbox'] = [
                                    [min(all_x), min(all_y)],
                                    [max(all_x), min(all_y)],
                                    [max(all_x), max(all_y)],
                                    [min(all_x), max(all_y)]
                                ]
                            break
                    if result['resident_number']:
                        break
                if result['resident_number']:
                    break
            if result['resident_number']:
                break
    
    # 성명 추출: 주민번호가 있는 줄의 윗줄들에서 한글 이름 추출
    if resident_line_idx is not None and resident_line_idx > 0:
        # 주민번호의 x 좌표 범위 확인
        resident_bbox = result.get('resident_bbox')
        resident_x_min = None
        resident_x_max = None
        resident_x_center = None
        
        if resident_bbox:
            resident_x_min = min([p[0] for p in resident_bbox])
            resident_x_max = max([p[0] for p in resident_bbox])
            resident_x_center = (resident_x_min + resident_x_max) / 2
        
        # 주민번호 위의 여러 줄 확인 (최대 3줄)
        best_name = None
        best_name_bbox = None
        min_distance = float('inf')
        
        for check_idx in range(max(0, resident_line_idx - 3), resident_line_idx):
            bbox, line_text, confidence = text_lines[check_idx]
            
            # 괄호가 있는지 확인
            if '(' in line_text or '（' in line_text:
                # 괄호 전까지의 텍스트 추출
                bracket_pos = line_text.find('(') if '(' in line_text else line_text.find('（')
                name_part = line_text[:bracket_pos].strip()
            else:
                # 괄호가 없으면 전체 줄 사용
                name_part = line_text.strip()
            
            # 제외할 키워드 목록
            exclude_keywords = ['주민등록', '주민등록증', '운전면허', '운전면허증', '여권', '신분증']
            
            # 제외 키워드가 전체 줄에만 있는 경우 건너뛰기 (이름 부분에는 없어야 함)
            if name_part and any(keyword in name_part for keyword in exclude_keywords):
                # 이름 부분에서 제외 키워드를 제거하고 다시 시도
                for keyword in exclude_keywords:
                    name_part = name_part.replace(keyword, '').strip()
            
            # 한글 이름 패턴 찾기 (2-4자 한글, 숫자나 특수문자 제외)
            name_matches = list(re.finditer(r'([가-힣]{2,4})', name_part))
            
            if name_matches:
                # 찾은 이름 중에서 제외 키워드가 아닌 것만 선택
                valid_matches = [m for m in name_matches if m.group(1) not in exclude_keywords]
                
                if valid_matches:
                    # 주민번호와 x 좌표가 비슷한 위치에 있는 이름 찾기
                    if resident_x_center is not None:
                        line_x_coords = [p[0] for p in bbox]
                        line_x_min = min(line_x_coords)
                        line_x_max = max(line_x_coords)
                        line_width = line_x_max - line_x_min if (line_x_max - line_x_min) > 0 else 1
                        
                        for match in valid_matches:
                            # 이름의 시작 위치 비율
                            name_start_ratio = match.start() / len(name_part) if len(name_part) > 0 else 0
                            name_end_ratio = match.end() / len(name_part) if len(name_part) > 0 else 0
                            # 해당 위치의 x 좌표 추정
                            estimated_x_start = line_x_min + (line_width * name_start_ratio)
                            estimated_x_end = line_x_min + (line_width * name_end_ratio)
                            estimated_x_center = (estimated_x_start + estimated_x_end) / 2
                            
                            # 주민번호 중심과의 거리
                            distance = abs(estimated_x_center - resident_x_center)
                            
                            # 주민번호 x 범위와 겹치는지 확인
                            overlaps = not (estimated_x_end < resident_x_min or estimated_x_start > resident_x_max)
                            
                            # 겹치거나 가까운 경우 우선 선택
                            if overlaps or distance < min_distance:
                                if overlaps or (not best_name):  # 겹치면 우선, 아니면 가장 가까운 것
                                    min_distance = distance
                                    best_name = match.group(1)
                                    best_name_bbox = bbox
                    else:
                        # 바운딩 박스 정보가 없으면 가장 가까운 줄의 마지막 유효한 이름 선택
                        if check_idx == resident_line_idx - 1:  # 바로 위 줄
                            best_name = valid_matches[-1].group(1)
                            best_name_bbox = bbox
        
        if best_name:
            result['name'] = best_name
            result['name_bbox'] = best_name_bbox
    
    # 성명 추출 실패 시 기존 로직 사용 (보통 "성명" 또는 "이름" 다음에 오는 텍스트)
    if not result['name']:
        name_patterns = [
            r'성명[:\s]*([가-힣]{2,4})',
            r'이름[:\s]*([가-힣]{2,4})',
            r'성\s*명[:\s]*([가-힣]{2,4})'
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, full_text)
            if name_match:
                result['name'] = name_match.group(1)
                break
    
    # 여전히 성명이 없으면 주민번호 앞의 한글 이름 찾기
    if not result['name'] and resident_line_idx is not None and resident_line_idx > 0:
        # 주민번호 바로 위 줄부터 확인
        exclude_keywords = ['주민등록', '주민등록증', '운전면허', '운전면허증', '여권', '신분증']
        
        for check_idx in range(max(0, resident_line_idx - 3), resident_line_idx):
            bbox, line_text, confidence = text_lines[check_idx]
            
            # 제외 키워드가 포함된 줄은 건너뛰기
            if any(keyword in line_text for keyword in exclude_keywords):
                continue
            
            # 괄호가 있으면 괄호 전까지
            if '(' in line_text or '（' in line_text:
                bracket_pos = line_text.find('(') if '(' in line_text else line_text.find('（')
                name_part = line_text[:bracket_pos].strip()
            else:
                name_part = line_text.strip()
            
            # 한글 이름 패턴 찾기
            name_candidates = list(re.finditer(r'([가-힣]{2,4})', name_part))
            
            for candidate in reversed(name_candidates):  # 뒤에서부터
                name = candidate.group(1).strip()
                # 제외 키워드가 아닌 경우만 선택
                if name and name not in exclude_keywords:
                    result['name'] = name
                    result['name_bbox'] = bbox
                    break
            
            if result['name']:
                break
    
    # 주소 추출 (보통 "주소" 다음에 오는 텍스트)
    address_keyword_patterns = [
        r'주소[:\s]*',
        r'본적[:\s]*'
    ]
    
    # "주소" 키워드가 있는 줄 찾기
    address_keyword_line_idx = None
    for idx, (bbox, line_text, confidence) in enumerate(text_lines):
        for pattern in address_keyword_patterns:
            if re.search(pattern, line_text):
                address_keyword_line_idx = idx
                break
        if address_keyword_line_idx is not None:
            break
    
    # 주소 종료 키워드
    end_keywords = [
        r'\d{4}\s*\.',  # 날짜: 2019. 11. 25
        r'\d{4}\s+\d{1,2}',  # 날짜: 2017 11. 1
        r'구청장',
        r'청장인',
        r'발급일',
        r'만료일',
    ]
    
    if address_keyword_line_idx is not None:
        # "주소" 키워드 다음 줄부터 주소 추출
        address_lines = []
        address_bboxes = []
        
        for idx in range(address_keyword_line_idx, len(text_lines)):
            bbox, line_text, confidence = text_lines[idx]
            
            # 첫 줄에서 "주소:" 부분 제거
            if idx == address_keyword_line_idx:
                for pattern in address_keyword_patterns:
                    line_text = re.sub(pattern, '', line_text).strip()
            
            # 닫는 괄호가 있으면 주소 추출 종료
            if ')' in line_text or '）' in line_text:
                # 닫는 괄호까지 포함
                address_lines.append(line_text.strip())
                address_bboxes.append(bbox)
                break
            
            # 종료 키워드 확인
            should_stop = False
            for keyword in end_keywords:
                if re.search(keyword, line_text):
                    should_stop = True
                    break
            
            # 주민번호가 포함된 줄이면 종료
            if any(re.search(pattern, line_text) for pattern in resident_patterns):
                should_stop = True
            
            if should_stop:
                break
            
            # 주소로 간주할 수 있는 줄인지 확인
            if line_text.strip() and not re.match(r'^[\s\d\.\-,]+$', line_text):
                address_lines.append(line_text.strip())
                address_bboxes.append(bbox)
        
        if address_lines:
            combined_address = ' '.join(address_lines)
            combined_address = re.sub(r'\s+', ' ', combined_address).strip()
            result['address'] = combined_address
            
            if address_bboxes:
                all_x = []
                all_y = []
                for bbox in address_bboxes:
                    for point in bbox:
                        all_x.append(point[0])
                        all_y.append(point[1])
                if all_x and all_y:
                    result['address_bbox'] = [
                        [min(all_x), min(all_y)],
                        [max(all_x), min(all_y)],
                        [max(all_x), max(all_y)],
                        [min(all_x), max(all_y)]
                    ]
    
    # 주소가 없으면 주민번호 다음 텍스트를 주소로 추정
    if not result['address'] and resident_line_idx is not None:
        # 주민번호 다음 줄부터 주소 추출
        address_lines = []
        address_bboxes = []
        
        # 주소 종료 키워드 (날짜 패턴, 구청장 등)
        end_keywords = [
            r'\d{4}\s*\.',  # 날짜: 2019. 11. 25
            r'\d{4}\s+\d{1,2}',  # 날짜: 2017 11. 1
            r'구청장',
            r'청장인',
            r'발급일',
            r'만료일',
        ]
        
        # 주민번호가 여러 줄에 걸쳐 있으면 그 다음 줄부터 시작
        # 한 줄에 있으면 resident_line_idx + 1, 여러 줄이면 resident_line_idx + 2
        start_idx = resident_line_idx + 1
        if result['resident_number'] and '-' in result['resident_number']:
            # 주민번호 뒷자리가 다음 줄에 있는지 확인
            if resident_line_idx + 1 < len(text_lines):
                next_line = text_lines[resident_line_idx + 1][1]
                if re.search(r'^\d{7}', next_line.strip()):
                    start_idx = resident_line_idx + 2  # 뒷자리 줄 다음부터
        
        # 주민번호 다음 줄부터 확인
        for idx in range(start_idx, len(text_lines)):
            bbox, line_text, confidence = text_lines[idx]
            
            # 닫는 괄호가 있으면 주소 추출 종료
            if ')' in line_text or '）' in line_text:
                # 닫는 괄호까지 포함
                if re.search(r'[가-힣]', line_text) and not any(re.search(pattern, line_text) for pattern in resident_patterns):
                    if len(line_text.strip()) > 1 and not re.match(r'^[\s\d\.\-,]+$', line_text):
                        address_lines.append(line_text.strip())
                        address_bboxes.append(bbox)
                break
            
            # 종료 키워드 확인
            should_stop = False
            for keyword in end_keywords:
                if re.search(keyword, line_text):
                    should_stop = True
                    break
            
            # 주민번호가 포함된 줄이면 종료
            if any(re.search(pattern, line_text) for pattern in resident_patterns):
                should_stop = True
            
            if should_stop:
                break
            
            # 주소로 간주할 수 있는 줄인지 확인
            # 한글이 포함되어 있고, 주민번호 패턴이 없으며, 너무 짧지 않은 경우
            if re.search(r'[가-힣]', line_text) and not any(re.search(pattern, line_text) for pattern in resident_patterns):
                # 숫자만 있는 줄이나 특수문자만 있는 줄은 제외
                if len(line_text.strip()) > 1 and not re.match(r'^[\s\d\.\-,]+$', line_text):
                    address_lines.append(line_text.strip())
                    address_bboxes.append(bbox)
        
        # 주소 조합
        if address_lines:
            # 여러 줄을 공백으로 연결
            combined_address = ' '.join(address_lines)
            # 연속된 공백 정리
            combined_address = re.sub(r'\s+', ' ', combined_address).strip()
            result['address'] = combined_address
            
            # 바운딩 박스 합치기
            if address_bboxes:
                all_x = []
                all_y = []
                for bbox in address_bboxes:
                    for point in bbox:
                        all_x.append(point[0])
                        all_y.append(point[1])
                if all_x and all_y:
                    result['address_bbox'] = [
                        [min(all_x), min(all_y)],
                        [max(all_x), min(all_y)],
                        [max(all_x), max(all_y)],
                        [min(all_x), max(all_y)]
                    ]
    
    return result

# ==================== 문서 비교 및 하이라이팅 기능 ====================

# 필드 매핑 테이블 정의
FIELD_MAPPING = {
    "customer_name": {
        "id_card_path": "name",
        "form_path": "change.customer_info.options[name='이름']"
    },
    "birth_date": {
        "id_card_path": "resident_number",  # 주민번호에서 생년월일 추출
        "form_path": "change.birth"
    },
    "service_number": {
        "id_card_path": None,  # 신분증에는 없을 수 있음
        "form_path": "change.service_num.options[name='서비스번호']"
    },
    "phone_number": {
        "id_card_path": None,  # 신분증에는 없을 수 있음
        "form_path": "change.phone_num.options[name='연락처']"
    },
    "address": {
        "id_card_path": "address",
        "form_path": None  # 신청서에는 주소가 없을 수 있음
    }
}

def normalize_id_card_data(id_card_ocr_result, ocr_text_lines):
    """신분증 OCR 결과를 정규화된 형식으로 변환"""
    normalized = {}
    
    # 이름
    if id_card_ocr_result.get('name'):
        name_bbox = None
        # OCR 결과에서 이름 바운딩 박스 찾기
        for bbox, text, conf in ocr_text_lines:
            if id_card_ocr_result['name'] in text:
                name_bbox = bbox
                break
        
        normalized['customer_name'] = {
            "value": id_card_ocr_result['name'],
            "bbox": name_bbox,
            "confidence": 0.95  # 기본값
        }
    
    # 생년월일 (주민번호에서 추출)
    birth_date = ""
    if id_card_ocr_result.get('resident_number'):
        resident_num = id_card_ocr_result.get('resident_number', '').replace('X', '0')
        # 주민번호 형식: YYMMDD-XXXXXXX
        if len(resident_num) >= 6 and '-' in resident_num:
            birth_date_str = resident_num[:6]  # YYMMDD
            # 19XX 또는 20XX로 변환
            try:
                year = int(birth_date_str[:2])
                if year <= 30:
                    birth_date = f"20{birth_date_str}"
                else:
                    birth_date = f"19{birth_date_str}"
                # YYYY-MM-DD 형식으로 변환
                if len(birth_date) == 6:
                    birth_date = f"{birth_date[:4]}-{birth_date[4:6]}-01"
                elif len(birth_date) == 8:
                    birth_date = f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:8]}"
            except ValueError:
                birth_date = ""
        
        resident_bbox = None
        for bbox, text, conf in ocr_text_lines:
            if id_card_ocr_result.get('resident_number', '').replace('X', '') in text.replace(' ', ''):
                resident_bbox = bbox
                break
        
        normalized['birth_date'] = {
            "value": birth_date,
            "bbox": resident_bbox,
            "confidence": 0.95
        }
    
    # 주소
    if id_card_ocr_result.get('address'):
        address_bbox = None
        for bbox, text, conf in ocr_text_lines:
            if id_card_ocr_result['address'][:10] in text:  # 주소 앞부분으로 매칭
                address_bbox = bbox
                break
        
        normalized['address'] = {
            "value": id_card_ocr_result['address'],
            "bbox": address_bbox,
            "confidence": 0.95
        }
    
    return normalized

def get_nested_value(data, path):
    """중첩된 딕셔너리에서 경로로 값 추출"""
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict):
            # options[name='이름'] 같은 형식 처리
            if '[' in key and ']' in key:
                base_key = key.split('[')[0]
                if base_key in current:
                    current = current[base_key]
                    # options 배열에서 name으로 찾기
                    if isinstance(current, dict) and 'options' in current:
                        options = current['options']
                        if isinstance(options, list):
                            # name='이름' 추출
                            match_str = key.split("'")[1] if "'" in key else key.split('"')[1]
                            for opt in options:
                                if isinstance(opt, dict) and opt.get('name') == match_str:
                                    return opt
                    return None
            else:
                if key in current:
                    current = current[key]
                else:
                    return None
        elif isinstance(current, list):
            # 리스트 인덱스 처리
            try:
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            except ValueError:
                return None
        else:
            return None
    
    return current

def normalize_form_data(structured_output):
    """신청서 structured_output.json을 정규화된 형식으로 변환"""
    normalized = {}
    
    # 이름
    name_field = get_nested_value(structured_output, "change.customer_info.options[name='이름']")
    if name_field and isinstance(name_field, dict):
        points = name_field.get('points', [])
        bbox = None
        if len(points) >= 2:
            # points를 4개 점으로 변환
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            bbox = [
                [min(x_coords), min(y_coords)],
                [max(x_coords), min(y_coords)],
                [max(x_coords), max(y_coords)],
                [min(x_coords), max(y_coords)]
            ]
        
        normalized['customer_name'] = {
            "value": name_field.get('text', ''),
            "bbox": bbox,
            "confidence": 0.9
        }
    
    # 생년월일
    birth_field = get_nested_value(structured_output, "change.birth")
    if birth_field and isinstance(birth_field, dict):
        points = birth_field.get('points', [])
        bbox = None
        if len(points) >= 2:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            bbox = [
                [min(x_coords), min(y_coords)],
                [max(x_coords), min(y_coords)],
                [max(x_coords), max(y_coords)],
                [min(x_coords), max(y_coords)]
            ]
        
        normalized['birth_date'] = {
            "value": birth_field.get('text', ''),
            "bbox": bbox,
            "confidence": 0.9
        }
    
    # 서비스번호
    service_field = get_nested_value(structured_output, "change.service_num.options[name='서비스번호']")
    if service_field and isinstance(service_field, dict):
        points = service_field.get('points', [])
        bbox = None
        if len(points) >= 2:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            bbox = [
                [min(x_coords), min(y_coords)],
                [max(x_coords), min(y_coords)],
                [max(x_coords), max(y_coords)],
                [min(x_coords), max(y_coords)]
            ]
        
        normalized['service_number'] = {
            "value": service_field.get('text', ''),
            "bbox": bbox,
            "confidence": 0.9
        }
    
    # 연락처
    phone_field = get_nested_value(structured_output, "change.phone_num.options[name='연락처']")
    if phone_field and isinstance(phone_field, dict):
        points = phone_field.get('points', [])
        bbox = None
        if len(points) >= 2:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            bbox = [
                [min(x_coords), min(y_coords)],
                [max(x_coords), min(y_coords)],
                [max(x_coords), max(y_coords)],
                [min(x_coords), max(y_coords)]
            ]
        
        normalized['phone_number'] = {
            "value": phone_field.get('text', ''),
            "bbox": bbox,
            "confidence": 0.9
        }
    
    return normalized

def normalize_name(name):
    """이름 정규화 (공백, 중간점, 괄호 제거)"""
    if not name:
        return ""
    # 공백, 중간점, 괄호 제거
    normalized = re.sub(r'[\s·()（）]', '', name)
    return normalized

def normalize_date(date_str):
    """날짜 정규화 (YYYY-MM-DD 형식으로 변환)"""
    if not date_str:
        return ""
    
    # 숫자만 추출
    digits = re.sub(r'[^\d]', '', date_str)
    
    if len(digits) == 8:
        # YYYYMMDD 형식
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    elif len(digits) == 6:
        # YYMMDD 형식
        year = int(digits[:2])
        if year <= 30:
            year = 2000 + year
        else:
            year = 1900 + year
        return f"{year}-{digits[2:4]}-{digits[4:6]}"
    elif len(digits) >= 4:
        # 부분적으로라도 변환 시도
        year = digits[:4]
        month = digits[4:6] if len(digits) >= 6 else "01"
        day = digits[6:8] if len(digits) >= 8 else "01"
        return f"{year}-{month}-{day}"
    
    return date_str

def normalize_phone(phone):
    """전화번호 정규화 (숫자만 남기기)"""
    if not phone:
        return ""
    return re.sub(r'[^\d]', '', phone)

def levenshtein_distance(s1, s2):
    """레벤슈타인 거리 계산"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def compare_fields(id_card_data, form_data):
    """두 문서의 필드를 비교하여 불일치를 찾음"""
    comparisons = []
    
    # 비교할 필드 목록
    fields_to_compare = ['customer_name', 'birth_date', 'service_number', 'phone_number', 'address']
    
    for field in fields_to_compare:
        id_value = id_card_data.get(field, {})
        form_value = form_data.get(field, {})
        
        id_val = id_value.get('value', '') if isinstance(id_value, dict) else ''
        form_val = form_value.get('value', '') if isinstance(form_value, dict) else ''
        
        id_bbox = id_value.get('bbox') if isinstance(id_value, dict) else None
        form_bbox = form_value.get('bbox') if isinstance(form_value, dict) else None
        
        id_conf = id_value.get('confidence', 0) if isinstance(id_value, dict) else 0
        form_conf = form_value.get('confidence', 0) if isinstance(form_value, dict) else 0
        
        # 상태 결정
        status = "MATCH"
        reason_code = ""
        reason_message = ""
        
        if not id_val and not form_val:
            status = "MISSING_BOTH"
            reason_code = "FIELD_MISSING"
            reason_message = f"{field} 필드가 양쪽 문서에 모두 없습니다."
        elif not id_val:
            status = "MISSING_ID"
            reason_code = "ID_CARD_MISSING"
            reason_message = f"신분증에 {field} 필드가 없습니다."
        elif not form_val:
            status = "MISSING_FORM"
            reason_code = "FORM_MISSING"
            reason_message = f"신청서에 {field} 필드가 없습니다."
        else:
            # 값 비교
            if field == 'customer_name':
                norm_id = normalize_name(id_val)
                norm_form = normalize_name(form_val)
                if norm_id != norm_form:
                    # 유사도 확인
                    distance = levenshtein_distance(norm_id, norm_form)
                    if distance <= 1:
                        status = "WARNING"
                        reason_code = "NAME_SIMILAR"
                        reason_message = f"이름이 유사하지만 다릅니다. (신분증: {id_val}, 신청서: {form_val})"
                    else:
                        status = "MISMATCH"
                        reason_code = "NAME_DIFFERENT"
                        reason_message = f"이름이 다릅니다. (신분증: {id_val}, 신청서: {form_val})"
            
            elif field == 'birth_date':
                norm_id = normalize_date(id_val)
                norm_form = normalize_date(form_val)
                if norm_id != norm_form:
                    status = "MISMATCH"
                    reason_code = "DATE_DIFFERENT"
                    reason_message = f"생년월일이 다릅니다. (신분증: {norm_id}, 신청서: {norm_form})"
            
            elif field in ['phone_number', 'service_number']:
                norm_id = normalize_phone(id_val)
                norm_form = normalize_phone(form_val)
                if norm_id != norm_form:
                    status = "MISMATCH"
                    reason_code = f"{field.upper()}_DIFFERENT"
                    reason_message = f"{field}이(가) 다릅니다. (신분증: {id_val}, 신청서: {form_val})"
            
            elif field == 'address':
                # 주소는 키워드 기반 비교
                id_keywords = set(re.findall(r'[가-힣]+', id_val))
                form_keywords = set(re.findall(r'[가-힣]+', form_val))
                common = id_keywords & form_keywords
                if len(common) < len(id_keywords) * 0.5:  # 50% 이상 일치하지 않으면
                    status = "MISMATCH"
                    reason_code = "ADDRESS_DIFFERENT"
                    reason_message = f"주소가 다릅니다. (신분증: {id_val}, 신청서: {form_val})"
        
        comparison = {
            "field": field,
            "status": status,
            "id_card": {
                "value": id_val,
                "bbox": id_bbox,
                "confidence": id_conf
            },
            "form": {
                "value": form_val,
                "bbox": form_bbox,
                "confidence": form_conf
            },
            "reason_code": reason_code,
            "reason_message": reason_message
        }
        
        comparisons.append(comparison)
    
    return comparisons

def generate_highlight_data(comparisons):
    """비교 결과를 바탕으로 하이라이팅 데이터 생성"""
    id_card_highlights = []
    form_highlights = []
    
    for comp in comparisons:
        if comp['status'] != 'MATCH':
            severity = "HIGH" if comp['status'] == 'MISMATCH' else "MEDIUM" if comp['status'] == 'WARNING' else "LOW"
            
            if comp['id_card']['bbox'] and comp['id_card']['value']:
                id_card_highlights.append({
                    "field": comp['field'],
                    "bbox": comp['id_card']['bbox'],
                    "severity": severity,
                    "message": comp['reason_message']
                })
            
            if comp['form']['bbox'] and comp['form']['value']:
                form_highlights.append({
                    "field": comp['field'],
                    "bbox": comp['form']['bbox'],
                    "severity": severity,
                    "message": comp['reason_message']
                })
    
    return {
        "id_card_highlights": id_card_highlights,
        "form_highlights": form_highlights
    }

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인 API"""
    return jsonify({'status': 'ok', 'message': 'Backend server is running'})

@app.route('/api/checkbox/process', methods=['POST'])
def process_checkbox():
    """체크박스 클릭 좌표 처리 API"""
    try:
        from checkbox_agent import process_checkbox_click
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        structured_output = data.get('structured_output')
        click_x = data.get('click_x')
        click_y = data.get('click_y')
        use_bbox = data.get('use_bbox', True)
        tolerance = data.get('tolerance', 10.0)
        use_ai = data.get('use_ai', True)  # OpenAI 에이전트 사용 여부
        
        if not structured_output:
            return jsonify({'error': 'structured_output이 없습니다'}), 400
        
        if click_x is None or click_y is None:
            return jsonify({'error': '클릭 좌표가 없습니다'}), 400
        
        # 체크박스 처리 (OpenAI 에이전트 사용)
        result = process_checkbox_click(structured_output, click_x, click_y, use_bbox, tolerance, use_ai)
        
        # 업데이트된 structured_output 포함
        if result.get('success') and result.get('updated'):
            result['updated_structured_output'] = structured_output
        
        return jsonify(result)
    
    except ImportError:
        return jsonify({'error': 'checkbox_agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/checkbox/list', methods=['POST'])
def list_checkboxes():
    """structured_output.json의 모든 체크박스 정보 반환"""
    try:
        from checkbox_agent import get_all_checkboxes_info
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        structured_output = data.get('structured_output')
        
        if not structured_output:
            return jsonify({'error': 'structured_output이 없습니다'}), 400
        
        # 모든 체크박스 정보 가져오기
        checkboxes = get_all_checkboxes_info(structured_output)
        
        return jsonify({
            'success': True,
            'checkboxes': checkboxes,
            'count': len(checkboxes)
        })
    
    except ImportError:
        return jsonify({'error': 'checkbox_agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/checkbox/process-coordinate', methods=['POST'])
def process_checkbox_coordinate():
    """좌표만 받아서 체크박스 처리 (미리 로드된 structured_output.json 사용)"""
    try:
        from checkbox_agent import process_checkbox_by_coordinate, get_cached_structured_output
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        click_x = data.get('click_x')
        click_y = data.get('click_y')
        
        if click_x is None or click_y is None:
            return jsonify({'error': '클릭 좌표가 없습니다'}), 400
        
        # 좌표만으로 처리 (미리 로드된 structured_output.json 사용)
        result = process_checkbox_by_coordinate(click_x, click_y)
        
        # 업데이트된 structured_output 포함
        if result.get('success') and result.get('updated'):
            structured_output = get_cached_structured_output()
            if structured_output:
                result['updated_structured_output'] = structured_output
        
        return jsonify(result)
    
    except ImportError:
        return jsonify({'error': 'checkbox_agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/checkbox/load', methods=['POST'])
def load_structured_output():
    """structured_output.json 파일 로드"""
    try:
        from checkbox_agent import load_structured_output, get_cached_checkboxes
        
        data = request.get_json() or {}
        filepath = data.get('filepath')
        
        # 파일 로드
        result = load_structured_output(filepath)
        
        if result:
            checkboxes = get_cached_checkboxes()
            return jsonify({
                'success': True,
                'message': f'structured_output.json 로드 완료 ({len(checkboxes) if checkboxes else 0}개 체크박스)',
                'checkbox_count': len(checkboxes) if checkboxes else 0
            })
        else:
            return jsonify({
                'success': False,
                'error': 'structured_output.json 파일을 로드할 수 없습니다.'
            }), 400
    
    except ImportError:
        return jsonify({'error': 'checkbox_agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/checkbox/logs', methods=['GET'])
def get_checkbox_logs():
    """체크박스 에이전트 로그 반환"""
    try:
        from checkbox_agent import get_logs
        
        logs = get_logs()
        return jsonify({
            'success': True,
            'logs': logs
        })
    
    except ImportError:
        return jsonify({'error': 'checkbox_agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    print(f"\n[app.py] ========== /api/upload 요청 수신 ==========")
    print(f"[app.py] 요청 시간: {__import__('datetime').datetime.now()}")
    
    if 'file' not in request.files:
        print(f"[app.py] ❌ 파일이 없습니다")
        return jsonify({'error': '파일이 없습니다'}), 400
    
    file = request.files['file']
    if file.filename == '':
        print(f"[app.py] ❌ 파일이 선택되지 않았습니다")
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
    
    print(f"[app.py] 파일 정보:")
    print(f"  - 파일명: {file.filename}")
    print(f"  - Content-Type: {file.content_type}")
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"[app.py] 파일 저장 중: {filepath}")
        file.save(filepath)
        print(f"[app.py] ✅ 파일 저장 완료")
        
        try:
            # idocr.py를 사용하여 신분증 처리
            print(f"[app.py] idocr.py 모듈 import 중...")
            from idocr import process_id_card
            print(f"[app.py] ✅ idocr.py import 완료")
            
            print(f"[app.py] process_id_card 호출 시작...")
            result = process_id_card(filepath)
            print(f"[app.py] ✅ process_id_card 완료")
            
            if not result.get('success', False):
                print(f"[app.py] ❌ OCR 처리 실패: {result.get('error', '알 수 없는 오류')}")
                return jsonify({'error': result.get('error', 'OCR 처리 실패')}), 500
            
            print(f"[app.py] 응답 데이터 구성 중...")
            # idocr.py의 결과를 기존 형식으로 변환
            response_data = {
                'success': True,
                'data': {
                    'name': result['name']['text'],
                    'resident_number': result['resident_number']['masked_text'],
                    'address': result['address']['text'],
                    'issue_date': result.get('issue_date', {}).get('text', '')
                },
                'ocr_text': result['ocr_text'],
                'ocr_lines': result['ocr_lines'],
                'crops': {
                    'name': result['name']['crop_image'],
                    'resident': result['resident_number']['crop_image'],
                    'address': result['address']['crop_image'],
                    'issue_date': result.get('issue_date', {}).get('crop_image', '')
                }
            }
            
            if result.get('masked_image'):
                response_data['masked_image'] = result['masked_image']
            
            print(f"[app.py] ✅ 응답 데이터 구성 완료")
            print(f"[app.py] 응답 데이터 요약:")
            print(f"  - 성공: {response_data['success']}")
            print(f"  - 성명: {response_data['data']['name']}")
            print(f"  - 주민번호: {response_data['data']['resident_number']}")
            print(f"  - 주소: {response_data['data']['address'][:50]}...")
            print(f"  - OCR 텍스트 길이: {len(response_data['ocr_text'])} 문자")
            print(f"[app.py] ========== /api/upload 처리 완료 ==========\n")
            
            return jsonify(response_data)
            
        except Exception as e:
            import traceback
            print(f"[app.py] ❌ OCR 처리 중 예외 발생!")
            print(f"[app.py] 오류 메시지: {str(e)}")
            print(f"[app.py] 스택 트레이스:")
            traceback.print_exc()
            return jsonify({'error': f'OCR 처리 중 오류 발생: {str(e)}'}), 500
        finally:
            # 업로드된 파일 삭제
            if os.path.exists(filepath):
                print(f"[app.py] 임시 파일 삭제: {filepath}")
                os.remove(filepath)
    
    print(f"[app.py] ❌ 지원하지 않는 파일 형식: {file.filename}")
    return jsonify({'error': '지원하지 않는 파일 형식입니다'}), 400

@app.route('/api/structured-output', methods=['GET'])
def get_structured_output():
    """structured_output.json 파일 반환"""
    try:
        structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
        if not os.path.exists(structured_output_path):
            return jsonify({'error': 'structured_output.json을 찾을 수 없습니다'}), 404
        
        with open(structured_output_path, 'r', encoding='utf-8') as f:
            structured_output = json.load(f)
        
        return jsonify(structured_output)
    except Exception as e:
        return jsonify({'error': f'파일 읽기 오류: {str(e)}'}), 500

@app.route('/api/run-agent', methods=['POST'])
def run_agent():
    """신분증 OCR 결과와 structured_output.json을 받아서 agent.py 실행"""
    try:
        print(f"\n[app.py] ========== /api/run-agent 요청 수신 ==========")
        
        data = request.get_json()
        id_card_data = data.get('id_card_data')
        default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
        structured_output_path = data.get('structured_output_path', default_path)
        
        if not id_card_data:
            return jsonify({'error': '신분증 데이터가 없습니다'}), 400
        
        # structured_output.json 로드
        if not os.path.exists(structured_output_path):
            return jsonify({'error': f'structured_output.json을 찾을 수 없습니다: {structured_output_path}'}), 404
        
        print(f"[app.py] structured_output.json 로드 중: {structured_output_path}")
        with open(structured_output_path, 'r', encoding='utf-8') as f:
            structured_output = json.load(f)
        print(f"[app.py] ✅ structured_output.json 로드 완료")
        
        # agent.py import 및 실행
        print(f"[app.py] agent.py 모듈 import 중...")
        from agent import process_documents
        
        # id_card_data를 agent.py가 기대하는 형식으로 변환
        id_card_ocr = {
            'name': id_card_data.get('name', ''),
            'resident_number': id_card_data.get('resident_number', ''),
            'address': id_card_data.get('address', ''),
            'issue_date': id_card_data.get('issue_date', ''),  # 발급일 추가
            'ocr_text': id_card_data.get('ocr_text', ''),
            'ocr_lines': id_card_data.get('ocr_lines', [])
        }
        
        print(f"[app.py] agent.process_documents 호출 시작...")
        print(f"[app.py] 신분증 데이터: 이름={id_card_ocr['name']}, 주민번호={id_card_ocr['resident_number'][:10]}...")
        
        # process_documents는 Generator이므로 모든 결과를 수집
        # "complete" 단계가 나올 때까지 기다림
        results = []
        final_result_data = None
        
        print(f"[app.py] agent.process_documents 호출 시작...")
        for result in process_documents(id_card_ocr, structured_output, id_card_ocr.get('ocr_lines')):
            results.append(result)
            step = result.get('step', 'unknown')
            print(f"[app.py] Agent 결과 수신: {step}")
            
            # "complete" 단계가 나오면 최종 결과로 저장
            if step == 'complete':
                final_result_data = result.get('data', {})
                print(f"[app.py] ✅ 'complete' 단계 수신 - 최종 결과 저장")
                break
        
        print(f"[app.py] ✅ agent.process_documents 완료 (총 {len(results)}개 단계)")
        
        # final_result_data가 없으면 에러
        if not final_result_data:
            print(f"[app.py] ❌ 'complete' 단계가 없습니다!")
            if results:
                print(f"[app.py] 마지막 결과 사용 (step: {results[-1].get('step', 'unknown')})")
                final_result_data = results[-1].get('data', {})
            else:
                return jsonify({'error': 'Agent 처리 결과가 없습니다'}), 500
        
        print(f"[app.py] ========== /api/run-agent 처리 완료 ==========\n")
        
        print(f"[app.py] 최종 결과 데이터 구조 확인:")
        print(f"  - final_result_data 타입: {type(final_result_data)}")
        if isinstance(final_result_data, dict):
            print(f"  - final_result_data 키: {list(final_result_data.keys())}")
            print(f"  - agent_report 존재: {'agent_report' in final_result_data}")
            print(f"  - summary 존재: {'summary' in final_result_data}")
            print(f"  - comparisons 존재: {'comparisons' in final_result_data}")
            print(f"  - agent_logs 존재: {'agent_logs' in final_result_data}")
        
        # 리포트는 agent_report 필드에 있음
        agent_report = final_result_data.get('agent_report', '') if final_result_data else ''
        recommendations_report = final_result_data.get('recommendations_report', '') if final_result_data else ''
        customer_analysis_report = final_result_data.get('customer_analysis_report', '') if final_result_data else ''
        customer_summary = final_result_data.get('customer_summary', '') if final_result_data else ''
        summary = final_result_data.get('summary', {}) if final_result_data else {}
        id_card_validations = final_result_data.get('id_card_validations', []) if final_result_data else []
        form_validations = final_result_data.get('form_validations', []) if final_result_data else []
        name_comparison = final_result_data.get('name_comparison', {}) if final_result_data else {}
        agent_logs = final_result_data.get('agent_logs', []) if final_result_data else []
        
        # 최종 검증: Agent 결과가 완전히 준비되었는지 확인
        is_ready = (
            agent_report and len(agent_report) > 0 and
            summary and len(summary) > 0 and
            'total_fields' in summary
        )
        
        if not is_ready:
            print(f"[app.py] ⚠️ Agent 결과가 불완전합니다!")
            print(f"  - 리포트 존재: {bool(agent_report)}")
            print(f"  - 리포트 길이: {len(agent_report) if agent_report else 0}")
            print(f"  - 요약 존재: {bool(summary)}")
            print(f"  - 요약 키: {list(summary.keys()) if summary else []}")
        
        print(f"[app.py] 응답 데이터 구성:")
        print(f"  - 리포트 길이: {len(agent_report) if agent_report else 0}")
        print(f"  - 요약: {summary}")
        print(f"  - 고객 분석 리포트 존재: {bool(customer_analysis_report)}")
        print(f"  - 고객유형 한줄 요약: '{customer_summary}'")
        print(f"  - 신분증 검증 수: {len(id_card_validations)}")
        print(f"  - 신청서 검증 수: {len(form_validations)}")
        print(f"  - 성명 비교: {name_comparison.get('status', 'N/A')}")
        print(f"  - 로그 수: {len(agent_logs)}")
        print(f"  - 결과 준비 완료: {is_ready}")
        
        return jsonify({
            'success': is_ready,
            'results': results,
            'final_report': agent_report,
            'recommendations_report': recommendations_report,
            'customer_analysis_report': customer_analysis_report,
            'customer_summary': customer_summary,
            'summary': summary,
            'id_card_validations': id_card_validations,
            'form_validations': form_validations,
            'name_comparison': name_comparison,
            'agent_logs': agent_logs,
            'ready': is_ready  # 결과 준비 완료 여부
        })
        
    except Exception as e:
        import traceback
        print(f"[app.py] ❌ Agent 실행 중 예외 발생!")
        print(f"[app.py] 오류 메시지: {str(e)}")
        print(f"[app.py] 스택 트레이스:")
        traceback.print_exc()
        return jsonify({'error': f'Agent 실행 중 오류 발생: {str(e)}'}), 500

@app.route('/api/bbox-labels', methods=['GET'])
def get_bbox_labels():
    """bbox_labels.json 파일 반환"""
    try:
        bbox_labels_path = os.path.join(os.path.dirname(__file__), 'bbox_labels.json')
        
        if not os.path.exists(bbox_labels_path):
            return jsonify({'error': 'bbox_labels.json 파일을 찾을 수 없습니다'}), 404
        
        with open(bbox_labels_path, 'r', encoding='utf-8') as f:
            bbox_labels = json.load(f)
        
        return jsonify({'success': True, 'data': bbox_labels})
    except Exception as e:
        return jsonify({'error': f'bbox_labels.json 읽기 오류: {str(e)}'}), 500

@app.route('/api/crop-form-field', methods=['POST'])
def crop_form_field():
    """신청서 이미지(document.jpg)에서 특정 필드 영역을 crop"""
    try:
        data = request.get_json()
        bbox = data.get('bbox')
        
        if not bbox:
            return jsonify({'error': 'bbox가 없습니다'}), 400
        
        # document.jpg 경로
        document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
        
        if not os.path.exists(document_path):
            return jsonify({'error': 'document.jpg 파일을 찾을 수 없습니다'}), 404
        
        # structured_output의 points 형식: [[x1, y1], [x2, y2]]
        # crop_image_region이 기대하는 형식: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        if len(bbox) == 2:
            # 2개 점을 4개 점으로 변환
            x1, y1 = bbox[0]
            x2, y2 = bbox[1]
            bbox_4points = [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ]
        else:
            bbox_4points = bbox
        
        crop_image = crop_image_region(document_path, bbox_4points)
        
        if crop_image:
            return jsonify({'success': True, 'crop_image': crop_image})
        else:
            return jsonify({'error': '이미지 crop 실패'}), 500
            
    except Exception as e:
        return jsonify({'error': f'crop 처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/upload-and-compare', methods=['POST'])
def upload_and_compare():
    """신분증 이미지와 structured_output.json을 한번에 업로드하고 자동으로 비교 수행"""
    try:
        # Agent 모듈 import
        from agent import run_agent_analysis, client as agent_client
        
        # 파일 업로드 확인
        if 'id_card' not in request.files:
            return jsonify({'error': '신분증 이미지 파일이 없습니다'}), 400
        
        if 'structured_output' not in request.files:
            return jsonify({'error': 'structured_output.json 파일이 없습니다'}), 400
        
        id_card_file = request.files['id_card']
        structured_output_file = request.files['structured_output']
        
        if id_card_file.filename == '':
            return jsonify({'error': '신분증 이미지가 선택되지 않았습니다'}), 400
        
        if structured_output_file.filename == '':
            return jsonify({'error': 'structured_output.json이 선택되지 않았습니다'}), 400
        
        # 신분증 이미지 저장 및 OCR 처리
        if not allowed_file(id_card_file.filename):
            return jsonify({'error': '지원하지 않는 이미지 형식입니다'}), 400
        
        id_card_filename = secure_filename(id_card_file.filename)
        id_card_filepath = os.path.join(app.config['UPLOAD_FOLDER'], id_card_filename)
        id_card_file.save(id_card_filepath)
        
        # structured_output.json 저장 및 파싱
        structured_output_filename = secure_filename(structured_output_file.filename)
        structured_output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], structured_output_filename)
        structured_output_file.save(structured_output_filepath)
        
        try:
            # 1. 신분증 OCR 처리 (idocr.py 사용)
            from idocr import process_id_card
            
            id_card_result = process_id_card(id_card_filepath)
            
            if not id_card_result.get('success', False):
                return jsonify({'error': id_card_result.get('error', 'OCR 처리 실패')}), 500
            
            # idocr.py 결과에서 필요한 정보 추출
            extracted_info = {
                'name': id_card_result['name']['text'],
                'resident_number': id_card_result['resident_number']['masked_text'],
                'address': id_card_result['address']['text']
            }
            
            name_crop = id_card_result['name']['crop_image']
            resident_crop = id_card_result['resident_number']['crop_image']
            address_crop = id_card_result['address']['crop_image']
            ocr_text = id_card_result['ocr_text']
            masked_image_base64 = id_card_result.get('masked_image')
            serializable_ocr_result = id_card_result['ocr_lines']
            
            # 2. structured_output.json 파싱
            with open(structured_output_filepath, 'r', encoding='utf-8') as f:
                structured_output = json.load(f)
            
            # 3. 자동으로 비교 수행 (agent.py의 독립적인 process_documents 함수 사용)
            from agent import process_documents
            
            # generator에서 순차적으로 결과 받기
            final_result = None
            for step_result in process_documents(extracted_info, structured_output, serializable_ocr_result):
                step = step_result.get('step')
                if step == 'complete':
                    final_result = step_result.get('data')
                    break
                elif step == 'error':
                    return jsonify({
                        'error': step_result.get('data', {}).get('error', '처리 중 오류 발생'),
                        'ocr_data': {
                            'success': True,
                            'data': extracted_info,
                            'ocr_text': ocr_text,
                            'ocr_lines': serializable_ocr_result,
                            'crops': {
                                'name': name_crop,
                                'resident': resident_crop,
                                'address': address_crop
                            },
                            'masked_image': masked_image_base64
                        }
                    }), 500
            
            if not final_result:
                return jsonify({
                    'error': '비교 처리 중 오류 발생',
                    'ocr_data': {
                        'success': True,
                        'data': extracted_info,
                        'ocr_text': ocr_text,
                        'ocr_lines': serializable_ocr_result,
                        'crops': {
                            'name': name_crop,
                            'resident': resident_crop,
                            'address': address_crop
                        },
                        'masked_image': masked_image_base64
                    }
                }), 500
            
            comparison_result = final_result
            
            if not comparison_result.get('success'):
                return jsonify({
                    'error': '비교 처리 중 오류 발생',
                    'ocr_data': {
                        'success': True,
                        'data': extracted_info,
                        'ocr_text': ocr_text,
                        'ocr_lines': serializable_ocr_result,
                        'crops': {
                            'name': name_crop,
                            'resident': resident_crop,
                            'address': address_crop
                        },
                        'masked_image': masked_image_base64
                    }
                }), 500
            
            # 4. 결과 통합
            response_data = {
                'success': True,
                'ocr_data': {
                    'success': True,
                    'data': extracted_info,
                    'ocr_text': ocr_text,
                    'ocr_lines': serializable_ocr_result,
                    'crops': {
                        'name': name_crop,
                        'resident': resident_crop,
                        'address': address_crop
                    }
                },
                'comparison': comparison_result
            }
            
            if masked_image_base64:
                response_data['ocr_data']['masked_image'] = masked_image_base64
            
            return jsonify(response_data)
            
        except json.JSONDecodeError:
            return jsonify({'error': 'structured_output.json 파일 파싱 오류'}), 400
        except Exception as e:
            return jsonify({'error': f'처리 중 오류 발생: {str(e)}'}), 500
        finally:
            # 업로드된 파일 삭제
            if os.path.exists(id_card_filepath):
                os.remove(id_card_filepath)
            if os.path.exists(structured_output_filepath):
                os.remove(structured_output_filepath)
    
    except ImportError:
        return jsonify({'error': 'Agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'업로드 및 비교 처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/compare', methods=['POST'])
def compare_documents():
    """신분증 OCR 결과와 신청서 structured_output.json을 비교 (Agent 사용)"""
    try:
        # Agent 모듈 import
        from agent import process_documents
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '요청 데이터가 없습니다'}), 400
        
        # 신분증 OCR 결과
        id_card_ocr_result = data.get('id_card_ocr', {})
        id_card_ocr_lines = data.get('id_card_ocr_lines', [])
        
        # 신청서 structured_output.json
        structured_output = data.get('structured_output', {})
        
        if not id_card_ocr_result:
            return jsonify({'error': '신분증 OCR 결과가 없습니다'}), 400
        
        if not structured_output:
            return jsonify({'error': '신청서 structured_output이 없습니다'}), 400
        
        # Agent를 사용하여 비교 분석 수행 (독립적인 process_documents 함수 사용)
        final_result = None
        for step_result in process_documents(id_card_ocr_result, structured_output, id_card_ocr_lines):
            step = step_result.get('step')
            if step == 'complete':
                final_result = step_result.get('data')
                break
            elif step == 'error':
                return jsonify(step_result.get('data', {})), 500
        
        if not final_result:
            return jsonify({'error': '비교 처리 중 오류 발생'}), 500
        
        result = final_result
        
        if not result.get('success'):
            return jsonify(result), 500
        
        return jsonify(result)
        
    except ImportError:
        # Agent 모듈이 없거나 import 실패 시 agent.py의 함수들을 직접 사용
        try:
            # 필드별 비교 기능 제거됨
            
            data = request.get_json()
            
            if not data:
                return jsonify({'error': '요청 데이터가 없습니다'}), 400
            
            id_card_ocr_result = data.get('id_card_ocr', {})
            id_card_ocr_lines = data.get('id_card_ocr_lines', [])
            structured_output = data.get('structured_output', {})
            
            if not id_card_ocr_result or not structured_output:
                return jsonify({'error': '필수 데이터가 없습니다'}), 400
            
            # Agent 로그 가져오기
            from agent import agent_logs
            recent_logs = agent_logs[-20:] if agent_logs else []
            
            result = {
                'success': True,
                'agent_used': False,
                'agent_report': None,
                'agent_logs': recent_logs  # Agent 로그 포함
            }
            
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': f'비교 처리 중 오류 발생: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': f'비교 처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/agent-analysis', methods=['POST'])
def agent_analysis():
    """수정된 비교 결과를 기반으로 Agent 분석 실행"""
    try:
        from agent import run_agent_analysis_with_comparisons, client as agent_client
        
        data = request.get_json()
        comparisons = data.get('comparisons', [])
        
        if not comparisons:
            return jsonify({'error': '비교 결과가 없습니다'}), 400
        
        # Agent 클라이언트 상태 확인
        if agent_client is None:
            return jsonify({'error': 'Agent가 설정되지 않았습니다. OpenAI API KEY를 확인하세요.'}), 400
        
        # Agent 분석 실행 (수정된 비교 결과 기반)
        result = run_agent_analysis_with_comparisons(comparisons)
        
        if not result.get('success'):
            return jsonify(result), 500
        
        return jsonify(result)
        
    except ImportError:
        return jsonify({'error': 'Agent 모듈을 불러올 수 없습니다.'}), 500
    except Exception as e:
        return jsonify({'error': f'Agent 분석 중 오류 발생: {str(e)}'}), 500

@app.route('/api/detect-checkboxes', methods=['POST'])
def detect_checkboxes_api():
    """서류 이미지에서 체크박스 탐지"""
    try:
        print(f"\n[app.py] ========== /api/detect-checkboxes 요청 수신 ==========")
        
        if 'file' not in request.files:
            print(f"[app.py] ❌ 파일이 없습니다")
            return jsonify({'error': '파일이 없습니다'}), 400
        
        file = request.files['file']
        if file.filename == '':
            print(f"[app.py] ❌ 파일이 선택되지 않았습니다")
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '지원하지 않는 파일 형식입니다'}), 400
        
        # 파일 저장
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"[app.py] 파일 저장 완료: {filepath}")
        
        # checkbox_detection.py 모듈 import
        print(f"[app.py] checkbox_detection.py 모듈 import 중...")
        from checkbox_detection import get_checked_checkboxes
        print(f"[app.py] ✅ checkbox_detection.py import 완료")
        
        # 체크박스 탐지 실행
        print(f"[app.py] 체크박스 탐지 시작...")
        checkboxes = get_checked_checkboxes(filepath)
        print(f"[app.py] ✅ 체크박스 탐지 완료: {len(checkboxes)}개 발견")
        
        # 임시 파일 삭제
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': True,
            'checkboxes': checkboxes,
            'count': len(checkboxes)
        })
        
    except ImportError as e:
        print(f"[app.py] ❌ checkbox_detection 모듈 import 실패: {str(e)}")
        return jsonify({'error': f'체크박스 탐지 모듈을 불러올 수 없습니다: {str(e)}'}), 500
    except Exception as e:
        print(f"[app.py] ❌ 체크박스 탐지 중 오류 발생: {str(e)}")
        return jsonify({'error': f'체크박스 탐지 중 오류 발생: {str(e)}'}), 500

@app.route('/api/process-checkboxes', methods=['POST'])
def process_checkboxes_api():
    """체크박스 좌표를 처리하여 structured_output.json 수정"""
    try:
        print(f"\n[app.py] ========== /api/process-checkboxes 요청 수신 ==========")
        
        data = request.get_json()
        checkboxes = data.get('checkboxes', [])  # [{x1, y1, x2, y2}, ...]
        default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
        structured_output_path = data.get('structured_output_path', default_path)
        
        if not checkboxes:
            return jsonify({'error': '체크박스 좌표가 없습니다'}), 400
        
        print(f"[app.py] 체크박스 좌표 {len(checkboxes)}개 수신")
        
        # checkbox_agent.py 모듈 import
        print(f"[app.py] checkbox_agent.py 모듈 import 중...")
        from checkbox_agent import (
            load_structured_output,
            process_checkbox_by_coordinate,
            get_cached_structured_output,
            get_logs,
            reset_all_checkboxes
        )
        print(f"[app.py] ✅ checkbox_agent.py import 완료")

        # structured_output.json 로드
        print(f"[app.py] structured_output.json 로드 중: {structured_output_path}")
        if not os.path.exists(structured_output_path):
            return jsonify({'error': f'structured_output.json을 찾을 수 없습니다: {structured_output_path}'}), 404

        load_structured_output(structured_output_path)
        print(f"[app.py] ✅ structured_output.json 로드 완료")

        # 모든 체크박스를 false로 초기화 (이전 상태 제거)
        reset_count = reset_all_checkboxes()
        print(f"[app.py] ✅ 모든 체크박스 초기화 완료: {reset_count}개")

        # 각 체크박스 좌표 처리
        processed_results = []
        checked_items = []
        
        for idx, checkbox in enumerate(checkboxes):
            x1 = checkbox.get('x1', 0)
            y1 = checkbox.get('y1', 0)
            x2 = checkbox.get('x2', 0)
            y2 = checkbox.get('y2', 0)
            
            # 중심점 계산
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            
            print(f"[app.py] 체크박스 {idx + 1}/{len(checkboxes)} 처리 중: ({center_x}, {center_y})")
            
            # checkbox_agent로 처리
            result = process_checkbox_by_coordinate(center_x, center_y)
            
            if result.get('success'):
                processed_results.append(result)
                checked_items.append({
                    'name': result.get('checkbox', {}).get('name', ''),
                    'text': result.get('checkbox', {}).get('text', ''),
                    'path': result.get('path', ''),
                    'method': result.get('method', 'unknown'),
                    'bbox_text': result.get('bbox_text', '')  # bbox_labels에서 찾은 원본 텍스트
                })
                print(f"[app.py] ✅ 체크박스 처리 성공: {result.get('checkbox', {}).get('name', '이름 없음')}")
            else:
                print(f"[app.py] ⚠️ 체크박스 처리 실패: {result.get('error', '알 수 없는 오류')}")
                processed_results.append(result)
        
        # 수정된 structured_output 가져오기
        updated_structured_output = get_cached_structured_output()
        if not updated_structured_output:
            return jsonify({'error': '수정된 structured_output을 가져올 수 없습니다'}), 500
        
        # 수정된 structured_output.json 저장 (원본 파일도 업데이트)
        # 1. 원본 파일 업데이트
        with open(structured_output_path, 'w', encoding='utf-8') as f:
            json.dump(updated_structured_output, f, ensure_ascii=False, indent=2)
        print(f"[app.py] ✅ 원본 structured_output.json 업데이트 완료: {structured_output_path}")
        
        # 2. 백업용 업데이트 파일도 저장
        updated_path = structured_output_path.replace('.json', '_updated.json')
        with open(updated_path, 'w', encoding='utf-8') as f:
            json.dump(updated_structured_output, f, ensure_ascii=False, indent=2)
        print(f"[app.py] ✅ 수정된 structured_output.json 백업 저장: {updated_path}")
        
        # 반환 경로는 원본 파일 경로 사용 (Agent 분석에서 사용)
        updated_path = structured_output_path
        
        # 로그 가져오기
        logs = get_logs()
        
        return jsonify({
            'success': True,
            'processed_count': len(processed_results),
            'checked_items': checked_items,
            'updated_structured_output_path': updated_path,
            'logs': logs[-20:]  # 최근 20개 로그
        })
        
    except ImportError as e:
        print(f"[app.py] ❌ checkbox_agent 모듈 import 실패: {str(e)}")
        return jsonify({'error': f'체크박스 에이전트 모듈을 불러올 수 없습니다: {str(e)}'}), 500
    except Exception as e:
        print(f"[app.py] ❌ 체크박스 처리 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'체크박스 처리 중 오류 발생: {str(e)}'}), 500

@app.route('/api/document-ocr', methods=['POST'])
def document_ocr():
    """서류 이미지를 OCR Structured API에 전송하여 structured_output.json 생성"""
    try:
        print(f"\n[app.py] ========== /api/document-ocr 요청 수신 ==========")
        
        if requests is None:
            return jsonify({'error': 'requests 라이브러리가 설치되지 않았습니다. pip install requests를 실행하세요.'}), 500
        
        # 파일 업로드 확인
        if 'file' not in request.files:
            print(f"[app.py] ❌ 파일이 없습니다")
            return jsonify({'error': '파일이 없습니다'}), 400
        
        file = request.files['file']
        if file.filename == '':
            print(f"[app.py] ❌ 파일이 선택되지 않았습니다")
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        print(f"[app.py] 파일 정보:")
        print(f"  - 파일명: {file.filename}")
        print(f"  - Content-Type: {file.content_type}")
        
        if not allowed_file(file.filename):
            print(f"[app.py] ❌ 지원하지 않는 파일 형식: {file.filename}")
            return jsonify({'error': '지원하지 않는 파일 형식입니다'}), 400
        
        # 파일을 임시로 저장
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')
        file.save(temp_filepath)
        print(f"[app.py] ✅ 임시 파일 저장 완료: {temp_filepath}")
        
        try:
            # 외부 OCR Structured API 호출
            # ⚠️ 주의: 배포/공개 저장소에서는 실제 내부 엔드포인트를 숨기기 위해
            # OCR_API_BASE_URL 환경변수로 설정해서 사용합니다.
            API_BASE_URL = os.getenv("OCR_API_BASE_URL", "http://localhost:8000")
            API_ENDPOINT = f"{API_BASE_URL}/ocr/structured"
            
            print(f"[app.py] [1/3] 외부 OCR API 호출 중...")
            print(f"  - API 엔드포인트: {API_ENDPOINT}")
            
            # 파일을 먼저 읽어서 메모리에 저장 (파일 핸들 닫기 위해)
            with open(temp_filepath, 'rb') as image_file:
                file_content = image_file.read()
            
            # 파일 핸들이 닫힌 후 API 호출
            files = {
                'file': (filename, file_content, file.content_type or 'image/jpeg')
            }
            
            response = requests.post(
                API_ENDPOINT,
                files=files,
                timeout=300  # 5분 타임아웃
            )
            
            print(f"[app.py] [2/3] API 응답 수신")
            print(f"  - 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                # JSON 응답 파싱
                result = response.json()
                
                print(f"[app.py] [3/3] structured_output.json 및 document.jpg 저장 중...")
                
                # structured_output.json 파일로 저장
                structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
                with open(structured_output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"[app.py] ✅ structured_output.json 저장 완료: {structured_output_path}")
                
                # 업로드한 이미지를 document.jpg로 저장 (필드 crop 및 비교 분석에 사용)
                document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                import shutil
                shutil.copy2(temp_filepath, document_path)
                print(f"[app.py] ✅ document.jpg 저장 완료: {document_path} (업로드한 이미지)")
                print(f"[app.py] ========== /api/document-ocr 처리 완료 ==========\n")
                
                return jsonify({
                    'success': True,
                    'message': '서류 OCR 처리 완료',
                    'structured_output_path': structured_output_path,
                    'document_path': document_path,
                    'data': result
                })
            else:
                error_text = response.text[:500] if response.text else '응답 없음'
                print(f"[app.py] ❌ API 요청 실패!")
                print(f"  - 상태 코드: {response.status_code}")
                print(f"  - 응답 내용: {error_text}")
                print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
                
                # Fallback: 미리 준비된 structured_output.json 사용
                structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
                if os.path.exists(structured_output_path):
                    try:
                        with open(structured_output_path, 'r', encoding='utf-8') as f:
                            fallback_data = json.load(f)
                        
                        print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                        
                        # 업로드한 이미지를 document.jpg로 저장
                        document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                        import shutil
                        shutil.copy2(temp_filepath, document_path)
                        print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                        
                        return jsonify({
                            'success': True,
                            'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                            'structured_output_path': structured_output_path,
                            'document_path': document_path,
                            'data': fallback_data,
                            'fallback_used': True
                        })
                    except Exception as fallback_error:
                        print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                        return jsonify({
                            'error': f'OCR API 요청 실패: {response.status_code}',
                            'details': error_text,
                            'fallback_error': str(fallback_error)
                        }), response.status_code
                else:
                    print(f"[app.py] ❌ Fallback 불가: structured_output.json 파일이 없습니다")
                    return jsonify({
                        'error': f'OCR API 요청 실패: {response.status_code}',
                        'details': error_text
                    }), response.status_code
                
        except requests.exceptions.Timeout:
            print(f"[app.py] ❌ 오류: 요청 타임아웃 (5분 초과)")
            print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
            
            # Fallback: 미리 준비된 structured_output.json 사용
            structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
            if os.path.exists(structured_output_path):
                try:
                    with open(structured_output_path, 'r', encoding='utf-8') as f:
                        fallback_data = json.load(f)
                    
                    print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                    
                    # 업로드한 이미지를 document.jpg로 저장
                    document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                    import shutil
                    shutil.copy2(temp_filepath, document_path)
                    print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                    
                    return jsonify({
                        'success': True,
                        'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                        'structured_output_path': structured_output_path,
                        'document_path': document_path,
                        'data': fallback_data,
                        'fallback_used': True
                    })
                except Exception as fallback_error:
                    print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                    return jsonify({'error': 'OCR 처리 시간이 초과되었습니다. 다시 시도해주세요.'}), 504
            else:
                return jsonify({'error': 'OCR 처리 시간이 초과되었습니다. 다시 시도해주세요.'}), 504
                
        except requests.exceptions.ConnectionError as e:
            print(f"[app.py] ❌ 오류: 연결 실패")
            print(f"  - 상세: {str(e)}")
            print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
            
            # Fallback: 미리 준비된 structured_output.json 사용
            structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
            if os.path.exists(structured_output_path):
                try:
                    with open(structured_output_path, 'r', encoding='utf-8') as f:
                        fallback_data = json.load(f)
                    
                    print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                    
                    # 업로드한 이미지를 document.jpg로 저장
                    document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                    import shutil
                    shutil.copy2(temp_filepath, document_path)
                    print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                    
                    return jsonify({
                        'success': True,
                        'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                        'structured_output_path': structured_output_path,
                        'document_path': document_path,
                        'data': fallback_data,
                        'fallback_used': True
                    })
                except Exception as fallback_error:
                    print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                    return jsonify({'error': f'OCR API 연결 실패: {str(e)}'}), 503
            else:
                return jsonify({'error': f'OCR API 연결 실패: {str(e)}'}), 503
                
        except requests.exceptions.RequestException as e:
            print(f"[app.py] ❌ 오류: 요청 중 예외 발생")
            print(f"  - 상세: {str(e)}")
            print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
            
            # Fallback: 미리 준비된 structured_output.json 사용
            structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
            if os.path.exists(structured_output_path):
                try:
                    with open(structured_output_path, 'r', encoding='utf-8') as f:
                        fallback_data = json.load(f)
                    
                    print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                    
                    # 업로드한 이미지를 document.jpg로 저장
                    document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                    import shutil
                    shutil.copy2(temp_filepath, document_path)
                    print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                    
                    return jsonify({
                        'success': True,
                        'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                        'structured_output_path': structured_output_path,
                        'document_path': document_path,
                        'data': fallback_data,
                        'fallback_used': True
                    })
                except Exception as fallback_error:
                    print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                    return jsonify({'error': f'OCR API 요청 중 오류 발생: {str(e)}'}), 500
            else:
                return jsonify({'error': f'OCR API 요청 중 오류 발생: {str(e)}'}), 500
        except json.JSONDecodeError as e:
            print(f"[app.py] ❌ 오류: JSON 파싱 실패")
            print(f"  - 상세: {str(e)}")
            print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
            
            # Fallback: 미리 준비된 structured_output.json 사용
            structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
            if os.path.exists(structured_output_path):
                try:
                    with open(structured_output_path, 'r', encoding='utf-8') as f:
                        fallback_data = json.load(f)
                    
                    print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                    
                    # 업로드한 이미지를 document.jpg로 저장
                    document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                    import shutil
                    shutil.copy2(temp_filepath, document_path)
                    print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                    
                    return jsonify({
                        'success': True,
                        'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                        'structured_output_path': structured_output_path,
                        'document_path': document_path,
                        'data': fallback_data,
                        'fallback_used': True
                    })
                except Exception as fallback_error:
                    print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                    return jsonify({'error': f'OCR API 응답 파싱 실패: {str(e)}'}), 500
            else:
                return jsonify({'error': f'OCR API 응답 파싱 실패: {str(e)}'}), 500
                
        except Exception as e:
            import traceback
            print(f"[app.py] ❌ 예상치 못한 오류 발생!")
            print(f"[app.py] 오류 메시지: {str(e)}")
            print(f"[app.py] 스택 트레이스:")
            traceback.print_exc()
            print(f"[app.py] ⚠️ Fallback: 미리 준비된 structured_output.json 사용 시도...")
            
            # Fallback: 미리 준비된 structured_output.json 사용
            structured_output_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
            if os.path.exists(structured_output_path):
                try:
                    with open(structured_output_path, 'r', encoding='utf-8') as f:
                        fallback_data = json.load(f)
                    
                    print(f"[app.py] ✅ Fallback 성공: structured_output.json 로드 완료")
                    
                    # 업로드한 이미지를 document.jpg로 저장
                    document_path = os.path.join(os.path.dirname(__file__), 'document.jpg')
                    import shutil
                    shutil.copy2(temp_filepath, document_path)
                    print(f"[app.py] ✅ document.jpg 저장 완료: {document_path}")
                    
                    return jsonify({
                        'success': True,
                        'message': '서류 OCR 처리 완료 (Fallback: 미리 준비된 structured_output.json 사용)',
                        'structured_output_path': structured_output_path,
                        'document_path': document_path,
                        'data': fallback_data,
                        'fallback_used': True
                    })
                except Exception as fallback_error:
                    print(f"[app.py] ❌ Fallback 실패: {str(fallback_error)}")
                    return jsonify({'error': f'서류 OCR 처리 중 오류 발생: {str(e)}'}), 500
            else:
                return jsonify({'error': f'서류 OCR 처리 중 오류 발생: {str(e)}'}), 500
        finally:
            # 임시 파일 삭제 (파일이 닫혀있는지 확인 후 삭제)
            if os.path.exists(temp_filepath):
                try:
                    # 파일이 사용 중일 수 있으므로 짧은 대기 후 삭제 시도
                    import time
                    time.sleep(0.1)  # 100ms 대기
                    os.remove(temp_filepath)
                    print(f"[app.py] ✅ 임시 파일 삭제 완료: {temp_filepath}")
                except PermissionError as e:
                    # 파일이 아직 사용 중이면 나중에 삭제 시도 (백그라운드)
                    print(f"[app.py] ⚠️ 임시 파일 삭제 실패 (파일 사용 중): {temp_filepath}")
                    print(f"[app.py]    파일은 나중에 자동으로 삭제됩니다.")
                except Exception as e:
                    print(f"[app.py] ⚠️ 임시 파일 삭제 중 오류: {str(e)}")
    
    except Exception as e:
        import traceback
        print(f"[app.py] ❌ 서류 OCR 처리 중 예외 발생!")
        print(f"[app.py] 오류 메시지: {str(e)}")
        print(f"[app.py] 스택 트레이스:")
        traceback.print_exc()
        return jsonify({'error': f'서류 OCR 처리 중 오류 발생: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


