"""
문서 검증 Agent 모듈
OpenAI GPT를 사용하여 신분증과 신청서를 검증하고 분석하는 Agent
완전히 독립적인 모듈로 설계되어 다른 시스템에서도 사용 가능

새로운 검증 로직:
1. 신분증 데이터 검증: 성명, 마스킹된 주민번호, 주소, 발급일의 형식과 누락 여부 판단
2. 신청서 필드 검증: 특정 필드의 누락 여부나 이상 여부 판단
3. 신분증과 신청서 비교: 성명만 비교
"""

import os
import json
import cv2
import base64
import numpy as np
import re
from typing import Dict, List, Any, Optional, Generator
from openai import OpenAI

# OpenAI 설정
# ⚠️ 주의: 실제 API 키를 **절대 코드에 직접 하드코딩하지 마세요.**
# - 로컬/서버 환경 변수로 OPENAI_API_KEY, OPENAI_MODEL 을 설정해서 사용합니다.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # 기본값: gpt-4o-mini

# OpenAI 클라이언트 초기화
client = None
agent_logs = []  # Agent 로그 저장소

def add_agent_log(message, level="info"):
    """Agent 로그 추가 (서버 콘솔 + 메모리 저장)"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        "level": level  # info, success, error, warning
    }
    agent_logs.append(log_entry)
    # 최근 100개만 유지
    if len(agent_logs) > 100:
        agent_logs.pop(0)
    
    # 서버 콘솔에도 출력
    icon = "ℹ️" if level == "info" else "✅" if level == "success" else "❌" if level == "error" else "⚠️"
    print(f"{icon} [Agent] {message}")

def get_agent_logs():
    """Agent 로그 반환"""
    return agent_logs[-50:]  # 최근 50개만 반환

# API KEY 확인 및 클라이언트 초기화
def initialize_client():
    """OpenAI 클라이언트 초기화 함수"""
    global client
    
    if client is not None:
        add_agent_log("클라이언트가 이미 초기화되어 있습니다.", "info")
        return client  # 이미 초기화됨
    
    add_agent_log("API KEY 확인 중...", "info")
    add_agent_log(f"API KEY 길이: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}", "info")
    
    if not OPENAI_API_KEY:
        add_agent_log("OPENAI_API_KEY가 비어있습니다.", "error")
        return None
    
    if OPENAI_API_KEY == "sk-your-api-key-here":
        add_agent_log("API KEY가 기본값입니다. 실제 API KEY를 입력하세요.", "error")
        return None
    
    if len(OPENAI_API_KEY) < 10:
        add_agent_log(f"API KEY가 너무 짧습니다. (길이: {len(OPENAI_API_KEY)})", "error")
        return None
    
    try:
        add_agent_log("OpenAI 클라이언트 생성 시도 중...", "info")
        add_agent_log(f"사용 모델: {OPENAI_MODEL}", "info")
        client = OpenAI(api_key=OPENAI_API_KEY)
        add_agent_log("OpenAI 클라이언트 초기화 완료!", "success")
        return client
    except Exception as e:
        add_agent_log(f"OpenAI 초기화 실패: {str(e)}", "error")
        add_agent_log(f"오류 타입: {type(e).__name__}", "error")
        client = None
        return None

# ============================================================================
# 신분증 데이터 검증 함수
# ============================================================================

def validate_id_card_name(name: str) -> Dict[str, Any]:
    """성명 검증"""
    if not name or not name.strip():
        return {
            "field": "name",
            "status": "MISSING",
            "reason": "성명이 누락되었습니다.",
            "value": ""
        }
    
    name = name.strip()
    
    # 한글 이름 형식 검증 (2-4자)
    if not re.match(r'^[가-힣]{2,4}$', name):
        return {
            "field": "name",
            "status": "INVALID_FORMAT",
            "reason": f"성명 형식이 올바르지 않습니다. (현재 값: {name})",
            "value": name
        }
    
    return {
        "field": "name",
        "status": "VALID",
        "reason": "성명이 정상적으로 추출되었습니다.",
        "value": name
    }

def validate_id_card_resident_number(resident_number: str) -> Dict[str, Any]:
    """마스킹된 주민번호 검증"""
    if not resident_number or not resident_number.strip():
        return {
            "field": "resident_number",
            "status": "MISSING",
            "reason": "주민번호가 누락되었습니다.",
            "value": ""
        }
    
    resident_number = resident_number.strip()
    
    # 주민번호 형식 검증: YYMMDD-XXXXXXX (뒷자리는 마스킹되어 X로 표시)
    pattern = r'^\d{6}-[X\d]{7}$'
    if not re.match(pattern, resident_number):
        return {
            "field": "resident_number",
            "status": "INVALID_FORMAT",
            "reason": f"주민번호 형식이 올바르지 않습니다. (현재 값: {resident_number})",
            "value": resident_number
        }
    
    # 앞자리 6자리 검증 (YYMMDD)
    front_part = resident_number[:6]
    try:
        year = int(front_part[:2])
        month = int(front_part[2:4])
        day = int(front_part[4:6])
        
        if month < 1 or month > 12:
            return {
                "field": "resident_number",
                "status": "INVALID_FORMAT",
                "reason": f"주민번호의 월이 올바르지 않습니다. (월: {month})",
                "value": resident_number
            }
        
        if day < 1 or day > 31:
            return {
                "field": "resident_number",
                "status": "INVALID_FORMAT",
                "reason": f"주민번호의 일이 올바르지 않습니다. (일: {day})",
                "value": resident_number
            }
    except ValueError:
        return {
            "field": "resident_number",
            "status": "INVALID_FORMAT",
            "reason": f"주민번호 앞자리가 숫자가 아닙니다. (현재 값: {front_part})",
            "value": resident_number
        }
    
    return {
        "field": "resident_number",
        "status": "VALID",
        "reason": "주민번호가 정상적으로 추출되었습니다.",
        "value": resident_number
    }

def validate_id_card_address(address: str) -> Dict[str, Any]:
    """주소 검증"""
    if not address or not address.strip():
        return {
            "field": "address",
            "status": "MISSING",
            "reason": "주소가 누락되었습니다.",
            "value": ""
        }
    
    address = address.strip()
    
    # 주소 최소 길이 검증
    if len(address) < 5:
        return {
            "field": "address",
            "status": "INVALID_FORMAT",
            "reason": f"주소가 너무 짧습니다. (현재 값: {address})",
            "value": address
        }
    
    # 한글이 포함되어야 함
    if not re.search(r'[가-힣]', address):
        return {
            "field": "address",
            "status": "INVALID_FORMAT",
            "reason": f"주소에 한글이 포함되어야 합니다. (현재 값: {address})",
            "value": address
        }
    
    return {
        "field": "address",
        "status": "VALID",
        "reason": "주소가 정상적으로 추출되었습니다.",
        "value": address
    }

def validate_id_card_issue_date(issue_date: str) -> Dict[str, Any]:
    """발급일 검증"""
    if not issue_date or not issue_date.strip():
        return {
            "field": "issue_date",
            "status": "MISSING",
            "reason": "발급일이 누락되었습니다.",
            "value": ""
        }
    
    issue_date = issue_date.strip()
    
    # 발급일 형식 검증: YYYY.M.D 또는 YYYY.MM.DD
    pattern = r'^\d{4}\.\d{1,2}\.\d{1,2}$'
    if not re.match(pattern, issue_date):
        return {
            "field": "issue_date",
            "status": "INVALID_FORMAT",
            "reason": f"발급일 형식이 올바르지 않습니다. (현재 값: {issue_date}, 예상 형식: YYYY.M.D 또는 YYYY.MM.DD)",
            "value": issue_date
        }
    
    # 날짜 유효성 검증
    try:
        parts = issue_date.split('.')
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        
        if year < 1900 or year > 2100:
            return {
                "field": "issue_date",
                "status": "INVALID_FORMAT",
                "reason": f"발급일의 연도가 올바르지 않습니다. (연도: {year})",
                "value": issue_date
            }
        
        if month < 1 or month > 12:
            return {
                "field": "issue_date",
                "status": "INVALID_FORMAT",
                "reason": f"발급일의 월이 올바르지 않습니다. (월: {month})",
                "value": issue_date
            }
        
        if day < 1 or day > 31:
            return {
                "field": "issue_date",
                "status": "INVALID_FORMAT",
                "reason": f"발급일의 일이 올바르지 않습니다. (일: {day})",
                "value": issue_date
            }
    except (ValueError, IndexError):
        return {
            "field": "issue_date",
            "status": "INVALID_FORMAT",
            "reason": f"발급일을 파싱할 수 없습니다. (현재 값: {issue_date})",
            "value": issue_date
        }
    
    return {
        "field": "issue_date",
        "status": "VALID",
        "reason": "발급일이 정상적으로 추출되었습니다.",
        "value": issue_date
    }

def validate_id_card_data(id_card_data: Dict) -> List[Dict[str, Any]]:
    """신분증 데이터 전체 검증"""
    validations = []
    
    # 성명 검증
    name = id_card_data.get('name', '')
    validations.append(validate_id_card_name(name))
    
    # 주민번호 검증 (마스킹된 값)
    resident_number = id_card_data.get('resident_number', '')
    validations.append(validate_id_card_resident_number(resident_number))
    
    # 주소 검증
    address = id_card_data.get('address', '')
    validations.append(validate_id_card_address(address))
    
    # 발급일 검증
    issue_date = id_card_data.get('issue_date', '')
    validations.append(validate_id_card_issue_date(issue_date))
    
    return validations

# ============================================================================
# 신청서 필드 검증 함수
# ============================================================================

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

def validate_form_field(structured_output: Dict, field_path: str, field_name: str, required: bool = True) -> Dict[str, Any]:
    """신청서 필드 검증 (고객 이름 필드는 제외)"""
    # 고객 이름 필드는 검증하지 않음
    if "고객 이름" in field_name or "이름" in field_name:
        return {
            "field": field_path,
            "field_name": field_name,
            "status": "SKIPPED",
            "reason": "고객 이름 필드는 검증하지 않습니다.",
            "value": None
        }
    """신청서 특정 필드 검증"""
    field_value = get_nested_value(structured_output, field_path)
    
    if not field_value:
        if required:
            return {
                "field": field_name,
                "field_path": field_path,
                "status": "MISSING",
                "reason": f"{field_name} 필드가 누락되었습니다.",
                "value": ""
            }
        else:
            return {
                "field": field_name,
                "field_path": field_path,
                "status": "OPTIONAL_MISSING",
                "reason": f"{field_name} 필드가 선택적으로 누락되었습니다.",
                "value": ""
            }
    
    # 필드 값 추출
    if isinstance(field_value, dict):
        text_value = field_value.get('text', '')
    elif isinstance(field_value, str):
        text_value = field_value
    else:
        text_value = str(field_value)
    
    if not text_value or not text_value.strip():
        if required:
            return {
                "field": field_name,
                "field_path": field_path,
                "status": "MISSING",
                "reason": f"{field_name} 필드의 값이 비어있습니다.",
                "value": ""
            }
        else:
            return {
                "field": field_name,
                "field_path": field_path,
                "status": "OPTIONAL_MISSING",
                "reason": f"{field_name} 필드의 값이 선택적으로 비어있습니다.",
                "value": ""
            }
    
    return {
        "field": field_name,
        "field_path": field_path,
        "status": "VALID",
        "reason": f"{field_name} 필드가 정상적으로 존재합니다.",
        "value": text_value
    }

def validate_form_data(structured_output: Dict) -> List[Dict[str, Any]]:
    """신청서 필드 전체 검증 (추후 정할 예정이므로 기본 필드들만 검증)"""
    validations = []
    
    # 기본 필수 필드들 (생년월일, 연락처, 주소, 고객 이름 제거 - 신청서 서류에서만)
    required_fields = [
        # ("change.customer_info.options[name='이름']", "고객 이름"),  # 신청서 서류에서 제거
        # ("change.birth", "생년월일"),  # 신청서 서류에서 제거
        # ("change.phone_num.options[name='연락처']", "연락처"),  # 신청서 서류에서 제거
    ]
    
    # 선택 필드들
    optional_fields = [
        ("change.service_num.options[name='서비스번호']", "서비스번호"),
        # ("change.address", "주소"),  # 신청서 서류에서 제거
    ]
    
    # 필수 필드 검증
    for field_path, field_name in required_fields:
        validations.append(validate_form_field(structured_output, field_path, field_name, required=True))
    
    # 선택 필드 검증
    for field_path, field_name in optional_fields:
        validations.append(validate_form_field(structured_output, field_path, field_name, required=False))
    
    return validations

# ============================================================================
# 신분증과 신청서 비교 함수 (성명만)
# ============================================================================

def normalize_name(name):
    """이름 정규화 (공백, 중간점, 괄호 제거)"""
    if not name:
        return ""
    # 공백, 중간점, 괄호 제거
    normalized = re.sub(r'[\s·()（）]', '', name)
    return normalized

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

def compare_name_only(id_card_name: str, form_name: str) -> Dict[str, Any]:
    """성명만 비교"""
    if not id_card_name or not id_card_name.strip():
        return {
            "field": "name_comparison",
            "status": "MISSING_ID",
            "reason": "신분증의 성명이 없습니다.",
            "id_card_value": "",
            "form_value": form_name
        }
    
    if not form_name or not form_name.strip():
        return {
            "field": "name_comparison",
            "status": "MISSING_FORM",
            "reason": "신청서의 성명이 없습니다.",
            "id_card_value": id_card_name,
            "form_value": ""
        }
    
    # 이름 정규화
    norm_id = normalize_name(id_card_name)
    norm_form = normalize_name(form_name)
    
    # 정확히 일치
    if norm_id == norm_form:
        return {
            "field": "name_comparison",
            "status": "MATCH",
            "reason": "성명이 일치합니다.",
            "id_card_value": id_card_name,
            "form_value": form_name
        }
    
    # 유사도 계산
    max_len = max(len(norm_id), len(norm_form))
    if max_len == 0:
        distance = 0
    else:
        distance = levenshtein_distance(norm_id, norm_form)
        similarity = 1 - (distance / max_len)
    
    # 1글자 차이까지는 유사로 판단
    if distance <= 1:
        return {
            "field": "name_comparison",
            "status": "SIMILAR",
            "reason": f"성명이 유사하지만 다릅니다. (신분증: {id_card_name}, 신청서: {form_name})",
            "id_card_value": id_card_name,
            "form_value": form_name
        }
    
    # 완전히 다름
    return {
        "field": "name_comparison",
        "status": "MISMATCH",
        "reason": f"성명이 다릅니다. (신분증: {id_card_name}, 신청서: {form_name})",
        "id_card_value": id_card_name,
        "form_value": form_name
    }

# ============================================================================
# 체크된 항목 분석 함수
# ============================================================================

def find_all_checkboxes(data: Any, path: str = "", checkboxes: List[Dict] = None) -> List[Dict]:
    """structured_output.json을 재귀적으로 탐색하여 모든 체크박스 항목 찾기"""
    if checkboxes is None:
        checkboxes = []
    
    if isinstance(data, dict):
        # 'selected' 속성이 있고 'points' 속성이 있는 항목을 체크박스로 간주
        if 'selected' in data and 'points' in data:
            checkbox_info = {
                'path': path,
                'name': data.get('name', ''),
                'text': data.get('text', ''),
                'selected': data.get('selected', False)
            }
            checkboxes.append(checkbox_info)
        
        # 재귀적으로 모든 키 탐색
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            find_all_checkboxes(value, new_path, checkboxes)
    
    elif isinstance(data, list):
        # 리스트의 각 항목 탐색
        for idx, item in enumerate(data):
            new_path = f"{path}[{idx}]" if path else f"[{idx}]"
            find_all_checkboxes(item, new_path, checkboxes)
    
    return checkboxes

def analyze_checked_items(structured_output: Dict) -> Dict[str, Any]:
    """
    체크된 항목 분석 (필수체크항목 제외)
    
    필수체크항목: '필수', 'required', 'mandatory' 등의 키워드가 포함된 항목
    """
    all_checkboxes = find_all_checkboxes(structured_output)
    
    # 필수체크항목 키워드 (이름이나 텍스트에 포함되면 필수로 간주)
    required_keywords = ['필수', 'required', 'mandatory', '필수체크', '필수선택']
    
    checked_items = []
    required_items = []
    
    for checkbox in all_checkboxes:
        name = checkbox.get('name', '').lower()
        text = checkbox.get('text', '').lower()
        
        # 필수체크항목인지 확인
        is_required = any(keyword in name or keyword in text for keyword in required_keywords)
        
        if checkbox.get('selected', False):
            if is_required:
                required_items.append(checkbox)
            else:
                checked_items.append(checkbox)
    
    # 입력된 텍스트 추출 (selected가 true인 항목의 text 필드)
    input_texts = []
    for checkbox in all_checkboxes:
        if checkbox.get('selected', False):
            text = checkbox.get('text', '').strip()
            name = checkbox.get('name', '').strip()
            if text:
                input_texts.append(text)
            elif name:
                input_texts.append(name)
    
    return {
        'total_checked': len(checked_items) + len(required_items),
        'checked_items_count': len(checked_items),
        'required_items_count': len(required_items),
        'checked_items': [
            {
                'name': item.get('name', ''),
                'text': item.get('text', ''),
                'path': item.get('path', '')
            }
            for item in checked_items
        ],
        'input_texts': input_texts
    }

# ============================================================================
# Agent 시스템 프롬프트
# ============================================================================

AGENT_SYSTEM_PROMPT = """당신은 전자 신청서 심사용 전문 에이전트입니다.

