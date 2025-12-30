from __future__ import annotations

from typing import Generator, Optional

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from .settings import settings


_engine = None


def _create_sqlite_engine(database_url: str):
    connect_args = {"check_same_thread": False}

    # 说明：
    # - sqlite:///:memory: 在多连接场景会丢数据；测试里可用 StaticPool 保持同一连接
    # - 文件型 sqlite 不需要 StaticPool
    if database_url.endswith(":memory:"):
        return create_engine(database_url, connect_args=connect_args, poolclass=StaticPool)

    return create_engine(database_url, connect_args=connect_args)


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_sqlite_engine(settings.database_url)
    return _engine


def override_engine_for_tests(engine) -> None:
    global _engine
    _engine = engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
