"""Tests for logging configuration."""

from __future__ import annotations

import logging

from segy_toolbox.logging import LOGGER_NAME, get_logger, setup_logging


class TestGetLogger:
    def test_root_logger(self):
        logger = get_logger()
        assert logger.name == LOGGER_NAME

    def test_named_logger(self):
        logger = get_logger("test_module")
        assert logger.name == f"{LOGGER_NAME}.test_module"

    def test_already_prefixed_name(self):
        logger = get_logger(f"{LOGGER_NAME}.sub.module")
        assert logger.name == f"{LOGGER_NAME}.sub.module"


class TestSetupLogging:
    def test_setup_adds_handler(self):
        logger = logging.getLogger(LOGGER_NAME)
        logger.handlers.clear()
        setup_logging(level=logging.DEBUG)
        assert len(logger.handlers) >= 1

    def test_setup_idempotent(self):
        logger = logging.getLogger(LOGGER_NAME)
        logger.handlers.clear()
        setup_logging(level=logging.INFO)
        count = len(logger.handlers)
        setup_logging(level=logging.INFO)
        assert len(logger.handlers) == count

    def test_file_handler(self, tmp_path):
        logger = logging.getLogger(LOGGER_NAME)
        logger.handlers.clear()
        log_file = str(tmp_path / "test.log")
        setup_logging(level=logging.DEBUG, log_file=log_file)
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        # Clean up
        logger.handlers.clear()
