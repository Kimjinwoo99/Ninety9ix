"""
체크박스 좌표 처리 Agent 모듈
structured_output.json의 좌표값을 토대로 체크박스 좌표가 들어오면 해당 항목을 true로 변경
OpenAI 에이전트를 사용하여 바운딩 박스 안에 없어도 가장 근처의 체크박스를 추론
완전히 독립적인 모듈로 설계되어 다른 시스템에서도 사용 가능
"""

import json
import math
import os
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI

# OpenAI 설정
# ⚠️ 주의: 실제 API 키를 **절대 코드에 직접 하드코딩하지 마세요.**
# - 로컬/서버 환경 변수로 OPENAI_API_KEY, OPENAI_MODEL 을 설정해서 사용합니다.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# OpenAI 클라이언트 초기화
openai_client = None

def initialize_openai_client():
    """OpenAI 클라이언트 초기화"""
    global openai_client
    
    if openai_client is not None:
        return openai_client
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-your-api-key-here":
        print("[CheckboxAgent] ⚠️ OpenAI API KEY가 설정되지 않았습니다.")
        return None
    
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[CheckboxAgent] ✅ OpenAI 클라이언트 초기화 완료")
        return openai_client
    except Exception as e:
        print(f"[CheckboxAgent] ❌ OpenAI 초기화 실패: {str(e)}")
        return None

# 모듈 로드 시 초기화
openai_client = initialize_openai_client()

# structured_output.json 미리 로드
_structured_output_cache = None
_checkboxes_cache = None

# bbox_labels.json 캐시
_bbox_labels_cache = None

def load_structured_output(filepath: str = None) -> Dict:
    """structured_output.json 파일을 로드하고 캐시에 저장"""
    global _structured_output_cache, _checkboxes_cache
    
    if filepath is None:
        # 기본 경로 사용
        default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
        filepath = default_path
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            _structured_output_cache = json.load(f)
        
        # 체크박스 목록도 미리 찾아서 캐시
        _checkboxes_cache = find_all_checkboxes(_structured_output_cache)
        
        print(f"[CheckboxAgent] ✅ structured_output.json 로드 완료: {len(_checkboxes_cache)}개 체크박스 발견")
        return _structured_output_cache
    except FileNotFoundError:
        print(f"[CheckboxAgent] ⚠️ 파일을 찾을 수 없습니다: {filepath}")
        return None
    except Exception as e:
        print(f"[CheckboxAgent] ❌ 파일 로드 오류: {str(e)}")
        return None

def get_cached_structured_output() -> Optional[Dict]:
    """캐시된 structured_output 반환"""
    return _structured_output_cache

def get_cached_checkboxes() -> Optional[List[Dict]]:
    """캐시된 체크박스 목록 반환"""
    return _checkboxes_cache

def load_bbox_labels(filepath: str = None) -> Dict:
    """bbox_labels.json 파일을 로드하고 캐시에 저장"""
    global _bbox_labels_cache
    
    if filepath is None:
        # 기본 경로 사용
        default_path = os.path.join(os.path.dirname(__file__), 'bbox_labels.json')
        filepath = default_path
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            _bbox_labels_cache = json.load(f)
        
        labels_count = len(_bbox_labels_cache.get('labels', []))
        print(f"[CheckboxAgent] ✅ bbox_labels.json 로드 완료: {labels_count}개 라벨 발견")
        return _bbox_labels_cache
    except FileNotFoundError:
        print(f"[CheckboxAgent] ⚠️ 파일을 찾을 수 없습니다: {filepath}")
        return None
    except Exception as e:
        print(f"[CheckboxAgent] ❌ 파일 로드 오류: {str(e)}")
        return None

def get_cached_bbox_labels() -> Optional[Dict]:
    """캐시된 bbox_labels 반환"""
    return _bbox_labels_cache

# 모듈 로드 시 자동으로 bbox_labels.json 로드 시도
_bbox_auto_loaded = False
def auto_load_bbox_labels():
    """자동으로 bbox_labels.json 로드 시도"""
    global _bbox_auto_loaded
    if not _bbox_auto_loaded:
        default_path = os.path.join(os.path.dirname(__file__), 'bbox_labels.json')
        if os.path.exists(default_path):
            load_bbox_labels(default_path)
        _bbox_auto_loaded = True

# 모듈 로드 시 자동 로드
auto_load_bbox_labels()

