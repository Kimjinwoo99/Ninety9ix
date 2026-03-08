"""
신분증 OCR 처리 모듈
독립적으로 신분증 이미지를 처리하여 정보를 추출하는 모듈
"""

import os
import re
import json
import base64
import numpy as np
import cv2
from PIL import Image
import easyocr
from typing import Dict, List, Optional, Tuple, Any

# EasyOCR 초기화 (한국어, 영어, 한문 지원)
ocr = easyocr.Reader(['ko', 'en'], gpu=False)
# 한문 특화 OCR (간체 중국어 - 영어와만 호환)
chinese_ocr = easyocr.Reader(['ch_sim', 'en'], gpu=False)
# 숫자 특화 OCR (숫자와 기본 기호만 인식)
number_ocr = easyocr.Reader(['en'], gpu=False)  # 영어 모델이 숫자 인식에 최적화됨


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
    
    Returns:
        base64 인코딩된 이미지 문자열
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
    
    Returns:
        base64 인코딩된 이미지 문자열 (또는 (base64, img_array) 튜플)
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
            
            # 마스킹 영역을 검은색으로 칠하기
            img[y_min:y_max, mask_start_x:mask_end_x] = 0
        
        # 이미지를 base64로 인코딩
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        if return_array:
            return (img_base64, img)
        return img_base64
    
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
        print(f"[idocr.py] 한문 OCR 오류: {str(e)}")
        return None
    
    return None


def clean_date_format(date_str):
    """발급일 문자열을 정리하여 yyyy.mm.dd 형식으로 변환 시도 (발급일 전용)"""
    if not date_str:
        return None
    
    # 공백 제거
    cleaned = re.sub(r'\s+', '', date_str)
    
    # 발급일 전용: 'i'와 'I'를 '1'로 변환 (숫자로 인식)
    # 예: "2019.I.25" -> "2019.1.25", "2019.i.25" -> "2019.1.25"
    cleaned = cleaned.replace('i', '1').replace('I', '1')
    # "Il", "l"을 "."로 변환 (구분자로 인식)
    cleaned = cleaned.replace('Il', '.').replace('l', '.')
    
    # 연속된 점을 하나로 통합
    cleaned = re.sub(r'\.+', '.', cleaned)
    
    # 숫자만 추출
    digits = re.findall(r'\d+', cleaned)
    
    if len(digits) >= 3:
        # 연도, 월, 일 추출
        year = digits[0]
        month = digits[1] if len(digits) > 1 else '1'
        day = digits[2] if len(digits) > 2 else '1'
        
        # 연도가 4자리가 아니면 보정
        if len(year) == 2:
            year_int = int(year)
            if year_int <= 30:
                year = f"20{year}"
            else:
                year = f"19{year}"
        elif len(year) != 4:
            return None
        
        # 월과 일이 1자리면 그대로, 2자리면 그대로 사용
        # yyyy.mm.dd 형식으로 조합
        return f"{year}.{month}.{day}"
    
    return None