당신의 역할:
1. 신분증 데이터(성명, 마스킹된 주민번호, 주소, 발급일)의 형식과 누락 여부를 검증
2. 신청서의 특정 필드에 대한 누락 여부나 이상 여부를 검증
3. 신분증과 신청서의 성명을 비교하여 일치 여부를 판단
4. 체크된 항목과 입력된 텍스트를 분석하여 고객 유형을 파악
5. 검증 결과를 바탕으로 사람이 이해하기 쉬운 리포트와 요약 생성

결과는 한국어로 작성하고, 전문적이면서도 이해하기 쉬운 형태로 제공하세요."""

# ============================================================================
# 메인 처리 함수
# ============================================================================

def process_documents(id_card_ocr: Dict, structured_output: Dict, ocr_lines: List = None) -> Generator[Dict[str, Any], None, None]:
    """
    문서 검증 및 분석 메인 함수 (독립적으로 동작)
    
    입력 데이터만 받아서 내부적으로 모든 처리를 수행하고,
    결과를 순차적으로 반환합니다.
    
    Args:
        id_card_ocr: 신분증 OCR 결과 (name, resident_number, address, issue_date 포함)
        structured_output: 신청서 structured_output.json 데이터
        ocr_lines: OCR 라인 정보 (선택사항, 사용하지 않음)
    
    Yields:
        각 단계별 결과 딕셔너리:
        - {"step": "id_card_validation", "data": [...]}
        - {"step": "form_validation", "data": [...]}
        - {"step": "name_comparison", "data": {...}}
        - {"step": "summary", "data": {...}}
        - {"step": "report", "data": "..."}
        - {"step": "complete", "data": {...}}  # 최종 결과
    """
    add_agent_log("문서 검증 및 분석 시작", "info")
    
    # ========== 시연용 발급일 하드코딩 (주석 해제 시 활성화) ==========
    DEMO_MODE_ISSUE_DATE = False  # False로 변경하거나 주석처리하면 정상 모드
    HARDCODED_ISSUE_DATE = "2019.11.25"  # 시연용 하드코딩된 발급일
    # =================================================================
    
    # 시연 모드일 때 발급일 하드코딩
    if DEMO_MODE_ISSUE_DATE and id_card_ocr:
        original_issue_date = id_card_ocr.get('issue_date', '')
        id_card_ocr = id_card_ocr.copy()  # 원본 수정 방지
        id_card_ocr['issue_date'] = HARDCODED_ISSUE_DATE
        add_agent_log(f"시연 모드: 발급일을 '{original_issue_date}' -> '{HARDCODED_ISSUE_DATE}'로 변경", "info")
    
    try:
        # 1단계: 신분증 데이터 검증
        add_agent_log("1단계: 신분증 데이터 검증 중...", "info")
        id_card_validations = validate_id_card_data(id_card_ocr)
        yield {
            "step": "id_card_validation",
            "data": id_card_validations
        }
        add_agent_log("신분증 데이터 검증 완료", "success")
        
        # 2단계: 신청서 필드 검증
        add_agent_log("2단계: 신청서 필드 검증 중...", "info")
        form_validations = validate_form_data(structured_output)
        yield {
            "step": "form_validation",
            "data": form_validations
        }
        add_agent_log("신청서 필드 검증 완료", "success")
        
        # 3단계: 성명 비교
        add_agent_log("3단계: 성명 비교 중...", "info")
        id_card_name = id_card_ocr.get('name', '')
        
        # 신청서 성명: Application_date의 signarea의 text에서 가져오기
        form_name = ""
        application_date = structured_output.get('Application_date', {})
        if isinstance(application_date, dict):
            options = application_date.get('options', [])
            if isinstance(options, list):
                for option in options:
                    if isinstance(option, dict) and option.get('name') == 'signarea':
                        form_name = option.get('text', '')
                        break
        
        name_comparison = compare_name_only(id_card_name, form_name)
        yield {
            "step": "name_comparison",
            "data": name_comparison
        }
        add_agent_log("성명 비교 완료", "success")
        
        # 4단계: 체크된 항목 분석
        add_agent_log("4단계: 체크된 항목 분석 중...", "info")
        checked_items_analysis = analyze_checked_items(structured_output)
        add_agent_log(f"체크된 항목 분석 완료: 총 {checked_items_analysis['total_checked']}개 (필수 제외: {checked_items_analysis['checked_items_count']}개)", "success")
        
        # 5단계: 요약 생성
        add_agent_log("5단계: 요약 생성 중...", "info")
        
        # 신분증 검증 통계
        id_card_valid = len([v for v in id_card_validations if v['status'] == 'VALID'])
        id_card_missing = len([v for v in id_card_validations if v['status'] == 'MISSING'])
        id_card_invalid = len([v for v in id_card_validations if v['status'] == 'INVALID_FORMAT'])
        
        # 신청서 검증 통계
        form_valid = len([v for v in form_validations if v['status'] == 'VALID'])
        form_missing = len([v for v in form_validations if v['status'] == 'MISSING'])
        form_optional_missing = len([v for v in form_validations if v['status'] == 'OPTIONAL_MISSING'])
        
        # 성명 비교 결과
        name_match = name_comparison['status'] == 'MATCH'
        name_mismatch = name_comparison['status'] == 'MISMATCH'
        name_similar = name_comparison['status'] == 'SIMILAR'
        
        # 전체 필드 수 (유효 + 누락)
        total_fields = len(id_card_validations) + len(form_validations)
        total_valid = id_card_valid + form_valid
        total_missing = id_card_missing + form_missing
        total_warnings = id_card_invalid + (1 if name_mismatch or name_similar else 0)
        
        summary = {
            'total_fields': total_fields,  # 전체 필드 (유효 + 누락)
            'valid': total_valid,  # 유효
            'missing': total_missing,  # 누락
            'warnings': total_warnings,  # 경고 (형식 오류 + 성명 불일치/유사)
            'id_card_validation': {
                'total': len(id_card_validations),
                'valid': id_card_valid,
                'missing': id_card_missing,
                'invalid_format': id_card_invalid
            },
            'form_validation': {
                'total': len(form_validations),
                'valid': form_valid,
                'missing': form_missing,
                'optional_missing': form_optional_missing
            },
            'name_comparison': {
                'match': name_match,
                'mismatch': name_mismatch,
                'similar': name_similar,
                'status': name_comparison['status']
            },
            'checked_items_analysis': checked_items_analysis,
            'total_issues': id_card_missing + id_card_invalid + form_missing + (1 if name_mismatch else 0)
        }
        
        yield {
            "step": "summary",
            "data": summary
        }
        add_agent_log("요약 생성 완료", "success")
        
        # 6단계: GPT 리포트 생성
        add_agent_log("6단계: GPT 리포트 생성 중...", "info")
        agent_report = None
        customer_analysis_report = None
        recommendations_report = None
        agent_used = False
        
        global client
        if not client:
            client = initialize_client()
        
        if client:
            try:
                add_agent_log("GPT API 호출 준비 중...", "info")
                add_agent_log(f"모델: {OPENAI_MODEL}", "info")
                
                # 체크된 항목 정보 정리
                checked_items_info = ""
                if checked_items_analysis['checked_items_count'] > 0:
                    checked_items_info = f"""
