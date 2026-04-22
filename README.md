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

### 6. 사내 사용자 인증/권한 관리 (Spring Boot + MySQL)

-   JWT 기반 로그인 (`/api/v1/auth/login`)
-   권한 분리: `SYSTEM_ADMIN`, `STAFF`
-   관리자 전용 사용자 관리(조회/삭제)
-   아이디 발급 요청 접수/승인/반려 및 발급 이력 관리
-   중복 검증:
    - 아이디(로그인 ID) 중복 차단
    - 사원번호 중복 차단(요청 + 계정 생성 단계)

------------------------------------------------------------------------

## 시스템 아키텍처

    React Frontend
         │
         │ REST API
         ▼
    Flask Backend + Spring Boot Backend
         │
         ├ Flask: OCR/EasyOCR, Checkbox(YOLO), AI Agent(OpenAI)
         └ Spring Boot: Auth/JWT, User Management, Access Request, MySQL

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
-   Spring Boot 3.2
-   Spring Security + JWT
-   Spring Data JPA
-   MySQL 8

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
    ├ backend-spring
    │   ├ src/main/java/com/ninety9ix
    │   │   ├ config
    │   │   ├ domain
    │   │   ├ dto
    │   │   ├ repository
    │   │   ├ service
    │   │   └ web
    │   └ src/main/resources/application.yml
    │
    ├ docker-compose.yml
    │
    └ README.md

------------------------------------------------------------------------

## 실행 방법

### 사전 준비

-   JDK 17+ (권장: JDK 21)
-   Node.js 18+
-   Python 3.10+
-   Docker Desktop (MySQL 컨테이너 사용 시)

### 1) MySQL 실행

프로젝트 루트(`Ninety9ix`)에서:

```bash
docker compose up -d
```

### 2) Spring Boot 실행 (인증/권한/사용자관리)

```bash
cd backend-spring
./mvnw spring-boot:run
```

Windows PowerShell:

```powershell
cd backend-spring
.\mvnw.cmd spring-boot:run
```

기본 포트: `http://localhost:8080`

### 3) Flask 실행 (OCR/문서 파이프라인)

```bash
cd backend
python app.py
```

기본 포트: `http://localhost:5000`

### 4) Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

기본 포트: `http://localhost:5173`

### 5) 프론트 환경변수 설정 (`frontend/.env`)

```env
VITE_API_URL=http://localhost:5000
VITE_SPRING_API_URL=http://localhost:8080
```

------------------------------------------------------------------------

## 주요 API

  API                         설명
  --------------------------- ----------------
  `/api/upload`               신분증 OCR
  `/api/document-ocr`         신청서 OCR
  `/api/detect-checkboxes`    체크박스 탐지
  `/api/process-checkboxes`   체크박스 처리
  `/api/run-agent`            문서 분석 실행
  `/api/v1/auth/login`        사내 로그인(JWT)
  `/api/v1/auth/users`        사용자 목록/삭제(관리자)
  `/api/v1/access-requests`   아이디 발급 요청(생성/조회)

------------------------------------------------------------------------

## 사내 계정/권한 정책

-   최고 관리자 계정: `admin`
-   `admin` 계정은 삭제 불가
-   다른 `SYSTEM_ADMIN` 계정 삭제는 `admin`만 가능
-   `STAFF` 계정은 관리자 권한 계정으로 삭제 가능
-   발급 요청 승인(`APPROVED`)은 계정 생성 성공 시에만 처리됨

------------------------------------------------------------------------

## 초기 관리자 계정

최초 실행 시 사용자 테이블이 비어 있으면 기본 최고 관리자 계정이 자동 생성됩니다.

-   ID: `admin`
-   PW: `Admin1234!`

운영 환경에서는 환경변수로 반드시 변경하세요.

------------------------------------------------------------------------

## Model Setup

체크박스 위치 탐지를 위해 YOLO 모델(`best.pt`)이 필요합니다.  
모델 파일은 용량 문제로 GitHub 저장소에 포함되어 있지 않습니다.

아래 링크에서 모델을 다운로드한 후 다음 경로에 배치해 주세요.

```
Ninety9ix/backend/GetLocation/models/best.pt
```

### Model Download

Download Link:  
https://drive.google.com/file/d/1wSXW_Br1cibOczj4xF-97mcKOSCtuXSX/view?usp=drive_link

### 디렉터리 구조 예시

```
backend
 └ GetLocation
    └ models
       └ best.pt
```

모델이 해당 경로에 존재하지 않을 경우 **체크박스 위치 탐지 기능(YOLO)이 정상적으로 동작하지 않습니다.**

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

------------------------------------------------------------------------

## 제한 사항 (Limitations)

본 프로젝트는 팀 프로젝트로 개발되었으며,
서류 OCR 처리는 외부 클라우드 OCR 서버와 연동되어 있습니다.

현재 해당 서버는 프로젝트 종료로 인해 접근이 제한되어
서류 OCR API 호출이 정상적으로 동작하지 않을 수 있습니다.

따라서 전체 파이프라인 중 일부 기능은
Mock 데이터 또는 기존 결과 파일을 기반으로 확인할 수 있습니다.
