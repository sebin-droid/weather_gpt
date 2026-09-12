from fastapi import APIRouter, UploadFile, File, HTTPException
from services.speech_service import speech_to_text

router = APIRouter()

@router.post("/speech-to-text")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        transcription = speech_to_text(audio_bytes, filename=file.filename or "audio.wav")
        return {"transcript": transcription}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))