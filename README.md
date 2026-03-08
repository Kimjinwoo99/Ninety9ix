# Ninety9ix

신분증 및 신청서 문서를 자동 분석하는 **AI 기반 문서 처리
시스템**입니다.\
OCR, 체크박스 탐지, 문서 검증, 고객 유형 분석을 하나의 파이프라인으로
처리합니다.

------------------------------------------------------------------------

## 주요 기능

### 1. 신분증 OCR

-   EasyOCR 기반으로 신분증 이미지에서 텍스트 추출
-   성명 / 주민등록번호 / 주소 / 발급일 자동 인식
-   주민번호 마스킹 처리

### 2. 신청서 OCR

-   외부 OCR API를 사용해 신청서 이미지를 구조화된 JSON으로 변환
-   필드 위치와 텍스트 정보를 함께 저장

### 3. 체크박스 자동 탐지

-   YOLO 모델을 사용하여 체크된 체크박스 위치 탐지
-   `{x1, y1, x2, y2}` 좌표 형태로 반환

### 4. 체크박스 AI 매칭

-   OCR 결과와 체크박스 좌표를 매칭
-   텍스트 유사도 / 바운딩 박스 / AI 추론 기반 매칭

### 5. 문서 검증 및 고객 분석

-   신분증 데이터 검증
-   신청서 필드 검증
-   체크된 항목 분석
-   고객 유형 분석 및 자연어 리포트 생성

------------------------------------------------------------------------

## 시스템 아키텍처

    React Frontend
         │
         │ REST API
         ▼
    Flask Backend
         │
         ├ OCR (EasyOCR)
         ├ Checkbox Detection (YOLO)
         └ AI Agent (OpenAI GPT)

------------------------------------------------------------------------

## 문서 처리 파이프라인

    신분증 OCR
        ↓
    신청서 OCR
        ↓
    체크박스 탐지 (YOLO)
        ↓
    체크박스 AI 매칭
        ↓
    문서 검증 및 분석 (AI Agent)

------------------------------------------------------------------------

## 기술 스택

### Frontend

-   React
-   TypeScript
-   Vite
-   Zustand
-   Tailwind CSS
-   React Router

### Backend

-   Python 3.10
-   Flask
-   EasyOCR
-   OpenCV
-   YOLO (Ultralytics)
-   OpenAI GPT API

------------------------------------------------------------------------

## 프로젝트 구조

    Ninety9ix
    │
    ├ frontend
    │   ├ src
    │   │   ├ components
    │   │   ├ pages
    │   │   ├ stores
    │   │   └ api
    │   └ vite.config.ts
    │
    ├ backend
    │   ├ app.py
    │   ├ idocr.py
    │   ├ checkbox_detection.py
    │   ├ checkbox_agent.py
    │   ├ agent.py
    │   └ uploads
    │
    └ README.md

------------------------------------------------------------------------

## 실행 방법

### 1. Backend 실행 (Flask 서버)

``` bash
cd backend
python app.py
```

### 2. Frontend 실행

``` bash
cd frontend
npm install
npm run dev
```

### 3. 브라우저 접속

    http://localhost:5173

------------------------------------------------------------------------

## 주요 API

  API                         설명
  --------------------------- ----------------
  `/api/upload`               신분증 OCR
  `/api/document-ocr`         신청서 OCR
  `/api/detect-checkboxes`    체크박스 탐지
  `/api/process-checkboxes`   체크박스 처리
  `/api/run-agent`            문서 분석 실행

------------------------------------------------------------------------
## Environment Variables

이 프로젝트는 일부 기능에서 **OpenAI API** 및 **외부 OCR API**를 사용합니다.  
실행 전 아래 환경변수를 설정해야 합니다.

### 1. `.env` 파일 생성

`backend` 디렉터리에 `.env` 파일을 생성합니다.

```
backend/.env
```

예시:

```
OPENAI_API_KEY=your_openai_api_key
OCR_API_BASE_URL=http://localhost:8000
```

---

### 2. 환경변수 사용 방식

백엔드 코드에서는 다음과 같이 환경변수를 통해 API 키와 외부 API 주소를 불러옵니다.

```python
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OCR_API_BASE_URL = os.getenv("OCR_API_BASE_URL", "http://localhost:8000")
```

이 방식으로 **API 키 및 외부 서비스 주소가 코드에 직접 포함되지 않도록 관리합니다.**

---

### 3. `.env` 파일 보안

`.env` 파일에는 API 키와 같은 민감한 정보가 포함될 수 있으므로  
Git 저장소에 업로드하지 않습니다.

`.gitignore`에 다음 항목이 포함되어 있어야 합니다.

```
.env
```

---

## 제한 사항 (Limitations)

본 프로젝트는 팀 프로젝트로 개발되었으며,
서류 OCR 처리는 외부 클라우드 OCR 서버와 연동되어 있습니다.

현재 해당 서버는 프로젝트 종료로 인해 접근이 제한되어
서류 OCR API 호출이 정상적으로 동작하지 않을 수 있습니다.

따라서 전체 파이프라인 중 일부 기능은
Mock 데이터 또는 기존 결과 파일을 기반으로 확인할 수 있습니다.