## 체크된 항목 정보 (필수체크항목 제외):
- 총 체크된 항목 수: {checked_items_analysis['total_checked']}개
- 필수체크항목 제외 체크된 항목 수: {checked_items_analysis['checked_items_count']}개
- 체크된 항목 목록:
{json.dumps(checked_items_analysis['checked_items'], ensure_ascii=False, indent=2)}

## 입력된 텍스트:
{chr(10).join(f"- {text}" for text in checked_items_analysis['input_texts']) if checked_items_analysis['input_texts'] else "- 입력된 텍스트 없음"}
"""
                else:
                    checked_items_info = "\n## 체크된 항목: 없음 (필수체크항목만 체크됨 또는 체크된 항목 없음)\n"
                
                # ========== 시연용 프롬프트 설정 (주석 해제 시 활성화) ==========
                # 시연 중이므로 부정적이거나 누락된 내용, 일치하지 않는다는 내용을 제외하고 출력
                DEMO_MODE = False  # False로 변경하거나 주석처리하면 정상 모드
                # =================================================================
                
                # 분석 리포트용 프롬프트 (고객 유형 분석 및 심사 권고사항 제외)
                demo_instruction = ""
                if DEMO_MODE:
                    demo_instruction = """
**⚠️ 시연 모드 활성화**: 현재 시연 중이므로 다음 내용을 제외하고 출력해주세요:
- 부정적인 내용 (누락, 오류, 불일치 등)
- 문제점이나 개선이 필요한 사항
- 검증 실패나 경고 메시지

