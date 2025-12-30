from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import edge_tts
import tempfile
import os
from fastapi.responses import FileResponse

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"

@router.post("/generate")
async def generate_speech(request: TTSRequest):
    try:
        communicate = edge_tts.Communicate(request.text, request.voice)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
            
        await communicate.save(tmp_path)
        
        return FileResponse(tmp_path, media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
