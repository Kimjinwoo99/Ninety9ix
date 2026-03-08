import React, { useCallback, useState } from 'react';
import { Upload, FileText, CheckCircle, Loader, X } from 'lucide-react';
import { useRegistrationStore } from '../../../stores/useRegistrationStore';
import type { UploadedDocument, DocumentType } from '../../../types';

interface UploadStepProps {
  onNext: () => void;
}

const UploadStep: React.FC<UploadStepProps> = ({ onNext }) => {
  const { currentSession, addDocument, removeDocument, updateDocumentStatus, updateSessionStatus } = useRegistrationStore();
  const [isDragging, setIsDragging] = useState(false);
  
  const handleRemoveDocument = (documentId: string) => {
    if (confirm('이 문서를 삭제하시겠습니까?')) {
      removeDocument(documentId);
    }
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, category: 'id_card' | 'document') => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files, category);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, category: 'id_card' | 'document') => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files, category);
      // input value를 리셋하여 같은 파일도 다시 선택 가능하게 함
      e.target.value = '';
    }
  };

  const handleFiles = (files: File[], category: 'id_card' | 'document') => {
    files.forEach((file) => {
      const documentId = `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      // 카테고리에 따라 타입 결정
      // 서류 업로드는 'document' 타입으로 분류 (기타가 아님)
      const documentType: DocumentType = category === 'id_card' ? 'id_card' : 'document';
      
      // 문서 추가 (업로드만, OCR은 나중에)
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
      
      addDocument(newDocument);
    });
  };

  const processIDCard = async (documentId: string, file: File) => {
    try {
      updateDocumentStatus(documentId, 'processing', 50);
      
      // 실제 OCR API 호출
      const result = await uploadAndProcessIDCard(file);
      
      if (result.success) {
        // OCR 결과를 문서에 저장
        updateDocumentStatus(documentId, 'review_required', 100);
        
        // OCR 결과를 세션에 저장 (나중에 ReviewStep에서 사용)
        const { currentSession } = useRegistrationStore.getState();
        if (currentSession) {
          useRegistrationStore.setState({
            currentSession: {
              ...currentSession,
              ocrResults: [
                ...currentSession.ocrResults,
                {
                  documentId,
                  extractedData: result.data,
                  confidence: 0.95,
                  processedAt: new Date(),
                  idCardResult: {
                    name: result.data.name,
                    resident_number: result.data.resident_number,
                    address: result.data.address,
                    crops: result.crops,
                    masked_image: result.masked_image,
                    ocr_text: result.ocr_text,
                    ocr_lines: result.ocr_lines,
                  },
                },
              ],
            },
          });
          
          // OCR 완료 후 자동으로 ProcessingStep으로 이동
          updateSessionStatus('processing');
        }
      } else {
        updateDocumentStatus(documentId, 'error', 0);
        console.error('OCR 처리 실패:', result.error);
        alert(`OCR 처리 실패: ${result.error || '알 수 없는 오류'}`);
      }
    } catch (error) {
      updateDocumentStatus(documentId, 'error', 0);
      console.error('신분증 OCR 처리 오류:', error);
      alert(`OCR 처리 중 오류가 발생했습니다: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  };

  const detectDocumentType = (fileName: string): DocumentType => {
    const lower = fileName.toLowerCase();
    if (lower.includes('신청') || lower.includes('application')) return 'application';
    if (lower.includes('위임') || lower.includes('proxy')) return 'proxy';
    if (lower.includes('신분') || lower.includes('id')) return 'id_card';
    return 'other';
  };

  const simulateUpload = (documentId: string) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      
      if (progress >= 100) {
        clearInterval(interval);
        updateDocumentStatus(documentId, 'processing');
        // OCR 처리 시뮬레이션
        setTimeout(() => {
          updateDocumentStatus(documentId, 'review_required');
        }, 2000);
      } else {
        updateDocumentStatus(documentId, 'uploading', progress);
      }
    }, 200);
  };

  const handleProceedToOCR = async () => {
    // 모든 문서가 업로드 완료되었는지 확인
    const allUploaded = currentSession?.documents.every(
      (doc) => doc.status !== 'uploading'
    );
    
    if (allUploaded && currentSession?.documents.length > 0) {
      // 세션 상태를 'processing'으로 변경하여 다음 단계로 이동
      updateSessionStatus('processing');
      onNext();
    }
  };

  const getDocumentTypeLabel = (type: DocumentType) => {
    const labels: Record<DocumentType, string> = {
      application: '신청서',
      proxy: '위임장',
      id_card: '신분증',
      document: '서류',
      other: '기타',
    };
    return labels[type];
  };

  const getStatusIcon = (status: UploadedDocument['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader className="animate-spin text-blue-500" size={20} />;
      case 'processing':
      case 'review_required':
        return <CheckCircle className="text-green-500" size={20} />;
      default:
        return <FileText className="text-gray-400" size={20} />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Drag & Drop Area - 좌: 신분증, 우: 서류 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 좌측: 신분증 업로드 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, 'id_card')}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400'
        }`}
      >
          <Upload className="mx-auto mb-3 text-gray-400" size={36} />
          <h3 className="text-base font-semibold text-gray-900 mb-2">
            신분증 업로드
          </h3>
          <p className="text-xs text-gray-500 mb-3">
            주민등록증, 운전면허증 등 (JPG, PNG)
          </p>
          <label className="inline-block">
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={(e) => handleFileInput(e, 'id_card')}
              className="hidden"
            />
            <span className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer transition-colors">
              파일 선택
            </span>
          </label>
        </div>

        {/* 우측: 서류 업로드 */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, 'document')}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            isDragging
              ? 'border-green-500 bg-green-50'
              : 'border-gray-300 hover:border-green-400'
          }`}
        >
          <Upload className="mx-auto mb-3 text-gray-400" size={36} />
          <h3 className="text-base font-semibold text-gray-900 mb-2">
            서류 업로드
        </h3>
          <p className="text-xs text-gray-500 mb-3">
            신청서, 위임장 등 (PDF, JPG, PNG)
        </p>
        <label className="inline-block">
          <input
            type="file"
            multiple
            accept="image/*,.pdf"
              onChange={(e) => handleFileInput(e, 'document')}
            className="hidden"
          />
            <span className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 cursor-pointer transition-colors">
            파일 선택
          </span>
        </label>
        </div>
      </div>

      {/* Uploaded Documents List */}
      {currentSession && currentSession.documents.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-900">업로드된 서류</h4>
          
          {currentSession.documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg"
            >
              {getStatusIcon(doc.status)}
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">{doc.fileName}</span>
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {getDocumentTypeLabel(doc.type)}
                  </span>
                </div>
                
                {doc.status === 'uploading' && doc.progress !== undefined && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${doc.progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 mt-1">
                      {doc.progress}%
                    </span>
                  </div>
                )}
                
                {doc.status === 'processing' && (
                  <span className="text-sm text-blue-600 mt-1">처리 중...</span>
                )}
                
                {doc.status === 'review_required' && (
                  <span className="text-sm text-green-600 mt-1">✓ 완료</span>
                )}
              </div>
              
              {/* 삭제 버튼 */}
              <button
                onClick={() => handleRemoveDocument(doc.id)}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="삭제"
              >
                <X size={20} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Next Button */}
      <div className="flex justify-end">
        <button
          onClick={handleProceedToOCR}
          disabled={
            !currentSession ||
            currentSession.documents.length === 0 ||
            currentSession.documents.some((doc) => doc.status === 'uploading')
          }
          className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          다음 단계 →
        </button>
      </div>
    </div>
  );
};

export default UploadStep;

