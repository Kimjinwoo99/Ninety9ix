import React, { useState, useEffect } from 'react';
import { CheckCircle, Printer, RotateCcw } from 'lucide-react';
import { useRegistrationStore } from '../../../stores/useRegistrationStore';

interface CompleteStepProps {
  onNext: () => void;
}

const CompleteStep: React.FC<CompleteStepProps> = ({ onNext }) => {
  const { currentSession, closeModal, startNewSession, openModal, agentResult } = useRegistrationStore();

  const handleNewCustomer = () => {
    closeModal();
    setTimeout(() => {
      startNewSession();
      openModal();
    }, 100);
  };

  const handleClose = () => {
    closeModal();
  };

  // 고객 이름 가져오기 (여러 소스에서 시도)
  let customerName = '';
  
  // 1. 신분증 OCR 결과에서 가져오기
  const idCardOCRResult = currentSession?.ocrResults.find(
    (ocr) => ocr.idCardResult !== undefined
  )?.idCardResult;
  
  if (idCardOCRResult?.name) {
    customerName = idCardOCRResult.name;
  }
  
  // 2. agentResult의 name_comparison에서 가져오기
  if (!customerName && agentResult?.comparisons) {
    const nameComparison = agentResult.comparisons.find(
      (comp: any) => comp.field === 'name_comparison'
    );
    if (nameComparison) {
      customerName = nameComparison.id_card?.value || nameComparison.form?.value || '';
    }
  }
  
  // 3. structured_output에서 Application_date.signarea 가져오기 (비동기로 시도)
  const [formName, setFormName] = useState<string>('');
  useEffect(() => {
    if (!customerName) {
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/structured-output`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.Application_date?.options) {
            const signarea = data.Application_date.options.find(
              (opt: any) => opt.name === 'signarea'
            );
            if (signarea?.text) {
              setFormName(signarea.text);
            }
          }
        })
        .catch(() => {});
    }
  }, [customerName]);

  // 최종 고객 이름 결정
  const finalCustomerName = customerName || formName || '고객명 없음';

  // 실제 고객 정보
  const customerInfo = {
    id: 'K' + Date.now().toString().slice(-8),
    name: finalCustomerName,
    phone: '010-1234-5678', // 필요시 structured_output에서 추출 가능
    registeredAt: new Date().toLocaleString('ko-KR'),
  };

  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-8">
      {/* Success Icon */}
      <div className="relative">
        <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center">
          <CheckCircle className="text-green-600" size={56} />
        </div>
        <div className="absolute -top-2 -right-2">
          <div className="w-8 h-8 bg-green-500 rounded-full animate-ping opacity-75"></div>
        </div>
      </div>

      {/* Success Message */}
      <div className="text-center">
        <h3 className="text-3xl font-bold text-gray-900 mb-2">
          처리 완료!
        </h3>
        <p className="text-lg text-gray-600">
          고객 정보가 성공적으로 승인되었습니다.
        </p>
      </div>

      {/* Customer Info Card */}
      <div className="w-full max-w-md bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
        <h4 className="text-sm font-semibold text-blue-900 mb-4">등록 정보</h4>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">고객번호</span>
            <span className="font-semibold text-gray-900">{customerInfo.id}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">고객명</span>
            <span className="font-semibold text-gray-900">{customerInfo.name}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">연락처</span>
            <span className="font-semibold text-gray-900">{customerInfo.phone}</span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">등록일시</span>
            <span className="font-semibold text-gray-900">{customerInfo.registeredAt}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 pt-4">
        <button
          onClick={handleClose}
          className="px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
        >
          <Printer size={20} />
          영수증 출력
        </button>
        
        <button
          onClick={handleNewCustomer}
          className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <RotateCcw size={20} />
          새 고객 처리
        </button>
      </div>

      {/* Close Link */}
      <button
        onClick={handleClose}
        className="text-sm text-gray-500 hover:text-gray-700 underline"
      >
        닫기
      </button>
    </div>
  );
};

export default CompleteStep;