대신 긍정적이고 정상적인 내용만 강조하여 작성해주세요. 모든 항목이 정상적으로 처리되었다는 톤으로 작성해주세요.
"""
                
                analysis_user_message = f"""다음은 신분증과 신청서의 검증 결과입니다:

## 신분증 데이터 검증 결과:
{json.dumps(id_card_validations, ensure_ascii=False, indent=2)}

## 신청서 필드 검증 결과:
{json.dumps(form_validations, ensure_ascii=False, indent=2)}

이 검증 결과를 분석하여:
1. 전체 요약 (신분증 검증 통계, 신청서 검증 통계)
2. 각 검증 항목에 대한 상세 설명

**⚠️ 중요**: 
- 심사 권고사항과 고객 유형 분석은 포함하지 마세요.
- 성명 비교 결과는 절대 언급하지 마세요.{demo_instruction}"""

                # 심사 권고사항용 프롬프트
                recommendations_demo_instruction = ""
                if DEMO_MODE:
                    recommendations_demo_instruction = """
**⚠️ 시연 모드 활성화**: 현재 시연 중이므로 부정적인 권고사항이나 문제점을 제외하고, 
모든 항목이 정상적으로 처리되었다는 긍정적인 메시지만 작성해주세요.
"""
                
                recommendations_user_message = f"""다음은 신분증과 신청서의 검증 결과입니다:

