"""
BBox 라벨링 시스템 - 독립 실행 서버
document.jpg에서 드래그로 bbox를 설정하고 텍스트를 라벨링하는 시스템
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 설정
UPLOAD_FOLDER = os.path.dirname(__file__)
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
LABELS_FILE = os.path.join(UPLOAD_FOLDER, 'bbox_labels.json')

# 전역 변수: 현재 라벨링 데이터
labeling_data = {
    'image_file': None,
    'labels': []  # [{'id': 1, 'bbox': [x1, y1, x2, y2], 'text': '라벨 텍스트'}, ...]
}

def load_labels():
    """저장된 라벨 데이터 로드"""
    global labeling_data
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE, 'r', encoding='utf-8') as f:
                labeling_data = json.load(f)
            print(f"[BBoxLabeler] ✅ 라벨 데이터 로드 완료: {len(labeling_data.get('labels', []))}개")
        except Exception as e:
            print(f"[BBoxLabeler] ⚠️ 라벨 로드 실패: {str(e)}")
            labeling_data = {'image_file': None, 'labels': []}

def save_labels():
    """라벨 데이터 저장"""
    try:
        with open(LABELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(labeling_data, f, ensure_ascii=False, indent=2)
        print(f"[BBoxLabeler] ✅ 라벨 데이터 저장 완료: {len(labeling_data.get('labels', []))}개")
        return True
    except Exception as e:
        print(f"[BBoxLabeler] ❌ 라벨 저장 실패: {str(e)}")
        return False

# 서버 시작 시 라벨 로드
load_labels()

@app.route('/')
def index():
    """메인 페이지"""
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BBox 라벨링 시스템</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover {
            background: #45a049;
        }
        
        .btn-secondary {
            background: #2196F3;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #0b7dda;
        }
        
        .btn-danger {
            background: #f44336;
            color: white;
        }
        
        .btn-danger:hover {
            background: #da190b;
        }
        
        .btn-warning {
            background: #ff9800;
            color: white;
        }
        
        .btn-warning:hover {
            background: #e68900;
        }
        
        input[type="file"] {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        .main-content {
            display: flex;
            gap: 20px;
            height: calc(100vh - 200px);
        }
        
        .image-container {
            flex: 1;
            position: relative;
            border: 2px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
            background: #fafafa;
            min-height: 500px;
        }
        
        #imageCanvas {
            display: block;
            max-width: 100%;
            max-height: 100%;
            cursor: crosshair;
        }
        
        .bbox {
            position: absolute;
            border: 2px solid #4CAF50;
            background: rgba(76, 175, 80, 0.1);
            cursor: move;
        }
        
        .bbox.selected {
            border-color: #2196F3;
            background: rgba(33, 150, 243, 0.2);
        }
        
        .bbox-label {
            position: absolute;
            top: -20px;
            left: 0;
            background: #4CAF50;
            color: white;
            padding: 2px 6px;
            font-size: 11px;
            border-radius: 2px;
            white-space: nowrap;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .labels-panel {
            width: 350px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .labels-list {
            flex: 1;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            background: #fafafa;
        }
        
        .label-item {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .label-item:hover {
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .label-item.selected {
            border-color: #2196F3;
            background: #e3f2fd;
        }
        
        .label-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .label-id {
            font-weight: bold;
            color: #4CAF50;
        }
        
        .label-coords {
            font-size: 11px;
            color: #666;
            font-family: monospace;
        }
        
        .label-text {
            width: 100%;
            padding: 6px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
        }
        
        .label-text:focus {
            outline: none;
            border-color: #4CAF50;
        }
        
        .delete-btn {
            background: #f44336;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
        }
        
        .delete-btn:hover {
            background: #da190b;
        }
        
        .status {
            padding: 10px;
            background: #e3f2fd;
            border-radius: 4px;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        .status.success {
            background: #c8e6c9;
            color: #2e7d32;
        }
        
        .status.error {
            background: #ffcdd2;
            color: #c62828;
        }
        
        .empty-state {
            text-align: center;
            color: #999;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📦 BBox 라벨링 시스템</h1>
        
        <div class="controls">
            <input type="file" id="imageInput" accept="image/*">
            <button class="btn-primary" onclick="loadDefaultImage()">기본 이미지 로드 (document.jpg)</button>
            <input type="file" id="jsonInput" accept=".json" style="display: none;" onchange="importJSON(event)">
            <button class="btn-secondary" onclick="document.getElementById('jsonInput').click()">📂 JSON 불러오기</button>
            <button class="btn-secondary" onclick="clearAll()">전체 삭제</button>
            <button class="btn-warning" onclick="exportJSON()">JSON 내보내기</button>
            <button class="btn-primary" onclick="saveLabels()">💾 저장</button>
        </div>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="main-content">
            <div class="image-container">
                <canvas id="imageCanvas"></canvas>
            </div>
            
            <div class="labels-panel">
                <div class="status" id="infoStatus">
                    <strong>📋 라벨 목록</strong> (<span id="labelCount">0</span>개)
                </div>
                <div class="labels-list" id="labelsList">
                    <div class="empty-state">이미지에서 드래그하여 bbox를 생성하세요</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let canvas = document.getElementById('imageCanvas');
        let ctx = canvas.getContext('2d');
        let image = null;
        let imageScale = 1;  // 원본 이미지와 캔버스의 스케일 비율
        let zoomScale = 1.0;  // 확대/축소 스케일 (Ctrl + 스크롤)
        let baseCanvasWidth = 0;  // 기본 캔버스 너비
        let baseCanvasHeight = 0;  // 기본 캔버스 높이
        let panX = 0;  // 이미지 X 오프셋 (팬)
        let panY = 0;  // 이미지 Y 오프셋 (팬)
        let labels = [];
        let selectedLabelId = null;
        let isDrawing = false;
        let startX = 0, startY = 0;
        let currentBbox = null;
        
        // 이미지 로드
        function loadImage(imgSrc) {
            image = new Image();
            image.onload = function() {
                const container = canvas.parentElement;
                const maxWidth = container.clientWidth - 20;
                const maxHeight = container.clientHeight - 20;
                
                let width = image.width;
                let height = image.height;
                
                if (width > maxWidth) {
                    height = (height * maxWidth) / width;
                    width = maxWidth;
                }
                if (height > maxHeight) {
                    width = (width * maxHeight) / height;
                    height = maxHeight;
                }
                
                baseCanvasWidth = width;
                baseCanvasHeight = height;
                canvas.width = width;
                canvas.height = height;
                imageScale = image.width / width;
                zoomScale = 1.0;  // 이미지 로드 시 확대/축소 초기화
                panX = 0;  // 팬 초기화
                panY = 0;  // 팬 초기화
                
                renderImage();
            };
            image.src = imgSrc;
        }
        
        // 이미지 렌더링 (확대/축소 및 팬 적용)
        function renderImage() {
            if (!image) return;
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 확대/축소된 크기 계산
            const scaledWidth = baseCanvasWidth * zoomScale;
            const scaledHeight = baseCanvasHeight * zoomScale;
            
            // 기본 중앙 정렬 오프셋
            const baseOffsetX = (canvas.width - scaledWidth) / 2;
            const baseOffsetY = (canvas.height - scaledHeight) / 2;
            
            // 팬 적용
            const offsetX = baseOffsetX + panX;
            const offsetY = baseOffsetY + panY;
            
            // 이미지 그리기
            ctx.drawImage(image, offsetX, offsetY, scaledWidth, scaledHeight);
            
            renderLabels();
        }
        
        // 기본 이미지 로드
        function loadDefaultImage() {
            fetch('/api/load-image')
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadImage(data.image_url);
                        if (data.labels && data.labels.length > 0) {
                            labels = data.labels;
                            updateLabelsList();
                            renderLabels();
                        }
                        showStatus('이미지 로드 완료', 'success');
                    } else {
                        showStatus('이미지 로드를 찾을 수 없습니다: document.jpg', 'error');
                    }
                });
        }
        
        // 파일 선택
        document.getElementById('imageInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    loadImage(e.target.result);
                    showStatus('이미지 로드 완료', 'success');
                };
                reader.readAsDataURL(file);
            }
        });
        
        // 화면 좌표를 이미지 좌표로 변환
        function screenToImageCoords(screenX, screenY) {
            const rect = canvas.getBoundingClientRect();
            const canvasX = (screenX - rect.left) * (canvas.width / rect.width);
            const canvasY = (screenY - rect.top) * (canvas.height / rect.height);
            
            // 확대/축소 및 오프셋 고려
            const scaledWidth = baseCanvasWidth * zoomScale;
            const scaledHeight = baseCanvasHeight * zoomScale;
            const baseOffsetX = (canvas.width - scaledWidth) / 2;
            const baseOffsetY = (canvas.height - scaledHeight) / 2;
            const offsetX = baseOffsetX + panX;
            const offsetY = baseOffsetY + panY;
            
            // 캔버스 좌표를 확대/축소된 이미지 좌표로 변환
            const imageX = (canvasX - offsetX) / zoomScale;
            const imageY = (canvasY - offsetY) / zoomScale;
            
            return { x: imageX, y: imageY };
        }
        
        // 이미지 좌표를 화면 좌표로 변환
        function imageToScreenCoords(imageX, imageY) {
            const scaledWidth = baseCanvasWidth * zoomScale;
            const scaledHeight = baseCanvasHeight * zoomScale;
            const baseOffsetX = (canvas.width - scaledWidth) / 2;
            const baseOffsetY = (canvas.height - scaledHeight) / 2;
            const offsetX = baseOffsetX + panX;
            const offsetY = baseOffsetY + panY;
            
            return {
                x: imageX * zoomScale + offsetX,
                y: imageY * zoomScale + offsetY
            };
        }
        
        // Ctrl + 스크롤로 확대/축소 (마우스 커서 위치 중심)
        canvas.addEventListener('wheel', function(e) {
            if (!image) return;
            
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                
                // 확대/축소 전 마우스 커서 위치의 이미지 좌표
                const imageCoordsBefore = screenToImageCoords(e.clientX, e.clientY);
                
                // 확대/축소 비율 변경
                const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
                const oldZoomScale = zoomScale;
                zoomScale = Math.max(0.1, Math.min(5.0, zoomScale * zoomFactor));
                
                // 확대/축소 후 같은 이미지 좌표가 마우스 커서 위치에 오도록 팬 조정
                const rect = canvas.getBoundingClientRect();
                const canvasX = (e.clientX - rect.left) * (canvas.width / rect.width);
                const canvasY = (e.clientY - rect.top) * (canvas.height / rect.height);
                
                // 새로운 스케일에서의 오프셋 계산
                const newScaledWidth = baseCanvasWidth * zoomScale;
                const newScaledHeight = baseCanvasHeight * zoomScale;
                const newBaseOffsetX = (canvas.width - newScaledWidth) / 2;
                const newBaseOffsetY = (canvas.height - newScaledHeight) / 2;
                
                // 마우스 커서 위치에 해당 이미지 좌표가 오도록 팬 계산
                panX = canvasX - (imageCoordsBefore.x * zoomScale) - newBaseOffsetX;
                panY = canvasY - (imageCoordsBefore.y * zoomScale) - newBaseOffsetY;
                
                // 이미지 경계 체크 (이미지가 캔버스 밖으로 나가지 않도록)
                const scaledWidth = baseCanvasWidth * zoomScale;
                const scaledHeight = baseCanvasHeight * zoomScale;
                const baseOffsetX = (canvas.width - scaledWidth) / 2;
                const baseOffsetY = (canvas.height - scaledHeight) / 2;
                
                // 팬 제한 (이미지가 캔버스 안에 있도록)
                const maxPanX = Math.max(0, (scaledWidth - canvas.width) / 2);
                const maxPanY = Math.max(0, (scaledHeight - canvas.height) / 2);
                panX = Math.max(-maxPanX, Math.min(maxPanX, panX));
                panY = Math.max(-maxPanY, Math.min(maxPanY, panY));
                
                // 이미지 다시 렌더링
                renderImage();
            }
        });
        
        // 드래그 시작
        canvas.addEventListener('mousedown', function(e) {
            if (!image) return;
            
            const coords = screenToImageCoords(e.clientX, e.clientY);
            const x = coords.x;
            const y = coords.y;
            
            // 기존 bbox 클릭 확인 (화면 좌표 기준)
            let clickedLabel = null;
            for (let label of labels) {
                const [x1, y1, x2, y2] = label.bbox;
                // 원본 이미지 좌표로 변환하여 비교
                const displayCoords1 = imageToScreenCoords(x1 / imageScale, y1 / imageScale);
                const displayCoords2 = imageToScreenCoords(x2 / imageScale, y2 / imageScale);
                
                const rect = canvas.getBoundingClientRect();
                const mouseX = (e.clientX - rect.left) * (canvas.width / rect.width);
                const mouseY = (e.clientY - rect.top) * (canvas.height / rect.height);
                
                const minX = Math.min(displayCoords1.x, displayCoords2.x);
                const maxX = Math.max(displayCoords1.x, displayCoords2.x);
                const minY = Math.min(displayCoords1.y, displayCoords2.y);
                const maxY = Math.max(displayCoords1.y, displayCoords2.y);
                
                if (mouseX >= minX && mouseX <= maxX && mouseY >= minY && mouseY <= maxY) {
                    clickedLabel = label;
                    break;
                }
            }
            
            if (clickedLabel) {
                selectedLabelId = clickedLabel.id;
                updateLabelsList();
                renderImage();
                return;
            }
            
            // 새 bbox 그리기 시작
            isDrawing = true;
            startX = x;
            startY = y;
            selectedLabelId = null;
            updateLabelsList();
        });
        
        // 드래그 중
        canvas.addEventListener('mousemove', function(e) {
            if (!isDrawing || !image) return;
            
            const coords = screenToImageCoords(e.clientX, e.clientY);
            const currentX = coords.x;
            const currentY = coords.y;
            
            renderImage();
            
            // 현재 그리는 bbox 미리보기 (화면 좌표로 변환)
            const screenStart = imageToScreenCoords(startX, startY);
            const screenCurrent = imageToScreenCoords(currentX, currentY);
            
            const x1 = Math.min(screenStart.x, screenCurrent.x);
            const y1 = Math.min(screenStart.y, screenCurrent.y);
            const x2 = Math.max(screenStart.x, screenCurrent.x);
            const y2 = Math.max(screenStart.y, screenCurrent.y);
            
            ctx.strokeStyle = '#ff9800';
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        });
        
        // 드래그 종료
        canvas.addEventListener('mouseup', function(e) {
            if (!isDrawing || !image) return;
            
            isDrawing = false;
            const coords = screenToImageCoords(e.clientX, e.clientY);
            const endX = coords.x;
            const endY = coords.y;
            
            const x1 = Math.min(startX, endX);
            const y1 = Math.min(startY, endY);
            const x2 = Math.max(startX, endX);
            const y2 = Math.max(startY, endY);
            
            // 최소 크기 체크 (이미지 좌표 기준)
            const minSize = 10 / zoomScale;  // 확대/축소에 따라 최소 크기 조정
            if (Math.abs(x2 - x1) < minSize || Math.abs(y2 - y1) < minSize) {
                renderImage();
                return;
            }
            
            // 실제 원본 이미지 좌표로 변환
            const realX1 = x1 * imageScale;
            const realY1 = y1 * imageScale;
            const realX2 = x2 * imageScale;
            const realY2 = y2 * imageScale;
            
            // 새 라벨 추가
            const newId = labels.length > 0 ? Math.max(...labels.map(l => l.id)) + 1 : 1;
            const newLabel = {
                id: newId,
                bbox: [Math.round(realX1), Math.round(realY1), Math.round(realX2), Math.round(realY2)],
                text: ''
            };
            
            labels.push(newLabel);
            selectedLabelId = newId;
            updateLabelsList();
            renderImage();
        });
        
        // 라벨 렌더링
        function renderLabels() {
            if (!image) return;
            
            labels.forEach(label => {
                const [x1, y1, x2, y2] = label.bbox;
                // 원본 이미지 좌표를 캔버스 좌표로 변환
                const canvasX1 = x1 / imageScale;
                const canvasY1 = y1 / imageScale;
                const canvasX2 = x2 / imageScale;
                const canvasY2 = y2 / imageScale;
                
                // 화면 좌표로 변환 (확대/축소 적용)
                const screenCoords1 = imageToScreenCoords(canvasX1, canvasY1);
                const screenCoords2 = imageToScreenCoords(canvasX2, canvasY2);
                
                const displayX1 = Math.min(screenCoords1.x, screenCoords2.x);
                const displayY1 = Math.min(screenCoords1.y, screenCoords2.y);
                const displayX2 = Math.max(screenCoords1.x, screenCoords2.x);
                const displayY2 = Math.max(screenCoords1.y, screenCoords2.y);
                
                const isSelected = label.id === selectedLabelId;
                ctx.strokeStyle = isSelected ? '#2196F3' : '#4CAF50';
                ctx.fillStyle = isSelected ? 'rgba(33, 150, 243, 0.2)' : 'rgba(76, 175, 80, 0.1)';
                ctx.lineWidth = 2;
                
                ctx.fillRect(displayX1, displayY1, displayX2 - displayX1, displayY2 - displayY1);
                ctx.strokeRect(displayX1, displayY1, displayX2 - displayX1, displayY2 - displayY1);
                
                // 라벨 텍스트 표시
                if (label.text) {
                    ctx.fillStyle = '#4CAF50';
                    ctx.font = '12px Arial';
                    ctx.fillText(label.text, displayX1, displayY1 - 5);
                }
            });
        }
        
        // 라벨 목록 업데이트
        function updateLabelsList() {
            const list = document.getElementById('labelsList');
            const count = document.getElementById('labelCount');
            count.textContent = labels.length;
            
            if (labels.length === 0) {
                list.innerHTML = '<div class="empty-state">이미지에서 드래그하여 bbox를 생성하세요</div>';
                return;
            }
            
            list.innerHTML = labels.map(label => {
                const [x1, y1, x2, y2] = label.bbox;
                const isSelected = label.id === selectedLabelId;
                return `
                    <div class="label-item ${isSelected ? 'selected' : ''}" onclick="selectLabel(${label.id})">
                        <div class="label-item-header">
                            <span class="label-id">#${label.id}</span>
                            <span class="label-coords">(${x1}, ${y1}) - (${x2}, ${y2})</span>
                            <button class="delete-btn" onclick="deleteLabel(${label.id}); event.stopPropagation();">삭제</button>
                        </div>
                        <input type="text" class="label-text" value="${label.text || ''}" 
                               placeholder="라벨 텍스트 입력..." 
                               onchange="updateLabelText(${label.id}, this.value)"
                               onclick="event.stopPropagation();">
                    </div>
                `;
            }).join('');
        }
        
        // 라벨 선택
        function selectLabel(id) {
            selectedLabelId = id;
            updateLabelsList();
            renderLabels();
        }
        
        // 라벨 텍스트 업데이트
        function updateLabelText(id, text) {
            const label = labels.find(l => l.id === id);
            if (label) {
                label.text = text;
                renderLabels();
            }
        }
        
        // 라벨 삭제
        function deleteLabel(id) {
            labels = labels.filter(l => l.id !== id);
            if (selectedLabelId === id) {
                selectedLabelId = null;
            }
            updateLabelsList();
            renderLabels();
        }
        
        // 전체 삭제
        function clearAll() {
            if (confirm('모든 라벨을 삭제하시겠습니까?')) {
                labels = [];
                selectedLabelId = null;
                updateLabelsList();
                renderLabels();
            }
        }
        
        // JSON 불러오기
        function importJSON(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const jsonData = JSON.parse(e.target.result);
                    
                    // JSON 구조 확인
                    let loadedLabels = [];
                    if (jsonData.labels && Array.isArray(jsonData.labels)) {
                        loadedLabels = jsonData.labels;
                    } else if (Array.isArray(jsonData)) {
                        loadedLabels = jsonData;
                    } else {
                        showStatus('올바른 JSON 형식이 아닙니다. labels 배열이 필요합니다.', 'error');
                        return;
                    }
                    
                    if (loadedLabels.length === 0) {
                        showStatus('라벨이 없는 JSON 파일입니다.', 'error');
                        return;
                    }
                    
                    // 기존 라벨이 있는지 확인
                    if (labels.length > 0) {
                        const merge = confirm(
                            `기존 라벨 ${labels.length}개가 있습니다.\n` +
                            `불러온 라벨 ${loadedLabels.length}개와 병합하시겠습니까?\n\n` +
                            `확인: 병합 (기존 라벨 유지)\n` +
                            `취소: 덮어쓰기 (기존 라벨 삭제)`
                        );
                        
                        if (merge) {
                            // 병합: ID 충돌 방지를 위해 기존 최대 ID 찾기
                            const maxId = labels.length > 0 ? Math.max(...labels.map(l => l.id)) : 0;
                            
                            // 불러온 라벨의 ID를 조정하여 추가
                            loadedLabels.forEach(label => {
                                const newId = maxId + label.id;
                                labels.push({
                                    id: newId,
                                    bbox: label.bbox,
                                    text: label.text || ''
                                });
                            });
                            
                            showStatus(`JSON 불러오기 완료: ${loadedLabels.length}개 라벨 병합됨 (총 ${labels.length}개)`, 'success');
                        } else {
                            // 덮어쓰기
                            labels = loadedLabels.map(label => ({
                                id: label.id,
                                bbox: label.bbox,
                                text: label.text || ''
                            }));
                            
                            showStatus(`JSON 불러오기 완료: ${loadedLabels.length}개 라벨 로드됨`, 'success');
                        }
                    } else {
                        // 기존 라벨이 없으면 그대로 로드
                        labels = loadedLabels.map(label => ({
                            id: label.id,
                            bbox: label.bbox,
                            text: label.text || ''
                        }));
                        
                        showStatus(`JSON 불러오기 완료: ${loadedLabels.length}개 라벨 로드됨`, 'success');
                    }
                    
                    // ID 정렬 및 재할당 (선택사항)
                    labels.sort((a, b) => a.id - b.id);
                    
                    // 라벨 목록 업데이트 및 렌더링
                    updateLabelsList();
                    renderImage();
                    
                    // 파일 입력 초기화 (같은 파일을 다시 선택할 수 있도록)
                    event.target.value = '';
                    
                } catch (error) {
                    showStatus('JSON 파일 읽기 오류: ' + error.message, 'error');
                    console.error('JSON 파싱 오류:', error);
                }
            };
            reader.readAsText(file);
        }
        
        // JSON 내보내기
        function exportJSON() {
            const data = {
                image_file: 'document.jpg',
                labels: labels,
                export_date: new Date().toISOString()
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bbox_labels.json';
            a.click();
            URL.revokeObjectURL(url);
            
            showStatus('JSON 파일 다운로드 완료', 'success');
        }
        
        // 라벨 저장
        function saveLabels() {
            fetch('/api/save-labels', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    image_file: 'document.jpg',
                    labels: labels
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showStatus('라벨 저장 완료!', 'success');
                } else {
                    showStatus('저장 실패: ' + data.error, 'error');
                }
            })
            .catch(err => {
                showStatus('저장 오류: ' + err.message, 'error');
            });
        }
        
        // 상태 메시지 표시
        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
            setTimeout(() => {
                status.style.display = 'none';
            }, 3000);
        }
        
        // 페이지 로드 시 기본 이미지 로드
        window.addEventListener('load', function() {
            loadDefaultImage();
        });
    </script>
</body>
</html>
    """
    return render_template_string(html_content)

