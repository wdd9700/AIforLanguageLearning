"""Celery 异步任务定义"""

from __future__ import annotations

import logging
from typing import Any

from .celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def grade_essay_task(self, essay_id: str, content: str) -> dict[str, Any]:
    """作文批改异步任务"""
    try:
        # 占位：后续接入真实批改逻辑
        result = {"essay_id": essay_id, "score": 85, "feedback": "Good job!"}
        logger.info(f"Graded essay {essay_id}")
        return result
    except Exception as exc:
        logger.error(f"grade_essay_task error: {exc}")
        raise self.retry(exc=exc, countdown=60)


@app.task(bind=True, max_retries=3)
def generate_daily_vocab_task(self, user_id: str) -> dict[str, Any]:
    """每日词汇生成异步任务"""
    try:
        result = {"user_id": user_id, "words": ["apple", "banana", "cherry"]}
        logger.info(f"Generated daily vocab for user {user_id}")
        return result
    except Exception as exc:
        logger.error(f"generate_daily_vocab_task error: {exc}")
        raise self.retry(exc=exc, countdown=60)