## 신분증 데이터 검증 결과:
{json.dumps(id_card_validations, ensure_ascii=False, indent=2)}

## 신청서 필드 검증 결과:
{json.dumps(form_validations, ensure_ascii=False, indent=2)}

위 검증 결과를 바탕으로 **심사 권고사항**을 작성해주세요.

**⚠️ 심사 권고사항에는 반드시 다음을 포함해야 합니다:**

1. 누락된 필드에 대한 보완 요청 (단, 신청서의 성명 필드와 고객 이름 필드는 제외)
2. 형식 오류가 있는 경우 수정 요청
3. 신분증과 신청서 간 불일치가 있는 경우 해결 방안 (단, 신청서의 성명 필드는 중요하지 않으므로 언급하지 않음)
4. 선택적 필드에 대한 입력 권장사항

**중요**: 
- 신청서의 성명 필드 누락이나 불일치는 언급하지 마세요. 신분증의 성명만 확인하면 됩니다.
- "고객 이름" 필드 관련 내용은 절대 언급하지 마세요.
- 성명 비교 결과는 절대 출력하지 마세요. 성명 비교 관련 내용을 리포트에 포함하지 마세요.

각 권고사항은 구체적이고 실행 가능한 형태로 작성해주세요.
한국어로 작성해주세요.{recommendations_demo_instruction}"""

                # 고객 분석 리포트용 프롬프트
                customer_analysis_user_message = f"""다음은 체크된 항목과 입력된 텍스트 정보입니다:
{checked_items_info}

