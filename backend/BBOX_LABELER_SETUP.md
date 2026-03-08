# BBox 라벨링 시스템 가이드

## 📦 필요한 파일 목록

### 필수 파일
1. **`bbox_labeler.py`** - 독립 실행 서버 (Flask + HTML UI 포함)
2. **`document.jpg`** - 라벨링할 이미지 파일

### 선택 파일
3. **`bbox_labels.json`** - 저장된 라벨 데이터 (자동 생성)
4. **`BBOX_LABELER_SETUP.md`** - 이 가이드 파일

---

## 🔧 수정해야 할 경로 및 설정

### 1. bbox_labeler.py

#### 이미지 파일 경로 (라인 16)
```python
UPLOAD_FOLDER = os.path.dirname(__file__)
```
**수정 불필요:**
- 같은 폴더에 `document.jpg`를 두면 자동으로 찾음
- 다른 경로에 있으면 코드에서 `UPLOAD_FOLDER` 수정

#### 라벨 저장 파일 경로 (라인 19)
```python
LABELS_FILE = os.path.join(UPLOAD_FOLDER, 'bbox_labels.json')
```
**수정 불필요:**
- 같은 폴더에 `bbox_labels.json`으로 자동 저장됨

#### 서버 포트 (라인 333)
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```
**수정 가능:**
- 다른 포트를 사용하려면 `port=5001` 변경
- 다른 포트를 사용 중이면 충돌 방지를 위해 변경

---

## 📋 Python 패키지 설치

다음 패키지들이 필요합니다:

```bash
pip install flask flask-cors
```

또는 `requirements.txt`가 있다면:

```bash
pip install flask==3.0.0 flask-cors==4.0.0
```

**최소 필요 패키지:**
- `flask` (웹 서버)
- `flask-cors` (CORS 처리)

---

## 🚀 사용 방법

### 1. 파일 준비
```
프로젝트 폴더/
├── bbox_labeler.py
└── document.jpg  (라벨링할 이미지)
```

### 2. 서버 실행
```bash
python bbox_labeler.py
```

### 3. 브라우저 접속
```
http://localhost:5001
```

### 4. 라벨링 작업

#### BBox 생성
1. 이미지에서 드래그하여 bbox 영역 선택
2. 자동으로 새 라벨 항목이 생성됨

#### 텍스트 라벨링
1. 우측 라벨 목록에서 해당 항목 클릭
2. 텍스트 입력 필드에 라벨 텍스트 입력
3. 자동으로 저장됨

#### 여러 BBox 처리
- 여러 번 드래그하여 여러 bbox 생성 가능
- 각각 독립적으로 라벨링 가능

#### 저장
- **💾 저장** 버튼: 서버에 저장 (`bbox_labels.json`)
- **JSON 내보내기** 버튼: 브라우저에서 JSON 파일 다운로드

---

## 📝 저장되는 JSON 형식

```json
{
  "image_file": "document.jpg",
  "labels": [
    {
      "id": 1,
      "bbox": [100, 200, 300, 400],
      "text": "이름"
    },
    {
      "id": 2,
      "bbox": [500, 600, 700, 800],
      "text": "주소"
    }
  ],
  "last_updated": "2025-01-09T12:00:00.000000"
}
```

**bbox 형식:**
- `[x1, y1, x2, y2]` - 좌상단 좌표와 우하단 좌표
- 실제 이미지 픽셀 좌표 기준

---

## 🎨 주요 기능

### 1. 드래그로 BBox 생성
- 이미지에서 마우스로 드래그하여 영역 선택
- 최소 크기 10x10 픽셀

### 2. BBox 선택 및 편집
- 우측 목록에서 라벨 클릭하여 선택
- 선택된 bbox는 파란색으로 표시

### 3. 텍스트 라벨링
- 각 bbox에 대해 텍스트 입력 가능
- 실시간으로 이미지에 표시됨

### 4. 라벨 삭제
- 각 라벨 항목의 "삭제" 버튼으로 개별 삭제
- "전체 삭제" 버튼으로 모든 라벨 삭제

### 5. 자동 저장
- 페이지 새로고침 시 저장된 라벨 자동 로드
- 서버 재시작 후에도 유지

### 6. 이미지 업로드
- "이미지 선택" 버튼으로 다른 이미지 로드 가능
- 기본적으로 `document.jpg` 자동 로드

---

## 🔍 문제 해결

### 1. "document.jpg 파일을 찾을 수 없습니다"
- `document.jpg` 파일이 같은 폴더에 있는지 확인
- 또는 "이미지 선택" 버튼으로 직접 업로드

### 2. "포트가 이미 사용 중입니다"
- `bbox_labeler.py`에서 포트 번호 변경 (라인 333)
- 또는 다른 서버 종료

### 3. "No module named 'flask'"
```bash
pip install flask flask-cors
```

### 4. BBox가 제대로 그려지지 않음
- 이미지가 완전히 로드되었는지 확인
- 브라우저 콘솔에서 오류 확인

### 5. 저장이 안됨
- 서버 로그 확인
- `bbox_labels.json` 파일 쓰기 권한 확인

---

## 📌 체크리스트

다른 환경으로 옮길 때:

- [ ] `bbox_labeler.py` 파일 복사
- [ ] `document.jpg` 파일 복사 (또는 다른 이미지)
- [ ] `flask`, `flask-cors` 패키지 설치 확인
- [ ] 포트 번호 확인 (기본: 5001)
- [ ] Python 3.7 이상 버전 확인

---

## 💡 팁

1. **좌표 확인**: 각 라벨 항목에 실제 픽셀 좌표가 표시됨
2. **일괄 작업**: 여러 bbox를 먼저 생성한 후 나중에 일괄 라벨링 가능
3. **백업**: 중요한 라벨링 작업 전에 JSON 파일 백업 권장
4. **이미지 크기**: 큰 이미지도 자동으로 화면에 맞게 조정됨
5. **실시간 미리보기**: 드래그 중 주황색으로 미리보기 표시

---

## 🔄 다른 이미지 사용하기

### 방법 1: 파일 이름 변경
- `document.jpg`를 다른 이름으로 변경
- 코드에서 `'document.jpg'`를 새 파일명으로 변경

### 방법 2: 이미지 선택 기능 사용
- 웹 UI에서 "이미지 선택" 버튼 사용
- 단, 이 경우 서버 재시작 시 자동 로드 안됨

### 방법 3: 코드 수정
```python
# 라인 16 수정
UPLOAD_FOLDER = '/path/to/your/images'
```

---

## 📊 API 엔드포인트

### GET `/`
- 메인 페이지 (HTML UI)

### GET `/document.jpg`
- 이미지 파일 제공

### GET `/api/load-image`
- 이미지 및 저장된 라벨 로드
```json
{
  "success": true,
  "image_url": "/document.jpg",
  "labels": [...]
}
```

### POST `/api/save-labels`
- 라벨 저장
```json
{
  "image_file": "document.jpg",
  "labels": [...]
}
```

### GET `/api/get-labels`
- 저장된 라벨 조회

---

## 🎯 사용 예시

### 1. 기본 사용
```bash
# 서버 시작
python bbox_labeler.py

# 브라우저에서 http://localhost:5001 접속
# 드래그로 bbox 생성 → 텍스트 입력 → 저장
```

### 2. 다른 포트 사용
```python
# bbox_labeler.py 라인 333 수정
app.run(host='0.0.0.0', port=8080, debug=True)
```

### 3. 다른 이미지 사용
```python
# bbox_labeler.py에서 'document.jpg'를 다른 파일명으로 변경
# 또는 웹 UI에서 "이미지 선택" 버튼 사용
```

---

## 📦 독립 실행 확인

이 시스템은 **완전히 독립적**으로 실행됩니다:
- ✅ `app.py` 불필요
- ✅ 다른 Flask 서버와 독립적 (다른 포트 사용)
- ✅ 단일 파일로 모든 기능 포함
- ✅ 외부 의존성 최소화 (flask, flask-cors만 필요)

