"""Alembic environment.

Resolves the database URL from (in order):
  1. ``-x db_url=...`` passed on the command line
  2. the ``DATABASE_URL`` environment variable (normalised to the psycopg driver)

Run offline with ``alembic upgrade head --sql`` to just emit DDL.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db import DATABASE_URL, normalise_url
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    x = context.get_x_argument(as_dictionary=True)
    if x.get("db_url"):
        return normalise_url(x["db_url"])
    if DATABASE_URL:
        return DATABASE_URL
    raise RuntimeError(
        "No database URL: pass -x db_url=... or set DATABASE_URL before running alembic."
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
