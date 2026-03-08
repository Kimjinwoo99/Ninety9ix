# checkbox_api.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from detect import detect_checkboxes  
import tempfile

app = FastAPI()

@app.post("/detect-checkbox")
async def detect_checkbox(
    file: UploadFile = File(...),
    doc_type: str = Form("가입신청서_v1")
):
    try:
        suffix = ".jpg"
        if file.filename and "." in file.filename:
            suffix = "." + file.filename.rsplit(".", 1)[1]

        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        data = detect_checkboxes(source=tmp_path)

        checkboxes = []
        if data:
            for item in data:
                cls = item["class"]
                x1, y1, x2, y2 = item["box"]
                checkboxes.append({
                    "class": cls,
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                })

        return JSONResponse({
            "success": True,
            "doc_type": doc_type,
            "checkboxes": checkboxes
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
