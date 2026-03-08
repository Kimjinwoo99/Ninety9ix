// 문서 유형
export type DocumentType = 'application' | 'proxy' | 'id_card' | 'document' | 'other';

// 문서 상태
export type DocumentStatus = 'uploading' | 'processing' | 'review_required' | 'approved' | 'rejected';

// 이슈 심각도
export type IssueSeverity = 'error' | 'warning' | 'info';

// 이슈 유형
export type IssueType = 'mismatch' | 'missing' | 'uncertain' | 'format_error';

// 업로드된 문서
export interface UploadedDocument {
  id: string;
  type: DocumentType;
  fileName: string;
  fileUrl: string;
  uploadedAt: Date;
  status: DocumentStatus;
  progress?: number;
  file?: File; // 파일 객체 (OCR 처리용)
}

// OCR 인식 결과
export interface OCRResult {
  documentId: string;
  extractedData: Record<string, unknown>;
  confidence: number;
  processedAt: Date;
  // 신분증 OCR 결과
  idCardResult?: {
    name: string;
    resident_number: string;
    address: string;
    issue_date?: string;
    crops: {
      name?: string;
      resident?: string;
      address?: string;
      issue_date?: string;
    };
    masked_image?: string;
    ocr_text: string;
    ocr_lines: any[];
  };
}

// 하이라이트된 이슈
export interface HighlightedIssue {
  id: string;
  documentType: DocumentType;
  documentId: string;
  severity: IssueSeverity;
  fieldName: string;
  issueType: IssueType;
  
  title: string;
  description: string;
  
  location?: {
    pageNumber?: number;
    boundingBox?: { x: number; y: number; width: number; height: number };
    formFieldId?: string;
  };
  
  reviewed: boolean;
  reviewNote?: string;
  correctedValue?: unknown;
  cropImage?: string; // 크롭된 이미지 (base64)
  metadata?: {
    checkboxes?: Array<{x1: number, y1: number, x2: number, y2: number, conf?: number}>;
    [key: string]: any;
  };
}

// 등록 세션
export interface RegistrationSession {
  id: string;
  documents: UploadedDocument[];
  ocrResults: OCRResult[];
  issues: HighlightedIssue[];
  status: 'uploading' | 'processing' | 'reviewing' | 'completed' | 'cancelled';
  createdAt: Date;
  completedAt?: Date;
}

// ERP 고객 데이터
export interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
  address?: string;
  birthDate?: string;
  registeredAt: Date;
  status: 'active' | 'inactive' | 'pending';
}

// 통계 데이터
export interface Statistics {
  today: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
  };
  weekly: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
  };
  monthly: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
  };
  avgProcessingTime: number; // 초 단위
  autoApprovalRate: number; // 퍼센트
}