이 정보를 종합하여 **고객 유형 분석**을 작성해주세요.

고객 유형 분석에는 다음을 포함해야 합니다:
1. 체크된 항목을 기반으로 한 고객의 서비스 선택 분석
2. 입력된 텍스트를 기반으로 한 고객의 특성 분석
3. 종합적인 고객 유형 요약 (예: "이 고객은 TV 서비스를 선택한 고객으로, 자녀 안심 설정 기능을 사용하는 가족 고객입니다" 등)

**중요**: 체크된 항목의 이름, 텍스트, 입력된 텍스트를 종합하여 고객이 어떤 서비스를 선택했는지, 어떤 특성을 가진 고객인지를 명확하게 요약해주세요.

한국어로 작성해주세요."""

                # 고객 유형 한줄 요약 프롬프트
                customer_summary_user_message = f"""다음은 체크된 항목과 입력된 텍스트 정보입니다:
{checked_items_info}

이 정보를 기반으로 **고객 유형을 한 줄로 요약**해주세요.

**요구사항**:
- 문장 형식이 아닌 형용사/명사구 형식으로 작성
- 한 줄로 간결하게 작성 (50자 이내 권장)
- **반드시 고객이 선택한 주요 상품/서비스를 명시** (예: TV, 인터넷, 일반전화 등)
- 고객의 특성과 선호도를 포함
- 예시: "TV 서비스를 선택한 안정적인 장기 고객으로, 통신사에 대한 선호도가 뚜렷한 특성을 가진 고객"
- 예시: "TV와 인터넷 서비스를 선택한 가족 고객으로, 자녀 안심 설정 기능을 활용하는 특성"
- 예시: "인터넷과 일반전화를 이용하는 중년층 고객으로, 안정적인 통신 서비스를 선호하는 특성"

