from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..llm import generate_definition, generate_vocab_fields
from ..models import PublicVocabEntry, UserVocabQuery
from ..ocr import ocr_image_base64

router = APIRouter(prefix="/v1/vocab", tags=["vocab"])


class VocabLookupRequest(BaseModel):
    term: str
    source: Literal["manual", "ocr"] = "manual"
    session_id: str = ""
    conversation_id: str = ""


class VocabLookupResponse(BaseModel):
    term: str
    definition: str
    from_public_vocab: bool


class VocabLookupOcrRequest(BaseModel):
    image: str
    language: str = "english"
    session_id: str = ""
    conversation_id: str = ""


class VocabLookupOcrResponse(BaseModel):
    term: str
    ocr_text: str
    meaning: str
    example: str
    example_translation: str


@router.post("/lookup", response_model=VocabLookupResponse)
async def lookup_vocab(
    req: VocabLookupRequest,
    session: Session = Depends(get_session),
) -> VocabLookupResponse:
    term = (req.term or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="term is required")

    entry = session.exec(select(PublicVocabEntry).where(PublicVocabEntry.term == term)).first()

    if entry is not None and entry.definition:
        definition = entry.definition
        from_public_vocab = True
    else:
        definition = await generate_definition(term)
        from_public_vocab = False

    session.add(
        UserVocabQuery(
            session_id=req.session_id,
            conversation_id=req.conversation_id,
            term=term,
            source=req.source,
            result=definition,
        )
    )
    session.commit()

    return VocabLookupResponse(term=term, definition=definition, from_public_vocab=from_public_vocab)


@router.post("/lookup-ocr", response_model=VocabLookupOcrResponse)
async def lookup_vocab_ocr(
    req: VocabLookupOcrRequest,
    session: Session = Depends(get_session),
) -> VocabLookupOcrResponse:
    ocr_text = ocr_image_base64(req.image, language=req.language)
    if not ocr_text:
        raise HTTPException(status_code=400, detail="OCR failed or empty text")

    term = ocr_text.splitlines()[0].strip() if ocr_text.splitlines() else ocr_text.strip()
    if not term:
        raise HTTPException(status_code=400, detail="OCR text is empty")

    fields = await generate_vocab_fields(term)
    meaning = str(fields.get("meaning") or "").strip()
    example = str(fields.get("example") or "").strip()
    example_translation = str(fields.get("example_translation") or "").strip()

    if not meaning:
        definition = await generate_definition(term)
        if "\n" in definition:
            lines = [ln.strip() for ln in definition.splitlines() if ln.strip()]
            if lines:
                meaning = lines[0].removeprefix("释义：").strip() or meaning
            if len(lines) > 1:
                example = lines[1].removeprefix("例句：").strip() or example

    session.add(
        UserVocabQuery(
            session_id=req.session_id,
            conversation_id=req.conversation_id,
            term=term,
            source="ocr",
            result=meaning or example or "",
        )
    )
    session.commit()

    return VocabLookupOcrResponse(
        term=term,
        ocr_text=ocr_text,
        meaning=meaning or "暂无",
        example=example,
        example_translation=example_translation,
    )
