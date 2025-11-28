from __future__ import annotations

import logging
import logging.handlers
import pathlib
from typing import Optional


def configure_logging(log_file: str, level: str = "INFO") -> None:
    log_path = pathlib.Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler, console],
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "pilink")

