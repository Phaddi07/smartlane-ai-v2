from pathlib import Path
from uuid import uuid4
import shutil
import traceback

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from smartlane.pipeline import SmartLanePipeline


app = FastAPI(
    title="SmartLane AI API",
    version="1.0.0",
    description="Dashcam video analysis API",
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@app.get("/")
def root():
    return {"message": "SmartLane AI API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {extension}",
        )

    processing_id = str(uuid4())
    video_path = UPLOAD_DIR / f"{processing_id}{extension}"

    try:
        with video_path.open("wb") as destination:
            shutil.copyfileobj(file.file, destination)

        pipeline = SmartLanePipeline(video_path)
        report = pipeline.run()

        return {
            "processing_id": processing_id,
            "status": "completed",
            "report": jsonable_encoder(report),
        }

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {str(exc)}",
        ) from exc

    finally:
        file.file.close()
