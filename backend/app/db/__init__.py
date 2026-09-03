"""Database access layer (Supabase / Postgres).

The DB is **optional**. When ``DATABASE_URL`` is unset the whole application
still runs -- the port resolver falls back to the bundled CSV and the sea-route
cache lives in-process. This keeps local dev, CI and the current Render
deployment working with zero configuration while the global / live-monitoring
build (which needs persistence) comes online.

    DATABASE_URL   postgresql://user:pass@host:5432/postgres   (Supabase)
                   sqlite+pysqlite:///./freightsight.db        (local)
                   (unset)                                     -> no DB

Set ``FREIGHTSIGHT_DB_ECHO=1`` to log SQL.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger("freightsight.db")

_RAW_URL = os.getenv("DATABASE_URL", "").strip()
_ECHO = os.getenv("FREIGHTSIGHT_DB_ECHO", "").strip() in {"1", "true", "yes"}


def normalise_url(url: str) -> str:
    """Coerce a plain ``postgres(ql)://`` DSN to the psycopg-v3 driver form.

    Supabase / Heroku hand out ``postgres://`` or ``postgresql://``; SQLAlchemy 2
    + psycopg 3 wants an explicit ``postgresql+psycopg://``.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL: str | None = normalise_url(_RAW_URL) if _RAW_URL else None
DB_ENABLED: bool = DATABASE_URL is not None

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def _build_engine(url: str) -> Engine:
    kwargs: dict = {"echo": _ECHO, "future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # small pool -- the API is read-mostly, the worker runs elsewhere
        kwargs.update(pool_size=5, max_overflow=5, pool_recycle=1800)
    return create_engine(url, **kwargs)


def engine() -> Engine:
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("engine() called but DATABASE_URL is not set")
        _engine = _build_engine(DATABASE_URL)
        log.info("database engine ready (%s)", _engine.url.render_as_string(hide_password=True))
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=engine(), expire_on_commit=False, future=True)
    return _Session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session: commit on success, rollback on error."""
    s = get_sessionmaker()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def healthcheck() -> dict:
    """Cheap connectivity probe for /api/system/health."""
    if not DB_ENABLED:
        return {"enabled": False}
    from sqlalchemy import text

    try:
        with engine().connect() as c:
            c.execute(text("SELECT 1"))
        return {"enabled": True, "reachable": True}
    except Exception as exc:  # pragma: no cover - network dependent
        return {"enabled": True, "reachable": False, "error": str(exc)[:200]}