# 모듈 로드 시 자동으로 structured_output.json 로드 시도
_auto_loaded = False
def auto_load_structured_output():
    """자동으로 structured_output.json 로드 시도"""
    global _auto_loaded
    if not _auto_loaded:
        default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
        if os.path.exists(default_path):
            load_structured_output(default_path)
        _auto_loaded = True

# 모듈 로드 시 자동 로드
auto_load_structured_output()

# 로그 시스템
agent_logs = []

def add_log(message: str, level: str = "info"):
    """로그 추가"""
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
    
    # 콘솔에도 출력
    icon = "ℹ️" if level == "info" else "✅" if level == "success" else "❌" if level == "error" else "⚠️"
    print(f"{icon} [CheckboxAgent] {message}")

def get_logs() -> List[Dict]:
    """로그 목록 반환"""
    return agent_logs.copy()


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """두 점 사이의 유클리드 거리 계산"""
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


def get_center_point(points: List[List[float]]) -> Tuple[float, float]:
    """points 배열에서 중심점 계산"""
    if not points or len(points) == 0:
        return (0, 0)
    
    if len(points) == 1:
        return (points[0][0], points[0][1])
    
    # 모든 점의 평균 계산
    x_sum = sum(p[0] for p in points)
    y_sum = sum(p[1] for p in points)
    count = len(points)
    
    return (x_sum / count, y_sum / count)


def is_point_in_bbox(point: Tuple[float, float], bbox_points: List[List[float]], tolerance: float = 10.0) -> bool:
    """점이 바운딩 박스 안에 있는지 확인 (tolerance 허용)"""
    if not bbox_points or len(bbox_points) < 2:
        return False
    
    # bbox의 최소/최대 좌표 계산
    x_coords = [p[0] for p in bbox_points]
    y_coords = [p[1] for p in bbox_points]
    
    x_min = min(x_coords) - tolerance
    x_max = max(x_coords) + tolerance
    y_min = min(y_coords) - tolerance
    y_max = max(y_coords) + tolerance
    
    return x_min <= point[0] <= x_max and y_min <= point[1] <= y_max


