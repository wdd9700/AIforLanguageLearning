from __future__ import annotations

from typing import Any

from sqlmodel import Session, col, select

from ..db import get_engine
from ..domain.models import LearningPath, LearningRecord


def create_record(
    user_id: int,
    record_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> LearningRecord:
    from datetime import datetime

    record = LearningRecord(
        user_id=user_id,
        type=record_type,
        content=content,
        meta_data=metadata or {},
        created_at=datetime.utcnow(),
    )
    with Session(get_engine()) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def get_records_by_user_and_type(
    user_id: int, record_type: str, limit: int = 50
) -> list[LearningRecord]:
    with Session(get_engine()) as session:
        return list(
            session.exec(
                select(LearningRecord)
                .where(LearningRecord.user_id == user_id)
                .where(LearningRecord.type == record_type)
                .order_by(col(LearningRecord.created_at).desc())
                .limit(limit)
            ).all()
        )


def create_path(user_id: int, title: str, description: str, milestones: list[Any]) -> LearningPath:
    from datetime import datetime

    now = datetime.utcnow()
    path = LearningPath(
        user_id=user_id,
        title=title,
        description=description,
        milestones=milestones,
        status="active",
        progress=0,
        created_at=now,
        updated_at=now,
    )
    with Session(get_engine()) as session:
        session.add(path)
        session.commit()
        session.refresh(path)
        return path


def get_active_path(user_id: int) -> LearningPath | None:
    with Session(get_engine()) as session:
        return session.exec(
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .where(LearningPath.status == "active")
            .order_by(col(LearningPath.created_at).desc())
        ).first()


def update_path_progress(path_id: int, progress: int) -> None:
    from datetime import datetime

    with Session(get_engine()) as session:
        path = session.get(LearningPath, path_id)
        if path:
            path.progress = progress
            path.updated_at = datetime.utcnow()
            session.add(path)
            session.commit()
