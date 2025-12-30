import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("language-learning-service")

app = FastAPI(title="Language Learning AI Microservice", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "Language Learning AI Microservice"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

from routers import asr, tts
app.include_router(asr.router, prefix="/asr", tags=["ASR"])
app.include_router(tts.router, prefix="/tts", tags=["TTS"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
