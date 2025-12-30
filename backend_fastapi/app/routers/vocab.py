from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..llm import generate_definition
from ..models import PublicVocabEntry, UserVocabQuery

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