def extract_date_with_reocr(image_path, bbox):
    """발급일 바운딩 박스 영역에 대해 숫자 특화 OCR 재실행하여 날짜 추출 (발급일 전용)"""
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
        
        # 숫자 특화 OCR 재실행 (number_ocr 사용)
        print(f"[idocr.py] 숫자 특화 OCR로 날짜 재인식 중...")
        ocr_results = number_ocr.readtext(cropped_img)
        
        if ocr_results:
            # OCR 결과에서 텍스트 추출
            date_texts = [result[1] for result in ocr_results]
            combined_date = ' '.join(date_texts).strip()
            
            print(f"[idocr.py] 재OCR 원본 결과: '{combined_date}'")
            
            # 공백 제거 및 정리
            combined_date = re.sub(r'\s+', '', combined_date)
            # 발급일 전용: 'i'와 'I'를 '1'로 변환 (숫자로 인식)
            # 예: "2019.I.25" -> "2019.1.25", "2019.i.25" -> "2019.1.25"
            combined_date = combined_date.replace('i', '1').replace('I', '1')
            # "Il", "l"을 "."로 변환 (구분자로 인식)
            combined_date = combined_date.replace('Il', '.').replace('l', '.')
            # 연속된 점을 하나로 통합
            combined_date = re.sub(r'\.+', '.', combined_date)
            
            print(f"[idocr.py] 재OCR 정리 후: '{combined_date}'")
            
            # 날짜 형식 검증 (YYYY.M.D 또는 YYYY.MM.DD, mm과 dd는 1 또는 01 둘 다 허용)
            date_pattern = r'^\d{4}\.\d{1,2}\.\d{1,2}$'
            if re.match(date_pattern, combined_date):
                print(f"[idocr.py] ✅ 재OCR 결과 형식 검증 통과: '{combined_date}'")
                return combined_date
            
            # 형식이 맞지 않으면 정리 시도
            cleaned_date = clean_date_format(combined_date)
            if cleaned_date and re.match(date_pattern, cleaned_date):
                print(f"[idocr.py] ✅ 정리 후 형식 검증 통과: '{cleaned_date}'")
                return cleaned_date
            
            print(f"[idocr.py] ❌ 재OCR 결과 형식 불일치: '{combined_date}'")
            return None
        
    except Exception as e:
        print(f"[idocr.py] 재OCR 처리 중 오류 발생: {str(e)}")
        return None
    
    return None


