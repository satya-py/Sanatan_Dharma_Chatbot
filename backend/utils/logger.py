import logging
import sys
from pathlib import Path

from ..config import settings

# Resolve logs directory. On a hosted instance the filesystem is ephemeral and
# stdout is what the platform actually collects, so file logging is opt-in.
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE_PATH = None


def setup_logger():
    """
    Configures logging to standard output, and optionally to a local log file
    when LOG_TO_FILE is enabled.
    """
    global LOG_FILE_PATH

    logger = logging.getLogger("SanatanAI")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler -- the one that matters in a container.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if settings.LOG_TO_FILE:
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            LOG_FILE_PATH = LOGS_DIR / "app.log"
            file_handler = logging.FileHandler(str(LOG_FILE_PATH), encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            LOG_FILE_PATH = None
            print(f"[Logger] Failed to initialize file logging: {e}")

    return logger


logger = setup_logger()
