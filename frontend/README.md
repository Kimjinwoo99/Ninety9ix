# KT 가입 시스템 - OCR Front

OCR 기반 가입서류 자동 판별 및 검증 시스템의 프론트엔드 애플리케이션입니다.

## 🚀 주요 기능

### 1. 신규 고객 등록 (모달 워크플로우)
- **단계 1: 서류 업로드** - 드래그 앤 드롭으로 여러 서류 한번에 업로드
- **단계 2: OCR 처리** - AI가 자동으로 문서 분석 및 텍스트 추출
- **단계 3: 검토** - Agent가 발견한 의심 항목만 집중 검토
  - 왼쪽: 하이라이트된 이슈 목록 (우선순위별)
  - 오른쪽: 문서 뷰어 (해당 항목 강조 표시)
  - 한 눈에 확인 가능한 검토 UI
- **단계 4: 완료** - ERP 자동 등록 및 영수증 출력

### 2. 대시보드
- 실시간 처리 현황 및 통계
- 오늘/주간/월간 데이터
- 평균 처리 시간, Agent 자동 승인율
- 최근 처리 내역

### 3. ERP 시스템
- **고객 관리**: 등록된 고객 조회, 검색, 필터링
- **계약 관리**: 계약 현황 조회
- **서류 관리**: 업로드된 서류 관리

### 4. 리포트
- 월별 처리 추이 차트
- Agent 성능 분석 (정확도, False Positive/Negative)
- 처리 시간 분포
- PDF 다운로드

### 5. 설정
- Agent 판단 규칙 설정
- 필수 필드 관리
- 사용자 및 권한 관리
- 알림 설정

## 🛠️ 기술 스택

- **React 18** + **TypeScript**
- **Vite** - 빠른 개발 환경
- **TailwindCSS** - 유틸리티 기반 스타일링
- **React Router** - 클라이언트 사이드 라우팅
- **Zustand** - 경량 상태 관리
- **Lucide React** - 아이콘

## 📦 설치 및 실행

```bash
# 의존성 설치
npm install

# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env

# 개발 서버 실행 (http://localhost:5173)
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview
```

## 환경 변수

`.env` 파일에서 백엔드 API URL을 설정합니다:

```
VITE_API_URL=http://localhost:5000
```

## 📁 프로젝트 구조

```
src/
├── components/          # 재사용 가능한 컴포넌트
│   ├── common/         # 공통 컴포넌트 (Header, Sidebar)
│   └── registration/   # 신규 등록 관련 컴포넌트
│       ├── RegistrationModal.tsx
│       └── steps/      # 단계별 컴포넌트
│           ├── UploadStep.tsx
│           ├── ProcessingStep.tsx
│           ├── ReviewStep.tsx
│           └── CompleteStep.tsx
├── layouts/            # 레이아웃 컴포넌트
│   └── MainLayout.tsx
├── pages/              # 페이지 컴포넌트
│   ├── Dashboard.tsx
│   ├── Report.tsx
│   ├── Settings.tsx
│   └── erp/
│       └── Customers.tsx
├── stores/             # 상태 관리 (Zustand)
│   └── useRegistrationStore.ts
├── types/              # TypeScript 타입 정의
│   └── index.ts
├── App.tsx             # 메인 App (라우팅)
└── main.tsx            # 엔트리 포인트
```

## 🎯 핵심 시나리오

### 현장 즉시 처리 플로우

1. 직원이 **신규 등록** 버튼 클릭 (왼쪽 하단 고정)
2. 전체화면 모달 표시
3. 고객이 작성한 서류들 업로드 (신청서, 위임장, 신분증 등)
4. OCR 자동 처리 (2-3초)
5. Agent가 이상 항목 발견 시:
   - **왼쪽 패널**: 확인 필요한 항목만 표시
     - ❌ 서명 누락
     - ⚠️ 생년월일 불일치
     - 🔍 주소 인식 불확실
   - **오른쪽 패널**: 클릭한 항목의 문서 자동 표시 + 하이라이팅
6. 검토자가 빠르게 확인 (평균 1-2분)
7. 승인 → ERP 자동 등록 완료
8. 고객번호 발급 및 영수증 출력

### 특징
- ✅ **빠른 처리**: 탭 전환 없이 한 화면에서 완료
- ✅ **집중 검토**: 의심 항목만 표시하여 시간 절약
- ✅ **직관적 UI**: 클릭 한 번으로 해당 문서 위치로 이동
- ✅ **실시간 피드백**: 고객 대기 시간 최소화

## 📄 PDF 크롭 및 OCR 기능

### PDF 뷰어 컴포넌트 (`PdfViewer`)

PDF 문서를 표시하고 특정 영역을 크롭하여 OCR 요청을 보낼 수 있는 컴포넌트입니다.

**주요 기능:**
- PDF 페이지 렌더링 및 네비게이션
- 줌 인/아웃 (50% ~ 300%)
- 마우스 드래그로 영역 선택
- 선택한 영역을 이미지로 추출하여 OCR 요청

**사용 예시:**
```tsx
import PdfViewer from './components/common/PdfViewer';

<PdfViewer
  fileUrl="/path/to/document.pdf"
  documentId="doc-123"
  onOCRResult={(text, confidence) => {
    console.log('OCR 결과:', text);
    console.log('신뢰도:', confidence);
  }}
  onOCRError={(error) => {
    console.error('OCR 오류:', error);
  }}
/>
```

### OCR API 클라이언트 (`ocrApi.ts`)

PDF의 특정 영역을 크롭하여 OCR 요청을 보내는 API 클라이언트입니다.

**현재 상태:**
- 실제 OCR 서버 연동은 아직 구현되지 않음
- 시뮬레이션 응답 반환
- 실제 서버 연동 시 `src/api/ocrApi.ts`의 TODO 주석 부분을 구현하면 됨

**API 함수:**
- `requestOCR(request: OCRRequest)` - 크롭 영역 정보로 OCR 요청
- `requestOCRFromImage(imageData: string, documentId: string)` - Base64 이미지로 OCR 요청

**실제 서버 연동 시:**
```typescript
// src/api/ocrApi.ts의 requestOCRFromImage 함수 수정
const formData = new FormData();
formData.append('image', imageData);
formData.append('documentId', documentId);

const response = await fetch('/api/ocr/process-image', {
  method: 'POST',
  body: formData,
});

return await response.json();
```

## 🔄 백엔드 API 연동

백엔드 서버는 `../backend` 폴더에 있습니다.

**백엔드 실행:**
```bash
cd ../backend
pip install -r requirements.txt
python app.py
```

**API 엔드포인트:**
- `GET /api/health` - 서버 상태 확인
- `POST /api/ocr` - OCR 처리
- `POST /api/checkbox/process` - 체크박스 처리
- `POST /api/log` - 프론트엔드 로그 수신

## 📝 다음 단계

- [x] 실제 문서 뷰어 구현 (PDF.js) - 완료
- [x] PDF 크롭 및 OCR 요청 기능 - 완료
- [ ] 백엔드 OCR API 연동 (`src/api/ocrApi.ts` 구현)
- [ ] 검토 항목 실시간 업데이트 (WebSocket)
- [ ] 사용자 인증 및 권한 관리
- [ ] 다국어 지원
- [ ] 모바일 반응형 최적화

## 📄 라이센스

MIT