def find_all_checkboxes(data: Any, path: str = "", checkboxes: List[Dict] = None) -> List[Dict]:
    """structured_output.json을 재귀적으로 탐색하여 모든 체크박스 항목 찾기"""
    if checkboxes is None:
        checkboxes = []
    
    if isinstance(data, dict):
        # 'selected' 속성이 있고 'points' 속성이 있는 항목을 체크박스로 간주
        if 'selected' in data and 'points' in data:
            checkbox_info = {
                'path': path,
                'data': data,
                'points': data.get('points', []),
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


def find_closest_checkbox(checkboxes: List[Dict], click_point: Tuple[float, float], 
                         use_bbox: bool = True, tolerance: float = 10.0) -> Optional[Dict]:
    """클릭한 좌표와 가장 가까운 체크박스 찾기"""
    if not checkboxes:
        return None
    
    closest = None
    min_distance = float('inf')
    
    for checkbox in checkboxes:
        points = checkbox.get('points', [])
        if not points:
            continue
        
        if use_bbox:
            # 바운딩 박스 안에 있는지 먼저 확인
            if is_point_in_bbox(click_point, points, tolerance):
                # 바운딩 박스 안에 있으면 중심점까지의 거리 계산
                center = get_center_point(points)
                distance = calculate_distance(click_point, center)
                
                if distance < min_distance:
                    min_distance = distance
                    closest = checkbox
        else:
            # 중심점까지의 거리만 계산
            center = get_center_point(points)
            distance = calculate_distance(click_point, center)
            
            if distance < min_distance:
                min_distance = distance
                closest = checkbox
    
    return closest


def find_text_from_bbox_labels(click_x: float, click_y: float) -> Optional[str]:
    """bbox_labels.json에서 좌표에 해당하는 텍스트 찾기"""
    bbox_labels = get_cached_bbox_labels()
    if not bbox_labels:
        add_log("⚠️ bbox_labels.json이 로드되지 않았습니다.", "warning")
        return None
    
    labels = bbox_labels.get('labels', [])
    if not labels:
        add_log("⚠️ bbox_labels.json에 라벨이 없습니다.", "warning")
        return None
    
    # 좌표가 bbox 안에 있는지 확인
    for label in labels:
        bbox = label.get('bbox', [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            # bbox 범위 확인 (약간의 여유 공간 허용)
            tolerance = 5
            if (x1 - tolerance <= click_x <= x2 + tolerance and 
                y1 - tolerance <= click_y <= y2 + tolerance):
                text = label.get('text', '')
                add_log(f"✅ bbox_labels에서 텍스트 찾음: {text}", "success")
                return text
    
    # 정확히 일치하는 것이 없으면 가장 가까운 것 찾기
    min_distance = float('inf')
    closest_text = None
    
    for label in labels:
        bbox = label.get('bbox', [])
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            distance = calculate_distance((click_x, click_y), (center_x, center_y))
            
            if distance < min_distance:
                min_distance = distance
                closest_text = label.get('text', '')
    
    if closest_text:
        add_log(f"✅ 가장 가까운 텍스트 찾음 (거리: {min_distance:.2f}): {closest_text}", "success")
        return closest_text
    
    add_log("❌ bbox_labels에서 텍스트를 찾을 수 없습니다.", "error")
    return None

def find_checkbox_by_text_with_ai(text: str, checkboxes: List[Dict]) -> Optional[Dict]:
    """텍스트를 기반으로 structured_output.json에서 체크박스 찾기 (GPT 사용)"""
    global openai_client
    
    if not openai_client:
        openai_client = initialize_openai_client()
        if not openai_client:
            return None
    
    if not text:
        add_log("❌ 텍스트가 비어있습니다.", "error")
        return None
    
    try:
        # 약관 확인 체크박스 우선 처리: "확인/"으로 시작하는 텍스트는 약관 확인 체크박스로 처리
        if text.strip().startswith("확인/"):
            add_log("📋 약관 확인 텍스트 감지: '확인' 체크박스 찾기", "info")
            # 체크박스 목록에서 "확인"이라는 name이나 text를 가진 체크박스 찾기
            for idx, checkbox in enumerate(checkboxes):
                checkbox_name = checkbox.get('name', '').strip()
                checkbox_text = checkbox.get('text', '').strip()
                # "확인"이라는 단어가 name이나 text에 정확히 포함되어 있는지 확인
                if checkbox_name == "확인" or checkbox_text == "확인":
                    add_log(f"✅ 약관 확인 체크박스 발견: index={idx}, name='{checkbox_name}', text='{checkbox_text}'", "success")
                    return checkbox
                # "확인"으로 시작하는 경우도 고려
                if checkbox_name.startswith("확인") or checkbox_text.startswith("확인"):
                    add_log(f"✅ 약관 확인 체크박스 발견 (시작): index={idx}, name='{checkbox_name}', text='{checkbox_text}'", "success")
                    return checkbox
        
        # 체크박스 정보를 정리
        checkbox_info = []
        for idx, checkbox in enumerate(checkboxes):
            checkbox_info.append({
                'index': idx,
                'name': checkbox.get('name', ''),
                'text': checkbox.get('text', ''),
                'path': checkbox.get('path', ''),
                'selected': checkbox.get('selected', False)
            })
        
        # OpenAI에 프롬프트 전달 (강제로 항목 찾기)
        system_prompt = """당신은 문서의 체크박스 매칭 전문가입니다.
주어진 텍스트 설명과 가장 적절하게 매칭되는 체크박스를 찾아야 합니다.
**중요: 반드시 목록 중 하나를 선택해야 합니다. 선택하지 못하면 안됩니다.**

**특별 규칙:**
- 텍스트가 "확인/"으로 시작하는 경우, 이것은 약관 확인 체크박스입니다. 반드시 name이나 text가 "확인"인 체크박스를 선택해야 합니다.
- "확인/" 뒤의 긴 설명은 무시하고, 오직 "확인" 체크박스만 선택하세요.

일반적인 경우:
- 텍스트 설명과 체크박스의 name, text를 비교하여 가장 적절한 매칭을 찾으세요.
- 유사한 의미, 동의어, 약어 등을 고려하여 매칭하세요.

응답은 반드시 JSON 형식으로 해주세요:
{
    "selected_index": 숫자 (0부터 시작하는 인덱스, 반드시 0 이상의 유효한 인덱스),
    "reason": "선택 이유 설명",
    "confidence": 숫자 (0.0 ~ 1.0, 매칭 신뢰도)
}"""

        # 약관 확인인지 여부를 프롬프트에 명시
        is_agreement_confirmation = text.strip().startswith("확인/")
        special_instruction = ""
        if is_agreement_confirmation:
            special_instruction = "\n**⚠️ 중요: 이 텍스트는 '확인/'으로 시작하는 약관 확인 텍스트입니다. 반드시 name이나 text가 '확인'인 체크박스를 선택해야 합니다. 텍스트의 나머지 부분(설명)은 무시하고 '확인' 체크박스만 선택하세요.**\n"

        user_prompt = f"""찾아야 할 텍스트: "{text}"
{special_instruction}
가능한 체크박스 목록:
{json.dumps(checkbox_info, ensure_ascii=False, indent=2)}

**반드시 위 목록 중 하나를 선택해야 합니다.**
텍스트 "{text}"와 가장 적절하게 매칭되는 체크박스의 index를 선택해주세요.
name과 text 필드를 모두 고려하여 매칭하세요."""

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        selected_index = result.get('selected_index')
        reason = result.get('reason', '')
        confidence = result.get('confidence', 0.0)
        
        add_log(f"AI 응답: selected_index={selected_index}, reason={reason}, confidence={confidence}", "info")
        
        # 유효한 인덱스인지 확인
        if selected_index is not None and isinstance(selected_index, int):
            if selected_index < 0 or selected_index >= len(checkboxes):
                add_log(f"⚠️ AI가 유효하지 않은 인덱스 선택: {selected_index}, 첫 번째로 대체", "warning")
                selected_index = 0
            
            add_log(f"✅ AI 추론 성공: {reason}", "success")
            return checkboxes[selected_index]
        else:
            add_log(f"⚠️ AI 응답에 유효한 인덱스 없음, 첫 번째로 대체", "warning")
            if checkboxes:
                return checkboxes[0]
        
        return None
        
    except Exception as e:
        add_log(f"❌ AI 추론 중 오류 발생: {str(e)}", "error")
        return None

def find_checkbox_with_ai(checkboxes: List[Dict], click_x: float, click_y: float) -> Optional[Dict]:
    """OpenAI를 사용하여 가장 적절한 체크박스 추론"""
    global openai_client
    
    if not openai_client:
        openai_client = initialize_openai_client()
        if not openai_client:
            return None
    
    try:
        # 체크박스 정보를 정리
        checkbox_info = []
        for idx, checkbox in enumerate(checkboxes):
            points = checkbox.get('points', [])
            center = get_center_point(points)
            distance = calculate_distance((click_x, click_y), center)
            
            # 바운딩 박스 범위 계산
            if points and len(points) >= 2:
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                bbox_info = {
                    'x_min': min(x_coords),
                    'x_max': max(x_coords),
                    'y_min': min(y_coords),
                    'y_max': max(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords)
                }
            else:
                bbox_info = None
            
            checkbox_info.append({
                'index': idx,
                'name': checkbox.get('name', ''),
                'text': checkbox.get('text', ''),
                'center': center,
                'distance': distance,
                'bbox': bbox_info,
                'path': checkbox.get('path', '')
            })
        
        # 거리순으로 정렬 (상위 10개만)
        checkbox_info.sort(key=lambda x: x['distance'])
        top_checkboxes = checkbox_info[:10]
        
        # OpenAI에 프롬프트 전달 (강제로 항목 찾기)
        system_prompt = """당신은 문서의 체크박스 매칭 전문가입니다.
클릭한 좌표와 가장 적절한 체크박스를 추론해야 합니다.
**중요: 반드시 목록 중 하나를 선택해야 합니다. 선택하지 못하면 안됩니다.**
바운딩 박스 안에 정확히 속해있지 않아도, 좌표의 위치, 거리, 컨텍스트를 종합적으로 고려하여 가장 적절한 체크박스를 선택하세요.

응답은 반드시 JSON 형식으로 해주세요:
{
    "selected_index": 숫자 (0부터 시작하는 인덱스, 반드시 0 이상의 유효한 인덱스),
    "reason": "선택 이유 설명"
}"""

        user_prompt = f"""클릭한 좌표: ({click_x}, {click_y})

가능한 체크박스 목록 (거리순으로 정렬됨):
{json.dumps(top_checkboxes, ensure_ascii=False, indent=2)}

**반드시 위 목록 중 하나를 선택해야 합니다.**
클릭한 좌표 ({click_x}, {click_y})와 가장 적절하게 매칭되는 체크박스의 index를 선택해주세요.
바운딩 박스 안에 정확히 속해있지 않아도, 거리와 컨텍스트를 고려하여 가장 합리적인 선택을 해주세요.
가장 가까운 거리의 체크박스를 우선적으로 고려하되, 논리적으로 가장 적절한 것을 선택하세요."""

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        selected_index = result.get('selected_index')
        reason = result.get('reason', '')
        
        add_log(f"AI 응답: selected_index={selected_index}, reason={reason}", "info")
        
        # 유효한 인덱스인지 확인
        if selected_index is not None and isinstance(selected_index, int):
            # 인덱스가 범위를 벗어나면 가장 가까운 것으로 대체
            if selected_index < 0 or selected_index >= len(top_checkboxes):
                add_log(f"⚠️ AI가 유효하지 않은 인덱스 선택: {selected_index}, 가장 가까운 것으로 대체", "warning")
                selected_index = 0  # 가장 가까운 것 (거리순 정렬됨)
            
            original_index = top_checkboxes[selected_index]['index']
            add_log(f"✅ AI 추론 성공: {reason}", "success")
            return checkboxes[original_index]
        else:
            # AI가 인덱스를 제대로 반환하지 않으면 가장 가까운 것으로 대체
            add_log(f"⚠️ AI 응답에 유효한 인덱스 없음, 가장 가까운 것으로 대체", "warning")
            if top_checkboxes:
                return checkboxes[top_checkboxes[0]['index']]
            return None
    
    except Exception as e:
        print(f"[CheckboxAgent] ⚠️ OpenAI 추론 실패: {str(e)}, 일반 로직 사용")
        return None


def set_checkbox_selected(data: Any, path: str, value: bool = True) -> bool:
    """특정 경로의 체크박스를 선택/해제"""
    if not path:
        return False
    
    keys = path.split('.')
    current = data
    
    # 경로를 따라가면서 마지막 키에 도달
    for i, key in enumerate(keys[:-1]):
        # 배열 인덱스 처리
        if '[' in key and ']' in key:
            base_key = key.split('[')[0]
            idx = int(key.split('[')[1].split(']')[0])
            if base_key in current:
                current = current[base_key]
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return False
        else:
            if key in current:
                current = current[key]
            else:
                return False
    
    # 마지막 키 처리
    last_key = keys[-1]
    if '[' in last_key and ']' in last_key:
        base_key = last_key.split('[')[0]
        idx = int(last_key.split('[')[1].split(']')[0])
        if base_key in current:
            current = current[base_key]
            if isinstance(current, list) and 0 <= idx < len(current):
                if isinstance(current[idx], dict):
                    current[idx]['selected'] = value
                    return True
    else:
        if last_key in current and isinstance(current[last_key], dict):
            current[last_key]['selected'] = value
            return True
    
    return False


def process_checkbox_click(structured_output: Dict, click_x: float, click_y: float, 
                          use_bbox: bool = True, tolerance: float = 10.0, use_ai: bool = True) -> Dict[str, Any]:
    """
    체크박스 클릭 좌표를 처리하여 해당 항목을 true로 변경
    
    Args:
        structured_output: structured_output.json 데이터
        click_x: 클릭한 X 좌표
        click_y: 클릭한 Y 좌표
        use_bbox: 바운딩 박스 내부 확인 사용 여부 (True: bbox 내부만, False: 가장 가까운 것)
        tolerance: 바운딩 박스 허용 오차 (픽셀)
    
    Returns:
        처리 결과 딕셔너리:
        {
            'success': bool,
            'updated': bool,  # 실제로 업데이트되었는지
            'checkbox': {...},  # 찾은 체크박스 정보
            'path': str,  # 체크박스 경로
            'distance': float,  # 클릭 지점과의 거리
            'error': str  # 오류 메시지 (실패 시)
        }
    """
    try:
        # 1. 모든 체크박스 찾기
        checkboxes = find_all_checkboxes(structured_output)
        
        if not checkboxes:
            return {
                'success': False,
                'updated': False,
                'error': 'structured_output.json에서 체크박스를 찾을 수 없습니다.'
            }
        
        click_point = (click_x, click_y)
        closest = None
        method = 'normal'
        
        # 2. OpenAI 에이전트를 사용한 추론 (선택적)
        if use_ai:
            ai_result = find_checkbox_with_ai(checkboxes, click_x, click_y)
            if ai_result:
                closest = ai_result
                method = 'ai'
                print(f"[CheckboxAgent] ✅ AI 에이전트로 체크박스 추론 성공")
        
        # 3. AI가 실패하거나 사용하지 않는 경우 일반 로직 사용
        if not closest:
            closest = find_closest_checkbox(checkboxes, click_point, use_bbox, tolerance)
            method = 'normal'
        
        if not closest:
            return {
                'success': False,
                'updated': False,
                'error': f'클릭한 좌표 ({click_x}, {click_y}) 근처에서 체크박스를 찾을 수 없습니다.'
            }
        
        # 4. 거리 계산
        center = get_center_point(closest['points'])
        distance = calculate_distance(click_point, center)
        
        # 5. 체크박스 선택 상태 변경
        path = closest['path']
        updated = set_checkbox_selected(structured_output, path, True)
        
        if not updated:
            return {
                'success': False,
                'updated': False,
                'error': f'체크박스 업데이트 실패: 경로 {path}를 찾을 수 없습니다.'
            }
        
        # 텍스트 오타 수정: '확은' -> '확인'
        corrected_text = closest.get('text', '')
        if corrected_text == '확은':
            corrected_text = '확인'
            add_log(f"✅ 텍스트 오타 수정: '확은' -> '확인'", "info")
        
        corrected_name = closest.get('name', '')
        if corrected_name == '확은':
            corrected_name = '확인'
            add_log(f"✅ 이름 오타 수정: '확은' -> '확인'", "info")
        
        return {
            'success': True,
            'updated': True,
            'checkbox': {
                'name': corrected_name,
                'text': corrected_text,
                'points': closest['points'],
                'selected': True
            },
            'path': path,
            'distance': distance,
            'method': method
        }
    
    except Exception as e:
        return {
            'success': False,
            'updated': False,
            'error': f'처리 중 오류 발생: {str(e)}'
        }


def process_checkbox_by_coordinate(click_x: float, click_y: float) -> Dict[str, Any]:
    """
    좌표만 받아서 체크박스 처리 (새로운 추론 과정)
    1. bbox_labels.json에서 좌표에 해당하는 텍스트 찾기
    2. 텍스트를 기반으로 structured_output.json에서 체크박스 찾기 (GPT 사용)
    3. 찾은 체크박스를 true로 변경
    무조건 항목을 찾아야 함
    
    Args:
        click_x: 클릭한 X 좌표
        click_y: 클릭한 Y 좌표
    
    Returns:
        처리 결과 딕셔너리
    """
    add_log(f"좌표 처리 시작: ({click_x}, {click_y})", "info")
    
    # 1단계: bbox_labels.json에서 텍스트 찾기
    add_log("1️⃣ bbox_labels.json에서 텍스트 찾기", "info")
    text = find_text_from_bbox_labels(click_x, click_y)
    
    if not text:
        add_log("❌ bbox_labels.json에서 텍스트를 찾을 수 없습니다.", "error")
        return {
            'success': False,
            'updated': False,
            'error': 'bbox_labels.json에서 텍스트를 찾을 수 없습니다.'
        }
    
    add_log(f"✅ 찾은 텍스트: {text}", "success")
    
    # 2단계: 캐시된 structured_output 사용
    structured_output = get_cached_structured_output()
    if not structured_output:
        add_log("❌ structured_output.json이 로드되지 않았습니다. 먼저 load_structured_output()을 호출하세요.", "error")
        return {
            'success': False,
            'updated': False,
            'error': 'structured_output.json이 로드되지 않았습니다.'
        }
    
    # 캐시된 체크박스 목록 사용
    checkboxes = get_cached_checkboxes()
    if not checkboxes:
        add_log("❌ 체크박스를 찾을 수 없습니다.", "error")
        return {
            'success': False,
            'updated': False,
            'error': '체크박스를 찾을 수 없습니다.'
        }
    
    add_log(f"체크박스 {len(checkboxes)}개 발견", "info")
    
    # 3단계: 텍스트를 기반으로 체크박스 찾기 (GPT 사용)
    add_log("2️⃣ AI 에이전트로 텍스트 기반 체크박스 추론 시작", "info")
    closest = find_checkbox_by_text_with_ai(text, checkboxes)
    
    method = 'ai_text'
    
    # AI 실패 시 대체 로직
    if not closest:
        add_log("⚠️ AI 추론 실패, 텍스트 유사도 기반으로 찾기", "warning")
        # 텍스트 유사도로 찾기
        best_match = None
        best_score = 0
        
        for checkbox in checkboxes:
            name = checkbox.get('name', '').lower()
            checkbox_text = checkbox.get('text', '').lower()
            search_text = text.lower()
            
            # 간단한 유사도 계산 (부분 일치)
            score = 0
            if search_text in name or name in search_text:
                score += 0.5
            if search_text in checkbox_text or checkbox_text in search_text:
                score += 0.5
            if name == search_text or checkbox_text == search_text:
                score = 1.0
            
            if score > best_score:
                best_score = score
                best_match = checkbox
        
        if best_match:
            closest = best_match
            method = 'text_similarity'
            add_log(f"✅ 텍스트 유사도로 체크박스 찾음 (점수: {best_score:.2f})", "success")
        else:
            # 그래도 없으면 첫 번째 체크박스
            add_log("⚠️ 매칭 실패, 첫 번째 체크박스 사용", "warning")
            if checkboxes:
                closest = checkboxes[0]
                method = 'fallback'
    
    if not closest:
        add_log("❌ 체크박스를 찾을 수 없습니다.", "error")
        return {
            'success': False,
            'updated': False,
            'error': '체크박스를 찾을 수 없습니다.'
        }
    
    add_log(f"선택된 체크박스: {closest.get('name', '이름 없음')}", "info")
    
    # 4단계: 체크박스 선택 상태 변경
    path = closest['path']
    updated = set_checkbox_selected(structured_output, path, True)
    
    if not updated:
        add_log(f"❌ 체크박스 업데이트 실패: 경로 {path}", "error")
        return {
            'success': False,
            'updated': False,
            'error': f'체크박스 업데이트 실패: 경로 {path}를 찾을 수 없습니다.'
        }
    
    add_log(f"✅ 체크박스 업데이트 성공: {closest.get('name', '이름 없음')}", "success")
    
    # 텍스트 오타 수정: '확은' -> '확인'
    corrected_text = closest.get('text', '')
    if corrected_text == '확은':
        corrected_text = '확인'
        add_log(f"✅ 텍스트 오타 수정: '확은' -> '확인'", "info")
    
    corrected_name = closest.get('name', '')
    if corrected_name == '확은':
        corrected_name = '확인'
        add_log(f"✅ 이름 오타 수정: '확은' -> '확인'", "info")
    
    return {
        'success': True,
        'updated': True,
        'checkbox': {
            'name': corrected_name,
            'text': corrected_text,
            'points': closest['points'],
            'selected': True
        },
        'path': path,
        'method': method,
        'bbox_text': text,  # bbox_labels에서 찾은 텍스트
        'logs': get_logs()[-10:]  # 최근 10개 로그
    }


def reset_all_checkboxes(structured_output: Dict = None) -> int:
    """
    모든 체크박스의 selected 값을 false로 초기화

    Args:
        structured_output: structured_output 데이터 (None이면 캐시 사용)

    Returns:
        초기화된 체크박스 개수
    """
    global _structured_output_cache, _checkboxes_cache

    if structured_output is None:
        structured_output = _structured_output_cache

    if not structured_output:
        add_log("❌ structured_output이 없어 초기화할 수 없습니다.", "error")
        return 0

    # 모든 체크박스 찾기
    checkboxes = find_all_checkboxes(structured_output)
    reset_count = 0

    for checkbox in checkboxes:
        path = checkbox['path']
        if set_checkbox_selected(structured_output, path, False):
            reset_count += 1

    # 캐시 업데이트
    _checkboxes_cache = find_all_checkboxes(structured_output)

    add_log(f"✅ 모든 체크박스 초기화 완료: {reset_count}개", "success")
    return reset_count


def get_all_checkboxes_info(structured_output: Dict) -> List[Dict]:
    """
    structured_output.json의 모든 체크박스 정보 반환

    Returns:
        체크박스 정보 리스트:
        [
            {
                'path': str,
                'name': str,
                'text': str,
                'points': List,
                'selected': bool,
                'center': Tuple[float, float]
            },
            ...
        ]
    """
    checkboxes = find_all_checkboxes(structured_output)

    result = []
    for checkbox in checkboxes:
        center = get_center_point(checkbox['points'])
        result.append({
            'path': checkbox['path'],
            'name': checkbox['name'],
            'text': checkbox['text'],
            'points': checkbox['points'],
            'selected': checkbox['selected'],
            'center': center
        })

    return result

