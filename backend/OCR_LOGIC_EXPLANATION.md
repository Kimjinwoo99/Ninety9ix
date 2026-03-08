# OCR 로직 작동 방식 및 서류 처리 설명

## 📋 목차
1. [현재 OCR 로직 작동 방식](#현재-ocr-로직-작동-방식)
2. [주석처리된 서류 OCR 로직](#주석처리된-서류-ocr-로직)
3. [전체 처리 흐름](#전체-처리-흐름)

---

## 현재 OCR 로직 작동 방식

### 1. **문서 업로드 단계 (UploadStep.tsx)**

#### 파일 분류
- **신분증 업로드 영역**: `type: 'id_card'`로 분류
- **서류 업로드 영역**: 파일명 기반 자동 분류
  - `application`: 신청서 관련 파일
  - `proxy`: 위임장 관련 파일
  - `other`: 기타 문서

#### 업로드 처리
```typescript
// 파일 객체를 저장만 하고, OCR은 즉시 실행하지 않음
const newDocument: UploadedDocument = {
  id: documentId,
  type: documentType,
  fileName: file.name,
  fileUrl: URL.createObjectURL(file),
  uploadedAt: new Date(),
  status: 'review_required', // 업로드 완료 상태
  progress: 100,
  file: file, // 파일 객체 저장 (나중에 OCR 처리용)
};
```

**핵심**: 업로드 시점에는 파일만 저장하고, OCR 처리는 "다음 단계" 버튼 클릭 시 시작됩니다.

---

### 2. **OCR 처리 단계 (ProcessingStep.tsx)**

#### 처리 흐름

```
1. 문서 목록 확인
   ↓
2. 각 문서 타입별 분기 처리
   ↓
3. 신분증 (id_card) → idocr.py 실행
   ↓
4. 서류 (application/proxy/other) → OCR 스킵
   ↓
5. 모든 처리 완료 후 검토 단계로 이동
```

#### 신분증 OCR 처리 (100-267줄)

```typescript
if (document.type === 'id_card') {
  // idocr.py를 사용하여 신분증 OCR 처리
  const result = await uploadAndProcessIDCard(document.file!);
  
  if (result.success) {
    // 1. OCR 결과를 세션에 저장
    // 2. 문서 상태를 'review_required'로 업데이트
    // 3. 신분증 이슈 생성 (성명, 주민번호, 주소, 발급일, 신분증 전체)
  }
}
```

**처리 내용**:
- `idocr.py` 모듈 호출
- 성명, 주민번호(마스킹), 주소, 발급일 추출
- 각 필드별 crop 이미지 생성
- 마스킹된 전체 이미지 생성
- 검토용 이슈 5개 자동 생성

#### 서류 OCR 처리 (268-272줄)

```typescript
else {
  // 서류인 경우 OCR 처리 없이 바로 완료 처리
  console.log(`[ProcessingStep] 서류 문서 (${document.type}) - OCR 처리 스킵`);
  useRegistrationStore.getState().updateDocumentStatus(document.id, 'review_required', 100);
}
```

**현재 상태**: 서류는 OCR 처리를 하지 않고, 바로 `review_required` 상태로 설정됩니다.

---

### 3. **idocr.py 모듈 (독립 실행 모듈)**

#### 주요 기능

1. **OCR 엔진 초기화**
   ```python
   ocr = easyocr.Reader(['ko', 'en'], gpu=False)  # 일반 OCR
   chinese_ocr = easyocr.Reader(['ch_sim', 'en'], gpu=False)  # 한문 OCR
   number_ocr = easyocr.Reader(['en'], gpu=False)  # 숫자 특화 OCR
   ```

2. **처리 단계**
   - **1단계**: 이미지 읽기 및 전처리
   - **2단계**: EasyOCR로 전체 텍스트 추출
   - **3단계**: OCR 텍스트를 6줄 형식으로 정규화
   - **4단계**: 한문(한자) 재인식 (이름 옆 괄호 내)
   - **5단계**: 정보 추출 (성명, 주민번호, 주소, 발급일)
   - **6단계**: 발급일 형식 검증 및 재OCR (필요시)
   - **7단계**: 이미지 마스킹 및 크롭

3. **반환 데이터 구조**
   ```python
   {
     'success': True,
     'name': {
       'text': '홍길동',
       'bbox': [[x1, y1], [x2, y2], ...],
       'crop_image': 'base64_encoded_image'
     },
     'resident_number': {
       'text': '991130-1234567',
       'masked_text': '991130-XXXXXXX',
       'bbox': [...],
       'crop_image': 'base64_encoded_image'
     },
     'address': {...},
     'issue_date': {...},
     'ocr_text': '전체 OCR 텍스트',
     'masked_image': 'base64_encoded_masked_image',
     'ocr_lines': [...]
   }
   ```

---

### 4. **Agent 분석 (비동기 실행)**

#### 실행 시점
- 신분증 OCR 완료 후 자동 실행
- **비동기 처리**: 결과를 기다리지 않고 검토 단계로 이동

#### 처리 내용
```typescript
// agent.py의 process_documents 호출
// - 신분증 데이터 검증
// - structured_output.json 검증
// - 성명 비교
// - 분석 리포트 생성
```

---

## 주석처리된 서류 OCR 로직

### 1. **ProcessingStep.tsx (420-459줄)**

#### 주석처리된 코드
```typescript
/*
// 다른 문서들의 OCR 처리 시뮬레이션
const timer = setTimeout(() => {
  // 시뮬레이션: Agent가 발견한 이슈들 (신분증이 아닌 경우만)
  const otherDocuments = currentSession?.documents.filter((doc) => doc.type !== 'id_card') || [];
  if (otherDocuments.length > 0) {
    const mockIssues: HighlightedIssue[] = [
      {
        id: 'issue-1',
        documentType: 'application',
        documentId: otherDocuments[0]?.id || '',
        severity: 'warning',
        fieldName: '생년월일',
        issueType: 'mismatch',
        title: '생년월일 불일치',
        description: '신청서: 1990.03.15 ≠ 신분증: 1990.03.25',
        reviewed: false,
      },
      {
        id: 'issue-2',
        documentType: 'proxy',
        documentId: otherDocuments[1]?.id || '',
        severity: 'error',
        fieldName: '서명',
        issueType: 'missing',
        title: '서명 누락',
        description: '위임인 서명란이 비어있습니다',
        reviewed: false,
      },
    ];
    addIssues(mockIssues);
  }
  
  updateSessionStatus('reviewing');
  setTimeout(() => {
    onNext();
  }, 500);
}, 2000);
*/
```

#### 설명
- **목적**: 신분증이 아닌 다른 문서(신청서, 위임장 등)에 대한 OCR 처리 시뮬레이션
- **처리 방식**: 
  - 하드코딩된 mock 이슈 생성
  - 2초 후 검토 단계로 이동
- **현재 상태**: 주석처리됨 (실제 서류 OCR 로직 구현 대기 중)

#### 향후 구현 방향
1. **서류 OCR 모듈 생성** (`document_ocr.py` 등)
2. **structured_output.json 생성**: 서류 OCR 결과를 구조화된 JSON으로 변환
3. **Agent 분석**: 신분증과 서류 데이터 비교
4. **이슈 자동 생성**: 불일치 항목을 검토 항목으로 추가

---

### 2. **ReviewStep.tsx (736-755줄)**

#### 주석처리된 코드
```typescript
{/*
if (document && document.fileName.toLowerCase().endsWith('.pdf')) {
  return (
    <div className="flex-1 min-h-0">
      <PdfViewer
        fileUrl={document.fileUrl}
        documentId={document.id}
        onOCRResult={(text, confidence) => {
          // OCR 결과 처리
        }}
        onOCRError={(error) => {
          alert(`OCR 오류: ${error}`);
        }}
        className="h-full"
      />
    </div>
  );
}
*/}
```

#### 설명
- **목적**: PDF 문서를 PDF 뷰어로 표시하고 OCR 처리
- **현재 상태**: 주석처리됨
- **이유**: 현재는 신분증만 처리하고, 서류는 OCR 처리를 하지 않음

---

## 전체 처리 흐름

### 현재 구현된 흐름

```
[1단계: 업로드]
  ├─ 신분증 업로드 → type: 'id_card'
  └─ 서류 업로드 → type: 'application' | 'proxy' | 'other'
  
[2단계: OCR 처리]
  ├─ 신분증 (id_card)
  │   ├─ idocr.py 실행
  │   ├─ 정보 추출 (성명, 주민번호, 주소, 발급일)
  │   ├─ 이미지 마스킹 및 크롭
  │   └─ 검토 이슈 생성 (5개)
  │
  └─ 서류 (application/proxy/other)
      └─ OCR 스킵 → review_required 상태로 설정

[3단계: Agent 분석]
  ├─ 신분증 데이터 검증
  ├─ structured_output.json 검증
  ├─ 성명 비교
  └─ 분석 리포트 생성 (비동기)

[4단계: 검토]
  ├─ 신분증 이슈 검토 (성명, 주민번호, 주소, 발급일, 전체)
  ├─ Agent 분석 결과 확인
  └─ 승인/반려 처리

[5단계: 완료]
  ├─ 고객 정보 저장 (로컬 스토리지)
  ├─ 계약 정보 저장
  └─ 대시보드 통계 업데이트
```

### 향후 구현 예정 (주석처리된 부분)

```
[2단계: OCR 처리 - 향후]
  └─ 서류 (application/proxy/other)
      ├─ document_ocr.py 실행 (구현 예정)
      ├─ 서류 OCR 텍스트 추출
      ├─ structured_output.json 생성
      └─ 검토 이슈 생성 (불일치 항목)

[3단계: Agent 분석 - 향후]
  ├─ 신분증 데이터 검증
  ├─ 서류 데이터 검증 (structured_output.json)
  ├─ 필드별 비교 (성명, 생년월일, 주소 등)
  └─ 불일치 항목 하이라이팅
```

---

## 주요 특징

### ✅ 현재 구현됨
1. **신분증 OCR**: 완전 자동화 (idocr.py)
2. **정보 추출**: 성명, 주민번호(마스킹), 주소, 발급일
3. **이미지 처리**: 마스킹, 크롭, 한문 재인식
4. **Agent 분석**: 신분증 검증 및 성명 비교
5. **대시보드 연동**: 승인 완료 시 자동 반영

### ⏳ 향후 구현 예정
1. **서류 OCR**: 신청서, 위임장 등 OCR 처리
2. **structured_output.json 자동 생성**: 서류 OCR 결과 구조화
3. **필드 비교**: 신분증과 서류 간 상세 비교
4. **PDF 뷰어**: PDF 문서 표시 및 OCR

---

## 파일 구조

```
프로젝트 루트/
├── idocr.py                    # 신분증 OCR 모듈 (독립 실행)
├── agent.py                    # Agent 분석 모듈
├── app.py                      # Flask 백엔드
└── KT-CS-project-front/
    └── src/
        └── components/
            └── registration/
                └── steps/
                    ├── UploadStep.tsx        # 업로드 단계
                    ├── ProcessingStep.tsx    # OCR 처리 단계
                    ├── ReviewStep.tsx        # 검토 단계
                    └── CompleteStep.tsx      # 완료 단계
```

---

## 참고사항

1. **서류 OCR은 현재 구현되지 않음**: 주석처리된 코드는 향후 구현을 위한 참고용입니다.
2. **structured_output.json**: 현재는 수동으로 제공되며, 향후 서류 OCR 결과로 자동 생성 예정입니다.
3. **Agent 분석**: 신분증 데이터와 structured_output.json을 비교하여 불일치를 찾습니다.

