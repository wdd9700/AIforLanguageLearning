from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import tempfile
# from faster_whisper import WhisperModel

router = APIRouter()

# model = WhisperModel("medium", device="cuda", compute_type="float16")

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), language: str = "en"):
    try:
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # segments, info = model.transcribe(tmp_path, language=language)
        # text = "".join([segment.text for segment in segments])
        
        # Mock response for now
        text = "This is a mock transcription from the Python microservice."
        
        os.unlink(tmp_path)
        return {"text": text, "language": language}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
