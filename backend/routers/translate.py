from fastapi import APIRouter
from pydantic import BaseModel
from services.translation_service import translate_text

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


@router.post("/translate")
def translate(req: TranslateRequest):
    return {"translated_text": translate_text(req.text, req.target_lang)}
