import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useRegistrationStore } from '../../stores/useRegistrationStore';
import UploadStep from './steps/UploadStep';
import ProcessingStep from './steps/ProcessingStep';
import ReviewStep from './steps/ReviewStep';
import CompleteStep from './steps/CompleteStep';

type Step = 'upload' | 'processing' | 'review' | 'complete';

const RegistrationModal: React.FC = () => {
  const { isModalOpen, closeModal, currentSession, cancelSession } = useRegistrationStore();
  const [currentStep, setCurrentStep] = useState<Step>('upload');

  // 모달이 열릴 때 새 세션이면 upload 단계로 초기화
  useEffect(() => {
    if (isModalOpen && currentSession) {
      // 새 세션이거나 uploading 상태면 upload 단계로
      if (currentSession.status === 'uploading' && currentStep !== 'upload') {
        setCurrentStep('upload');
      }
    } else if (!isModalOpen) {
      // 모달이 닫히면 단계 초기화
      setCurrentStep('upload');
    }
  }, [isModalOpen, currentSession?.id]);

  useEffect(() => {
    if (!currentSession) return;
    
    // status 기반 자동 단계 전환 최소화
    // 단계 전환은 주로 onNext 콜백으로만 수행
    // upload → processing (단 1회만, upload 단계에서만)
    if (currentSession.status === 'processing' && currentStep === 'upload') {
      setCurrentStep('processing');
    }
    
    // completed 상태는 자동 전환 (ReviewStep에서 completeSession 호출 시)
    if (currentSession.status === 'completed' && currentStep !== 'complete') {
      setCurrentStep('complete');
    }
    
    // 'uploading' 상태로 되돌아가는 것 절대 금지
    // 'reviewing' 상태는 단계 전환에 사용하지 않음 (ProcessingStep의 onNext로만 전환)
    // 'processing' 상태에서 다른 단계로 자동 전환 금지
  }, [currentSession?.status, currentStep]);

  // ProcessingStep에서 취소 이벤트 감지
  React.useEffect(() => {
    const handleProcessingCancelled = () => {
      cancelSession();
    };
    
    window.addEventListener('processing-cancelled', handleProcessingCancelled);
    return () => {
      window.removeEventListener('processing-cancelled', handleProcessingCancelled);
    };
  }, [cancelSession]);

  const handleClose = () => {
    if (currentStep !== 'complete' && currentSession) {
      if (confirm('진행 중인 작업이 있습니다. 정말 닫으시겠습니까?')) {
        // ProcessingStep에 취소 신호 전달
        if (currentStep === 'processing') {
          window.dispatchEvent(new CustomEvent('cancel-processing'));
        }
        cancelSession();
        setCurrentStep('upload'); // 단계 초기화
      }
    } else {
      closeModal();
      setCurrentStep('upload'); // 단계 초기화
    }
  };

  if (!isModalOpen) return null;

  const stepConfig = {
    upload: { title: '① 서류 업로드' },
    processing: { title: '② OCR 처리 중' },
    review: { title: '③ 검토' },
    complete: { title: '④ 완료' },
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">신규 고객 등록</h2>
            <p className="text-sm text-gray-500 mt-1">{stepConfig[currentStep].title}</p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} className="text-gray-600" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="px-6 pt-4">
          <div className="flex items-center justify-between mb-2">
            {Object.entries(stepConfig).map(([key, config], index) => {
              const isActive = key === currentStep;
              const isPassed = Object.keys(stepConfig).indexOf(currentStep) > index;
              
              return (
                <React.Fragment key={key}>
                  <div className="flex items-center flex-1">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                        isActive
                          ? 'bg-blue-600 text-white'
                          : isPassed
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {index + 1}
                    </div>
                    <span
                      className={`ml-2 text-sm font-medium ${
                        isActive ? 'text-blue-600' : isPassed ? 'text-green-600' : 'text-gray-500'
                      }`}
                    >
                      {config.title.replace(/[①②③④]/g, '').trim()}
                    </span>
                  </div>
                  {index < Object.keys(stepConfig).length - 1 && (
                    <div
                      className={`h-1 flex-1 mx-2 rounded ${
                        isPassed ? 'bg-green-500' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentStep === 'upload' && (
            <UploadStep
              onNext={() => {
                // 업로드 끝 → processing 시작
                console.log('[RegistrationModal] UploadStep에서 다음 단계로 이동');
                setCurrentStep('processing');
                if (currentSession) {
                  useRegistrationStore.getState().updateSessionStatus('processing');
                }
              }}
            />
          )}
          {currentStep === 'processing' && (
            <ProcessingStep
              onNext={() => {
                // ProcessingStep에서 모든 준비가 완료되었을 때만 호출됨
                console.log('[RegistrationModal] ProcessingStep onNext() → review 단계로 전환');
                setCurrentStep('review');
                if (currentSession) {
                  // 상태는 기록용으로만 사용 (단계 전환에는 사용하지 않음)
                  useRegistrationStore.getState().updateSessionStatus('reviewing');
                }
              }}
            />
          )}
          {currentStep === 'review' && (
            <ReviewStep
              onNext={() => {
                // ReviewStep에서 완료 버튼 클릭 시
                console.log('[RegistrationModal] ReviewStep에서 완료 단계로 이동');
                setCurrentStep('complete');
                if (currentSession) {
                  useRegistrationStore.getState().updateSessionStatus('completed');
                }
              }}
            />
          )}
          {currentStep === 'complete' && (
            <CompleteStep onNext={() => {}} />
          )}
        </div>
      </div>
    </div>
  );
};

export default RegistrationModal;

