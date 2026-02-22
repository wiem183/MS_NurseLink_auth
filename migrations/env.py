from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import database and models
# ---------------------------------------------------------------------------
try:
    from app.core.database import Base  # ← CHANGED: app.core.database not app.database
    from app.models.user import User
    from app.models.refresh_token import RefreshToken
    # Add more models as you create them
except ImportError as e:
    print(f"Error importing models: {e}")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    raise

# Set target metadata
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Set database URL
# ---------------------------------------------------------------------------
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Convert async URL to sync for Alembic
    if 'asyncpg' in database_url:
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
    config.set_main_option('sqlalchemy.url', database_url)
else:
    raise ValueError("DATABASE_URL not found in environment variables")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    # Use the sync URL we already built (Alembic needs a sync driver, not asyncpg)
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()