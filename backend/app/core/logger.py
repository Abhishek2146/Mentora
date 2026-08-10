"""
Logging Configuration
"""
import logging
import sys
from pathlib import Path


def setup_logging():
    log_level = "DEBUG" if True else "INFO"

    logger = logging.getLogger("mentora")
    logger.setLevel(getattr(logging, log_level))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(getattr(logging, log_level))

    Path("logs").mkdir(exist_ok=True)
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
