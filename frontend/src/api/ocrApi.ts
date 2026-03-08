/**
 * OCR API 클라이언트
 */

import { API_ENDPOINTS } from './config';

export interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  pageNumber: number;
}

export interface OCRRequest {
  documentId: string;
  fileUrl: string;
  cropRegion: CropRegion;
}

export interface OCRResponse {
  success: boolean;
  text?: string;
  confidence?: number;
  error?: string;
}

/**
 * PDF의 특정 영역을 크롭하여 OCR 요청을 보냅니다
 * 
 * @param request OCR 요청 정보
 * @returns OCR 결과
 */
export async function requestOCR(request: OCRRequest): Promise<OCRResponse> {
  try {
    console.log('OCR 요청:', {
      documentId: request.documentId,
      cropRegion: request.cropRegion,
    });

    const formData = new FormData();
    formData.append('documentId', request.documentId);
    formData.append('cropRegion', JSON.stringify(request.cropRegion));

    const response = await fetch(API_ENDPOINTS.ocr, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`OCR 요청 실패: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('OCR 요청 오류:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : '알 수 없는 오류',
    };
  }
}

/**
 * 크롭된 이미지 데이터를 Base64로 변환하여 OCR 요청을 보냅니다
 * 
 * @param imageData Base64 인코딩된 이미지 데이터
 * @param documentId 문서 ID
 * @returns OCR 결과
 */
export async function requestOCRFromImage(
  imageData: string,
  documentId: string
): Promise<OCRResponse> {
  try {
    console.log('OCR 요청 (이미지):', {
      documentId,
      imageSize: imageData.length,
    });

    const formData = new FormData();
    formData.append('image', imageData);
    formData.append('documentId', documentId);

    const response = await fetch(API_ENDPOINTS.ocr, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`OCR 요청 실패: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('OCR 요청 오류:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : '알 수 없는 오류',
    };
  }
}

