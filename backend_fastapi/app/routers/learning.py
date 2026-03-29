from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import ConversationEvent, EssaySubmission, UserVocabQuery

router = APIRouter(prefix="/v1/learning", tags=["learning"])


class LearningStats(BaseModel):
    vocabulary: int
    essay: int
    dialogue: int
    analysis: int


class LearningAnalyzeRequest(BaseModel):
    dimension: str


class LearningAnalyzeResult(BaseModel):
    dimension: str
    score: int
    trend: int
    insights: list[str]
    recommendations: list[str]
    visualization: dict


def _calc_learning_stats(session: Session) -> LearningStats:
    vocab = len(list(session.exec(select(UserVocabQuery.id))))
    essay = len(list(session.exec(select(EssaySubmission.id))))

    started = list(session.exec(select(ConversationEvent).where(ConversationEvent.type == "TASK_STARTED")))
    dialogue = sum(1 for e in started if isinstance(e.payload, dict) and e.payload.get("task") == "voice_audio")

    analysis = len(list(session.exec(select(ConversationEvent.id).where(ConversationEvent.type == "ANALYSIS_RESULT"))))

    return LearningStats(vocabulary=vocab, essay=essay, dialogue=dialogue, analysis=analysis)


@router.get("/stats", response_model=LearningStats)
async def learning_stats(session: Session = Depends(get_session)) -> LearningStats:
    return _calc_learning_stats(session)


@router.post("/analyze", response_model=LearningAnalyzeResult)
async def learning_analyze(req: LearningAnalyzeRequest, session: Session = Depends(get_session)) -> LearningAnalyzeResult:
    dim = (req.dimension or "").strip() or "vocabulary"

    stats = _calc_learning_stats(session)
    base = int(min(100, max(0, (stats.vocabulary + stats.essay + stats.dialogue))))

    return LearningAnalyzeResult(
        dimension=dim,
        score=max(10, min(95, base)),
        trend=0,
        insights=[
            f"当前维度：{dim}",
            "FastAPI 分析模块为轻量实现，后续可接入更细粒度分析模型",
        ],
        recommendations=[
            "继续完成更多练习以积累数据",
            "结合词汇与作文训练提高综合表现",
        ],
        visualization={
            "type": "bar",
            "title": "Learning Overview",
            "labels": ["vocabulary", "essay", "dialogue", "analysis"],
            "datasets": [
                {
                    "label": "count",
                    "data": [stats.vocabulary, stats.essay, stats.dialogue, stats.analysis],
                }
            ],
        },
    )
