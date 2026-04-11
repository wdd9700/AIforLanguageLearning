"""任务投递路由"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.messaging.celery_app import app as celery_app
from app.infrastructure.messaging.tasks import generate_daily_vocab_task, grade_essay_task

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class EssayTaskRequest(BaseModel):
    essay_id: str
    content: str


class VocabTaskRequest(BaseModel):
    user_id: str


class TaskResponse(BaseModel):
    task_id: str | None
    status: str


@router.post("/essay", response_model=TaskResponse)
async def submit_essay_task(req: EssayTaskRequest) -> TaskResponse:
    if celery_app is None:
        raise HTTPException(status_code=503, detail="Celery not available")
    result = grade_essay_task.delay(req.essay_id, req.content)
    return TaskResponse(task_id=result.id, status="submitted")


@router.post("/vocab", response_model=TaskResponse)
async def submit_vocab_task(req: VocabTaskRequest) -> TaskResponse:
    if celery_app is None:
        raise HTTPException(status_code=503, detail="Celery not available")
    result = generate_daily_vocab_task.delay(req.user_id)
    return TaskResponse(task_id=result.id, status="submitted")
