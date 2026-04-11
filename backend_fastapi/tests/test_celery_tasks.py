"""Celery 任务测试"""

from __future__ import annotations

import os

os.environ.setdefault("CELERY_DEMO_EAGER", "1")

from app.infrastructure.messaging.tasks import grade_essay_task, generate_daily_vocab_task


def test_grade_essay_task_eager():
    result = grade_essay_task.run(essay_id="essay_123", content="Hello world")
    assert result["essay_id"] == "essay_123"
    assert "score" in result


def test_generate_daily_vocab_task_eager():
    result = generate_daily_vocab_task.run(user_id="user_456")
    assert result["user_id"] == "user_456"
    assert isinstance(result["words"], list)
