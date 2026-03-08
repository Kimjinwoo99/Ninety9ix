"""
OCR Structured API 테스트 스크립트
document.jpg를 입력받아 structured_output_test.json을 생성합니다.

사용 방법:
    python test_ocr_structured.py

필요한 패키지:
    pip install requests

API 엔드포인트:
    https://sryjsymzaxpkzfhf.tunnel.elice.io/ocr/structured
"""

import os
import json
import sys

try:
    import requests
except ImportError:
    print("❌ 오류: requests 라이브러리가 설치되지 않았습니다.")
    print("   다음 명령어로 설치하세요: pip install requests")
    sys.exit(1)

# API 엔드포인트
# ⚠️ 주의: 실제 서버 URL은 코드에 직접 넣지 않고 OCR_API_BASE_URL 환경변수로 관리합니다.
API_BASE_URL = os.getenv("OCR_API_BASE_URL", "http://localhost:8000")
API_ENDPOINT = f"{API_BASE_URL}/ocr/structured"

# 파일 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_IMAGE = os.path.join(SCRIPT_DIR, 'document.jpg')
OUTPUT_JSON = os.path.join(SCRIPT_DIR, 'structured_output_test.json')


def test_ocr_structured():
    """document.jpg를 OCR Structured API에 전송하여 structured_output_test.json 생성"""
    
    print("=" * 80)
    print("OCR Structured API 테스트")
    print("=" * 80)
    
    # 1. 입력 파일 확인
    print(f"\n[1/4] 입력 파일 확인 중...")
    if not os.path.exists(INPUT_IMAGE):
        print(f"❌ 오류: 입력 파일을 찾을 수 없습니다: {INPUT_IMAGE}")
        return False
    
    file_size = os.path.getsize(INPUT_IMAGE) / (1024 * 1024)  # MB
    print(f"✅ 입력 파일 확인 완료: {INPUT_IMAGE} ({file_size:.2f} MB)")
    
    # 2. API 요청 준비
    print(f"\n[2/4] API 요청 준비 중...")
    print(f"  - API 엔드포인트: {API_ENDPOINT}")
    
    try:
        # 파일을 multipart/form-data로 전송
        with open(INPUT_IMAGE, 'rb') as image_file:
            files = {
                'file': ('document.jpg', image_file, 'image/jpeg')
            }
            
            # 3. API 요청 전송
            print(f"\n[3/4] API 요청 전송 중...")
            response = requests.post(
                API_ENDPOINT,
                files=files,
                timeout=300  # 5분 타임아웃 (OCR 처리 시간 고려)
            )
            
            # 4. 응답 처리
            print(f"\n[4/4] 응답 처리 중...")
            print(f"  - 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                # JSON 응답 파싱
                result = response.json()
                
                # 결과를 파일로 저장
                print(f"\n✅ API 요청 성공!")
                print(f"  - 응답 데이터 크기: {len(json.dumps(result))} bytes")
                
                with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 결과 저장 완료: {OUTPUT_JSON}")
                
                # 결과 요약 출력
                if isinstance(result, dict):
                    print(f"\n📊 결과 요약:")
                    for key in result.keys():
                        if isinstance(result[key], (dict, list)):
                            print(f"  - {key}: {type(result[key]).__name__} (크기: {len(result[key])})")
                        else:
                            print(f"  - {key}: {result[key]}")
                
                return True
            else:
                print(f"❌ API 요청 실패!")
                print(f"  - 상태 코드: {response.status_code}")
                print(f"  - 응답 내용: {response.text[:500]}")
                return False
                
    except requests.exceptions.Timeout:
        print(f"❌ 오류: 요청 타임아웃 (5분 초과)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 오류: 연결 실패")
        print(f"  - 상세: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 오류: 요청 중 예외 발생")
        print(f"  - 상세: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 오류: JSON 파싱 실패")
        print(f"  - 상세: {str(e)}")
        print(f"  - 응답 내용: {response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ 오류: 예상치 못한 오류 발생")
        print(f"  - 상세: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print(f"\n🚀 OCR Structured API 테스트 시작\n")
    
    success = test_ocr_structured()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ 테스트 완료!")
        print(f"📄 결과 파일: {OUTPUT_JSON}")
    else:
        print("❌ 테스트 실패!")
    print("=" * 80)

