from __future__ import annotations

import logging
from pathlib import Path

from .paths import SERVICE_LOG_FILE


def setup_logging(
    log_file: str | Path | None = None,
    *,
    level: str = "INFO",
    console: bool = True,
) -> Path:
    resolved = Path(log_file or SERVICE_LOG_FILE)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("led_controller")
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    logger.propagate = False

    current_path = getattr(logger, "_configured_log_path", None)
    current_console = getattr(logger, "_configured_console", None)
    if current_path == str(resolved) and current_console == bool(console) and logger.handlers:
        return resolved

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    file_handler = logging.FileHandler(resolved, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logger._configured_log_path = str(resolved)
    logger._configured_console = bool(console)
    return resolved


def get_logger(name: str) -> logging.Logger:
    normalized = str(name or "app").strip().replace("respeaker_led.", "").replace("src.", "")
    if normalized == "__main__":
        normalized = "main"
    return logging.getLogger(f"led_controller.{normalized}")