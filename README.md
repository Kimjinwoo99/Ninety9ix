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

## 향후 개선 계획

-   문서 유형 자동 분류 모델 추가
-   OCR 정확도 개선
-   실시간 검증 UI 개선
-   AI 기반 오류 수정 제안 기능
