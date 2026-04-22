# 시스템 아키텍처 (최신)

본 문서는 Ninety9ix의 최신 아키텍처를 설명합니다.  
현재 시스템은 **Flask(문서 처리 파이프라인)** + **Spring Boot(MySQL, 인증/권한/사용자관리)** + **React 프론트엔드**의 3계층으로 동작합니다.

---

## 1. 시스템 개요

Ninety9ix는 다음 두 흐름이 결합된 내부 운영 시스템입니다.

1. **문서 처리 흐름 (Flask)**
   - 신분증 OCR
   - 신청서 OCR
   - 체크박스 탐지/매칭
   - AI 기반 검증/고객유형 분석

2. **사내 사용자/권한 관리 흐름 (Spring Boot + MySQL)**
   - JWT 로그인
   - 관리자/실무자 권한 분리
   - 아이디 발급 요청/승인/반려
   - 사용자 목록 조회/삭제
   - 발급 완료 이력 관리

---

## 2. 상위 아키텍처

```text
┌───────────────────────────────────────────┐
│ Frontend (React + TypeScript + Vite)     │
│  - 로그인/권한 기반 라우팅                │
│  - 사용자 관리/발급요청 처리 UI           │
│  - 등록(업로드→처리→검토) UI             │
└───────────────┬───────────────────────────┘
                │ HTTP/REST
       ┌────────┴────────┐
       │                 │
┌──────▼──────────┐  ┌───▼───────────────────┐
│ Flask Backend    │  │ Spring Boot Backend   │
│ (port 5000)      │  │ (port 8080)           │
│ - OCR/YOLO/Agent │  │ - Auth/JWT            │
│ - 문서 처리 파이 │  │ - User/Role 관리      │
│   프라인         │  │ - Access Request      │
└──────┬──────────┘  │ - 고객/세션 메타 저장 │
       │             └──────────┬────────────┘
       │ 파일 기반               │ JPA
       │                         │
       │               ┌─────────▼──────────┐
       │               │ MySQL 8             │
       │               │ - app_user          │
       │               │ - access_request    │
       │               │ - user_provision_   │
       │               │   history           │
       │               │ - customer/session  │
       │               └─────────────────────┘
```

---

## 3. 프론트엔드 구조

### 기술 스택
- React 18 + TypeScript
- Vite
- Zustand
- Tailwind CSS
- React Router

### 핵심 페이지/컴포넌트

- `Login`
  - 사내 로그인
  - 아이디 발급 요청(이름/사원번호/부서/요청권한)
- `UserManagement`
  - 사용자 목록 테이블 (ID, 이름, 사원번호, 부서, 권한, 삭제)
  - 발급요청 처리(승인+계정생성 / 반려)
  - 발급 완료 로그 조회
- `Dashboard`, `Customers`, `Contracts`, `Report`, `Settings`
  - 기존 업무/등록 흐름
- `RegistrationModal` + `UploadStep` + `ProcessingStep` + `ReviewStep` + `CompleteStep`
  - 문서 처리 파이프라인 UI

### 권한 기반 라우팅
- 비로그인: `/login`만 접근
- 로그인 사용자: 일반 업무 라우트 접근
- 관리자 전용 라우트: `/settings`, `/user-management`

---

## 4. 백엔드 구조

## 4.1 Flask 백엔드 (`backend/`)

### 역할
- 문서 처리 파이프라인 오케스트레이션
- OCR, 체크박스 탐지/매칭, AI 분석

### 주요 모듈
- `app.py`: Flask 엔드포인트 집합
- `idocr.py`: 신분증 OCR
- `checkbox_detection.py`: YOLO 체크박스 탐지
- `checkbox_agent.py`: 체크박스 매칭/추론
- `agent.py`: 문서 검증/고객 분석

### 저장소
- `structured_output.json`
- `bbox_labels.json`
- `uploads/`

## 4.2 Spring Boot 백엔드 (`backend-spring/`)

### 역할
- 인증/인가(JWT, Spring Security)
- 사용자/권한/발급요청/이력
- 고객/세션/문서 메타 데이터 관리

### 레이어
- `web`: REST Controller
- `service`: 도메인 규칙/트랜잭션
- `repository`: JPA Repository
- `domain`: 엔티티/Enum
- `dto`: 요청/응답 모델

### 보안 정책
- 권한: `SYSTEM_ADMIN`, `STAFF`
- 최고 관리자: `username = admin`
- `admin` 계정 삭제 불가
- 다른 관리자 삭제는 `admin`만 가능
- 본인 계정 삭제 불가
- 요청 승인(`APPROVED`)은 **계정 생성 API 성공 시에만** 처리

