import React, { useEffect, useRef } from 'react';
import { Loader, CheckCircle, FileText, X } from 'lucide-react';
import { useRegistrationStore } from '../../../stores/useRegistrationStore';
import { uploadAndProcessIDCard } from '../../../api/idCardApi';
import type { HighlightedIssue } from '../../../types';

interface ProcessingStepProps {
  onNext: () => void;
}

const ProcessingStep: React.FC<ProcessingStepProps> = ({ onNext }) => {
  // onNext: 모든 준비가 완료되었을 때 부모에게 알리는 콜백
  const { currentSession, addIssues, setAgentResult, agentResult, cancelSession } = useRegistrationStore();
  const [showAgentResult, setShowAgentResult] = React.useState(false);
  
  // 진행 상태 관리
  const [processingSteps, setProcessingSteps] = React.useState({
    idCardOCR: false,      // 신분증 OCR 추출
    documentOCR: false,    // 서류 OCR 추출
    checkboxDetection: false, // 체크박스 항목 탐지 및 반영
    agentAnalysis: false   // 에이전트 분석결과 도출
  });
  
  // 취소 플래그 (X 버튼 클릭 시 true)
  const [isCancelled, setIsCancelled] = React.useState(false);
  
  // 처리 완료 플래그 (중복 실행 방지)
  const [isProcessingComplete, setIsProcessingComplete] = React.useState(false);
  
  // 실행 중 플래그 (useRef로 중복 실행 방지 - 리렌더링과 무관하게 유지)
  const isProcessingRef = useRef(false);

  useEffect(() => {
    // 이미 처리 완료되었거나 취소된 경우 실행하지 않음
    if (isProcessingComplete || isCancelled) {
      console.log('[ProcessingStep] 이미 처리 완료되었거나 취소됨, 실행 스킵');
      return;
    }
    
    // 이미 실행 중인 경우 중복 실행 방지
    if (isProcessingRef.current) {
      console.log('[ProcessingStep] ⚠️ 이미 처리 중입니다. 중복 실행 방지');
      return;
    }
    
    // 실행 시작 플래그 설정
    isProcessingRef.current = true;
    console.log('[ProcessingStep] 🔒 처리 시작 - 중복 실행 방지 플래그 설정');
    
    const processDocuments = async () => {
      // 취소된 경우 즉시 종료
      if (isCancelled) {
        console.log('[ProcessingStep] 사용자에 의해 취소됨');
        return;
      }
      if (!currentSession) {
        console.log('[ProcessingStep] currentSession이 없습니다.');
        return;
      }

      console.log('[ProcessingStep] 문서 목록:', currentSession.documents);
      console.log('[ProcessingStep] OCR 결과:', currentSession.ocrResults);

      // 신분증 OCR이 이미 완료되었는지 확인
      const existingIdCardOCR = currentSession.ocrResults.find((ocr) => ocr.idCardResult !== undefined);
      
      if (existingIdCardOCR) {
        console.log('[ProcessingStep] 이미 OCR이 완료되었습니다.');
        // 이미 OCR이 완료되었어도 Agent 결과를 기다려야 하므로 여기서는 진행 계속
        // onNext() 호출 제거 - Agent 결과가 준비될 때만 호출됨
        console.log('[ProcessingStep] 기존 OCR 결과 발견, Agent 처리 계속 진행');
        // return 제거하여 계속 진행
      }

      // 모든 문서에 대해 OCR 처리 (파일이 있는 경우)
      const documentsToProcess = currentSession.documents.filter((doc) => doc.file);
      
      console.log('[ProcessingStep] 처리할 문서 수:', documentsToProcess.length);
      
      if (documentsToProcess.length === 0) {
        console.log('[ProcessingStep] 처리할 문서가 없습니다.');
        // 문서가 없어도 Agent 결과를 기다려야 하므로 여기서는 진행 계속
        // onNext() 호출 제거 - Agent 결과가 준비될 때만 호출됨
        console.log('[ProcessingStep] 문서가 없지만 Agent 처리 계속 진행');
        // return 제거하여 계속 진행
      }
      
      let processedCount = 0;
      let hasIdCard = false;
      const processingPromises: Promise<void>[] = [];
      
      // 모든 문서를 병렬로 처리
      for (const document of documentsToProcess) {
        if (!document.file) {
          console.log('[ProcessingStep] 파일이 없는 문서 스킵:', document.fileName);
          processedCount++;
          continue;
        }
        
        // 각 문서 처리를 Promise로 래핑
        const processPromise = (async () => {
          const docStartTime = Date.now();
          const logMsg1 = `========== 문서 처리 시작 ==========`;
          const logMsg2 = `문서 ID: ${document.id}, 파일명: ${document.fileName}, 타입: ${document.type}`;
          const logMsg3 = `시작 시간: ${new Date().toISOString()}`;
          
          console.log(`\n[ProcessingStep] ${logMsg1}`);
          console.log(`[ProcessingStep] ${logMsg2}`);
          console.log(`[ProcessingStep] ${logMsg3}`);
          
          // 서버 터미널에 로그 전송
          await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg1}`, timestamp: new Date().toISOString() }),
          }).catch(() => {});
          await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg2}`, timestamp: new Date().toISOString() }),
          }).catch(() => {});
          
          try {
            // 신분증인 경우에만 신분증 OCR 처리
            if (document.type === 'id_card') {
              // 취소 확인
              if (isCancelled) {
                console.log('[ProcessingStep] 신분증 OCR 처리 취소됨');
                return;
              }
              
              // 1단계: 신분증 OCR 추출
              setProcessingSteps(prev => ({ ...prev, idCardOCR: false }));
              const logMsg4 = `신분증 OCR 처리 시작 (uploadAndProcessIDCard 호출 중)...`;
              console.log(`[ProcessingStep] ${logMsg4}`);
              const result = await uploadAndProcessIDCard(document.file!);
              
              // 취소 확인
              if (isCancelled) {
                console.log('[ProcessingStep] 신분증 OCR 완료 후 취소됨');
                return;
              }
              
              // 신분증 OCR 완료
              setProcessingSteps(prev => ({ ...prev, idCardOCR: true }));
              const docDuration = Date.now() - docStartTime;
              const logMsg5 = `✅ 신분증 OCR 완료 (소요 시간: ${docDuration}ms)`;
              console.log(`[ProcessingStep] ${logMsg5}`);
              
              console.log('[ProcessingStep] 신분증 OCR 결과:', {
                success: result.success,
                hasData: !!result.data,
                hasCrops: !!result.crops,
                ocr_text: result.ocr_text?.substring(0, 100),
                error: result.error
              });
              
              if (result.success) {
                hasIdCard = true;
              
                // OCR 결과를 세션에 저장
                const { currentSession: updatedSession } = useRegistrationStore.getState();
                if (updatedSession) {
                  useRegistrationStore.setState({
                    currentSession: {
                      ...updatedSession,
                      ocrResults: [
                        ...updatedSession.ocrResults.filter((ocr) => ocr.documentId !== document.id),
                        {
                          documentId: document.id,
                          extractedData: result.data,
                          confidence: 0.95,
                          processedAt: new Date(),
                          idCardResult: {
                            name: result.data.name,
                            resident_number: result.data.resident_number,
                            address: result.data.address,
                            issue_date: result.data.issue_date || '',
                            crops: result.crops,
                            masked_image: result.masked_image,
                            ocr_text: result.ocr_text,
                            ocr_lines: result.ocr_lines,
                          },
                        },
                      ],
                    },
                  });
                }
              
                // 문서 상태 업데이트
                useRegistrationStore.getState().updateDocumentStatus(document.id, 'review_required', 100);
              
                // 신분증 이슈 생성
                console.log('[ProcessingStep] 신분증 이슈 생성 시작:', {
                  name: result.data.name,
                  resident_number: result.data.resident_number,
                  address: result.data.address,
                  issue_date: result.data.issue_date,
                  hasNameCrop: !!result.crops.name,
                  hasResidentCrop: !!result.crops.resident,
                  hasAddressCrop: !!result.crops.address,
                  hasIssueDateCrop: !!result.crops.issue_date,
                  hasMaskedImage: !!result.masked_image
                });
              
                // 기존 이슈 중복 체크
                const { currentSession: sessionBeforeAdd } = useRegistrationStore.getState();
                const existingIssueIds = new Set(sessionBeforeAdd?.issues?.map(i => i.id) || []);
              
                const idCardIssues: HighlightedIssue[] = [
                  {
                    id: `id-card-name-${document.id}`,
                    documentType: 'id_card',
                    documentId: document.id,
                    severity: 'info',
                    fieldName: '성명',
                    issueType: 'uncertain',
                    title: '성명 확인',
                    description: result.data.name || '추출 실패',
                    reviewed: false,
                    correctedValue: result.data.name,
                    cropImage: result.crops.name,
                  },
                  {
                    id: `id-card-resident-${document.id}`,
                    documentType: 'id_card',
                    documentId: document.id,
                    severity: 'info',
                    fieldName: '주민번호',
                    issueType: 'uncertain',
                    title: '주민번호 확인',
                    description: result.data.resident_number || '추출 실패',
                    reviewed: false,
                    correctedValue: result.data.resident_number,
                    cropImage: result.crops.resident,
                  },
                  {
                    id: `id-card-address-${document.id}`,
                    documentType: 'id_card',
                    documentId: document.id,
                    severity: 'info',
                    fieldName: '주소',
                    issueType: 'uncertain',
                    title: '주소 확인',
                    description: result.data.address || '추출 실패',
                    reviewed: false,
                    correctedValue: result.data.address,
                    cropImage: result.crops.address,
                  },
                  {
                    id: `id-card-issue-date-${document.id}`,
                    documentType: 'id_card',
                    documentId: document.id,
                    severity: 'info',
                    fieldName: '발급일',
                    issueType: 'uncertain',
                    title: '발급일 확인',
                    description: result.data.issue_date || '추출 실패',
                    reviewed: false,
                    correctedValue: result.data.issue_date,
                    cropImage: result.crops.issue_date,
                  },
                  {
                    id: `id-card-full-${document.id}`,
                    documentType: 'id_card',
                    documentId: document.id,
                    severity: 'info',
                    fieldName: '신분증 전체',
                    issueType: 'uncertain',
                    title: '신분증 전체 확인',
                    description: '신분증 전체 이미지',
                    reviewed: false,
                    correctedValue: '',
                    cropImage: result.masked_image, // 마스킹된 전체 이미지
                  },
                ];
              
                // 중복되지 않은 이슈만 필터링
                const newIssues = idCardIssues.filter(issue => !existingIssueIds.has(issue.id));
              
                console.log('[ProcessingStep] 이슈 추가 전 현재 이슈 수:', sessionBeforeAdd?.issues?.length || 0);
                console.log('[ProcessingStep] 기존 이슈 ID:', Array.from(existingIssueIds));
                console.log('[ProcessingStep] 추가할 이슈:', newIssues.map(i => ({ id: i.id, fieldName: i.fieldName, hasCrop: !!i.cropImage })));
              
                if (newIssues.length > 0) {
                  addIssues(newIssues);
                } else {
                  console.log('[ProcessingStep] 모든 이슈가 이미 존재하여 추가하지 않음');
                }
              
                // 이슈 추가 후 확인 (상태 업데이트 대기)
                await new Promise(resolve => setTimeout(resolve, 200));
              
                const { currentSession: checkSession } = useRegistrationStore.getState();
                console.log('[ProcessingStep] 이슈 추가 후 현재 이슈 수:', checkSession?.issues?.length || 0);
                const addedIdCardIssues = checkSession?.issues?.filter(i => i.documentType === 'id_card') || [];
                console.log('[ProcessingStep] 신분증 이슈 목록:', addedIdCardIssues.map(i => ({ id: i.id, fieldName: i.fieldName, reviewed: i.reviewed })));
              
                if (addedIdCardIssues.length === 0) {
                  console.error('[ProcessingStep] ⚠️ 이슈가 추가되지 않았습니다!');
                } else {
                  console.log('[ProcessingStep] ✅ 신분증 이슈 추가 완료:', addedIdCardIssues.length, '개');
                }
              } else {
                console.error('[ProcessingStep] 신분증 OCR 처리 실패:', result.error);
                useRegistrationStore.getState().updateDocumentStatus(document.id, 'review_required', 0);
              }
            } else {
              // 서류인 경우 서류 OCR 처리 (나중에 서류 OCR 추출 단계에서 처리)
              console.log(`[ProcessingStep] 서류 문서 (${document.type}) - 서류 OCR 추출 단계에서 처리 예정`);
              // 여기서는 상태만 업데이트 (실제 OCR은 2단계에서 처리)
              useRegistrationStore.getState().updateDocumentStatus(document.id, 'processing', 0);
            }
          } catch (error) {
            console.error('[ProcessingStep] 문서 처리 오류:', error);
            useRegistrationStore.getState().updateDocumentStatus(document.id, 'review_required', 0);
          } finally {
            processedCount++;
            const docDuration = Date.now() - docStartTime;
            const logMsg6 = `문서 처리 완료: ${document.fileName} (${processedCount}/${documentsToProcess.length})`;
            const logMsg7 = `문서별 총 소요 시간: ${docDuration}ms`;
            const logMsg8 = `========== 문서 OCR 처리 종료 ==========`;
            
            console.log(`[ProcessingStep] ${logMsg6}`);
            console.log(`[ProcessingStep] ${logMsg7}`);
            console.log(`[ProcessingStep] ${logMsg8}\n`);
            
            // 서버 터미널에 로그 전송
            await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg6}`, timestamp: new Date().toISOString() }),
            }).catch(() => {});
          }
        })();
        
        processingPromises.push(processPromise);
      }
      
      // 모든 OCR 처리가 완료될 때까지 대기
      const allStartTime = Date.now();
      const logMsg9 = `========== 모든 OCR 처리 시작 ==========`;
      const logMsg10 = `총 ${documentsToProcess.length}개 문서 처리 대기 중...`;
      const logMsg11 = `시작 시간: ${new Date().toISOString()}`;
      
      console.log(`\n[ProcessingStep] ${logMsg9}`);
      console.log(`[ProcessingStep] ${logMsg10}`);
      console.log(`[ProcessingStep] ${logMsg11}`);
      
      // 서버 터미널에 로그 전송
      await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg9}`, timestamp: new Date().toISOString() }),
      }).catch(() => {});
      
      await Promise.all(processingPromises);
      const allDuration = Date.now() - allStartTime;
      
      const logMsg12 = `✅ 모든 OCR 처리 완료!`;
      const logMsg13 = `총 소요 시간: ${allDuration}ms`;
      const logMsg14 = `========== 모든 OCR 처리 종료 ==========`;
      
      console.log(`[ProcessingStep] ${logMsg12}`);
      console.log(`[ProcessingStep] ${logMsg13}`);
      console.log(`[ProcessingStep] ${logMsg14}\n`);
      
      // 서버 터미널에 로그 전송
      await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg12}`, timestamp: new Date().toISOString() }),
      }).catch(() => {});
      await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level: 'INFO', message: `[ProcessingStep] ${logMsg13}`, timestamp: new Date().toISOString() }),
      }).catch(() => {});

      // 모든 문서 처리 완료 후 상태 확인
      console.log('[ProcessingStep] 모든 문서 처리 완료:', {
        processedCount,
        totalDocuments: documentsToProcess.length,
        hasIdCard
      });
      
      // 취소 확인
      if (isCancelled) {
        console.log('[ProcessingStep] OCR 처리 완료 후 취소됨');
        return;
      }
      
      // 상태 업데이트가 완료될 때까지 짧은 대기 (React 상태 업데이트 반영 시간)
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const { currentSession: finalSession } = useRegistrationStore.getState();
      console.log('[ProcessingStep] 최종 이슈 수:', finalSession?.issues?.length || 0);
      console.log('[ProcessingStep] 신분증 이슈 수:', finalSession?.issues?.filter(i => i.documentType === 'id_card').length || 0);
      
      // 2단계: 서류 OCR 추출 및 체크박스 탐지
      setProcessingSteps(prev => ({ ...prev, documentOCR: false }));
      console.log('[ProcessingStep] ========== 서류 OCR 추출 단계 ==========');
      
      // 서류 파일 찾기 (type !== 'id_card')
      const documentFiles = finalSession?.documents.filter(
        (doc) => doc.type !== 'id_card' && doc.file
      ) || [];
      
      let checkboxCoordinates: Array<{x1: number, y1: number, x2: number, y2: number}> = [];
      let structuredOutputGenerated = false;
      
      if (documentFiles.length > 0) {
        console.log(`[ProcessingStep] 서류 파일 ${documentFiles.length}개 발견, 서류 OCR 처리 시작...`);
        
        // 첫 번째 서류 파일에 대해 OCR Structured API 호출
        const firstDocument = documentFiles[0];
        if (firstDocument.file) {
          // 취소 확인
          if (isCancelled) {
            console.log('[ProcessingStep] 서류 OCR 처리 중 취소됨');
            return;
          }
          
          try {
            console.log(`[ProcessingStep] [1/2] 서류 OCR API 호출 중: ${firstDocument.fileName}`);
            
            // FormData 생성
            const formData = new FormData();
            formData.append('file', firstDocument.file);
            
            // 서류 OCR API 호출
            const ocrResponse = await fetch(
              `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/document-ocr`,
              {
                method: 'POST',
                body: formData,
              }
            );
            
            if (!ocrResponse.ok) {
              const errorText = await ocrResponse.text();
              console.error(`[ProcessingStep] ❌ 서류 OCR 실패:`, errorText);
              throw new Error(`서류 OCR 실패: ${ocrResponse.status} ${errorText}`);
            }
            
            const ocrData = await ocrResponse.json();
            
            if (ocrData.success) {
              console.log(`[ProcessingStep] ✅ 서류 OCR 완료: structured_output.json 생성됨`);
              structuredOutputGenerated = true;
              
              // 문서 상태 업데이트
              useRegistrationStore.getState().updateDocumentStatus(firstDocument.id, 'review_required', 100);
            } else {
              throw new Error(ocrData.error || '서류 OCR 처리 실패');
            }
          } catch (error) {
            console.error(`[ProcessingStep] 서류 OCR 처리 중 오류:`, error);
            useRegistrationStore.getState().updateDocumentStatus(firstDocument.id, 'error', 0);
            // 오류가 발생해도 체크박스 탐지는 계속 진행
          }
        }
        
        // 체크박스 탐지 (모든 서류 파일에 대해)
        console.log(`[ProcessingStep] [2/2] 체크박스 탐지 시작...`);
        for (const doc of documentFiles) {
          if (!doc.file) continue;
          
          // 취소 확인
          if (isCancelled) {
            console.log('[ProcessingStep] 체크박스 탐지 중 취소됨');
            return;
          }
          
          try {
            // FormData 생성
            const formData = new FormData();
            formData.append('file', doc.file);
            
            // 체크박스 탐지 API 호출
            const checkboxResponse = await fetch(
              `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/detect-checkboxes`,
              {
                method: 'POST',
                body: formData,
              }
            );
            
            if (!checkboxResponse.ok) {
              const errorText = await checkboxResponse.text();
              console.error(`[ProcessingStep] 체크박스 탐지 실패 (${doc.fileName}):`, errorText);
              continue;
            }
            
            const checkboxData = await checkboxResponse.json();
            
            if (checkboxData.success && checkboxData.checkboxes) {
              console.log(`[ProcessingStep] ✅ ${doc.fileName}에서 ${checkboxData.checkboxes.length}개 체크박스 발견`);
              checkboxCoordinates = checkboxCoordinates.concat(checkboxData.checkboxes);
            }
          } catch (error) {
            console.error(`[ProcessingStep] 체크박스 탐지 중 오류 (${doc.fileName}):`, error);
            // 오류가 발생해도 계속 진행
          }
        }
      } else {
        console.log('[ProcessingStep] 서류 파일이 없어 서류 OCR 스킵');
      }
      
      if (structuredOutputGenerated) {
        console.log('[ProcessingStep] ✅ structured_output.json 생성 완료 (서류 OCR 결과)');
      } else {
        console.log('[ProcessingStep] ⚠️ structured_output.json이 생성되지 않았습니다. 기존 파일을 사용합니다.');
      }
      
      setProcessingSteps(prev => ({ ...prev, documentOCR: true }));
      console.log('[ProcessingStep] ✅ 서류 OCR 추출 완료');
      
      // 취소 확인
      if (isCancelled) {
        console.log('[ProcessingStep] 서류 OCR 완료 후 취소됨');
        return;
      }
      
      // 3단계: 체크박스 항목 탐지 및 반영
      setProcessingSteps(prev => ({ ...prev, checkboxDetection: false }));
      console.log('[ProcessingStep] ========== 체크박스 항목 탐지 및 반영 단계 ==========');
      
      let updatedStructuredOutputPath = 'structured_output.json';
      let checkedItems: Array<{name: string, text: string, path: string, method: string}> = [];
      
      try {
        // 체크박스 좌표가 있으면 checkbox_agent를 사용하여 structured_output.json 수정
        if (checkboxCoordinates.length > 0) {
          console.log(`[ProcessingStep] 체크박스 좌표 ${checkboxCoordinates.length}개 발견, checkbox_agent로 처리 시작`);
          
          // checkbox_agent API 호출
          const processResponse = await fetch(
            `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/process-checkboxes`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                checkboxes: checkboxCoordinates,
                structured_output_path: 'structured_output.json'
              })
            }
          );
          
          if (!processResponse.ok) {
            const errorText = await processResponse.text();
            console.error(`[ProcessingStep] 체크박스 처리 실패:`, errorText);
            // 오류가 발생해도 계속 진행
          } else {
            const processData = await processResponse.json();
            
            if (processData.success) {
              console.log(`[ProcessingStep] ✅ 체크박스 처리 완료: ${processData.processed_count}개 처리됨`);
              updatedStructuredOutputPath = processData.updated_structured_output_path || 'structured_output_updated.json';
              checkedItems = processData.checked_items || [];
              
              // 체크된 항목을 검토 목록에 추가
              if (checkedItems.length > 0) {
                // 기존 이슈 중복 체크 (fieldName으로 확인)
                const { currentSession: sessionBeforeAdd } = useRegistrationStore.getState();
                const existingCheckedItemsIssue = sessionBeforeAdd?.issues?.find(
                  (issue) => issue.fieldName === '체크된 항목'
                );
                
                // 이미 '체크된 항목' 이슈가 있으면 업데이트, 없으면 새로 추가
                if (existingCheckedItemsIssue) {
                  // 기존 이슈 업데이트 (metadata만 업데이트)
                  console.log('[ProcessingStep] 기존 체크된 항목 이슈 발견, 업데이트 스킵 (중복 방지)');
                } else {
                  // 새 이슈 추가 (고정된 ID 사용)
                  const checkedItemsIssue: HighlightedIssue = {
                    id: 'checked-items-issue',  // 고정된 ID 사용
                    documentType: 'application',
                    documentId: documentFiles[0]?.id || 'unknown',
                    severity: 'info',
                    fieldName: '체크된 항목',
                    issueType: 'uncertain',
                    title: '체크된 항목 확인',
                    description: `${checkedItems.length}개의 항목이 체크되었습니다.`,
                    reviewed: false,
                    correctedValue: '',
                    cropImage: '',
                    metadata: {
                      checkedItems: checkedItems
                    } as any
                  };
                  
                  addIssues([checkedItemsIssue]);
                  console.log('[ProcessingStep] ✅ 체크된 항목 이슈 추가 완료');
                }
                
                // 필수약관동의 항목 필터링 및 검토 항목 추가 ('확인' 항목들)
                const agreementItems = checkedItems.filter((item: any) => 
                  item.name === '확인' || (item.path && item.path.includes('condition_'))
                );
                
                if (agreementItems.length > 0) {
                  // 필수약관동의 이슈 추가 (하나의 이슈로 통합)
                  const { currentSession: sessionBeforeAgreement } = useRegistrationStore.getState();
                  const existingAgreementIssue = sessionBeforeAgreement?.issues?.find(
                    (issue) => issue.fieldName === '필수약관동의'
                  );
                  
                  if (!existingAgreementIssue) {
                    const agreementIssue: HighlightedIssue = {
                      id: 'agreement-confirmation-issue',
                      documentType: 'application' as const,
                      documentId: documentFiles[0]?.id || 'unknown',
                      severity: 'info' as const,
                      fieldName: '필수약관동의',
                      issueType: 'uncertain' as const,
                      title: '필수약관동의 확인',
                      description: `${agreementItems.length}개의 필수약관동의 항목이 체크되었습니다.`,
                      reviewed: false,
                      correctedValue: '',
                      cropImage: '',
                      metadata: {
                        agreementItems: agreementItems
                      } as any
                    };
                    
                    addIssues([agreementIssue]);
                    console.log('[ProcessingStep] ✅ 필수약관동의 이슈 추가 완료');
                  }
                }
                
                // 약정기간 항목 필터링 및 검토 항목 추가
                const contractPeriodItems = checkedItems.filter((item: any) => 
                  item.path && item.path.includes('contract_period')
                );
                
                if (contractPeriodItems.length > 0) {
                  // 서비스별로 그룹화
                  const contractPeriodIssues: HighlightedIssue[] = contractPeriodItems.map((item: any, idx: number) => {
                    // 경로에서 서비스명 추출 (TV, 인터넷, 일반전화 등)
                    let serviceName = '';
                    const path = item.path || '';
                    if (path.includes('TV') || path.includes('TV_')) {
                      serviceName = 'TV';
                    } else if (path.includes('인터넷') || path.includes('internet')) {
                      serviceName = '인터넷';
                    } else if (path.includes('일반전화') || path.includes('landlinephone')) {
                      serviceName = '일반전화';
                    } else if (path.includes('인터넷전화') || path.includes('internetcall')) {
                      serviceName = '인터넷전화';
                    }
                    
                    return {
                      id: `contract-period-${serviceName}-${idx}-${Date.now()}`,
                      documentType: 'application' as const,
                      documentId: documentFiles[0]?.id || 'unknown',
                      severity: 'info' as const,
                      fieldName: serviceName ? `${serviceName} 약정기간` : '약정기간',
                      issueType: 'uncertain' as const,
                      title: serviceName ? `${serviceName} 약정기간: ${item.name || item.text || '확인 필요'}` : `약정기간: ${item.name || item.text || '확인 필요'}`,
                      description: serviceName ? `${serviceName} 약정기간이 ${item.name || item.text || '확인 필요'}로 체크되었습니다.` : `약정기간이 ${item.name || item.text || '확인 필요'}로 체크되었습니다.`,
                      reviewed: false,
                      correctedValue: '',
                      cropImage: '', // 나중에 API로 가져올 예정
                      metadata: {
                        contractPeriodItem: item,
                        serviceName: serviceName,
                        path: item.path
                      } as any
                    };
                  });
                  
                  // 중복 체크
                  const existingIssueIds = new Set(sessionBeforeAdd?.issues?.map(i => i.id) || []);
                  const newContractPeriodIssues = contractPeriodIssues.filter(issue => !existingIssueIds.has(issue.id));
                  
                  if (newContractPeriodIssues.length > 0) {
                    addIssues(newContractPeriodIssues);
                    console.log('[ProcessingStep] ✅ 약정기간 항목 이슈 추가 완료:', newContractPeriodIssues.length, '개');
                  }
                }
              }
            } else {
              console.error(`[ProcessingStep] 체크박스 처리 실패:`, processData.error);
            }
          }
        } else {
          console.log('[ProcessingStep] 체크박스 좌표가 없어 처리 스킵');
        }
      } catch (error) {
        console.error('[ProcessingStep] 체크박스 처리 중 오류:', error);
        // 오류가 발생해도 계속 진행
      }
      
      setProcessingSteps(prev => ({ ...prev, checkboxDetection: true }));
      console.log('[ProcessingStep] ✅ 체크박스 항목 탐지 및 반영 완료');
      
      // 취소 확인
      if (isCancelled) {
        console.log('[ProcessingStep] 체크박스 처리 완료 후 취소됨');
        return;
      }
      
      // 4단계: 에이전트 분석결과 도출
      setProcessingSteps(prev => ({ ...prev, agentAnalysis: false }));
      console.log('[ProcessingStep] ========== 에이전트 분석결과 도출 단계 ==========');
      
      // 신분증 OCR 결과와 structured_output.json을 사용하여 Agent 실행
      const finalIdCardOCR = finalSession?.ocrResults.find((ocr) => ocr.idCardResult !== undefined);
      if (finalIdCardOCR && finalIdCardOCR.idCardResult) {
        // idCardResult를 변수에 저장하여 타입 안전성 확보
        const idCardResult = finalIdCardOCR.idCardResult;
        
        // Agent 실행 (결과를 기다림)
        try {
          const agentStartTime = Date.now();
          const agentResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/run-agent`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id_card_data: {
                name: idCardResult.name,
                resident_number: idCardResult.resident_number,
                address: idCardResult.address,
                issue_date: idCardResult.issue_date || '',
                ocr_text: idCardResult.ocr_text,
                ocr_lines: idCardResult.ocr_lines
              },
              structured_output_path: updatedStructuredOutputPath
            })
          });
          
          // 취소 확인
          if (isCancelled) {
            console.log('[ProcessingStep] Agent 실행 중 취소됨');
            return;
          }
          
          if (!agentResponse.ok) {
            const errorText = await agentResponse.text();
            console.error('[ProcessingStep] ❌ Agent 실행 실패:', errorText);
            setAgentResult({ success: false, error: 'Agent 실행 실패: ' + errorText });
            setProcessingSteps(prev => ({ ...prev, agentAnalysis: true })); // 실패해도 완료로 표시
            return;
          }
          
          const agentResultData = await agentResponse.json();
          const agentDuration = Date.now() - agentStartTime;
          console.log('[ProcessingStep] ✅ Agent 응답 수신 완료 (소요 시간: ' + agentDuration + 'ms)');
          
          // 취소 확인
          if (isCancelled) {
            console.log('[ProcessingStep] Agent 응답 수신 후 취소됨');
            return;
          }
          
          // Agent 결과가 준비되었는지 확인
          const isAgentReady = agentResultData.success && 
                               agentResultData.ready !== false &&
                               agentResultData.final_report && 
                               agentResultData.final_report.length > 0 &&
                               agentResultData.summary &&
                               Object.keys(agentResultData.summary).length > 0 &&
                               'total_fields' in agentResultData.summary;
          
          if (isAgentReady) {
            console.log('[ProcessingStep] ✅ Agent 결과가 완전히 준비되었습니다.');
            setAgentResult(agentResultData);
            
            // ========== 최종 검증: 모든 준비 상태 확인 ==========
            const { currentSession: sessionInStore } = useRegistrationStore.getState();
            
            const finalIdCardOCRCheck = sessionInStore?.ocrResults.find((ocr) => ocr.idCardResult);
            const idCardResultCheck = finalIdCardOCRCheck?.idCardResult;
            const idCardIssues = sessionInStore?.issues?.filter((i) => i.documentType === 'id_card') ?? [];
            
            const idCardReady = !!idCardResultCheck &&
                                !!idCardResultCheck.name &&
                                !!idCardResultCheck.resident_number &&
                                !!idCardResultCheck.address &&
                                idCardIssues.length > 0;
            
            const allStepsComplete = processingSteps.idCardOCR &&
                                     processingSteps.documentOCR &&
                                     processingSteps.checkboxDetection;
            
            if (!idCardReady) {
              console.error('[ProcessingStep] ❌ 신분증 정보/이슈가 아직 준비되지 않아 reviewing 상태로 전환하지 않습니다.', {
                hasResult: !!idCardResultCheck,
                name: idCardResultCheck?.name,
                resident_number: idCardResultCheck?.resident_number,
                address: idCardResultCheck?.address,
                idCardIssuesCount: idCardIssues.length,
              });
              // 에이전트 분석은 완료되었지만 다른 조건이 맞지 않아 체크만 표시
              setProcessingSteps(prev => ({ ...prev, agentAnalysis: true }));
              return;
            }
            
            if (!allStepsComplete) {
              console.error('[ProcessingStep] ❌ 모든 단계가 완료되지 않아 reviewing 상태로 전환하지 않습니다.', {
                idCardOCR: processingSteps.idCardOCR,
                documentOCR: processingSteps.documentOCR,
                checkboxDetection: processingSteps.checkboxDetection,
              });
              // 에이전트 분석은 완료되었지만 다른 단계가 완료되지 않아 체크만 표시
              setProcessingSteps(prev => ({ ...prev, agentAnalysis: true }));
              return;
            }
            
            // ✅ 여기까지 왔다면, 진짜로 "준비된 상태"
            // 모든 4단계가 완료되고 Agent 결과가 준비되었을 때만 부모에게 알림
            console.log('[ProcessingStep] ✅ 모든 4단계가 완료되어 ReviewStep으로 이동합니다.');
            console.log('[ProcessingStep] 완료된 단계:', {
              idCardOCR: processingSteps.idCardOCR,
              documentOCR: processingSteps.documentOCR,
              checkboxDetection: processingSteps.checkboxDetection,
              agentAnalysis: true
            });
            
            // 처리 완료 플래그 설정 (중복 실행 방지)
            setIsProcessingComplete(true);
            isProcessingRef.current = false;  // 실행 완료 플래그 해제
            console.log('[ProcessingStep] 처리 완료 - 중복 실행 방지 플래그 해제');
            
            // 에이전트 분석결과 도출 완료 표시 (체크표시)
            setProcessingSteps(prev => ({ ...prev, agentAnalysis: true }));
            
            // 자동 전환 제거 - 사용자가 "다음 단계" 버튼을 클릭할 때까지 대기
            console.log('[ProcessingStep] ✅ 모든 준비 완료 - 다음 단계 버튼 활성화 대기');
          } else {
            console.warn('[ProcessingStep] ⚠️ Agent 결과가 불완전합니다.');
            console.warn('[ProcessingStep] Agent 결과 검증 실패:', {
              success: agentResultData.success,
              ready: agentResultData.ready,
              hasFinalReport: !!agentResultData.final_report,
              finalReportLength: agentResultData.final_report?.length || 0,
              hasSummary: !!agentResultData.summary,
              summaryKeys: agentResultData.summary ? Object.keys(agentResultData.summary) : [],
              hasTotalFields: 'total_fields' in (agentResultData.summary || {})
            });
            setAgentResult({ success: false, error: 'Agent 결과가 불완전합니다.' });
            setProcessingSteps(prev => ({ ...prev, agentAnalysis: true }));
            isProcessingRef.current = false;  // 불완전한 경우에도 플래그 해제
            // 불완전한 경우 검토 단계로 이동하지 않음 - status 변경 안 함
            console.error('[ProcessingStep] ❌ Agent 결과가 불완전하여 검토 단계로 이동하지 않습니다.');
          }
        } catch (error) {
          console.error('[ProcessingStep] ❌ Agent 실행 오류:', error);
          setAgentResult({ success: false, error: error instanceof Error ? error.message : '알 수 없는 오류' });
          setProcessingSteps(prev => ({ ...prev, agentAnalysis: true }));
          isProcessingRef.current = false;  // 오류 발생 시에도 플래그 해제
          // 오류 발생 시 검토 단계로 이동하지 않음 - status 변경 안 함
          console.error('[ProcessingStep] ❌ Agent 실행 오류로 인해 검토 단계로 이동하지 않습니다.');
        }
      } else {
        console.log('[ProcessingStep] 신분증 OCR 결과가 없어 Agent 실행 스킵');
        setProcessingSteps(prev => ({ ...prev, agentAnalysis: true })); // 스킵해도 완료로 표시
        isProcessingRef.current = false;  // 스킵 시에도 플래그 해제
        // Agent 실행이 없으면 검토 단계로 이동하지 않음 - status 변경 안 함
        console.warn('[ProcessingStep] ⚠️ 신분증 OCR 결과가 없어 Agent를 실행할 수 없습니다. 검토 단계로 이동하지 않습니다.');
      }

      // 하드코딩된 검토항목들 주석처리
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
    };

    processDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 마운트 시 한 번만 실행 (의존성 배열 비워서 중복 실행 방지)

  const processingTasks = [
    { 
      label: '신분증 OCR 추출', 
      done: processingSteps.idCardOCR 
    },
    { 
      label: '서류 OCR 추출', 
      done: processingSteps.documentOCR 
    },
    { 
      label: '체크박스 항목 탐지 및 반영', 
      done: processingSteps.checkboxDetection 
    },
    { 
      label: '에이전트 분석결과 도출', 
      done: processingSteps.agentAnalysis 
    },
  ];

  // 취소 이벤트 감지 (RegistrationModal의 X 버튼 클릭 시)
  React.useEffect(() => {
    const handleCancel = () => {
      console.log('[ProcessingStep] 취소 신호 수신');
      setIsCancelled(true);
      cancelSession();
    };
    
    window.addEventListener('cancel-processing', handleCancel);
    return () => {
      window.removeEventListener('cancel-processing', handleCancel);
    };
  }, [cancelSession]);

  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-8">
      {/* Processing Animation */}
      <div className="relative">
        <div className="w-24 h-24 border-8 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader className="text-blue-600" size={32} />
        </div>
      </div>

      <div className="text-center">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">
          AI가 서류를 분석하고 있습니다
        </h3>
        <p className="text-gray-500">
          잠시만 기다려 주세요. 곧 완료됩니다.
        </p>
      </div>

      {/* Processing Tasks */}
      <div className="w-full max-w-md space-y-3">
        {processingTasks.map((task, index) => (
          <div
            key={index}
            className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
          >
            {task.done ? (
              <CheckCircle className="text-green-500 flex-shrink-0" size={20} />
            ) : (
              <div className="w-5 h-5 border-2 border-gray-300 rounded-full animate-pulse flex-shrink-0" />
            )}
            <span
              className={`text-sm ${
                task.done ? 'text-gray-900 font-medium' : 'text-gray-500'
              }`}
            >
              {task.label}
            </span>
          </div>
        ))}
        
        {/* 다음 단계 버튼 (프로세스 카드 우하단) */}
        <div className="pt-4 border-t border-gray-200">
          <button
            onClick={() => {
              console.log('[ProcessingStep] 다음 단계 버튼 클릭 → 검토 단계로 이동');
              if (typeof onNext === 'function') {
                onNext();
              } else {
                console.error('[ProcessingStep] ❌ onNext가 함수가 아닙니다!', onNext);
              }
            }}
            disabled={!processingSteps.agentAnalysis}
            className={`w-full py-3 px-6 rounded-lg font-semibold transition-all ${
              processingSteps.agentAnalysis
                ? 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {processingSteps.agentAnalysis ? '다음 단계 →' : '처리 중...'}
          </button>
          {!processingSteps.agentAnalysis && (
            <p className="text-xs text-gray-500 text-center mt-2">
              모든 처리가 완료되면 활성화됩니다
            </p>
          )}
        </div>
      </div>

      {/* Documents being processed */}
      {currentSession && (
        <div className="w-full max-w-md">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            처리 중인 문서
          </h4>
          <div className="space-y-2">
            {currentSession.documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-2 text-sm text-gray-600"
              >
                <CheckCircle className="text-green-500" size={16} />
                <span>{doc.fileName}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent 결과 모달 */}
      {showAgentResult && agentResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* 모달 헤더 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <FileText size={24} />
                Agent 분석 결과
              </h2>
              <button
                onClick={() => setShowAgentResult(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X size={24} className="text-gray-500" />
              </button>
            </div>
            
            {/* 모달 내용 */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {agentResult.success ? (
                <>
                  {/* 요약 */}
                  {agentResult.summary && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h3 className="font-semibold text-blue-900 mb-2">📊 분석 요약</h3>
                      <div className="text-sm text-blue-800 space-y-1">
                        {agentResult.summary.total_fields && (
                          <p>• 전체 필드: {agentResult.summary.total_fields}개</p>
                        )}
                        {agentResult.summary.matched !== undefined && (
                          <p>• 일치: {agentResult.summary.matched}개</p>
                        )}
                        {agentResult.summary.mismatched !== undefined && (
                          <p>• 불일치: {agentResult.summary.mismatched}개</p>
                        )}
                        {agentResult.summary.warnings !== undefined && (
                          <p>• 경고: {agentResult.summary.warnings}개</p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* 최종 리포트 */}
                  {agentResult.final_report && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-2">📋 분석 리포트</h3>
                      <div className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded border">
                        {agentResult.final_report}
                      </div>
                    </div>
                  )}
                  
                  {/* Agent 로그 */}
                  {agentResult.agent_logs && agentResult.agent_logs.length > 0 && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-3">📝 처리 로그</h3>
                      <div className="space-y-1 max-h-60 overflow-y-auto">
                        {agentResult.agent_logs.map((log: any, idx: number) => (
                          <div key={idx} className="text-xs text-gray-600 font-mono">
                            <span className="text-gray-400">[{log.timestamp || ''}]</span> {log.message || ''}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="font-semibold text-red-900 mb-2">❌ Agent 실행 실패</h3>
                  <p className="text-sm text-red-800">{agentResult.error || '알 수 없는 오류가 발생했습니다.'}</p>
                </div>
              )}
            </div>
            
            {/* 모달 푸터 */}
            <div className="p-6 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setShowAgentResult(false)}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessingStep;

