/**
 * 신분증 OCR API 클라이언트
 * app.py의 /api/upload 엔드포인트와 연동
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

/**
 * 서버 터미널에 로그 전송
 */
async function sendLogToServer(level: string, message: string) {
  try {
    await fetch(`${API_BASE_URL}/api/log`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        level,
        message,
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {
      // 로그 전송 실패는 무시 (서버가 꺼져있을 수 있음)
    });
  } catch (error) {
    // 로그 전송 실패는 무시
  }
}

export interface IDCardOCRResult {
  success: boolean;
  data: {
    name: string;
    resident_number: string; // 마스킹된 주민번호
    address: string;
    issue_date: string; // 발급일
  };
  crops: {
    name?: string; // base64 이미지
    resident?: string; // base64 이미지
    address?: string; // base64 이미지
    issue_date?: string; // base64 이미지
  };
  masked_image?: string; // base64 이미지
  ocr_text: string; // 전체 OCR 텍스트
  ocr_lines: any[]; // OCR 라인 정보
  error?: string;
}

/**
 * 신분증 이미지를 업로드하고 OCR 처리
 * 
 * @param file 신분증 이미지 파일
 * @returns OCR 결과
 */
export async function uploadAndProcessIDCard(file: File): Promise<IDCardOCRResult> {
  const startTime = Date.now();
  const timestamp = new Date().toISOString();
  
  const logMsg1 = `========== OCR 요청 시작 ==========`;
  const logMsg2 = `시간: ${timestamp}`;
  const logMsg3 = `파일 정보: ${file.name} (${(file.size / 1024).toFixed(2)} KB, ${file.type})`;
  
  console.log(`\n[idCardApi] ${logMsg1}`);
  console.log(`[idCardApi] ${logMsg2}`);
  console.log(`[idCardApi] ${logMsg3}`);
  
  await sendLogToServer('INFO', logMsg1);
  await sendLogToServer('INFO', logMsg2);
  await sendLogToServer('INFO', logMsg3);

  try {
    const logMsg4 = `[1/3] FormData 생성 중...`;
    console.log(`[idCardApi] ${logMsg4}`);
    await sendLogToServer('INFO', logMsg4);
    
    const formData = new FormData();
    formData.append('file', file);
    
    const logMsg5 = `[1/3] ✅ FormData 생성 완료`;
    console.log(`[idCardApi] ${logMsg5}`);
    await sendLogToServer('INFO', logMsg5);

    const logMsg6 = `[2/3] 서버로 요청 전송 중...`;
    console.log(`[idCardApi] ${logMsg6}`);
    await sendLogToServer('INFO', logMsg6);
    
    const requestStartTime = Date.now();
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    const requestDuration = Date.now() - requestStartTime;
    
    const logMsg7 = `[2/3] ✅ 서버 응답 수신 (소요 시간: ${requestDuration}ms)`;
    const logMsg8 = `응답 상태: ${response.status} ${response.statusText}`;
    console.log(`[idCardApi] ${logMsg7}`);
    console.log(`[idCardApi] ${logMsg8}`);
    await sendLogToServer('INFO', logMsg7);
    await sendLogToServer('INFO', logMsg8);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'OCR 처리 실패' }));
      const errorMsg = `❌ OCR 처리 실패: ${JSON.stringify(errorData)}`;
      console.error(`[idCardApi] ${errorMsg}`);
      await sendLogToServer('ERROR', errorMsg);
      throw new Error(errorData.error || `OCR 처리 실패: ${response.statusText}`);
    }

    const logMsg9 = `[3/3] 응답 JSON 파싱 중...`;
    console.log(`[idCardApi] ${logMsg9}`);
    await sendLogToServer('INFO', logMsg9);
    
    const result = await response.json();
    const totalDuration = Date.now() - startTime;
    
    const logMsg10 = `[3/3] ✅ JSON 파싱 완료`;
    const logMsg11 = `OCR 결과 요약: 성공=${result.success}, 성명=${result.data?.name || 'N/A'}, 주민번호=${result.data?.resident_number || 'N/A'}`;
    const logMsg12 = `========== OCR 요청 완료 (총 소요 시간: ${totalDuration}ms) ==========`;
    
    console.log(`[idCardApi] ${logMsg10}`);
    console.log(`[idCardApi] ${logMsg11}`);
    console.log(`[idCardApi] ${logMsg12}\n`);
    
    await sendLogToServer('INFO', logMsg10);
    await sendLogToServer('INFO', logMsg11);
    await sendLogToServer('INFO', logMsg12);
    
    return result;
  } catch (error) {
    const totalDuration = Date.now() - startTime;
    const errorMsg = `❌ 신분증 OCR 요청 오류 (소요 시간: ${totalDuration}ms): ${error instanceof Error ? error.message : '알 수 없는 오류'}`;
    console.error(`[idCardApi] ${errorMsg}`);
    await sendLogToServer('ERROR', errorMsg);
    return {
      success: false,
      data: {
        name: '',
        resident_number: '',
        address: '',
        issue_date: '',
      },
      crops: {},
      ocr_text: '',
      ocr_lines: [],
      error: error instanceof Error ? error.message : '알 수 없는 오류',
    };
  }
}