**형식**: 
- 문장이 아닌 형용사/명사구 형식으로 작성
- 마크다운이나 특수문자 없이 순수 텍스트로만 작성
- "~상품/서비스를 선택한 ~고객으로, ~특성" 또는 "~상품/서비스를 선택한 ~고객으로, ~특성을 가진 고객" 형식 사용
- 선택한 상품/서비스는 반드시 포함해야 함 (TV, 인터넷, 일반전화, 인터넷전화 등)

한국어로 작성해주세요."""

                # 1. 분석 리포트 생성
                analysis_messages = [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": analysis_user_message}
                ]
                
                add_agent_log("분석 리포트 GPT API 호출 중...", "info")
                analysis_response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=analysis_messages,
                    temperature=0.3,
                    max_tokens=2000
                )
                add_agent_log("분석 리포트 GPT API 호출 성공!", "success")
                add_agent_log(f"응답 토큰 수: {analysis_response.usage.total_tokens if hasattr(analysis_response, 'usage') else 'N/A'}", "info")
                
                agent_report = analysis_response.choices[0].message.content
                
                # 2. 심사 권고사항 리포트 생성
                recommendations_messages = [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": recommendations_user_message}
                ]
                
                add_agent_log("심사 권고사항 GPT API 호출 중...", "info")
                recommendations_response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=recommendations_messages,
                    temperature=0.3,
                    max_tokens=1500
                )
                add_agent_log("심사 권고사항 GPT API 호출 성공!", "success")
                add_agent_log(f"응답 토큰 수: {recommendations_response.usage.total_tokens if hasattr(recommendations_response, 'usage') else 'N/A'}", "info")
                
                recommendations_report = recommendations_response.choices[0].message.content
                
                # 3. 고객 분석 리포트 생성 (체크된 항목이 있는 경우만)
                customer_analysis_report = None
                customer_summary = ""  # 기본값을 빈 문자열로 설정
                if checked_items_analysis['checked_items_count'] > 0 or checked_items_analysis['input_texts']:
                    customer_analysis_messages = [
                        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": customer_analysis_user_message}
                    ]
                    
                    add_agent_log("고객 분석 리포트 GPT API 호출 중...", "info")
                    customer_analysis_response = client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=customer_analysis_messages,
                        temperature=0.3,
                        max_tokens=1500
                    )
                    add_agent_log("고객 분석 리포트 GPT API 호출 성공!", "success")
                    add_agent_log(f"응답 토큰 수: {customer_analysis_response.usage.total_tokens if hasattr(customer_analysis_response, 'usage') else 'N/A'}", "info")
                    
                    customer_analysis_report = customer_analysis_response.choices[0].message.content
                    
                    # 3-1. 고객 유형 한줄 요약 생성
                    try:
                        customer_summary_messages = [
                            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                            {"role": "user", "content": customer_summary_user_message}
                        ]
                        
                        add_agent_log("고객 유형 한줄 요약 GPT API 호출 중...", "info")
                        customer_summary_response = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=customer_summary_messages,
                            temperature=0.3,
                            max_tokens=100
                        )
                        add_agent_log("고객 유형 한줄 요약 GPT API 호출 성공!", "success")
                        add_agent_log(f"응답 토큰 수: {customer_summary_response.usage.total_tokens if hasattr(customer_summary_response, 'usage') else 'N/A'}", "info")
                        
                        customer_summary = customer_summary_response.choices[0].message.content.strip()
                        if not customer_summary:
                            customer_summary = "고객 유형 요약 생성 실패"
                    except Exception as summary_error:
                        add_agent_log(f"고객 유형 한줄 요약 GPT API 호출 실패: {str(summary_error)}", "error")
                        customer_summary = "고객 유형 요약 생성 실패"
                else:
                    customer_analysis_report = "체크된 항목이 없어 고객 유형 분석을 수행할 수 없습니다."
                    customer_summary = "체크된 항목 없음"
                    add_agent_log("체크된 항목 없음 - 고객 분석 리포트 스킵", "info")
                
                agent_used = True
                add_agent_log("GPT 리포트 생성 완료", "success")
            except Exception as e:
                add_agent_log(f"GPT API 호출 실패: {str(e)}", "error")
                add_agent_log("일반 리포트 생성으로 계속 진행", "warning")
                # 기본 리포트 생성
                agent_report = f"""## 검증 결과 요약

