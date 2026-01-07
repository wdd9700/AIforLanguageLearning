from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, col, select

from ..db import get_session
from ..llm import generate_vocab_fields, grade_essay
from ..models import ConversationEvent, EssayResult, EssaySubmission, UserVocabQuery

router = APIRouter(tags=["compat-v5"])


# -----------------------------
# /api/query/*
# -----------------------------


class V5VocabQueryRequest(BaseModel):
    word: str


@router.post("/api/query/vocabulary")
async def v5_query_vocabulary(req: V5VocabQueryRequest, session: Session = Depends(get_session)) -> dict:
    term = (req.word or "").strip()
    if not term:
        return {"success": False, "error": "word is required"}

    fields = await generate_vocab_fields(term)
    meaning = (fields.get("meaning") or "").strip()
    example = (fields.get("example") or "").strip()
    example_translation = (fields.get("example_translation") or "").strip()

    defs: list[dict[str, Any]] = []
    raw_defs = fields.get("definitions")
    if isinstance(raw_defs, list) and raw_defs:
        for d in raw_defs:
            if not isinstance(d, dict):
                continue
            defs.append(
                {
                    "meaning": str(d.get("meaning") or "").strip(),
                    "example": str(d.get("example") or "").strip(),
                    "exampleTranslation": str(d.get("example_translation") or "").strip(),
                }
            )
        defs = [d for d in defs if d.get("meaning") or d.get("example") or d.get("exampleTranslation")]

    legacy_text = f"释义：{meaning or '暂无'}\n例句：{example or '暂无'}"
    if example_translation:
        legacy_text += f"\n例句翻译：{example_translation}"

    # v5 期望 VocabularyResult
    if defs:
        data = {
            "word": term,
            "definitions": defs,
            "meaning": defs[0].get("meaning") or meaning or legacy_text,
        }
    else:
        data = {
            "word": term,
            "definitions": [
                {
                    "meaning": meaning or legacy_text,
                    "example": example,
                    "exampleTranslation": example_translation,
                }
            ],
            # legacy fields
            "meaning": meaning or legacy_text,
        }

    # 记一条查询历史（用于 stats）
    session.add(UserVocabQuery(session_id="", conversation_id="", term=term, source="manual", result=legacy_text))
    session.commit()

    return {"success": True, "data": data}


class V5OcrQueryRequest(BaseModel):
    image: str


@router.post("/api/query/ocr")
async def v5_query_ocr(_: V5OcrQueryRequest) -> dict:
    # P0：FastAPI 侧暂未实现 OCR。
    return {"success": False, "error": "OCR not implemented in FastAPI yet"}


# -----------------------------
# /api/essay/*
# -----------------------------


class V5EssayCorrectRequest(BaseModel):
    text: str | None = None
    image: str | None = None
    language: str = "english"


