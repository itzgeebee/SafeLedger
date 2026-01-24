import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ----------------------------
# Path setup (CRITICAL)
# ----------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

# ----------------------------
# App imports
# ----------------------------

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402

# ----------------------------
# Alembic config
# ----------------------------

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ----------------------------
# DB URL handling
# ----------------------------

settings = get_settings()

sync_database_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)

config.set_main_option("sqlalchemy.url", sync_database_url)

# ----------------------------
# Migration runner
# ----------------------------


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
