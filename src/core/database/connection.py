from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

from src.app.config import settings


class Base(DeclarativeBase):
    pass


_db_url = settings.database.get_url()
_is_sqlite = "sqlite" in _db_url

engine = create_engine(
    _db_url,
    echo=settings.database.echo,
    pool_pre_ping=settings.database.pool_pre_ping,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=StaticPool if _is_sqlite else None,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if _is_sqlite:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


_web_session: Session | None = None


def get_web_session() -> Session:
    global _web_session
    if _web_session is None or not _web_session.is_active:
        _web_session = SessionLocal()
    return _web_session


def close_web_session() -> None:
    global _web_session
    if _web_session is not None:
        _web_session.close()
        _web_session = None


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    import src.core.models  # noqa: F401
    import src.core.models.hr_models  # noqa: F401
    import src.core.models.marketing_models  # noqa: F401
    import src.core.models.maintenance_models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