@router.post("/api/essay/correct")
async def v5_essay_correct(req: V5EssayCorrectRequest, session: Session = Depends(get_session)) -> dict:
    # P0：仅支持纯文本批改；图片 OCR 先返回明确错误。
    if req.image and not req.text:
        return {"success": False, "error": "OCR essay correction not implemented in FastAPI yet"}

    text = (req.text or "").strip()
    if not text:
        return {"success": False, "error": "text is required"}

    language = (req.language or "").strip() or "english"

    # 复用现有 grade_essay（返回 score/feedback/errors/suggestions/rewritten）
    result = await grade_essay(ocr_text=text, language=language)
    total = int(result.get("score") or 0)
    total = max(0, min(100, total))

    scores_obj = result.get("scores")
    if isinstance(scores_obj, dict):
        def _safe_score(key: str) -> int:
            try:
                v = int(scores_obj.get(key, total))
            except Exception:
                v = total
            return max(0, min(100, v))

        scores = {
            "vocabulary": _safe_score("vocabulary"),
            "grammar": _safe_score("grammar"),
            "fluency": _safe_score("fluency"),
            "logic": _safe_score("logic"),
            "content": _safe_score("content"),
            "structure": _safe_score("structure"),
            "total": _safe_score("total"),
        }
        total = scores["total"]
    else:
        scores = {
            "vocabulary": total,
            "grammar": total,
            "fluency": total,
            "logic": total,
            "content": total,
            "structure": total,
            "total": total,
        }

    raw_suggestions = result.get("suggestions")
    suggestions = [s for s in (raw_suggestions if isinstance(raw_suggestions, list) else []) if isinstance(s, str) and s.strip()]

    raw_questions = result.get("questions")
    questions = [q for q in (raw_questions if isinstance(raw_questions, list) else []) if isinstance(q, str) and q.strip()]

    raw_improvements = result.get("improvements")
    improvements: list[str] = [
        s
        for s in (raw_improvements if isinstance(raw_improvements, list) else [])
        if isinstance(s, str) and s.strip()
    ]
    if not improvements:
        raw_errors = result.get("errors")
        if isinstance(raw_errors, list):
            for e in raw_errors:
                if isinstance(e, str) and e.strip():
                    improvements.append(e.strip())
                    continue
                if isinstance(e, dict):
                    msg = str(e.get("message") or "").strip()
                    sug = str(e.get("suggestion") or "").strip()
                    span = str(e.get("span") or "").strip()
                    parts = [p for p in [msg, sug] if p]
                    improvement_text = "；".join(parts)
                    if span:
                        improvement_text = f"{span}: {improvement_text}" if improvement_text else span
                    if improvement_text:
                        improvements.append(improvement_text)

    # 兼容 v5 的 EssayCorrectionResult
    data = {
        "original": text,
        "correction": str(result.get("rewritten") or ""),
        "scores": scores,
        "feedback": str(result.get("feedback") or ""),
        "suggestions": suggestions,
        "questions": questions,
        "improvements": improvements,
        "evaluation": str(result.get("evaluation") or ""),
    }

    # 写入 essay 表（用于 stats；也方便后续做历史/分析）
    session_id = ""
    conversation_id = f"conv_essay_{uuid.uuid4().hex[:8]}"
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    ts = int(time.time() * 1000)

    submission = EssaySubmission(
        session_id=session_id,
        conversation_id=conversation_id,
        request_id=request_id,
        ocr_text=text,
        language=language,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    if submission.id is not None:
        session.add(EssayResult(submission_id=int(submission.id), score=total, result=result))

        # events for replay/debug
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
                type="ANALYSIS_RESULT",
                ts=ts,
                request_id=request_id,
                final=False,
                payload={"kind": "essay_grade", "score": total, "result": result},
            )
        )
        session.commit()

    return {"success": True, "data": data}


# -----------------------------
# /api/learning/*
# -----------------------------


@router.get("/api/learning/stats")
async def v5_learning_stats(session: Session = Depends(get_session)) -> dict:
    vocab = len(list(session.exec(select(UserVocabQuery.id))))
    essay = len(list(session.exec(select(EssaySubmission.id))))

    # voice/dialogue: best-effort count from conversation_events
    started = list(session.exec(select(ConversationEvent).where(ConversationEvent.type == "TASK_STARTED")))
    dialogue = sum(1 for e in started if isinstance(e.payload, dict) and e.payload.get("task") == "voice_audio")

    analysis = len(list(session.exec(select(ConversationEvent.id).where(ConversationEvent.type == "ANALYSIS_RESULT"))))

    return {"success": True, "data": {"vocabulary": vocab, "essay": essay, "dialogue": dialogue, "analysis": analysis}}


class V5AnalyzeRequest(BaseModel):
    dimension: str


@router.post("/api/learning/analyze")
async def v5_learning_analyze(req: V5AnalyzeRequest, session: Session = Depends(get_session)) -> dict:
    dim = (req.dimension or "").strip() or "vocabulary"

    # P0：先返回稳定结构（前端图表可渲染），后续再接入真实分析模型。
    stats = (await v5_learning_stats(session))["data"]
    base = int(min(100, max(0, (stats.get("vocabulary", 0) + stats.get("essay", 0) + stats.get("dialogue", 0)))))

    data = {
        "dimension": dim,
        "score": max(10, min(95, base)),
        "trend": 0,
        "insights": [
            f"当前维度：{dim}",
            "FastAPI 分析模块尚在迁移中（P0 先返回可渲染结构）",
        ],
        "recommendations": [
            "继续完成更多练习以积累数据",
            "后续将接入分析模型生成个性化建议",
        ],
        "visualization": {
            "type": "bar",
            "title": "Learning Overview",
            "labels": ["vocabulary", "essay", "dialogue", "analysis"],
            "datasets": [{"label": "count", "data": [stats["vocabulary"], stats["essay"], stats["dialogue"], stats["analysis"]]}],
        },
    }

    return {"success": True, "data": data}
