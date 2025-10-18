"""Logging helpers for the ccq CLI."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_LOGGER_INITIALISED = False


def configure_logging(log_file: Optional[Path] = None, console_level: int = logging.INFO) -> None:
    """Configure logging for the CLI.

    Parameters
    ----------
    log_file:
        Destination log file for DEBUG level output. Defaults to ``logs/ccq.log``.
    console_level:
        Logging level used for the console handler.
    """

    global _LOGGER_INITIALISED
    if _LOGGER_INITIALISED:
        return

    log_file = log_file or Path("logs/ccq.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    _LOGGER_INITIALISED = True
