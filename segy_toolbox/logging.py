"""Centralized logging configuration for SEG-Y Batch Inspector & Fixer."""

from __future__ import annotations

import logging
import sys

LOGGER_NAME = "segy_toolbox"


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger under the ``segy_toolbox`` namespace.

    Usage::

        from segy_toolbox.logging import get_logger
        logger = get_logger(__name__)
        logger.info("message")
    """
    if name is None:
        return logging.getLogger(LOGGER_NAME)
    if not name.startswith(LOGGER_NAME):
        name = f"{LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> None:
    """Configure the root ``segy_toolbox`` logger.

    Parameters
    ----------
    level:
        Logging level (e.g. ``logging.DEBUG``).
    log_file:
        Optional path to a log file.  When provided a
        :class:`~logging.FileHandler` is attached.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
