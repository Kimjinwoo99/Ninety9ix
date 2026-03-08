# 체크박스 에이전트 독립 실행 가이드

## 📦 필요한 파일 목록

다른 환경에서 테스트할 때 다음 파일들을 함께 가져가야 합니다:

### 필수 파일
1. **checkbox_agent.py** - 체크박스 에이전트 핵심 모듈
2. **checkbox_agent_test.py** - 독립 실행 테스트 스크립트
3. **structured_output.json** - 체크박스 좌표 데이터 파일
4. **requirements.txt** - Python 패키지 의존성 (또는 아래 패키지 설치)

### 선택 파일
5. **CHECKBOX_AGENT_SETUP.md** - 이 가이드 파일

---

## 🔧 수정해야 할 경로 및 설정

### 1. checkbox_agent.py

#### OpenAI API KEY 설정
```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
```
**권장 방법:**
- 실제 키는 코드에 직접 넣지 말고, **환경 변수 `OPENAI_API_KEY`** 로 설정해서 사용하세요.

#### structured_output.json 기본 경로 (라인 59, 92)
```python
default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
```
**수정 방법:**
- 같은 폴더에 `structured_output.json`을 두면 자동으로 찾음
- 다른 경로에 있으면 `checkbox_agent_test.py`에서 경로 입력하거나
- `load_structured_output()` 함수에 직접 경로 전달

---

### 2. checkbox_agent_test.py

#### structured_output.json 기본 경로 (라인 24)
```python
default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
```
**수정 방법:**
- 같은 폴더에 `structured_output.json`을 두면 자동으로 찾음
- 다른 경로에 있으면 실행 시 경로 입력 가능

#### 수정된 JSON 저장 경로 (라인 144)
```python
output_path = os.path.join(os.path.dirname(__file__), 'structured_output_updated.json')
```
**수정 방법:**
- 필요시 다른 경로로 변경 가능

---

## 📋 Python 패키지 설치

다음 패키지들이 필요합니다:

```bash
pip install openai
```

또는 `requirements.txt`가 있다면:

```bash
pip install -r requirements.txt
```

**최소 필요 패키지:**
- `openai` (최신 버전 권장)

---

## 🚀 사용 방법

### 1. 파일 준비
```
프로젝트 폴더/
├── checkbox_agent.py
├── checkbox_agent_test.py
└── structured_output.json
```

### 2. API KEY 설정
`checkbox_agent.py` 파일에서 OpenAI API KEY 수정

### 3. 실행
```bash
python checkbox_agent_test.py
```

### 4. 좌표 입력
```
좌표 입력: 1398 2114 1409 2125
좌표 입력: 1375 844 1386 855
좌표 입력: [Enter]  # 빈 줄 입력 시 처리 시작
```

---

## 🔍 환경 변수 사용 (선택사항)

코드 수정 없이 환경 변수로 설정할 수도 있습니다:

### Windows (PowerShell)
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
python checkbox_agent_test.py
```

### Windows (CMD)
```cmd
set OPENAI_API_KEY=your-api-key-here
python checkbox_agent_test.py
```

### Linux/Mac
```bash
export OPENAI_API_KEY="your-api-key-here"
python checkbox_agent_test.py
```

---

## 📝 파일 구조 예시

```
프로젝트 폴더/
├── checkbox_agent.py          # 핵심 모듈
├── checkbox_agent_test.py     # 테스트 스크립트
├── structured_output.json      # 체크박스 데이터
├── structured_output_updated.json  # 처리 후 저장 (자동 생성)
└── CHECKBOX_AGENT_SETUP.md    # 이 가이드
```

---

## ⚙️ 주요 함수 사용법

### Python 코드에서 직접 사용

```python
from checkbox_agent import (
    load_structured_output,
    process_checkbox_by_coordinate,
    get_cached_structured_output,
    get_logs
)

# 1. structured_output.json 로드
load_structured_output('path/to/structured_output.json')

# 2. 좌표로 체크박스 처리
result = process_checkbox_by_coordinate(1403.5, 2119.5)

# 3. 결과 확인
if result['success']:
    print(f"체크박스: {result['checkbox']['name']}")
    print(f"방법: {result['method']}")

# 4. 로그 확인
logs = get_logs()
for log in logs:
    print(f"[{log['timestamp']}] {log['message']}")

# 5. 수정된 JSON 가져오기
updated_json = get_cached_structured_output()
```

---

## 🐛 문제 해결

### 1. "structured_output.json을 찾을 수 없습니다"
- 파일이 같은 폴더에 있는지 확인
- 또는 실행 시 경로를 직접 입력

### 2. "OpenAI API KEY가 설정되지 않았습니다"
- `checkbox_agent.py`에서 API KEY 확인
- 또는 환경 변수 설정 확인

### 3. "No module named 'openai'"
```bash
pip install openai
```

### 4. AI 추론 실패
- API KEY가 유효한지 확인
- 인터넷 연결 확인
- OpenAI API 사용량 확인

---

## 📌 체크리스트

다른 환경으로 옮길 때:

- [ ] `checkbox_agent.py` 파일 복사
- [ ] `checkbox_agent_test.py` 파일 복사
- [ ] `structured_output.json` 파일 복사
- [ ] `checkbox_agent.py`에서 OpenAI API KEY 수정
- [ ] `openai` 패키지 설치 확인
- [ ] Python 3.7 이상 버전 확인

---

## 💡 팁

1. **API KEY 보안**: API KEY를 코드에 직접 넣지 않고 환경 변수 사용 권장
2. **경로 설정**: 절대 경로보다 상대 경로 사용 권장 (이식성 향상)
3. **로그 확인**: 문제 발생 시 `get_logs()`로 상세 로그 확인
4. **배치 처리**: 여러 좌표를 한번에 처리하려면 `checkbox_agent_test.py` 사용

