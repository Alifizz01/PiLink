from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
from typing import Optional

FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(log_file: str, level: str = "INFO", fallback_dir: str | None = None,
                      console: bool = False) -> str:
    """Log to a rotating file. If that file is not writable (an old config
    pointing at /var/log while the service runs as a normal user), fall back
    to fallback_dir instead of crashing the UI. Returns the file in use."""
    candidates = [log_file] + ([os.path.join(fallback_dir, "pilink.log")] if fallback_dir else [])
    handler = None
    for candidate in candidates:
        try:
            pathlib.Path(candidate).parent.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(candidate, maxBytes=5 * 1024 * 1024,
                                                           backupCount=3, encoding="utf-8")
            log_file = candidate
            break
        except OSError:
            continue
    handlers: list[logging.Handler] = [handler] if handler else []
    if console or not handlers:
        handlers.append(logging.StreamHandler())
    for h in handlers:
        h.setFormatter(logging.Formatter(FORMAT, "%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.handlers[:] = handlers
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    return log_file


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "pilink")
