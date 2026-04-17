"""Alembic environment for BookCabinet.

We do not use SQLAlchemy models here — migrations are raw SQL applied to the
SQLite database whose path is taken from `bookcabinet.config.DATABASE_PATH`
(which already honours the DATABASE_PATH env var).
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `bookcabinet.*` importable when alembic is run from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Resolve the target DB path. Prefer DATABASE_PATH env var, then fall back to
# the project config constant so behaviour matches the running application.
def _resolve_database_url() -> str:
    db_path = os.environ.get('DATABASE_PATH')
    if not db_path:
        try:
            from bookcabinet.config import DATABASE_PATH  # type: ignore
            db_path = DATABASE_PATH
        except Exception:
            db_path = os.path.join(_REPO_ROOT, 'data', 'shelf_data.db')
    # Ensure parent directory exists so SQLite can create the file.
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return f"sqlite:///{db_path}"


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the resolved URL into the alembic config so both online and offline
# modes see the same thing.
config.set_main_option('sqlalchemy.url', _resolve_database_url())

# No ORM metadata — raw SQL migrations only.
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
