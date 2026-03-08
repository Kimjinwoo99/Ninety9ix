# 시스템 아키텍처

본 문서는 Ninety9ix 문서 처리 시스템의 전체 아키텍처를 설명합니다.

## 목차

1. [시스템 개요](#시스템-개요)
2. [아키텍처 다이어그램](#아키텍처-다이어그램)
3. [프론트엔드 구조](#프론트엔드-구조)
4. [백엔드 구조](#백엔드-구조)
5. [데이터 플로우](#데이터-플로우)
6. [주요 컴포넌트](#주요-컴포넌트)
7. [API 엔드포인트](#api-엔드포인트)
8. [데이터 구조](#데이터-구조)
9. [기술 스택](#기술-스택)

---

## 시스템 개요

Ninety9ix는 신분증 및 서류 OCR 처리, 체크박스 탐지 및 분석, 문서 검증 및 고객 유형 분석을 수행하는 통합 문서 처리 시스템입니다.

### 주요 기능

- **신분증 OCR**: 신분증 이미지에서 텍스트 추출 및 데이터 구조화
- **서류 OCR**: 서류 이미지를 구조화된 형식으로 OCR 처리
- **체크박스 탐지**: YOLO 모델을 사용한 체크박스 자동 탐지
- **체크박스 에이전트**: AI 기반 체크박스 매칭 및 상태 업데이트
- **문서 검증**: 신분증 및 서류 필드 검증
- **고객 유형 분석**: 체크된 항목을 기반으로 한 고객 유형 분석 및 요약

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                        프론트엔드 (React)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ UploadStep   │  │ProcessingStep│  │ ReviewStep    │      │
│  │ (업로드)     │→ │ (처리)       │→ │ (검토)        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                  │
│                   ┌────────▼────────┐                         │
│                   │ Zustand Store   │                         │
│                   │ (상태 관리)     │                         │
│                   └─────────────────┘                         │
└────────────────────────────┬──────────────────────────────────┘
                             │ HTTP/REST API
┌────────────────────────────▼──────────────────────────────────┐
│                      백엔드 (Flask)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ idocr.py     │  │checkbox_     │  │ agent.py      │      │
│  │ (신분증 OCR) │  │ agent.py     │  │ (문서 분석)   │      │
│  └──────────────┘  │ (체크박스)   │  └──────────────┘      │
│         │           └──────────────┘         │              │
│         │                  │                  │              │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐      │
│  │ EasyOCR     │   │checkbox_    │   │ OpenAI GPT  │      │
│  │ (OCR 엔진)  │   │ detection.py│   │ (AI 분석)   │      │
│  └─────────────┘   │ (YOLO)      │   └─────────────┘      │
│                     └─────────────┘                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              데이터 파일                              │   │
│  │  - structured_output.json                            │   │
│  │  - bbox_labels.json                                   │   │
│  │  - document.jpg                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## 프론트엔드 구조

### 기술 스택

- **프레임워크**: React 18 + TypeScript
- **빌드 도구**: Vite
- **상태 관리**: Zustand
- **스타일링**: Tailwind CSS
- **UI 컴포넌트**: 커스텀 컴포넌트

### 디렉토리 구조

```
frontend/src/
├── components/
│   ├── common/              # 공통 컴포넌트
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── PdfViewer.tsx
│   └── registration/        # 등록 관련 컴포넌트
│       ├── RegistrationModal.tsx
│       └── steps/
│           ├── UploadStep.tsx        # 1단계: 파일 업로드
│           ├── ProcessingStep.tsx    # 2단계: 문서 처리
│           ├── ReviewStep.tsx        # 3단계: 검토
│           ├── CompleteStep.tsx      # 4단계: 완료
│           └── IDCardResultView.tsx   # 신분증 결과 표시
├── stores/
│   └── useRegistrationStore.ts      # Zustand 상태 관리
├── api/
│   ├── config.ts            # API 설정
│   ├── idCardApi.ts         # 신분증 API
│   └── ocrApi.ts            # OCR API
├── types/
│   └── index.ts             # TypeScript 타입 정의
├── pages/                    # 페이지 컴포넌트
│   ├── Dashboard.tsx
│   ├── Report.tsx
│   ├── Settings.tsx
│   └── erp/
│       ├── Contracts.tsx
│       └── Customers.tsx
└── layouts/
    └── MainLayout.tsx        # 메인 레이아웃
```

### 주요 컴포넌트

#### 1. UploadStep
- **역할**: 신분증 및 서류 이미지 업로드
- **기능**:
  - 드래그 앤 드롭 파일 업로드
  - 파일 유효성 검사
  - 업로드된 파일 미리보기

#### 2. ProcessingStep
- **역할**: 문서 처리 파이프라인 실행
- **기능**:
  - 신분증 OCR 처리
  - 서류 OCR 처리
  - 체크박스 탐지
  - 체크박스 에이전트 처리
  - Agent 분석 실행
  - 처리 상태 표시 및 진행률 업데이트

#### 3. ReviewStep
- **역할**: 처리된 문서 검토 및 이슈 확인
- **기능**:
  - 검토필요항목 목록 표시
  - 이슈별 상세 정보 표시
  - Crop 이미지 표시
  - Agent 분석 결과 표시
  - 이슈 검토 완료 처리

#### 4. useRegistrationStore (Zustand)
- **역할**: 전역 상태 관리
- **주요 상태**:
  - `currentSession`: 현재 등록 세션
  - `agentResult`: Agent 분석 결과
  - `isModalOpen`: 모달 열림 상태
- **주요 액션**:
  - `startNewSession()`: 새 세션 시작
  - `addDocument()`: 문서 추가
  - `addIssues()`: 이슈 추가
  - `setAgentResult()`: Agent 결과 설정
  - `markIssueAsReviewed()`: 이슈 검토 완료

---

## 백엔드 구조

### 기술 스택

- **프레임워크**: Flask
- **OCR 엔진**: EasyOCR(신분증), PaddleOCR(서류)
- **체크박스 탐지**: YOLO (Ultralytics)
- **AI 분석**: OpenAI GPT API
- **이미지 처리**: OpenCV, PIL

### 디렉토리 구조

```
backend/
├── app.py                    # Flask 메인 애플리케이션
├── idocr.py                  # 신분증 OCR 처리
├── checkbox_detection.py     # 체크박스 탐지 (YOLO)
├── checkbox_agent.py         # 체크박스 에이전트 처리
├── agent.py                  # 문서 검증 및 분석 Agent
├── bbox_labeler.py           # 바운딩 박스 라벨링 도구
├── structured_output.json    # 서류 OCR 결과
├── bbox_labels.json          # 체크박스/텍스트 바운딩 박스
└── uploads/                  # 업로드된 파일 저장소
```

### 주요 모듈

#### 1. app.py
- **역할**: Flask 애플리케이션 및 API 엔드포인트 정의
- **주요 기능**:
  - 파일 업로드 처리
  - API 라우팅
  - CORS 설정
  - 에러 핸들링

#### 2. idocr.py
- **역할**: 신분증 OCR 처리
- **기능**:
  - EasyOCR을 사용한 텍스트 추출
  - 한자 특화 OCR 처리
  - 주민등록번호 마스킹
  - 신분증 필드 파싱 (성명, 주소, 발급일 등)

#### 3. checkbox_detection.py
- **역할**: 체크박스 탐지
- **기능**:
  - YOLO 모델을 사용한 체크박스 좌표 탐지
  - 바운딩 박스 좌표 반환

#### 4. checkbox_agent.py
- **역할**: 체크박스 매칭 및 상태 업데이트
- **기능**:
  - 좌표 기반 체크박스 매칭
  - AI 기반 체크박스 추론 (OpenAI GPT)
  - 텍스트 유사도 기반 매칭
  - `structured_output.json` 업데이트

#### 5. agent.py
- **역할**: 문서 검증 및 고객 유형 분석
- **기능**:
  - 신분증 데이터 검증
  - 신청서 필드 검증
  - 체크된 항목 분석
  - 고객 유형 분석 및 요약
  - 자연어 리포트 생성 (OpenAI GPT)

---

## 데이터 플로우

### 1. 파일 업로드 플로우

```
사용자 업로드
    ↓
[UploadStep] 파일 선택
    ↓
[useRegistrationStore] 문서 추가
    ↓
[ProcessingStep] 처리 시작
    ↓
[/api/upload] 신분증 OCR
    ↓
[idocr.py] OCR 처리
    ↓
[useRegistrationStore] OCR 결과 저장
```

### 2. 서류 처리 플로우

```
[ProcessingStep] 서류 OCR 요청
    ↓
[/api/document-ocr] 외부 OCR API 호출
    ↓
structured_output.json 생성
    ↓
[/api/detect-checkboxes] 체크박스 탐지
    ↓
[checkbox_detection.py] YOLO 모델 실행
    ↓
체크박스 좌표 목록 반환
    ↓
[/api/process-checkboxes] 체크박스 처리
    ↓
[checkbox_agent.py] 체크박스 매칭
    ↓
structured_output.json 업데이트
    ↓
[useRegistrationStore] 체크된 항목 저장
```

### 3. Agent 분석 플로우

```
[ProcessingStep] Agent 분석 요청
    ↓
[/api/run-agent] Agent 실행
    ↓
[agent.py] 문서 검증 및 분석
    ↓
OpenAI GPT API 호출
    ↓
검증 리포트 생성
    ↓
고객 유형 분석 리포트 생성
    ↓
[useRegistrationStore] Agent 결과 저장
    ↓
[ReviewStep] 결과 표시
```

### 4. 검토 플로우

```
[ReviewStep] 이슈 목록 표시
    ↓
사용자 이슈 선택
    ↓
이슈 상세 정보 로드
    ↓
[/api/crop-form-field] Crop 이미지 요청
    ↓
이미지 표시
    ↓
사용자 검토 완료
    ↓
[useRegistrationStore] 이슈 상태 업데이트
```

---

## 주요 컴포넌트

### 프론트엔드 컴포넌트

#### RegistrationModal
- 등록 프로세스의 메인 모달 컨테이너
- 단계별 네비게이션 관리

#### ProcessingStep
- 문서 처리 파이프라인 실행
- 진행 상태 표시
- 이슈 생성 및 저장

#### ReviewStep
- 검토필요항목 목록 표시
- 이슈별 상세 정보 표시
- Crop 이미지 동적 로드
- Agent 분석 결과 표시

### 백엔드 모듈

#### checkbox_agent.py
- **주요 함수**:
  - `process_checkbox_by_coordinate()`: 좌표 기반 체크박스 처리
  - `process_checkbox_click()`: 클릭 좌표 처리
  - `find_checkbox_by_coordinate()`: 좌표로 체크박스 찾기
  - `update_structured_output()`: structured_output.json 업데이트

#### agent.py
- **주요 함수**:
  - `process_documents()`: 문서 처리 메인 함수
  - `validate_id_card()`: 신분증 데이터 검증
  - `validate_form_fields()`: 신청서 필드 검증
  - `analyze_customer_type()`: 고객 유형 분석
  - `generate_customer_summary()`: 고객 유형 한줄 요약

---

## API 엔드포인트

### 파일 업로드 및 OCR

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/upload` | POST | 신분증 이미지 업로드 및 OCR 처리 |
| `/api/document-ocr` | POST | 서류 이미지 업로드 및 구조화된 OCR 처리 |

### 체크박스 처리

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/detect-checkboxes` | POST | 서류 이미지에서 체크박스 탐지 |
| `/api/process-checkboxes` | POST | 체크박스 좌표를 처리하여 structured_output.json 업데이트 |
| `/api/checkbox/process` | POST | 체크박스 클릭 좌표 처리 |
| `/api/checkbox/process-coordinate` | POST | 좌표 기반 체크박스 처리 |
| `/api/checkbox/list` | POST | 체크박스 목록 반환 |
| `/api/checkbox/load` | POST | 체크박스 상태 로드 |

### Agent 분석

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/run-agent` | POST | 신분증 및 서류 데이터를 기반으로 Agent 분석 실행 |
| `/api/agent-analysis` | POST | Agent 분석 실행 (대체 엔드포인트) |

### 데이터 조회

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/structured-output` | GET | structured_output.json 내용 반환 |
| `/api/bbox-labels` | GET | bbox_labels.json 내용 반환 |
| `/api/crop-form-field` | POST | 특정 필드 영역의 이미지 crop |

### 유틸리티

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/health` | GET | 서버 상태 확인 |
| `/api/log` | POST | 프론트엔드 로그 수신 |
| `/api/compare` | POST | 문서 비교 |
| `/api/upload-and-compare` | POST | 업로드 및 비교 |

---

## 데이터 구조

### RegistrationSession (프론트엔드)

```typescript
interface RegistrationSession {
  id: string;
  documents: UploadedDocument[];
  ocrResults: OCRResult[];
  issues: HighlightedIssue[];
  status: 'uploading' | 'processing' | 'reviewing' | 'completed' | 'cancelled';
  createdAt: Date;
}
```

### UploadedDocument

```typescript
interface UploadedDocument {
  id: string;
  file: File;
  fileName: string;
  type: 'id_card' | 'application' | 'other';
  status: 'pending' | 'processing' | 'completed' | 'error' | 'review_required';
  progress: number;
}
```

### HighlightedIssue

```typescript
interface HighlightedIssue {
  id: string;
  documentType: 'id_card' | 'application' | 'other';
  documentId: string;
  severity: 'error' | 'warning' | 'info';
  fieldName: string;
  issueType: 'missing' | 'invalid' | 'uncertain' | 'mismatch';
  title: string;
  description: string;
  reviewed: boolean;
  correctedValue?: string;
  cropImage?: string;
  metadata?: any;
}
```

### AgentResult

```typescript
interface AgentResult {
  success: boolean;
  results?: any[];
  final_report?: string;
  recommendations_report?: string;
  customer_analysis_report?: string;
  customer_summary?: string;
  summary?: any;
  id_card_validations?: any[];
  form_validations?: any[];
  name_comparison?: any;
  agent_logs?: any[];
  error?: string;
}
```

### structured_output.json 구조

```json
{
  "data": {
    "TV": {
      "TV_contract_period": {
        "options": [
          {
            "name": "5년",
            "text": "5년",
            "selected": true,
            "points": [[x1, y1], [x2, y2]]
          }
        ]
      }
    },
    "condition_": {
      "options": [
        {
          "name": "확인",
          "text": "확인",
          "selected": true,
          "points": [[x1, y1], [x2, y2]]
        }
      ]
    }
  }
}
```

### bbox_labels.json 구조

```json
{
  "data": {
    "labels": [
      {
        "id": 112,
        "bbox": [x1, y1, x2, y2],
        "text": "확인/기존 사용하시던 서비스는 기존 통신사에 해지하시기 바랍니다."
      }
    ]
  }
}
```

---

## 기술 스택

### 프론트엔드

- **React 18**: UI 프레임워크
- **TypeScript**: 타입 안정성
- **Vite**: 빌드 도구
- **Zustand**: 상태 관리
- **Tailwind CSS**: 스타일링
- **React Hooks**: 상태 및 사이드 이펙트 관리

### 백엔드

- **Flask**: 웹 프레임워크
- **Python 3.10+**: 프로그래밍 언어
- **EasyOCR**: OCR 엔진
- **YOLO (Ultralytics)**: 객체 탐지 모델
- **OpenAI GPT API**: AI 분석
- **OpenCV**: 이미지 처리
- **PIL (Pillow)**: 이미지 처리
- **NumPy**: 수치 연산

### 외부 서비스

- **OCR Structured API**: 서류 구조화 OCR 처리
  - URL: `https://sryjsymzaxpkzfhf.tunnel.elice.io`
- **OpenAI GPT API**: AI 기반 분석 및 리포트 생성

---

## 보안 고려사항

1. **주민등록번호 마스킹**: 신분증 OCR 결과에서 주민등록번호는 자동으로 마스킹 처리됩니다.
2. **CORS 설정**: 백엔드에서 CORS를 설정하여 프론트엔드와의 통신을 제한합니다.
3. **파일 업로드 제한**: 최대 파일 크기 16MB로 제한됩니다.
4. **파일 형식 검증**: 허용된 이미지 형식만 업로드 가능합니다.

---

## 확장 가능성

### 향후 개선 사항

1. **데이터베이스 통합**: 현재 파일 기반 저장소를 데이터베이스로 전환
2. **인증/인가**: 사용자 인증 및 권한 관리 시스템 추가
3. **배치 처리**: 여러 문서를 한 번에 처리하는 기능
4. **실시간 처리**: WebSocket을 사용한 실시간 처리 상태 업데이트
5. **모바일 지원**: 모바일 앱 또는 반응형 웹 지원 강화

---

## 참고 문서

- [프로세스 플로우](./PROCESS_FLOW.md): 전체 처리 프로세스 상세 설명
- [에이전트 문서](./AGENT_DOCUMENTATION.md): 체크박스 에이전트 및 분석 에이전트 설명
- [에이전트 간단 설명](./AGENT_SIMPLE.md): 에이전트 간단 설명







