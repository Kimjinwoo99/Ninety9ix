# KT-CS Backend

OCR 및 문서 처리를 위한 Flask 백엔드 서버입니다.

## 설치

```bash
cd backend
pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

서버는 기본적으로 `http://localhost:5000`에서 실행됩니다.

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |
| POST | `/api/log` | 프론트엔드 로그 수신 |
| POST | `/api/ocr` | OCR 처리 |
| POST | `/api/checkbox/process` | 체크박스 처리 |

## 환경

- Python 3.8+
- Flask 3.0.0
- EasyOCR
- OpenCV