### 신분증 데이터 검증
- 총 {len(id_card_validations)}개 필드 검증
- 정상: {id_card_valid}개
- 누락: {id_card_missing}개
- 형식 오류: {id_card_invalid}개

### 신청서 필드 검증
- 총 {len(form_validations)}개 필드 검증
- 정상: {form_valid}개
- 누락: {form_missing}개
- 선택적 누락: {form_optional_missing}개
"""
                # 심사 권고사항 리포트 기본값 생성
                recommendations_report = f"""## 심사 권고사항

### 신분증 데이터 검증 관련
{chr(10).join(f"- {v.get('field', '알 수 없음')}: {v.get('reason', '')}" for v in id_card_validations if v.get('status') != 'VALID') if any(v.get('status') != 'VALID' for v in id_card_validations) else "- 모든 신분증 필드가 유효합니다."}

### 신청서 필드 검증 관련
{chr(10).join(f"- {v.get('field', '알 수 없음')}: {v.get('reason', '')}" for v in form_validations if v.get('status') != 'VALID') if any(v.get('status') != 'VALID' for v in form_validations) else "- 모든 신청서 필드가 유효합니다."}

**참고**: 위 권고사항은 기본 템플릿입니다. GPT API 호출 실패로 인해 상세한 권고사항을 생성할 수 없습니다."""

                # 고객 분석 리포트도 기본값 생성
                if checked_items_analysis['checked_items_count'] > 0 or checked_items_analysis['input_texts']:
                    customer_analysis_report = f"""## 고객 유형 분석

### 체크된 항목 정보
- 총 체크된 항목 수: {checked_items_analysis['total_checked']}개
- 필수체크항목 제외 체크된 항목 수: {checked_items_analysis['checked_items_count']}개

### 체크된 항목 목록
{chr(10).join(f"- {item.get('name', '이름 없음')}: {item.get('text', '텍스트 없음')}" for item in checked_items_analysis['checked_items'])}

### 입력된 텍스트
{chr(10).join(f"- {text}" for text in checked_items_analysis['input_texts']) if checked_items_analysis['input_texts'] else "- 입력된 텍스트 없음"}

**고객 유형 분석**: 체크된 항목과 입력된 텍스트를 기반으로 고객 유형을 분석할 수 없습니다. (GPT API 호출 실패)"""
                    customer_summary = "분석 불가 (GPT API 호출 실패)"
                else:
                    customer_analysis_report = "체크된 항목이 없어 고객 유형 분석을 수행할 수 없습니다."
                    customer_summary = "체크된 항목 없음"
        
        yield {
            "step": "report",
            "data": agent_report or "리포트 생성 실패",
            "agent_used": agent_used
        }
        
        # 심사 권고사항 리포트도 yield
        yield {
            "step": "recommendations",
            "data": recommendations_report or "심사 권고사항 생성 실패",
            "agent_used": agent_used
        }
        
        # 고객 분석 리포트도 yield
        yield {
            "step": "customer_analysis",
            "data": customer_analysis_report or "고객 분석 리포트 생성 실패",
            "agent_used": agent_used
        }
        
        # 7단계: 최종 결과 반환
        # customer_summary가 None이면 빈 문자열로 설정
        if customer_summary is None:
            customer_summary = ""
            add_agent_log("⚠️ customer_summary가 None이어서 빈 문자열로 설정", "warning")
        
        add_agent_log(f"최종 customer_summary 값: '{customer_summary}'", "info")
        
        final_result = {
            'success': True,
            'id_card_validations': id_card_validations,
            'form_validations': form_validations,
            'name_comparison': name_comparison,
            'checked_items_analysis': checked_items_analysis,
            'summary': summary,
            'agent_report': agent_report or "",
            'recommendations_report': recommendations_report or "",
            'customer_analysis_report': customer_analysis_report or "",
            'customer_summary': customer_summary,
            'agent_used': agent_used,
            'agent_logs': get_agent_logs()
        }
        
        yield {
            "step": "complete",
            "data": final_result
        }
        
        add_agent_log("문서 검증 및 분석 완료", "success")
        
    except Exception as e:
        add_agent_log(f"문서 처리 중 오류 발생: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        yield {
            "step": "error",
            "data": {
                "success": False,
                "error": f"처리 중 오류 발생: {str(e)}"
            }
        }

# 모듈 로드 시 자동 초기화
add_agent_log("agent.py 모듈이 로드되었습니다.", "info")
client = initialize_client()
