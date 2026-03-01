import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Alembic config
# ---------------------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment (strip async driver for sync Alembic)
_raw_url = os.getenv(
    "SYNC_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://forecasting:forecasting@localhost:5432/forecasting"),
)
# If someone passes the asyncpg URL, convert it to psycopg2 for Alembic
_sync_url = (
    _raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("+asyncpg", "")
)
config.set_main_option("sqlalchemy.url", _sync_url)

# Import all models so their metadata is registered
from app.db.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  (registers all ORM classes)

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
