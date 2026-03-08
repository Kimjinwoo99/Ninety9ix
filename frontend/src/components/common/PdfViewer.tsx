import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { Crop, X, Loader } from 'lucide-react';
import { requestOCRFromImage } from '../../api/ocrApi';

// PDF.js 워커 설정
// CDN 또는 로컬 워커 사용 가능
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.js',
    import.meta.url
  ).toString();
}

interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface PdfViewerProps {
  fileUrl: string;
  documentId: string;
  onOCRResult?: (text: string, confidence: number) => void;
  onOCRError?: (error: string) => void;
  className?: string;
}

const PdfViewer: React.FC<PdfViewerProps> = ({
  fileUrl,
  documentId,
  onOCRResult,
  onOCRError,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.5);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 크롭 관련 상태
  const [isCropMode, setIsCropMode] = useState(false);
  const [cropStart, setCropStart] = useState<{ x: number; y: number } | null>(null);
  const [cropRegion, setCropRegion] = useState<CropRegion | null>(null);
  const [isProcessingOCR, setIsProcessingOCR] = useState(false);

  // PDF 로드
  useEffect(() => {
    const loadPdf = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const loadingTask = pdfjsLib.getDocument(fileUrl);
        const pdf = await loadingTask.promise;
        
        setPdfDoc(pdf);
        setTotalPages(pdf.numPages);
        setCurrentPage(1);
      } catch (err) {
        console.error('PDF 로드 오류:', err);
        setError('PDF 파일을 불러올 수 없습니다.');
      } finally {
        setIsLoading(false);
      }
    };

    loadPdf();
  }, [fileUrl]);

  // 페이지 렌더링
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;

    const renderPage = async () => {
      try {
        const page = await pdfDoc.getPage(currentPage);
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        if (!context) return;

        const viewport = page.getViewport({ scale });
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        await page.render({
          canvasContext: context,
          viewport: viewport,
        }).promise;
      } catch (err) {
        console.error('페이지 렌더링 오류:', err);
        setError('페이지를 렌더링할 수 없습니다.');
      }
    };

    renderPage();
  }, [pdfDoc, currentPage, scale]);

  // 크롭 모드 시작
  const handleStartCrop = useCallback(() => {
    setIsCropMode(true);
    setCropRegion(null);
    setCropStart(null);
  }, []);

  // 크롭 모드 취소
  const handleCancelCrop = useCallback(() => {
    setIsCropMode(false);
    setCropRegion(null);
    setCropStart(null);
  }, []);

  // 마우스 다운 - 크롭 시작점
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isCropMode || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setCropStart({ x, y });
    setCropRegion(null);
  }, [isCropMode]);

  // 마우스 이동 - 크롭 영역 업데이트
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isCropMode || !cropStart || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const width = Math.abs(x - cropStart.x);
    const height = Math.abs(y - cropStart.y);
    const minX = Math.min(x, cropStart.x);
    const minY = Math.min(y, cropStart.y);

    setCropRegion({
      x: minX,
      y: minY,
      width,
      height,
    });
  }, [isCropMode, cropStart]);

  // 마우스 업 - 크롭 완료
  const handleMouseUp = useCallback(() => {
    if (!isCropMode || !cropStart) return;
    setCropStart(null);
  }, [isCropMode, cropStart]);

  // 크롭된 영역을 이미지로 추출하고 OCR 요청
  const handleProcessCrop = useCallback(async () => {
    if (!cropRegion || !canvasRef.current || isProcessingOCR) return;

    try {
      setIsProcessingOCR(true);

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // 크롭된 영역을 새 캔버스에 그리기
      const cropCanvas = document.createElement('canvas');
      cropCanvas.width = cropRegion.width;
      cropCanvas.height = cropRegion.height;
      const cropCtx = cropCanvas.getContext('2d');
      if (!cropCtx) return;

      cropCtx.drawImage(
        canvas,
        cropRegion.x,
        cropRegion.y,
        cropRegion.width,
        cropRegion.height,
        0,
        0,
        cropRegion.width,
        cropRegion.height
      );

      // Base64로 변환
      const imageData = cropCanvas.toDataURL('image/png');

      // OCR 요청
      const result = await requestOCRFromImage(imageData, documentId);

      if (result.success && result.text) {
        onOCRResult?.(result.text, result.confidence || 0);
        handleCancelCrop();
      } else {
        onOCRError?.(result.error || 'OCR 처리에 실패했습니다.');
      }
    } catch (err) {
      console.error('OCR 처리 오류:', err);
      onOCRError?.(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setIsProcessingOCR(false);
    }
  }, [cropRegion, documentId, onOCRResult, onOCRError, handleCancelCrop, isProcessingOCR]);

  // 크롭 영역 그리기
  useEffect(() => {
    if (!canvasRef.current || !cropRegion) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 페이지 다시 렌더링
    const redraw = async () => {
      if (!pdfDoc) return;
      const page = await pdfDoc.getPage(currentPage);
      const viewport = page.getViewport({ scale });
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      await page.render({
        canvasContext: ctx,
        viewport: viewport,
      }).promise;

      // 크롭 영역 그리기
      if (cropRegion) {
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(cropRegion.x, cropRegion.y, cropRegion.width, cropRegion.height);
        
        // 반투명 배경
        ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
        ctx.fillRect(cropRegion.x, cropRegion.y, cropRegion.width, cropRegion.height);
      }
    };

    redraw();
  }, [cropRegion, pdfDoc, currentPage, scale]);

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center h-96 ${className}`}>
        <Loader className="animate-spin text-blue-600" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-96 text-red-600 ${className}`}>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {/* 툴바 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            이전
          </button>
          <span className="text-sm text-gray-700">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            다음
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((prev) => Math.max(0.5, prev - 0.25))}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            -
          </button>
          <span className="text-sm text-gray-700 w-16 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((prev) => Math.min(3, prev + 0.25))}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            +
          </button>
        </div>

        <div className="flex items-center gap-2">
          {!isCropMode ? (
            <button
              onClick={handleStartCrop}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Crop size={16} />
              영역 선택
            </button>
          ) : (
            <>
              <button
                onClick={handleCancelCrop}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <X size={16} />
                취소
              </button>
              {cropRegion && (
                <button
                  onClick={handleProcessCrop}
                  disabled={isProcessingOCR}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessingOCR ? (
                    <>
                      <Loader className="animate-spin" size={16} />
                      처리 중...
                    </>
                  ) : (
                    <>
                      <Crop size={16} />
                      OCR 요청
                    </>
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* PDF 뷰어 */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-gray-100 p-4 flex justify-center"
      >
        <div className="relative inline-block">
          <canvas
            ref={canvasRef}
            className={`border border-gray-300 shadow-lg ${
              isCropMode ? 'cursor-crosshair' : 'cursor-default'
            }`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          />
        </div>
      </div>

      {/* 크롭 모드 안내 */}
      {isCropMode && !cropRegion && (
        <div className="p-3 bg-blue-50 border-t border-blue-200 text-sm text-blue-800">
          마우스를 드래그하여 OCR을 수행할 영역을 선택하세요.
        </div>
      )}
    </div>
  );
};

export default PdfViewer;

