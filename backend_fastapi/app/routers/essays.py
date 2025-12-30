from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select

from ..db import get_session
from ..llm import grade_essay
from ..models import ConversationEvent, EssayResult, EssaySubmission

router = APIRouter(prefix="/v1/essays", tags=["essays"])


class EssayGradeRequest(BaseModel):
    ocr_text: str
    language: str = "en"
    session_id: str = "anonymous"
    conversation_id: str | None = None
    request_id: str | None = None


class EssayGradeResponse(BaseModel):
    submission_id: int
    session_id: str
    conversation_id: str
    request_id: str
    score: int
    result: dict[str, Any]


class EssayGetResponse(BaseModel):
    submission_id: int
    session_id: str
    conversation_id: str
    request_id: str
    ocr_text: str
    language: str
    score: int | None
    result: dict[str, Any]


def _append_event(
    session: Session,
    *,
    session_id: str,
    conversation_id: str,
    request_id: str,
    event_type: str,
    payload: dict[str, Any],
    ts: int,
    final: bool = False,
) -> int:
    max_seq = session.exec(
        select(ConversationEvent.seq)
        .where(ConversationEvent.conversation_id == conversation_id)
        .order_by(col(ConversationEvent.seq).desc())
    ).first()
    next_seq = int(max_seq or 0) + 1
    session.add(
        ConversationEvent(
            session_id=session_id,
            conversation_id=conversation_id,
            seq=next_seq,
            type=event_type,
            ts=ts,
            request_id=request_id,
            final=bool(final),
            payload=dict(payload or {}),
        )
    )
    return next_seq


@router.post("/grade", response_model=EssayGradeResponse)
async def grade(req: EssayGradeRequest, session: Session = Depends(get_session)) -> EssayGradeResponse:
    ocr_text = (req.ocr_text or "").strip()
    if not ocr_text:
        raise HTTPException(status_code=400, detail="ocr_text is required")

    session_id = (req.session_id or "anonymous").strip() or "anonymous"
    conversation_id = (req.conversation_id or f"conv_{uuid.uuid4().hex[:8]}").strip()
    request_id = (req.request_id or f"req_{uuid.uuid4().hex[:10]}").strip()
    language = (req.language or "").strip() or "en"
    ts = int(time.time() * 1000)

    submission = EssaySubmission(
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        ocr_text=ocr_text,
        language=language,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    submission_id = submission.id
    if submission_id is None:
        raise HTTPException(status_code=500, detail="failed to create submission")

    _append_event(
        session,
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        event_type="TASK_STARTED",
        payload={"task": "essay_grade", "submission_id": submission_id, "language": language},
        ts=ts,
        final=False,
    )
    session.commit()

    result = await grade_essay(ocr_text=ocr_text, language=language)
    score = int(result.get("score") or 0)

    essay_result = EssayResult(submission_id=int(submission_id), score=score, result=result)
    session.add(essay_result)

    _append_event(
        session,
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        event_type="ANALYSIS_RESULT",
        payload={
            "kind": "essay_grade",
            "submission_id": submission_id,
            "score": score,
            "result": result,
        },
        ts=ts,
        final=False,
    )
    _append_event(
        session,
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        event_type="TASK_FINISHED",
        payload={"ok": True, "submission_id": submission_id},
        ts=ts,
        final=True,
    )

    session.commit()

    return EssayGradeResponse(
        submission_id=int(submission_id),
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        score=score,
        result=result,
    )


@router.get("/{submission_id}", response_model=EssayGetResponse)
def get_essay(submission_id: int, session: Session = Depends(get_session)) -> EssayGetResponse:
    submission = session.get(EssaySubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")

    sid = submission.id
    if sid is None:
        raise HTTPException(status_code=500, detail="invalid submission")

    essay_result = session.exec(
        select(EssayResult)
        .where(EssayResult.submission_id == submission_id)
        .order_by(col(EssayResult.id).desc())
    ).first()

    return EssayGetResponse(
        submission_id=int(sid),
        session_id=str(submission.session_id or ""),
        conversation_id=str(submission.conversation_id or ""),
        request_id=str(submission.request_id or ""),
        ocr_text=str(submission.ocr_text or ""),
        language=str(submission.language or ""),
        score=int(essay_result.score) if essay_result is not None and essay_result.score is not None else None,
        result=dict(essay_result.result or {}) if essay_result is not None else {},
    )