@app.route('/document.jpg')
def serve_image():
    """이미지 파일 제공"""
    image_path = os.path.join(UPLOAD_FOLDER, 'document.jpg')
    if os.path.exists(image_path):
        return send_from_directory(UPLOAD_FOLDER, 'document.jpg')
    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/load-image')
def load_image():
    """이미지 및 저장된 라벨 로드"""
    image_path = os.path.join(UPLOAD_FOLDER, 'document.jpg')
    if os.path.exists(image_path):
        return jsonify({
            'success': True,
            'image_url': '/document.jpg',
            'labels': labeling_data.get('labels', [])
        })
    return jsonify({
        'success': False,
        'error': 'document.jpg 파일을 찾을 수 없습니다.'
    })

@app.route('/api/save-labels', methods=['POST'])
def save_labels_api():
    """라벨 저장 API"""
    try:
        data = request.json
        global labeling_data
        
        labeling_data = {
            'image_file': data.get('image_file', 'document.jpg'),
            'labels': data.get('labels', []),
            'last_updated': datetime.now().isoformat()
        }
        
        if save_labels():
            return jsonify({
                'success': True,
                'message': f'{len(labeling_data["labels"])}개 라벨 저장 완료'
            })
        else:
            return jsonify({
                'success': False,
                'error': '파일 저장 실패'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/get-labels')
def get_labels():
    """저장된 라벨 조회"""
    return jsonify(labeling_data)

if __name__ == '__main__':
    print("="*80)
    print("📦 BBox 라벨링 시스템 시작")
    print("="*80)
    print(f"📁 작업 폴더: {UPLOAD_FOLDER}")
    print(f"📄 이미지 파일: {os.path.join(UPLOAD_FOLDER, 'document.jpg')}")
    print(f"💾 라벨 파일: {LABELS_FILE}")
    print("="*80)
    print("🌐 브라우저에서 http://localhost:5001 접속")
    print("="*80)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

