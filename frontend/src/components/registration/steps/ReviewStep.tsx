import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, Info, Check, Eye, FileText, Bot, ChevronRight } from 'lucide-react';
import { useRegistrationStore } from '../../../stores/useRegistrationStore';
import type { HighlightedIssue } from '../../../types';
import PdfViewer from '../../common/PdfViewer';
import type { IDCardOCRResult } from '../../../api/idCardApi';

interface ReviewStepProps {
  onNext?: () => void;
}

const ReviewStep: React.FC<ReviewStepProps> = () => {
  const { currentSession, markIssueAsReviewed, completeSession, agentResult } = useRegistrationStore();
  const [selectedIssue, setSelectedIssue] = useState<HighlightedIssue | null>(null);
  const [showAgentResult, setShowAgentResult] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [contractPeriodCropImage, setContractPeriodCropImage] = useState<string>('');
  const [loadingContractPeriodCrop, setLoadingContractPeriodCrop] = useState(false);
  const [checkedItemsCropImages, setCheckedItemsCropImages] = useState<Record<string, string>>({});
  const [loadingCheckedItemsCrops, setLoadingCheckedItemsCrops] = useState<Record<string, boolean>>({});
  const [checkedItemsDetailTexts, setCheckedItemsDetailTexts] = useState<Record<string, string>>({});
  const [agreementItemsCropImages, setAgreementItemsCropImages] = useState<Record<string, string>>({});
  const [loadingAgreementItemsCrops, setLoadingAgreementItemsCrops] = useState<Record<string, boolean>>({});
  
  // 신분증 OCR 결과 찾기
  const idCardOCRResult = currentSession?.ocrResults.find(
    (ocr) => ocr.idCardResult !== undefined
  )?.idCardResult;

  // IDCardResult를 IDCardOCRResult 형식으로 변환
  const idCardResult: IDCardOCRResult | null = idCardOCRResult ? {
    success: true,
    data: {
      name: idCardOCRResult.name,
      resident_number: idCardOCRResult.resident_number,
      address: idCardOCRResult.address,
      issue_date: idCardOCRResult.issue_date || '',
    },
    crops: idCardOCRResult.crops,
    masked_image: idCardOCRResult.masked_image,
    ocr_text: idCardOCRResult.ocr_text,
    ocr_lines: idCardOCRResult.ocr_lines,
  } : null;


  // 신분증 이슈 및 체크된 항목 필터링
  const allIssues = currentSession?.issues || [];
  const idCardIssues = allIssues.filter((issue) => issue.documentType === 'id_card');
  // 필수약관동의 항목 필터링 (신청서 카테고리)
  const agreementIssues = allIssues.filter(
    (issue) => issue.fieldName === '필수약관동의'
  );
  // 약정기간 항목 필터링 (서류 카테고리)
  const contractPeriodIssues = allIssues.filter(
    (issue) => issue.fieldName && issue.fieldName.includes('약정기간')
  );
  // 체크된 항목도 포함
  const checkedItemsIssues = allIssues.filter(
    (issue) => issue.fieldName === '체크된 항목'
  );
  // 신분증 이슈, 약정기간 항목, 필수약관동의, 체크된 항목을 합침 (순서: 약정기간 > 필수약관동의 > 체크된 항목)
  const displayIssues = [...idCardIssues, ...contractPeriodIssues, ...agreementIssues, ...checkedItemsIssues];
  const unreviewedIssues = displayIssues.filter((issue) => !issue.reviewed);
  const reviewedIssues = displayIssues.filter((issue) => issue.reviewed);
  const autoApprovedCount = 0; // 하드코딩 제거
  
  // 디버깅: 이슈 상태 확인
  React.useEffect(() => {
    console.log('[ReviewStep] 현재 세션 이슈 상태:', {
      totalIssues: allIssues.length,
      idCardIssues: idCardIssues.length,
      checkedItemsIssues: checkedItemsIssues.length,
      displayIssues: displayIssues.length,
      unreviewedIssues: unreviewedIssues.length,
      reviewedIssues: reviewedIssues.length,
      issues: allIssues.map(i => ({ id: i.id, type: i.documentType, fieldName: i.fieldName, reviewed: i.reviewed }))
    });
  }, [allIssues, idCardIssues, checkedItemsIssues, displayIssues, unreviewedIssues, reviewedIssues]);

  // 약정기간 항목의 crop 이미지 로드
  React.useEffect(() => {
    // 약정기간 항목이 선택되었는지 확인
    const isContractPeriod = selectedIssue?.fieldName && selectedIssue.fieldName.includes('약정기간');
    const contractPeriodItem = selectedIssue?.metadata?.contractPeriodItem as any;
    
    if (!isContractPeriod || !contractPeriodItem?.path) {
      // 약정기간 항목이 아니거나 경로가 없으면 이미지 초기화
      setContractPeriodCropImage('');
      setLoadingContractPeriodCrop(false);
      return;
    }
    
    // 이전 이미지 초기화
    setContractPeriodCropImage('');
    setLoadingContractPeriodCrop(true);
    
    // 두 좌표를 모두 가져와서 최소 bounding box 계산
    Promise.all([
      // structured_output.json에서 텍스트 좌표 가져오기
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/structured-output`)
        .then(res => res.ok ? res.json() : null),
      // bbox_labels.json에서 체크박스 좌표 가져오기
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/bbox-labels`)
        .then(res => res.ok ? res.json() : null)
    ])
      .then(([structuredData, bboxLabelsData]) => {
        if (!structuredData || !bboxLabelsData) {
          setLoadingContractPeriodCrop(false);
          return;
        }
        
        // 1. structured_output에서 텍스트 좌표 찾기
        const pathParts = contractPeriodItem.path.split('.');
        let current: any = structuredData;
        for (const part of pathParts) {
          if (part.includes('[') && part.includes(']')) {
            const [key, index] = part.split('[');
            const idx = parseInt(index.replace(']', ''));
            if (current[key] && Array.isArray(current[key]) && current[key][idx]) {
              current = current[key][idx];
            } else {
              setLoadingContractPeriodCrop(false);
              return;
            }
          } else if (current[part]) {
            current = current[part];
          } else {
            setLoadingContractPeriodCrop(false);
            return;
          }
        }
        
        const textPoints = current?.points; // [[x1, y1], [x2, y2]]
        if (!textPoints || !Array.isArray(textPoints) || textPoints.length < 2) {
          setLoadingContractPeriodCrop(false);
          return;
        }
        
        // 2. bbox_labels에서 체크박스 좌표 찾기 (경로나 텍스트로 매칭)
        const serviceName = selectedIssue?.metadata?.serviceName as string || '';
        const itemName = contractPeriodItem.name || contractPeriodItem.text || '';
        
        // 경로에서 서비스명과 약정기간 값 추출하여 bbox_labels에서 찾기
        // 예: "TV/약정기간/5년" 형식
        const searchText = serviceName && itemName 
          ? `${serviceName}/약정기간/${itemName}`
          : contractPeriodItem.path.includes('TV') 
            ? `TV/약정기간/${itemName}`
            : contractPeriodItem.path.includes('인터넷') || contractPeriodItem.path.includes('internet')
              ? `인터넷/약정기간/${itemName}`
              : contractPeriodItem.path.includes('일반전화') || contractPeriodItem.path.includes('landlinephone')
                ? `일반전화/약정기간/${itemName}`
                : contractPeriodItem.path.includes('인터넷전화') || contractPeriodItem.path.includes('internetcall')
                  ? `인터넷전화/약정기간/${itemName}`
                  : null;
        
        let checkboxBbox: number[] | null = null;
        if (searchText && bboxLabelsData.data?.labels) {
          const matchingLabel = bboxLabelsData.data.labels.find((label: any) => 
            label.text === searchText
          );
          if (matchingLabel?.bbox && Array.isArray(matchingLabel.bbox) && matchingLabel.bbox.length === 4) {
            checkboxBbox = matchingLabel.bbox; // [x1, y1, x2, y2]
          }
        }
        
        // 3. 두 좌표를 합쳐서 최소 bounding box 계산
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        // 텍스트 좌표 추가
        textPoints.forEach((point: number[]) => {
          if (point && point.length >= 2) {
            minX = Math.min(minX, point[0]);
            minY = Math.min(minY, point[1]);
            maxX = Math.max(maxX, point[0]);
            maxY = Math.max(maxY, point[1]);
          }
        });
        
        // 체크박스 좌표 추가
        if (checkboxBbox) {
          const [cbx1, cby1, cbx2, cby2] = checkboxBbox;
          minX = Math.min(minX, cbx1, cbx2);
          minY = Math.min(minY, cby1, cby2);
          maxX = Math.max(maxX, cbx1, cbx2);
          maxY = Math.max(maxY, cby1, cby2);
        }
        
        // 유효한 좌표가 있는지 확인
        if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
          setLoadingContractPeriodCrop(false);
          return;
        }
        
        // 최소 bounding box 생성: [[minX, minY], [maxX, maxY]]
        const combinedBbox = [[minX, minY], [maxX, maxY]];
        
        // 4. crop API 호출
        fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/crop-form-field`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bbox: combinedBbox })
        })
          .then(res => res.ok ? res.json() : null)
          .then(cropData => {
            if (cropData?.crop_image) {
              setContractPeriodCropImage(cropData.crop_image);
            }
            setLoadingContractPeriodCrop(false);
          })
          .catch(err => {
            console.error('[ReviewStep] crop 이미지 로드 실패:', err);
            setLoadingContractPeriodCrop(false);
          });
      })
      .catch(err => {
        console.error('[ReviewStep] 데이터 로드 실패:', err);
        setLoadingContractPeriodCrop(false);
      });
  }, [selectedIssue?.id, selectedIssue?.fieldName]); // selectedIssue가 변경될 때만 실행

  // 필수약관동의 항목의 crop 이미지 로드
  React.useEffect(() => {
    // 필수약관동의 항목이 선택되었는지 확인
    const isAgreementItems = selectedIssue?.fieldName === '필수약관동의';
    const agreementItems = isAgreementItems 
      ? (selectedIssue.metadata?.agreementItems || []) as Array<{name: string, text: string, path: string, method: string}>
      : [];
    
    if (!isAgreementItems || agreementItems.length === 0) {
      // 필수약관동의 항목이 아니면 이미지 초기화
      setAgreementItemsCropImages({});
      setLoadingAgreementItemsCrops({});
      return;
    }
    
    // structured_output과 bbox_labels를 한 번만 가져오기
    Promise.all([
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/structured-output`)
        .then(res => res.ok ? res.json() : null),
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/bbox-labels`)
        .then(res => res.ok ? res.json() : null)
    ])
      .then(([structuredData, bboxLabelsData]) => {
        if (!structuredData || !bboxLabelsData) return;
        
        // 각 항목에 대해 crop 이미지 가져오기
        agreementItems.forEach((item, index) => {
          const itemKey = `${item.path}-${index}`;
          
          if (agreementItemsCropImages[itemKey] || loadingAgreementItemsCrops[itemKey]) {
            return; // 이미 로드 중이거나 로드 완료
          }
          
          setLoadingAgreementItemsCrops(prev => ({ ...prev, [itemKey]: true }));
          
          // 1. structured_output에서 텍스트 좌표 찾기
          const pathParts = item.path.split('.');
          let current: any = structuredData;
          let found = true;
          
          for (const part of pathParts) {
            if (part.includes('[') && part.includes(']')) {
              const [key, indexStr] = part.split('[');
              const idx = parseInt(indexStr.replace(']', ''));
              if (current[key] && Array.isArray(current[key]) && current[key][idx]) {
                current = current[key][idx];
              } else {
                found = false;
                break;
              }
            } else if (current[part]) {
              current = current[part];
            } else {
              found = false;
              break;
            }
          }
          
          if (!found || !current?.points) {
            setLoadingAgreementItemsCrops(prev => {
              const newState = { ...prev };
              delete newState[itemKey];
              return newState;
            });
            return;
          }
          
          const textPoints = current.points; // [[x1, y1], [x2, y2]]
          
          // 2. bbox_labels에서 체크박스 좌표 찾기
          let checkboxBbox: number[] | null = null;
          if (bboxLabelsData.data?.labels) {
            // 경로나 텍스트로 매칭 시도
            const searchTexts = [
              item.text,
              item.name,
              item.path.split('.').pop()?.replace(/\[.*?\]/g, ''),
            ].filter(Boolean);
            
            const matchingLabel = bboxLabelsData.data.labels.find((label: any) => 
              searchTexts.some(searchText => 
                label.text && label.text.includes(searchText as string)
              )
            );
            
            if (matchingLabel?.bbox && Array.isArray(matchingLabel.bbox) && matchingLabel.bbox.length === 4) {
              checkboxBbox = matchingLabel.bbox; // [x1, y1, x2, y2]
            }
          }
          
          // 3. 최소 bounding box 계산
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          
          // 텍스트 좌표 추가
          textPoints.forEach((point: number[]) => {
            if (point && point.length >= 2) {
              minX = Math.min(minX, point[0]);
              minY = Math.min(minY, point[1]);
              maxX = Math.max(maxX, point[0]);
              maxY = Math.max(maxY, point[1]);
            }
          });
          
          // 체크박스 좌표 추가
          if (checkboxBbox) {
            const [cbx1, cby1, cbx2, cby2] = checkboxBbox;
            minX = Math.min(minX, cbx1, cbx2);
            minY = Math.min(minY, cby1, cby2);
            maxX = Math.max(maxX, cbx1, cbx2);
            maxY = Math.max(maxY, cby1, cby2);
          }
          
          if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
            setLoadingAgreementItemsCrops(prev => {
              const newState = { ...prev };
              delete newState[itemKey];
              return newState;
            });
            return;
          }
          
          // 최소 bounding box 생성
          const combinedBbox = [[minX, minY], [maxX, maxY]];
          
          // 4. crop API 호출
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/crop-form-field`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bbox: combinedBbox })
          })
            .then(res => res.ok ? res.json() : null)
            .then(cropData => {
              if (cropData?.crop_image) {
                setAgreementItemsCropImages(prev => ({
                  ...prev,
                  [itemKey]: cropData.crop_image
                }));
              }
              setLoadingAgreementItemsCrops(prev => {
                const newState = { ...prev };
                delete newState[itemKey];
                return newState;
              });
            })
            .catch(err => {
              console.error(`[ReviewStep] 필수약관동의 항목 ${index} crop 이미지 로드 실패:`, err);
              setLoadingAgreementItemsCrops(prev => {
                const newState = { ...prev };
                delete newState[itemKey];
                return newState;
              });
            });
        });
      })
      .catch(err => {
        console.error('[ReviewStep] 데이터 로드 실패:', err);
      });
  }, [selectedIssue?.id, selectedIssue?.fieldName]); // selectedIssue가 변경될 때만 실행

  // 체크된 항목의 crop 이미지 로드
  React.useEffect(() => {
    // 체크된 항목이 선택되었는지 확인
    const isCheckedItems = selectedIssue?.fieldName === '체크된 항목';
    const checkedItems = isCheckedItems 
      ? (selectedIssue.metadata?.checkedItems || []) as Array<{name: string, text: string, path: string, method: string}>
      : [];
    
    if (!isCheckedItems || checkedItems.length === 0) {
      // 체크된 항목이 아니면 이미지 초기화
      setCheckedItemsCropImages({});
      setLoadingCheckedItemsCrops({});
      return;
    }
    
    // structured_output과 bbox_labels를 한 번만 가져오기
    Promise.all([
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/structured-output`)
        .then(res => res.ok ? res.json() : null),
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/bbox-labels`)
        .then(res => res.ok ? res.json() : null)
    ])
      .then(([structuredData, bboxLabelsData]) => {
        if (!structuredData || !bboxLabelsData) return;
        
        // 각 항목에 대해 crop 이미지 가져오기
        checkedItems.forEach((item, index) => {
          const itemKey = `${item.path}-${index}`;
          
          if (checkedItemsCropImages[itemKey] || loadingCheckedItemsCrops[itemKey]) {
            return; // 이미 로드 중이거나 로드 완료
          }
          
          setLoadingCheckedItemsCrops(prev => ({ ...prev, [itemKey]: true }));
          
          // 1. structured_output에서 텍스트 좌표 찾기
          const pathParts = item.path.split('.');
          let current: any = structuredData;
          let found = true;
          
          for (const part of pathParts) {
            if (part.includes('[') && part.includes(']')) {
              const [key, indexStr] = part.split('[');
              const idx = parseInt(indexStr.replace(']', ''));
              if (current[key] && Array.isArray(current[key]) && current[key][idx]) {
                current = current[key][idx];
              } else {
                found = false;
                break;
              }
            } else if (current[part]) {
              current = current[part];
            } else {
              found = false;
              break;
            }
          }
          
          if (!found || !current?.points) {
            setLoadingCheckedItemsCrops(prev => {
              const newState = { ...prev };
              delete newState[itemKey];
              return newState;
            });
            return;
          }
          
          const textPoints = current.points; // [[x1, y1], [x2, y2]]
          
          // 2. bbox_labels에서 체크박스 좌표 찾기
          let checkboxBbox: number[] | null = null;
          if (bboxLabelsData.data?.labels) {
            // 경로나 텍스트로 매칭 시도
            const searchTexts = [
              item.text,
              item.name,
              item.path.split('.').pop()?.replace(/\[.*?\]/g, ''),
            ].filter(Boolean);
            
            const matchingLabel = bboxLabelsData.data.labels.find((label: any) => 
              searchTexts.some(searchText => 
                label.text && label.text.includes(searchText as string)
              )
            );
            
            if (matchingLabel?.bbox && Array.isArray(matchingLabel.bbox) && matchingLabel.bbox.length === 4) {
              checkboxBbox = matchingLabel.bbox; // [x1, y1, x2, y2]
            }
          }
          
          // 3. 최소 bounding box 계산
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          
          // 텍스트 좌표 추가
          textPoints.forEach((point: number[]) => {
            if (point && point.length >= 2) {
              minX = Math.min(minX, point[0]);
              minY = Math.min(minY, point[1]);
              maxX = Math.max(maxX, point[0]);
              maxY = Math.max(maxY, point[1]);
            }
          });
          
          // 체크박스 좌표 추가
          if (checkboxBbox) {
            const [cbx1, cby1, cbx2, cby2] = checkboxBbox;
            minX = Math.min(minX, cbx1, cbx2);
            minY = Math.min(minY, cby1, cby2);
            maxX = Math.max(maxX, cbx1, cbx2);
            maxY = Math.max(maxY, cby1, cby2);
          }
          
          if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
            setLoadingCheckedItemsCrops(prev => {
              const newState = { ...prev };
              delete newState[itemKey];
              return newState;
            });
            return;
          }
          
          // 최소 bounding box 생성
          const combinedBbox = [[minX, minY], [maxX, maxY]];
          
          // 4. crop API 호출
          fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/crop-form-field`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bbox: combinedBbox })
          })
            .then(res => res.ok ? res.json() : null)
            .then(cropData => {
              if (cropData?.crop_image) {
                setCheckedItemsCropImages(prev => ({
                  ...prev,
                  [itemKey]: cropData.crop_image
                }));
              }
              setLoadingCheckedItemsCrops(prev => {
                const newState = { ...prev };
                delete newState[itemKey];
                return newState;
              });
            })
            .catch(err => {
              console.error(`[ReviewStep] 항목 ${index} crop 이미지 로드 실패:`, err);
              setLoadingCheckedItemsCrops(prev => {
                const newState = { ...prev };
                delete newState[itemKey];
                return newState;
              });
            });
        });
      })
      .catch(err => {
        console.error('[ReviewStep] 데이터 로드 실패:', err);
      });
  }, [selectedIssue?.id, selectedIssue?.fieldName]); // selectedIssue가 변경될 때만 실행

  const getSeverityIcon = (severity: HighlightedIssue['severity']) => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="text-red-500" size={20} />;
      case 'warning':
        return <AlertTriangle className="text-yellow-500" size={20} />;
      case 'info':
        return <Info className="text-blue-500" size={20} />;
    }
  };

  const getSeverityBadge = (severity: HighlightedIssue['severity']) => {
    const colors = {
      error: 'bg-red-100 text-red-700',
      warning: 'bg-yellow-100 text-yellow-700',
      info: 'bg-blue-100 text-blue-700',
    };
    
    const labels = {
      error: '오류',
      warning: '주의',
      info: '확인',
    };

    return (
      <span className={`px-2 py-1 text-xs rounded ${colors[severity]}`}>
        {labels[severity]}
      </span>
    );
  };

  const getDocumentTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      application: '신청서',
      proxy: '위임장',
      id_card: '신분증',
      other: '기타',
    };
    return labels[type] || type;
  };

  const handleMarkAsReviewed = (issueId: string) => {
    markIssueAsReviewed(issueId, reviewNote || undefined);
    setReviewNote('');
    
    // 다음 미검토 항목으로 자동 이동
    const nextUnreviewedIssue = unreviewedIssues.find((issue) => issue.id !== issueId);
    setSelectedIssue(nextUnreviewedIssue || null);
  };

  const handleApproveAll = async () => {
    if (confirm('모든 항목을 확인하고 승인하시겠습니까?')) {
      try {
        // 신분증 OCR 결과에서 고객 정보 추출
        const idCardData = idCardOCRResult;
        if (!idCardData) {
          throw new Error('신분증 정보가 없습니다.');
        }

        // 처리 시작 시간 계산 (세션 생성 시간 기준)
        const sessionStartTime = currentSession?.createdAt || new Date();
        const processingTime = Math.floor((Date.now() - sessionStartTime.getTime()) / 1000); // 초 단위

        // 고객 정보 생성
        const customerData = {
          id: 'K' + Date.now().toString().slice(-8),
          name: idCardData.name || '',
          phone: '', // structured_output에서 추출 필요
          address: idCardData.address || '',
          registeredAt: new Date(),
          status: 'active' as const,
        };

        // structured_output.json에서 계약 정보 추출 시도
        let contractData: any = {
          customer_name: customerData.name,
          application_date: new Date().toISOString().split('T')[0],
        };

        try {
          // structured_output.json 파일 읽기 시도 (서버에서 제공하는 경우)
          const structuredResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/structured-output`);
          if (structuredResponse.ok) {
            const structuredData = await structuredResponse.json();
            
            // 인터넷 계약 정보 추출
            if (structuredData.internet) {
              contractData = {
                ...contractData,
                plan_name: structuredData.internet.options?.find((opt: any) => opt.name === '요금제')?.value || '',
                speed_category: structuredData.internet.options?.find((opt: any) => opt.name === '속도')?.value || '',
                contract_period: structuredData.internet.options?.find((opt: any) => opt.name === '약정기간')?.value || '',
                status: '활성',
                type: 'internet',
              };
            }
            // TV 계약 정보 추출
            else if (structuredData.tv) {
              contractData = {
                ...contractData,
                service_type: structuredData.tv.options?.find((opt: any) => opt.name === '서비스유형')?.value || '',
                settop_type: structuredData.tv.options?.find((opt: any) => opt.name === '셋탑박스')?.value || '',
                contract_period: structuredData.tv.options?.find((opt: any) => opt.name === '약정기간')?.value || '',
                status: '활성',
                type: 'tv',
              };
            }
            // 전화 계약 정보 추출
            else if (structuredData.phone) {
              contractData = {
                ...contractData,
                phone_type: structuredData.phone.options?.find((opt: any) => opt.name === '전화구분')?.value || '',
                plan_name: structuredData.phone.options?.find((opt: any) => opt.name === '요금제')?.value || '',
                desired_number: structuredData.phone.options?.find((opt: any) => opt.name === '희망번호')?.value || '',
                status: '활성',
                type: 'phone',
              };
            }
            // 단말 정보 추출
            else if (structuredData.device) {
              contractData = {
                ...contractData,
                device_model: structuredData.device.options?.find((opt: any) => opt.name === '기기명')?.value || '',
                price: parseInt(structuredData.device.options?.find((opt: any) => opt.name === '가격')?.value || '0'),
                purchase_type: structuredData.device.options?.find((opt: any) => opt.name === '구매방식')?.value || '',
                status: '활성',
                type: 'device',
              };
            }
          }
        } catch (error) {
          console.warn('structured_output.json 읽기 실패, 기본 계약 정보만 저장:', error);
        }

        // Spring(MySQL)에 고객 동기화 (VITE_SPRING_API_URL 설정 시)
        const { isSpringConfigured, postCustomerToSpring } = await import('../../../api/springApi');
        if (isSpringConfigured()) {
          await postCustomerToSpring(customerData);
        }

        // 로컬 스토리지에 데이터 저장
        // 1. 고객 데이터 저장
        const existingCustomers = JSON.parse(localStorage.getItem('customers') || '[]');
        existingCustomers.push(customerData);
        localStorage.setItem('customers', JSON.stringify(existingCustomers));

        // 2. 계약 데이터 저장
        const existingContracts = JSON.parse(localStorage.getItem('contracts') || '[]');
        existingContracts.push(contractData);
        localStorage.setItem('contracts', JSON.stringify(existingContracts));

        // 3. 대시보드 통계 업데이트
        const today = new Date().toISOString().split('T')[0];
        const dashboardStats = JSON.parse(localStorage.getItem('dashboardStats') || '{}');
        
        if (!dashboardStats[today]) {
          dashboardStats[today] = {
            total: 0,
            approved: 0,
            rejected: 0,
            pending: 0,
            processingTimes: [],
          };
        }
        
        dashboardStats[today].total += 1;
        dashboardStats[today].approved += 1;
        dashboardStats[today].processingTimes.push(processingTime);
        
        // 주간 처리 추이 업데이트
        const weekStats = JSON.parse(localStorage.getItem('weekStats') || '[]');
        const dayOfWeek = new Date().getDay(); // 0=일요일, 1=월요일, ..., 6=토요일
        // 차트 순서: ['월', '화', '수', '목', '금', '토', '일'] (인덱스 0=월요일, 6=일요일)
        // getDay() 순서를 차트 순서로 변환: 일요일(0) -> 6, 월요일(1) -> 0, 화요일(2) -> 1, ...
        const chartIndex = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        
        if (weekStats.length < 7) {
          weekStats.push(...Array(7 - weekStats.length).fill(0));
        }
        weekStats[chartIndex] = (weekStats[chartIndex] || 0) + 1;
        
        localStorage.setItem('dashboardStats', JSON.stringify(dashboardStats));
        localStorage.setItem('weekStats', JSON.stringify(weekStats));

        // 모든 미검토 항목 자동 승인 처리
        unreviewedIssues.forEach((issue) => {
          markIssueAsReviewed(issue.id, '자동 승인');
        });
        
        completeSession();
      } catch (error) {
        alert('승인 처리 중 오류가 발생했습니다: ' + error);
        console.error(error);
      }
    }
  };

  const getProgressPercentage = () => {
    const total = currentSession?.issues.length || 0;
    const reviewed = reviewedIssues.length;
    return total > 0 ? Math.round((reviewed / total) * 100) : 0;
  };

  return (
    <div className="flex gap-6 h-[600px]">
      {/* Left Panel: Issues List */}
      <div className="w-96 flex flex-col border border-gray-200 rounded-lg bg-white">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-gray-900">검토 필요 항목</h3>
            <span className="px-2 py-1 bg-red-100 text-red-700 text-sm font-medium rounded">
              {unreviewedIssues.length}건
            </span>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
              <span>검토 진행률</span>
              <span>{getProgressPercentage()}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${getProgressPercentage()}%` }}
              />
            </div>
          </div>
        </div>

        {/* Issues List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Agent 분석 결과 섹션 - 항상 표시 */}
          <div
            onClick={() => {
              if (agentResult && agentResult.success && agentResult.final_report) {
                setShowAgentResult(true);
                setSelectedIssue(null);
              }
            }}
            className={`p-3 border rounded-lg transition-all mb-3 ${
              agentResult && agentResult.success && agentResult.final_report
                ? 'cursor-pointer border-purple-200 hover:border-purple-300 hover:bg-purple-50'
                : 'cursor-default border-gray-200 bg-gray-50'
            } ${
              showAgentResult
                ? 'border-purple-500 bg-purple-50'
                : ''
            }`}
          >
            <div className="flex items-center gap-2">
              <Bot className="text-purple-600" size={20} />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm text-gray-900">Agent 분석 결과</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    agentResult && agentResult.success && agentResult.final_report
                      ? 'bg-green-100 text-green-700'
                      : agentResult && !agentResult.success
                      ? 'bg-red-100 text-red-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {agentResult && agentResult.success && agentResult.final_report
                      ? '완료'
                      : agentResult && !agentResult.success
                      ? '오류'
                      : '진행중'}
                  </span>
                </div>
              </div>
              {agentResult && agentResult.success && agentResult.final_report && (
                <ChevronRight className="text-gray-400" size={16} />
              )}
            </div>
          </div>
          
          {/* Unreviewed Issues */}
          {unreviewedIssues.map((issue) => (
            <div
              key={issue.id}
              onClick={() => {
                setSelectedIssue(issue);
                setShowAgentResult(false);
              }}
              className={`p-3 border rounded-lg cursor-pointer transition-all ${
                selectedIssue?.id === issue.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-2 mb-2">
                {getSeverityIcon(issue.severity)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm text-gray-900">
                      {getDocumentTypeLabel(issue.documentType)}
                    </span>
                    {getSeverityBadge(issue.severity)}
                  </div>
                  <h4 className="font-semibold text-gray-900 text-sm">
                    {issue.fieldName}
                  </h4>
                  <p className="text-xs text-gray-600 mt-1">
                    {issue.description}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {/* Reviewed Issues */}
          {reviewedIssues.length > 0 && (
            <>
              <div className="pt-4 pb-2 border-t border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <Check className="text-green-500" size={16} />
                  확인 완료 ({reviewedIssues.length})
                </h4>
              </div>
              
              {reviewedIssues.map((issue) => (
                <div
                  key={issue.id}
                  className="p-3 bg-gray-50 border border-gray-200 rounded-lg opacity-60"
                >
                  <div className="flex items-center gap-2">
                    <Check className="text-green-500 flex-shrink-0" size={16} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-gray-700 line-through">
                        {issue.fieldName}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* Auto Approved - 주석처리 */}
          {/*
          <div className="pt-4 pb-2">
            <button className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-2">
              <Check className="text-green-500" size={16} />
              자동 승인 ({autoApprovedCount}개 항목)
              <span className="text-xs">▼</span>
            </button>
          </div>
          */}
        </div>

        {/* Action Buttons */}
        <div className="p-4 border-t border-gray-200 space-y-2">
          <button
            onClick={handleApproveAll}
            disabled={unreviewedIssues.length > 0}
            className="w-full py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            승인
          </button>
          <button className="w-full py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
            반려
          </button>
        </div>
      </div>

      {/* Right Panel: Document Viewer */}
      <div className="flex-1 border border-gray-200 rounded-lg bg-white flex flex-col">
        {showAgentResult && agentResult && agentResult.success && agentResult.final_report ? (
          <>
            {/* Agent Result Header */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Bot className="text-purple-600" size={24} />
                  Agent 분석 결과
                </h3>
                <button
                  onClick={() => {
                    setShowAgentResult(false);
                    setSelectedIssue(null);
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  닫기
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 text-xs rounded ${
                  agentResult.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {agentResult.success ? '✅ 분석 완료' : '❌ 분석 실패'}
                </span>
              </div>
            </div>

            {/* Agent Result Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
              {agentResult.success ? (
                <>
                  {/* 요약 */}
                  {agentResult.summary && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <FileText size={18} />
                        📊 분석 요약
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-blue-50 border border-blue-200 rounded p-3">
                          <div className="text-xs text-blue-600 mb-1">전체 필드</div>
                          <div className="text-2xl font-bold text-blue-900">
                            {agentResult.summary.total_fields || 0}개
                          </div>
                        </div>
                        <div className="bg-green-50 border border-green-200 rounded p-3">
                          <div className="text-xs text-green-600 mb-1">유효</div>
                          <div className="text-2xl font-bold text-green-900">
                            {agentResult.summary.valid || 0}개
                          </div>
                        </div>
                        <div className="bg-red-50 border border-red-200 rounded p-3">
                          <div className="text-xs text-red-600 mb-1">누락</div>
                          <div className="text-2xl font-bold text-red-900">
                            {agentResult.summary.missing || 0}개
                          </div>
                        </div>
                        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                          <div className="text-xs text-yellow-600 mb-1">경고</div>
                          <div className="text-2xl font-bold text-yellow-900">
                            {agentResult.summary.warnings || 0}개
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 분석 리포트 */}
                  {agentResult.final_report && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <FileText size={18} />
                        📋 분석 리포트
                      </h4>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded border border-gray-200 max-h-96 overflow-y-auto">
                        {agentResult.final_report}
                      </div>
                    </div>
                  )}

                  {/* 심사 권고사항 */}
                  {agentResult.recommendations_report && (
                    <div className="bg-white border border-orange-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <AlertTriangle size={18} className="text-orange-600" />
                        ⚠️ 심사 권고사항
                      </h4>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap bg-orange-50 p-4 rounded border border-orange-200 max-h-96 overflow-y-auto">
                        {agentResult.recommendations_report}
                      </div>
                    </div>
                  )}

                  {/* 고객 분석 리포트 */}
                  {agentResult.customer_analysis_report && (
                    <div className="bg-white border border-purple-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <Bot size={18} className="text-purple-600" />
                        👤 고객 유형 분석 리포트
                      </h4>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap bg-purple-50 p-4 rounded border border-purple-200 max-h-96 overflow-y-auto">
                        {agentResult.customer_analysis_report}
                      </div>
                    </div>
                  )}
                  
                  {/* 고객유형 한줄 요약 - 별도 섹션 */}
                  {agentResult.customer_summary && (
                    <div className="bg-white border border-blue-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <span className="text-lg">📝</span>
                        고객유형 한줄 요약
                      </h4>
                      <div className="text-sm text-gray-900 font-medium bg-blue-50 p-4 rounded border border-blue-200">
                        {agentResult.customer_summary}
                      </div>
                    </div>
                  )}

                  {/* Agent 작업 로그 */}
                  {agentResult.agent_logs && agentResult.agent_logs.length > 0 && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <FileText size={18} />
                        📝 Agent 작업 로그
                      </h4>
                      <div className="space-y-1 max-h-60 overflow-y-auto bg-gray-50 p-3 rounded border border-gray-200">
                        {agentResult.agent_logs.map((log: any, idx: number) => (
                          <div key={idx} className="text-xs text-gray-600 font-mono flex items-start gap-2">
                            <span className="text-gray-400 flex-shrink-0">
                              [{log.timestamp || ''}]
                            </span>
                            <span className={`flex-1 ${
                              log.level === 'error' ? 'text-red-600' :
                              log.level === 'success' ? 'text-green-600' :
                              log.level === 'warning' ? 'text-yellow-600' :
                              'text-gray-600'
                            }`}>
                              {log.message || ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h4 className="font-semibold text-red-900 mb-2">❌ Agent 실행 실패</h4>
                  <p className="text-sm text-red-800">{agentResult.error || '알 수 없는 오류가 발생했습니다.'}</p>
                </div>
              )}
            </div>
          </>
        ) : selectedIssue ? (
          <>
            {/* Viewer Header */}
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900">
                  {getDocumentTypeLabel(selectedIssue.documentType)} - {selectedIssue.fieldName}
                </h3>
                <button className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  <Eye size={16} />
                  원본 보기
                </button>
              </div>
              
              <div className="flex items-center gap-2">
                {getSeverityIcon(selectedIssue.severity)}
                <span className="text-sm text-gray-600">{selectedIssue.title}</span>
              </div>
            </div>

            {/* Document Preview */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* PDF Viewer */}
              {(() => {
                const document = currentSession?.documents.find(
                  (doc) => doc.id === selectedIssue.documentId
                );
                
                // 신분증 OCR 결과 찾기
                const idCardOCR = currentSession?.ocrResults.find(
                  (ocr) => ocr.documentId === selectedIssue.documentId && ocr.idCardResult
                )?.idCardResult;
                
                // 신분증 필드인 경우 크롭 이미지와 수정 가능한 필드 표시
                if (selectedIssue.documentType === 'id_card') {
                  // "신분증 전체" 항목인 경우
                  if (selectedIssue.fieldName === '신분증 전체') {
                    return (
                      <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                        <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-sm space-y-4">
                          {/* 필드명 */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              {selectedIssue.fieldName}
                            </label>
                            
                            {/* 마스킹된 전체 이미지 */}
                            {selectedIssue.cropImage && (
                              <div className="mb-4">
                                <p className="text-xs text-gray-500 mb-2">추출된 영역</p>
                                <img
                                  src={`data:image/jpeg;base64,${selectedIssue.cropImage}`}
                                  alt="신분증 전체 (마스킹)"
                                  className="w-full max-w-2xl mx-auto object-contain border-2 border-blue-200 rounded-lg bg-gray-50 p-2"
                                />
                              </div>
                            )}
                            
                            {/* OCR 텍스트 전체 (수정 가능) */}
                            {idCardOCR && (
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">
                                  OCR 추출 텍스트 전체 (수정 가능)
                                </label>
                                <textarea
                                  value={idCardOCR.ocr_text || ''}
                                  onChange={(e) => {
                                    // OCR 텍스트 업데이트
                                    const { currentSession: updatedSession } = useRegistrationStore.getState();
                                    if (updatedSession) {
                                      useRegistrationStore.setState({
                                        currentSession: {
                                          ...updatedSession,
                                          ocrResults: updatedSession.ocrResults.map((ocr) =>
                                            ocr.documentId === selectedIssue.documentId && ocr.idCardResult
                                              ? {
                                                  ...ocr,
                                                  idCardResult: {
                                                    ...ocr.idCardResult,
                                                    ocr_text: e.target.value,
                                                  },
                                                }
                                              : ocr
                                          ),
                                        },
                                      });
                                    }
                                  }}
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                  rows={6}
                                  placeholder="OCR 텍스트를 입력하세요"
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  }
                  
                  // 개별 필드 (성명, 주민번호, 주소)인 경우
                  return (
                    <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                      <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-sm space-y-4">
                        {/* 필드명 */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            {selectedIssue.fieldName}
                          </label>
                          
                          {/* 크롭 이미지 */}
                          {selectedIssue.cropImage && (
                            <div className="mb-4">
                              <p className="text-xs text-gray-500 mb-2">추출된 영역</p>
                              <img
                                src={`data:image/jpeg;base64,${selectedIssue.cropImage}`}
                                alt={selectedIssue.fieldName}
                                className="w-full max-w-md h-32 object-contain border-2 border-blue-200 rounded-lg bg-gray-50 p-2"
                              />
                            </div>
                          )}
                          
                          {/* 수정 가능한 필드 */}
                          <div className="mb-4">
                            <label className="block text-xs text-gray-600 mb-1">
                              추출된 값 (수정 가능)
                            </label>
                            <input
                              type="text"
                              value={selectedIssue.correctedValue as string || selectedIssue.description || ''}
                              onChange={(e) => {
                                // 이슈 값 업데이트
                                const updatedIssues = currentSession?.issues.map((issue) =>
                                  issue.id === selectedIssue.id
                                    ? { ...issue, correctedValue: e.target.value, description: e.target.value }
                                    : issue
                                );
                                if (currentSession && updatedIssues) {
                                  useRegistrationStore.setState({
                                    currentSession: {
                                      ...currentSession,
                                      issues: updatedIssues,
                                    },
                                  });
                                  setSelectedIssue({ ...selectedIssue, correctedValue: e.target.value, description: e.target.value });
                                }
                              }}
                              className="w-full px-3 py-2 border border-blue-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                              placeholder="값을 입력하세요"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }
                
                // 신분증이 아닌 다른 문서 타입은 주석처리
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
                
                // 필수약관동의 항목인 경우
                if (selectedIssue.fieldName === '필수약관동의') {
                  const agreementItems = (selectedIssue.metadata?.agreementItems || []) as Array<{name: string, text: string, path: string, method: string, bbox_text?: string}>;
                  
                  // '확인' 항목들을 정렬 (원본 순서 유지)
                  const sortedAgreementItems = agreementItems.map((item, originalIndex) => ({
                    ...item,
                    originalIndex,
                    // '확인' 항목이고 bbox_text가 "확인/"으로 시작하면 세부 텍스트 추출
                    detailText: (item.name === '확인' && item.bbox_text && item.bbox_text.startsWith('확인/'))
                      ? item.bbox_text.replace(/^확인\//, '')
                      : undefined
                  }));
                  
                  return (
                    <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                      <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-sm space-y-4">
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2">
                            {selectedIssue.fieldName}
                          </label>
                          <div className="p-3 bg-blue-50 border border-blue-300 rounded mb-4">
                            <p className="text-sm text-gray-900 mb-2">
                              총 {agreementItems.length}개의 필수약관동의 항목이 체크되었습니다.
                            </p>
                          </div>
                          
                          {/* 필수약관동의 항목 목록 */}
                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {sortedAgreementItems.map((itemWithIndex, displayIndex) => {
                              const item = { name: itemWithIndex.name, text: itemWithIndex.text, path: itemWithIndex.path, method: itemWithIndex.method };
                              const originalIndex = itemWithIndex.originalIndex;
                              const detailText = itemWithIndex.detailText;
                              const itemKey = `${item.path}-${originalIndex}`;
                              const cropImage = agreementItemsCropImages[itemKey];
                              const isLoading = loadingAgreementItemsCrops[itemKey];
                              
                              return (
                                <div
                                  key={`${item.path}-${originalIndex}`}
                                  className="p-3 bg-gray-50 border border-gray-200 rounded flex items-start gap-3"
                                >
                                  {/* 왼쪽: 항목 정보 */}
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-gray-500 font-semibold">#{displayIndex + 1}</span>
                                      <span className={`px-2 py-0.5 text-xs rounded ${
                                        item.method === 'ai_text' ? 'bg-green-100 text-green-700' :
                                        item.method === 'text_similarity' ? 'bg-yellow-100 text-yellow-700' :
                                        'bg-gray-100 text-gray-700'
                                      }`}>
                                        {item.method === 'ai_text' ? 'AI 추론' :
                                         item.method === 'text_similarity' ? '텍스트 유사도' :
                                         item.method}
                                      </span>
                                    </div>
                                    <div className="text-sm text-gray-700 space-y-1">
                                      {item.name && (
                                        <div>
                                          <span className="font-medium">이름:</span> {item.name}
                                        </div>
                                      )}
                                      {item.text && (
                                        <div>
                                          <span className="font-medium">텍스트:</span> {item.text}
                                        </div>
                                      )}
                                      {item.path && (
                                        <div className="text-xs text-gray-500 font-mono">
                                          경로: {item.path}
                                        </div>
                                      )}
                                      {/* '확인' 항목인 경우 세부내용 표시 */}
                                      {item.name === '확인' && detailText && (
                                        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
                                          <span className="font-medium text-blue-700">세부내용:</span>{' '}
                                          <span className="text-blue-900">{detailText}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  
                                  {/* 오른쪽: Crop 이미지 */}
                                  <div className="flex-shrink-0">
                                    {isLoading ? (
                                      <div className="w-24 h-16 flex items-center justify-center border border-gray-200 rounded bg-gray-50">
                                        <span className="text-xs text-gray-400">로딩...</span>
                                      </div>
                                    ) : cropImage ? (
                                      <img
                                        src={`data:image/jpeg;base64,${cropImage}`}
                                        alt={`${item.name || item.text || '항목'} crop`}
                                        className="w-24 h-16 object-contain border border-gray-200 rounded bg-gray-50 p-1"
                                      />
                                    ) : (
                                      <div className="w-24 h-16 flex items-center justify-center border border-gray-200 rounded bg-gray-50">
                                        <span className="text-xs text-gray-400">이미지 없음</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }
                
                // 체크된 항목인 경우
                if (selectedIssue.fieldName === '체크된 항목') {
                  const checkedItems = (selectedIssue.metadata?.checkedItems || []) as Array<{name: string, text: string, path: string, method: string, bbox_text?: string}>;
                  
                  // '확인' 항목을 맨 아래로 정렬 (원본 인덱스 유지)
                  const sortedCheckedItems = checkedItems
                    .map((item, originalIndex) => ({ 
                      ...item, 
                      originalIndex,
                      // '확인' 항목이고 bbox_text가 "확인/"으로 시작하면 세부 텍스트 추출
                      detailText: (item.name === '확인' && item.bbox_text && item.bbox_text.startsWith('확인/'))
                        ? item.bbox_text.replace(/^확인\//, '')
                        : undefined
                    }))
                    .sort((a, b) => {
                      const aIsConfirm = a.name === '확인';
                      const bIsConfirm = b.name === '확인';
                      
                      // '확인' 항목이 아닌 것들을 먼저, '확인' 항목들을 나중에
                      if (aIsConfirm && !bIsConfirm) return 1;
                      if (!aIsConfirm && bIsConfirm) return -1;
                      // 둘 다 '확인'이거나 둘 다 아닌 경우 원본 순서 유지
                      return a.originalIndex - b.originalIndex;
                    });
                  
                  return (
                    <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                      <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-sm space-y-4">
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2">
                            {selectedIssue.fieldName}
                          </label>
                          <div className="p-3 bg-blue-50 border border-blue-300 rounded mb-4">
                            <p className="text-sm text-gray-900 mb-2">
                              총 {checkedItems.length}개의 항목이 체크되었습니다.
                            </p>
                          </div>
                          
                          {/* 체크된 항목 목록 */}
                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {sortedCheckedItems.map((itemWithIndex, displayIndex) => {
                              const item = { name: itemWithIndex.name, text: itemWithIndex.text, path: itemWithIndex.path, method: itemWithIndex.method };
                              const originalIndex = itemWithIndex.originalIndex;
                              // 원본 인덱스를 사용하여 키 생성 (crop 이미지 매칭 유지)
                              const itemKey = `${item.path}-${originalIndex}`;
                              const cropImage = checkedItemsCropImages[itemKey];
                              const isLoading = loadingCheckedItemsCrops[itemKey];
                              // bbox_text에서 추출한 세부 텍스트 사용 (없으면 기존 방식 사용)
                              const detailText = itemWithIndex.detailText || checkedItemsDetailTexts[itemKey];
                              
                              return (
                                <div
                                  key={`${item.path}-${originalIndex}`}
                                  className="p-3 bg-gray-50 border border-gray-200 rounded flex items-start gap-3"
                                >
                                  {/* 왼쪽: 항목 정보 */}
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-gray-500 font-semibold">#{displayIndex + 1}</span>
                                      <span className={`px-2 py-0.5 text-xs rounded ${
                                        item.method === 'ai_text' ? 'bg-green-100 text-green-700' :
                                        item.method === 'text_similarity' ? 'bg-yellow-100 text-yellow-700' :
                                        'bg-gray-100 text-gray-700'
                                      }`}>
                                        {item.method === 'ai_text' ? 'AI 추론' :
                                         item.method === 'text_similarity' ? '텍스트 유사도' :
                                         item.method}
                                      </span>
                                    </div>
                                    <div className="text-sm text-gray-700 space-y-1">
                                      {item.name && (
                                        <div>
                                          <span className="font-medium">이름:</span> {item.name}
                                        </div>
                                      )}
                                      {item.text && (
                                        <div>
                                          <span className="font-medium">텍스트:</span> {item.text}
                                        </div>
                                      )}
                                      {item.path && (
                                        <div className="text-xs text-gray-500 font-mono">
                                          경로: {item.path}
                                        </div>
                                      )}
                                      {/* '확인' 항목인 경우 세부내용 표시 */}
                                      {item.name === '확인' && detailText && (
                                        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
                                          <span className="font-medium text-blue-700">세부내용:</span>{' '}
                                          <span className="text-blue-900">{detailText}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  
                                  {/* 오른쪽: Crop 이미지 */}
                                  <div className="flex-shrink-0">
                                    {isLoading ? (
                                      <div className="w-24 h-16 flex items-center justify-center border border-gray-200 rounded bg-gray-50">
                                        <span className="text-xs text-gray-400">로딩...</span>
                                      </div>
                                    ) : cropImage ? (
                                      <img
                                        src={`data:image/jpeg;base64,${cropImage}`}
                                        alt={`${item.name || item.text || '항목'} crop`}
                                        className="w-24 h-16 object-contain border border-gray-200 rounded bg-gray-50 p-1"
                                      />
                                    ) : (
                                      <div className="w-24 h-16 flex items-center justify-center border border-gray-200 rounded bg-gray-50">
                                        <span className="text-xs text-gray-400">이미지 없음</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }
                
                // 약정기간 항목인 경우
                if (selectedIssue.fieldName && selectedIssue.fieldName.includes('약정기간')) {
                  const contractPeriodItem = selectedIssue.metadata?.contractPeriodItem as any;
                  const serviceName = selectedIssue.metadata?.serviceName as string || '';
                  
                  return (
                    <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                      <div className="bg-white border-2 border-blue-300 rounded-lg p-6 shadow-sm space-y-4">
                        <div>
                          <label className="block text-sm font-semibold text-gray-700 mb-2">
                            {selectedIssue.fieldName}
                          </label>
                          <div className="p-3 bg-blue-50 border border-blue-300 rounded mb-4">
                            <p className="text-sm text-gray-900 mb-2">
                              {selectedIssue.description}
                            </p>
                          </div>
                          
                          {/* AI 추론 정보 */}
                          {contractPeriodItem && (
                            <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                              <h4 className="text-sm font-semibold text-gray-700 mb-3">AI 추론</h4>
                              <div className="space-y-2 text-sm">
                                {contractPeriodItem.name && (
                                  <div>
                                    <span className="font-medium text-gray-600">이름:</span>{' '}
                                    <span className="text-gray-900">{contractPeriodItem.name}</span>
                                  </div>
                                )}
                                {contractPeriodItem.text && (
                                  <div>
                                    <span className="font-medium text-gray-600">텍스트:</span>{' '}
                                    <span className="text-gray-900">{contractPeriodItem.text}</span>
                                  </div>
                                )}
                                {contractPeriodItem.path && (
                                  <div>
                                    <span className="font-medium text-gray-600">경로:</span>{' '}
                                    <span className="text-xs text-gray-500 font-mono">{contractPeriodItem.path}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                          
                          {/* Crop 이미지 */}
                          <div className="mb-4">
                            <p className="text-xs text-gray-500 mb-2">추출된 영역</p>
                            {loadingContractPeriodCrop ? (
                              <div className="w-full max-w-md h-32 flex items-center justify-center border-2 border-blue-200 rounded-lg bg-gray-50">
                                <p className="text-sm text-gray-500">이미지 로딩 중...</p>
                              </div>
                            ) : contractPeriodCropImage ? (
                              <img
                                src={`data:image/jpeg;base64,${contractPeriodCropImage}`}
                                alt={selectedIssue.fieldName}
                                className="w-full max-w-md h-32 object-contain border-2 border-blue-200 rounded-lg bg-gray-50 p-2"
                              />
                            ) : (
                              <div className="w-full max-w-md h-32 flex items-center justify-center border-2 border-gray-200 rounded-lg bg-gray-50">
                                <p className="text-sm text-gray-400">이미지를 불러올 수 없습니다</p>
                              </div>
                            )}
                          </div>
                          
                          {/* 서비스명 표시 */}
                          {serviceName && (
                            <div className="p-3 bg-green-50 border border-green-300 rounded">
                              <p className="text-sm text-gray-900">
                                <span className="font-semibold">{serviceName} 약정기간</span>이{' '}
                                <span className="font-semibold">{contractPeriodItem?.name || contractPeriodItem?.text || '확인 필요'}</span>로 체크되었습니다.
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                }
                
                // 기타 문서 타입
                return (
                  <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
                    <div className="bg-white border-2 border-yellow-300 rounded-lg p-6 shadow-sm">
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {selectedIssue.fieldName}
                        </label>
                        <div className="p-3 bg-yellow-50 border border-yellow-300 rounded">
                          <p className="text-sm text-gray-900">{selectedIssue.description}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Review Form */}
              <div className="p-4 border-t border-gray-200 bg-white">
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      검토 의견 (선택사항)
                    </label>
                    <textarea
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      placeholder="필요시 의견을 입력하세요..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={3}
                    />
                  </div>

                  <button
                    onClick={() => {
                      handleMarkAsReviewed(selectedIssue.id);
                    }}
                    className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    확인 완료
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Eye size={48} className="mx-auto mb-2 opacity-50" />
              <p>왼쪽에서 항목을 선택하세요</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewStep;