def format_resident_card_ocr(text_lines, image_path=None):
    """주민등록증 OCR 텍스트를 6줄로 정렬"""
    # 주민등록증인지 확인
    full_text = ' '.join([line[1] for line in text_lines])
    if '주민등록증' not in full_text:
        return None  # 주민등록증이 아니면 None 반환
    
    # 주민번호 패턴 찾기 (더 많은 패턴 추가)
    resident_patterns = [
        r'\d{6}[-]\d{7}',  # 기본: 501111-1234567
        r'\d{6}[-]\s*\d{1}\s*\d{6}',  # 공백 포함: 501111-1 234567
        r'\d{6}[-]\d{1}\s+\d{6}',  # 하이픈 후 공백: 501111-1 234567
        r'\d{6}[-]\s*\d{7}',  # 하이픈 후 공백: 501111- 1234567
        r'\d{6}[-]\d{1}\s*\d{6}',  # 하이픈 후 첫자리와 공백: 501111-1 234567
    ]
    
    resident_line_idx = None
    resident_number = None
    
    # 한 줄에 있는 경우
    for idx, (bbox, line_text, confidence) in enumerate(text_lines):
        # 먼저 패턴으로 찾기 시도
        for pattern in resident_patterns:
            matched = re.search(pattern, line_text)
            if matched:
                # 공백 제거하여 정규화
                resident_number = re.sub(r'\s+', '', matched.group())
                resident_line_idx = idx
                break
        
        # 패턴으로 찾지 못한 경우, 공백을 무시하고 숫자와 하이픈만으로 찾기
        if resident_line_idx is None:
            # 공백 제거한 텍스트에서 주민번호 패턴 찾기
            text_no_spaces = re.sub(r'\s+', '', line_text)
            flexible_pattern = r'\d{6}[-]\d{7}'
            matched = re.search(flexible_pattern, text_no_spaces)
            if matched:
                resident_number = matched.group()
                resident_line_idx = idx
                break
        
        if resident_line_idx is not None:
            break
    
    # 여러 줄에 걸쳐 있는 경우
    if resident_line_idx is None:
        for idx in range(len(text_lines) - 1):
            current_line = text_lines[idx][1]
            next_line = text_lines[idx + 1][1]
            
            # 여러 패턴 시도 (더 많은 패턴 추가)
            front_patterns = [
                r'(\d{6}[-])$',  # 501111-
                r'(\d{6}[-]\s*)$',  # 501111- (공백 포함)
                r'(\d{6}[-]\d{1})$',  # 501111-1
                r'(\d{6}[-]\d{1}\s*)$',  # 501111-1 (공백 포함)
            ]
            
            back_patterns = [
                r'^(\d{7})',  # 1234567
                r'^(\s*\d{7})',  #  1234567 (공백 포함)
                r'^(\d{1}\s*\d{6})',  # 1 234567
                r'^(\d{1}\s+\d{6})',  # 1  234567 (여러 공백)
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
        original_date_text = ' '.join(date_lines)
        combined_date = re.sub(r'\s+', ' ', original_date_text).strip()
        
        # 발급일(5번째 줄) 전용: 'i'와 'I'를 '1'로 변환 (숫자로 인식)
        # 예: "2019.I.25" -> "2019.1.25", "2019.i.25" -> "2019.1.25", "2019.Ii.25" -> "2019.11.25", "2019.Il.25" -> "2019.11.25"
        # 1단계: "Il", "il", "IL" 등을 먼저 "11"로 변환 (특수 케이스: I와 l이 함께 있으면 각각 1로 변환)
        combined_date = re.sub(r'[iI][lL]', '11', combined_date)
        # 2단계: 나머지 'i'와 'I'를 '1'로 변환
        combined_date = re.sub(r'[iI]', '1', combined_date)
        # 3단계: "l"을 "."로 변환 (구분자로 인식, 단독으로 있을 때만)
        combined_date = combined_date.replace('l', '.').replace('L', '.')
        
        # 공백 정리
        combined_date = re.sub(r'\s*\.\s*', '.', combined_date)
        # 연속된 점을 하나로 통합
        combined_date = re.sub(r'\.+', '.', combined_date)
        
        print(f"[idocr.py] 발급일 변환: '{original_date_text}' -> '{combined_date}'")
        
        # 날짜 형식 검증 (YYYY.M.D 또는 YYYY.MM.DD, mm과 dd는 1 또는 01 둘 다 허용)
        date_pattern = r'^\d{4}\.\d{1,2}\.\d{1,2}$'
        is_valid_format = re.match(date_pattern, combined_date)
        
        # 형식이 맞지 않으면 숫자 특화 OCR로 재시도
        if not is_valid_format:
            print(f"[idocr.py] 발급일 형식 검증 실패: '{combined_date}' -> 숫자 특화 OCR 재시도")
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
                    
                    # 숫자 특화 OCR로 재시도
                    reocr_date = extract_date_with_reocr(image_path, combined_bbox)
                    if reocr_date:
                        # 재OCR 결과도 형식 검증
                        if re.match(date_pattern, reocr_date):
                            print(f"[idocr.py] ✅ 재OCR 성공: '{reocr_date}'")
                            combined_date = reocr_date
                        else:
                            print(f"[idocr.py] ⚠️ 재OCR 결과도 형식 불일치: '{reocr_date}'")
                            # 재OCR 결과를 정리해서 다시 시도
                            cleaned_date = clean_date_format(reocr_date)
                            if cleaned_date and re.match(date_pattern, cleaned_date):
                                print(f"[idocr.py] ✅ 정리 후 형식 일치: '{cleaned_date}'")
                                combined_date = cleaned_date
                            else:
                                print(f"[idocr.py] ❌ 최종적으로 형식 불일치, 원본 사용: '{combined_date}'")
                    else:
                        print(f"[idocr.py] ❌ 재OCR 실패, 원본 사용: '{combined_date}'")
        
        # 최종 형식 검증
        # ========== 시연용 발급일 하드코딩 (주석 해제 시 활성화) ==========
        HARDCODE_ISSUE_DATE = False  # False로 변경하거나 주석처리하면 정상 모드
        HARDCODED_DATE = "2019.11.25"  # 시연용 하드코딩된 발급일
        # =================================================================
        
        if not re.match(date_pattern, combined_date):
            print(f"[idocr.py] ⚠️ 최종 발급일 형식 불일치: '{combined_date}'")
            # 시연용: 형식이 맞지 않으면 하드코딩된 날짜로 대체
            if HARDCODE_ISSUE_DATE:
                print(f"[idocr.py] 🔧 시연 모드: 발급일을 하드코딩된 값으로 대체: '{HARDCODED_DATE}'")
                combined_date = HARDCODED_DATE
        else:
            print(f"[idocr.py] ✅ 발급일 형식 검증 통과: '{combined_date}'")
        
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


def extract_info_from_ocr(text_lines, image_path=None):
    """OCR 결과에서 성명, 주민번호, 주소, 발급일 추출 및 바운딩 박스 정보 반환"""
    result = {
        'name': '',
        'resident_number': '',
        'address': '',
        'issue_date': '',
        'name_bbox': None,
        'resident_bbox': None,
        'address_bbox': None,
        'issue_date_bbox': None
    }
    
    # 주민등록증인 경우 정렬된 텍스트에서 추출
    formatted_text = format_resident_card_ocr(text_lines, image_path=image_path)
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
        
        # 5번째 줄에서 발급일 추출
        if len(formatted_lines) >= 5:
            result['issue_date'] = formatted_lines[4].strip()
        
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
        
        # 발급일 바운딩 박스 찾기 (5번째 줄에 해당하는 원본 OCR 줄)
        # 재추출과 무관하게 무조건 첫 OCR 결과의 원본 텍스트(예: "2019...25")를 기준으로 bbox를 찾음
        # 재추출된 텍스트(예: "2019.25")와 매칭하지 않고, 원본 OCR 결과에서 날짜 패턴을 직접 찾음
        issue_date_bboxes = []
        
        # 주민번호 위치를 먼저 찾기 (주소 위치 찾기보다 더 정확함)
        resident_line_idx = None
        for idx, (bbox, line_text, confidence) in enumerate(text_lines):
            if re.search(r'\d{6}[-]', line_text):
                resident_line_idx = idx
                break
        
        # 주민번호가 여러 줄에 걸쳐 있을 수 있음
        if resident_line_idx is not None:
            # 주민번호 뒷자리가 다음 줄에 있는지 확인
            start_search_idx = resident_line_idx + 1
            if resident_line_idx + 1 < len(text_lines):
                next_line = text_lines[resident_line_idx + 1][1]
                if re.search(r'^\d{7}', next_line.strip()) or re.search(r'^\d{1}\s*\d{6}', next_line.strip()):
                    start_search_idx = resident_line_idx + 2
            
            # 주민번호 다음 줄부터 날짜 찾기 (구청장/청장인 전까지)
            print(f"[idocr.py] 발급일 검색 시작 인덱스: {start_search_idx} (주민번호 인덱스: {resident_line_idx})")
            for idx in range(start_search_idx, len(text_lines)):
                bbox, line_text, confidence = text_lines[idx]
                
                # 구청장, 청장인 등이 나오면 종료
                if '구청장' in line_text or '청장인' in line_text:
                    print(f"[idocr.py] 구청장/청장인 발견으로 검색 종료: '{line_text}' (인덱스: {idx})")
                    break
                
                # 원본 OCR 텍스트에서 날짜 패턴 찾기 (재추출된 텍스트와 무관)
                # "2019...25", "2019.25", "2019 Il 25", "2019 Il. 25" 등 다양한 형식 허용
                # 4자리 연도가 있고, 점이나 Il, l, I 등이 포함되어 있으면 날짜로 간주
                if re.search(r'\d{4}', line_text):
                    # 점, Il, l, I 등이 포함되어 있거나, 다음 줄에 숫자가 있으면 날짜로 간주
                    has_date_marker = '.' in line_text or 'Il' in line_text or 'l' in line_text or 'I' in line_text
                    has_next_line_number = False
                    if idx + 1 < len(text_lines):
                        next_line = text_lines[idx + 1][1]
                        if re.search(r'\d{1,2}', next_line.strip()) and ('구청장' not in next_line and '청장인' not in next_line):
                            has_next_line_number = True
                    
                    if has_date_marker or has_next_line_number:
                        issue_date_bboxes.append(bbox)
                        print(f"[idocr.py] 발급일 원본 텍스트 발견: '{line_text}' (인덱스: {idx})")
                        # 다음 줄도 확인 (날짜가 두 줄에 걸쳐 있을 수 있음)
                        if has_next_line_number:
                            next_bbox, next_line, next_conf = text_lines[idx + 1]
                            issue_date_bboxes.append(next_bbox)
                            print(f"[idocr.py] 발급일 다음 줄 텍스트: '{next_line}' (인덱스: {idx + 1})")
                        break
        
        # 바운딩 박스 합치기 (재추출 결과와 무관하게 항상 첫 OCR 결과의 원본 텍스트 기준)
        if issue_date_bboxes:
            all_x = []
            all_y = []
            for bbox in issue_date_bboxes:
                for point in bbox:
                    all_x.append(point[0])
                    all_y.append(point[1])
            if all_x and all_y:
                result['issue_date_bbox'] = [
                    [min(all_x), min(all_y)],
                    [max(all_x), min(all_y)],
                    [max(all_x), max(all_y)],
                    [min(all_x), max(all_y)]
                ]
                print(f"[idocr.py] ✅ 발급일 bbox 찾기 완료 (첫 OCR 원본 텍스트 기준): {len(issue_date_bboxes)}개 줄")
        else:
            print(f"[idocr.py] ⚠️ 발급일 bbox를 찾을 수 없음 (첫 OCR 원본 텍스트에서)")
            # 디버깅: 모든 텍스트 라인 출력
            print(f"[idocr.py] 디버깅: 전체 텍스트 라인 ({len(text_lines)}개):")
            for idx, (bbox, line_text, confidence) in enumerate(text_lines):
                print(f"  [{idx}] {line_text}")
        
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
                            resident_line_idx = idx
                            break
                    if result['resident_number']:
                        break
                if result['resident_number']:
                    break
            if result['resident_number']:
                break
    
    # 이름 추출 (주민번호 위 줄들 중에서)
    if resident_line_idx is not None and resident_line_idx > 0:
        # 주민번호 위 3줄까지 확인
        for check_idx in range(max(0, resident_line_idx - 3), resident_line_idx):
            bbox, line_text, confidence = text_lines[check_idx]
            # 키워드 제외
            exclude_keywords = ['주민등록', '주민등록증', '운전면허', '운전면허증', '여권', '신분증']
            if any(keyword in line_text for keyword in exclude_keywords):
                continue
            # 한글 이름 패턴 (2-4자)
            name_match = re.search(r'([가-힣]{2,4})', line_text)
            if name_match:
                # 괄호 전까지 추출
                bracket_pos = line_text.find('(') if '(' in line_text else line_text.find('（')
                if bracket_pos != -1:
                    result['name'] = line_text[:bracket_pos].strip()
                else:
                    result['name'] = name_match.group(1)
                result['name_bbox'] = bbox
                break
    
    # 주소 추출 (주민번호 다음 줄부터)
    if resident_line_idx is not None:
        start_idx = resident_line_idx + 1
        # 주민번호 뒷자리가 다음 줄에 있으면 그 다음부터
        if resident_line_idx + 1 < len(text_lines):
            next_line = text_lines[resident_line_idx + 1][1]
            if re.search(r'^\d{7}', next_line.strip()) or re.search(r'^\d{1}\s*\d{6}', next_line.strip()):
                start_idx = resident_line_idx + 2
        
        address_lines = []
        address_bboxes = []
        
        for idx in range(start_idx, len(text_lines)):
            bbox, line_text, confidence = text_lines[idx]
            
            # 날짜 패턴이 있으면 주소 종료
            if re.search(r'\d{4}', line_text) and ('.' in line_text or 'Il' in line_text):
                break
            
            # 구청장, 청장인 등이 나오면 주소 종료
            if '구청장' in line_text or '청장인' in line_text:
                break
            
            # 주소로 간주할 수 있는 줄
            if re.search(r'[가-힣]', line_text) and len(line_text.strip()) > 1:
                address_lines.append(line_text.strip())
                address_bboxes.append(bbox)
                
                # 닫는 괄호가 있으면 포함하고 종료
                if ')' in line_text or '）' in line_text:
                    break
        
        if address_lines:
            result['address'] = ' '.join(address_lines)
            result['address'] = re.sub(r'\s+', ' ', result['address']).strip()
            
            # 주소 바운딩 박스 합치기
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


def process_id_card(image_path: str) -> Dict[str, Any]:
    """
    신분증 이미지를 처리하여 모든 정보를 추출하는 메인 함수
    
    Args:
        image_path: 신분증 이미지 파일 경로
    
    Returns:
        딕셔너리 형태의 결과:
        {
            'name': {
                'text': str,
                'bbox': List,
                'crop_image': str (base64)
            },
            'resident_number': {
                'text': str,
                'masked_text': str,
                'bbox': List,
                'crop_image': str (base64)
            },
            'address': {
                'text': str,
                'bbox': List,
                'crop_image': str (base64)
            },
            'ocr_text': str,
            'masked_image': str (base64),
            'ocr_lines': List (JSON 직렬화 가능한 OCR 결과)
        }
    """
    print(f"[idocr.py] ========== OCR 처리 시작 ==========")
    print(f"[idocr.py] 이미지 경로: {image_path}")
    
    try:
        # OCR 수행
        print(f"[idocr.py] [1/7] EasyOCR 초기 OCR 수행 중...")
        ocr_result = ocr.readtext(image_path)
        print(f"[idocr.py] [1/7] ✅ OCR 완료: {len(ocr_result)}개 텍스트 라인 발견")
        
        if not ocr_result:
            print(f"[idocr.py] ❌ OCR 결과 없음")
            return {
                'success': False,
                'error': 'OCR 결과를 찾을 수 없습니다.'
            }
        
        # 정보 추출
        print(f"[idocr.py] [2/7] 정보 추출 중 (성명, 주민번호, 주소, 발급일)...")
        extracted_info = extract_info_from_ocr(ocr_result, image_path=image_path)
        print(f"[idocr.py] [2/7] ✅ 정보 추출 완료:")
        print(f"  - 성명: {extracted_info.get('name', '추출 실패')}")
        print(f"  - 주민번호: {extracted_info.get('resident_number', '추출 실패')}")
        print(f"  - 주소: {extracted_info.get('address', '추출 실패')[:50]}...")
        print(f"  - 발급일: {extracted_info.get('issue_date', '추출 실패')}")
        
        # 원본 주민번호 저장 (마스킹 전)
        original_resident_number = extracted_info['resident_number']
        
        # 주민번호 마스킹 처리
        print(f"[idocr.py] [3/7] 주민번호 마스킹 처리 중...")
        masked_resident_number = None
        if extracted_info['resident_number']:
            masked_resident_number = mask_resident_number(extracted_info['resident_number'])
            print(f"[idocr.py] [3/7] ✅ 마스킹 완료: {masked_resident_number}")
        
        # 마스킹된 이미지 생성 (주민번호 crop에 사용)
        print(f"[idocr.py] [4/7] 마스킹된 이미지 생성 중...")
        masked_image_base64 = None
        masked_image_array = None
        if original_resident_number:
            masked_result = create_masked_image(image_path, ocr_result, original_resident_number, return_array=True)
            if masked_result:
                masked_image_base64, masked_image_array = masked_result
                print(f"[idocr.py] [4/7] ✅ 마스킹된 이미지 생성 완료")
            else:
                print(f"[idocr.py] [4/7] ⚠️ 마스킹된 이미지 생성 실패")
        else:
            print(f"[idocr.py] [4/7] ⚠️ 주민번호 없음, 마스킹 이미지 생성 스킵")
        
        # 각 필드의 crop 이미지 생성
        print(f"[idocr.py] [5/7] Crop 이미지 생성 중...")
        name_crop = crop_image_region(image_path, extracted_info.get('name_bbox'))
        print(f"[idocr.py] [5/7]   - 성명 crop: {'✅' if name_crop else '❌'}")
        # 주민번호는 마스킹된 이미지에서 crop
        if masked_image_array is not None:
            resident_crop = crop_image_region(image_path, extracted_info.get('resident_bbox'), img_array=masked_image_array)
        else:
            resident_crop = crop_image_region(image_path, extracted_info.get('resident_bbox'))
        print(f"[idocr.py] [5/7]   - 주민번호 crop: {'✅' if resident_crop else '❌'}")
        address_crop = crop_image_region(image_path, extracted_info.get('address_bbox'))
        print(f"[idocr.py] [5/7]   - 주소 crop: {'✅' if address_crop else '❌'}")
        # 발급일은 마스킹된 이미지에서 crop
        if masked_image_array is not None:
            issue_date_crop = crop_image_region(image_path, extracted_info.get('issue_date_bbox'), img_array=masked_image_array)
        else:
            issue_date_crop = crop_image_region(image_path, extracted_info.get('issue_date_bbox'))
        print(f"[idocr.py] [5/7]   - 발급일 crop: {'✅' if issue_date_crop else '❌'}")
        print(f"[idocr.py] [5/7] ✅ Crop 이미지 생성 완료")
        
        # OCR 텍스트 포맷팅
        print(f"[idocr.py] [6/7] OCR 텍스트 포맷팅 중...")
        formatted_ocr_text = format_resident_card_ocr(ocr_result, image_path=image_path)
        if formatted_ocr_text:
            ocr_text = formatted_ocr_text
            print(f"[idocr.py] [6/7] ✅ 포맷팅 완료: {len(formatted_ocr_text)} 문자")
        else:
            ocr_text = '\n'.join([line[1] for line in ocr_result])
            print(f"[idocr.py] [6/7] ⚠️ 포맷팅 실패, 원본 텍스트 사용: {len(ocr_text)} 문자")
        
        # OCR 결과를 JSON 직렬화 가능한 형태로 변환
        print(f"[idocr.py] [7/7] JSON 직렬화 변환 중...")
        serializable_ocr_result = convert_ocr_result_to_json_serializable(ocr_result)
        print(f"[idocr.py] [7/7] ✅ JSON 직렬화 완료")
        
        # 결과 구성
        print(f"[idocr.py] 결과 구성 중...")
        result = {
            'success': True,
            'name': {
                'text': extracted_info.get('name', ''),
                'bbox': convert_numpy_to_python(extracted_info.get('name_bbox')),
                'crop_image': name_crop
            },
            'resident_number': {
                'text': original_resident_number,
                'masked_text': masked_resident_number,
                'bbox': convert_numpy_to_python(extracted_info.get('resident_bbox')),
                'crop_image': resident_crop
            },
            'address': {
                'text': extracted_info.get('address', ''),
                'bbox': convert_numpy_to_python(extracted_info.get('address_bbox')),
                'crop_image': address_crop
            },
            'issue_date': {
                'text': extracted_info.get('issue_date', ''),
                'bbox': convert_numpy_to_python(extracted_info.get('issue_date_bbox')),
                'crop_image': issue_date_crop
            },
            'ocr_text': ocr_text,
            'masked_image': masked_image_base64,
            'ocr_lines': serializable_ocr_result
        }
        
        print(f"[idocr.py] ========== OCR 처리 완료 ==========")
        print(f"[idocr.py] 최종 결과:")
        print(f"  - 성공 여부: {result['success']}")
        print(f"  - 성명: {result['name']['text']}")
        print(f"  - 주민번호(마스킹): {result['resident_number']['masked_text']}")
        print(f"  - 주소: {result['address']['text'][:50]}...")
        print(f"  - 발급일: {result['issue_date']['text']}")
        print(f"  - Crop 이미지: 성명={bool(name_crop)}, 주민번호={bool(resident_crop)}, 주소={bool(address_crop)}, 발급일={bool(issue_date_crop)}")
        print(f"  - 마스킹 이미지: {bool(masked_image_base64)}")
        print(f"[idocr.py] =====================================")
        
        return result
        
    except Exception as e:
        import traceback
        print(f"[idocr.py] ❌ OCR 처리 중 오류 발생!")
        print(f"[idocr.py] 오류 메시지: {str(e)}")
        print(f"[idocr.py] 스택 트레이스:")
        traceback.print_exc()
        return {
            'success': False,
            'error': f'OCR 처리 중 오류 발생: {str(e)}'
        }

