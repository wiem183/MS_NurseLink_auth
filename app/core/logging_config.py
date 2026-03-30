# app/core/logging_config.py
import logging
import sys
from datetime import datetime
from pathlib import Path

# ── Create logs directory if it doesn't exist ─────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# ── Timestamped logs file for this server run ──────────────────────────────────
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOGS_DIR / f"server_{timestamp}.log"

# ── Format ────────────────────────────────────────────────────────────────────
FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Handlers ──────────────────────────────────────────────────────────────────
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(FORMATTER)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(FORMATTER)
console_handler.setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to both the timestamped file and terminal."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False
    return logger


def setup_logging() -> None:
    """
    Call once at startup (in main.py).
    Configures the root logger + silences noisy third-party loggers.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    # Silence overly verbose libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logging.getLogger("app").setLevel(logging.DEBUG)

    print(f"📁 Logging to: {LOG_FILE.resolve()}")