---

## 5. 데이터 플로우

## 5.1 문서 처리 플로우

```text
업로드(Frontend)
  → /api/upload (Flask, 신분증 OCR)
  → /api/document-ocr (Flask, 신청서 OCR)
  → /api/detect-checkboxes (Flask, YOLO)
  → /api/process-checkboxes (Flask, 매칭/반영)
  → /api/run-agent (Flask, 검증/리포트)
  → 검토/완료(Frontend)
```

## 5.2 계정 발급 플로우

```text
Login 페이지에서 발급요청 생성
  → POST /api/v1/access-requests (Spring)
  → 상태 PENDING

관리자 UserManagement 페이지
  → 요청별 ID/PW 입력
  → POST /api/v1/auth/provision-from-request
      - app_user 생성 성공
      - access_request 상태 APPROVED
      - user_provision_history 기록
```

## 5.3 사용자 삭제 플로우

```text
관리자 UserManagement 목록에서 삭제
  → DELETE /api/v1/auth/users/{id}
  → 서버 정책 검증
      - admin 삭제 불가
      - 다른 관리자 삭제는 admin만 가능
      - 본인 삭제 불가
```

---

## 6. API 엔드포인트

## 6.1 Flask API (문서 처리)

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/api/upload` | POST | 신분증 OCR |
| `/api/document-ocr` | POST | 신청서 OCR |
| `/api/detect-checkboxes` | POST | 체크박스 탐지 |
| `/api/process-checkboxes` | POST | 체크박스 처리 |
| `/api/run-agent` | POST | AI 분석 실행 |
| `/api/structured-output` | GET | 구조화 결과 조회 |
| `/api/crop-form-field` | POST | 필드 crop 조회 |

## 6.2 Spring API (인증/권한/관리)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|---|---|---|---|
| `/api/v1/health` | GET | 공개 | 헬스 체크 |
| `/api/v1/auth/login` | POST | 공개 | 로그인(JWT) |
| `/api/v1/auth/me` | GET | 인증 | 내 정보 |
| `/api/v1/auth/users` | GET | SYSTEM_ADMIN | 사용자 목록 |
| `/api/v1/auth/users/{id}` | DELETE | SYSTEM_ADMIN | 사용자 삭제 |
| `/api/v1/auth/provision-from-request` | POST | SYSTEM_ADMIN | 요청 기반 계정 생성+승인 |
| `/api/v1/auth/provision-histories` | GET | SYSTEM_ADMIN | 발급 로그 조회 |
| `/api/v1/access-requests` | POST | 공개 | 발급 요청 생성 |
| `/api/v1/access-requests` | GET | SYSTEM_ADMIN | 발급 요청 목록 |
| `/api/v1/access-requests/{id}/review` | PATCH | SYSTEM_ADMIN | 요청 반려(REJECTED) |
| `/api/v1/customers` | GET/POST | 인증 | 고객 조회/생성 |
| `/api/v1/sessions/*` | GET/POST/PATCH | 인증 | 세션/문서 메타 관리 |

---

## 7. 데이터 모델 (핵심)

### 인증/사용자
- `app_user`
  - `username` unique
  - `employee_number` unique
  - `role`, `enabled`
- `access_request`
  - `employee_number` unique
  - `status`: `PENDING`/`APPROVED`/`REJECTED`
- `user_provision_history`
  - 계정 발급 완료 로그

### 업무 데이터
- `customer`
- `registration_session`
- `document`
- `structured_output_snapshot`

---

## 8. 예외/중복 처리 정책

- 아이디 중복: `409`
- 사원번호 중복: `409`
- 발급요청 사원번호 중복: `409`
- 권한 없음: `403`
- 인증 만료/미인증: `401`

프론트는 `409`를 사용자 친화 메시지로 분기:
- `중복된 아이디입니다`
- `이미 아이디가 존재하는 사원번호입니다`

---

## 9. 실행 구성

1. MySQL
   - `docker compose up -d`
2. Spring Boot
   - `cd backend-spring`
   - `.\mvnw.cmd spring-boot:run` (Windows)
3. Flask
   - `cd backend`
   - `python app.py`
4. Frontend
   - `cd frontend`
   - `npm run dev`
5. Frontend `.env`
   - `VITE_API_URL=http://localhost:5000`
   - `VITE_SPRING_API_URL=http://localhost:8080`

---

## 10. 참고

- `PROCESS_FLOW.md`
- `BACKEND_SPRING_MYSQL.md`
- `README.md`
