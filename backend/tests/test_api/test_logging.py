import pytest
import json
import logging
from app.utils.logger import ModuleLogger, JsonFormatter, TextFormatter


class TestLogger:

    def test_module_logger_info(self):
        logger = ModuleLogger("test.module")
        # Just ensure it doesn't crash
        logger.info("test message")
        logger.info("test with data", {"key": "value"})

    def test_module_logger_error(self):
        logger = ModuleLogger("test.error")
        logger.error("something went wrong")
        logger.error("with exception", ValueError("test error"))

    def test_json_formatter(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello world", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "info"
        assert data["message"] == "hello world"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_text_formatter(self):
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warning message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "WARNING" in output
        assert "warning message" in output

    def test_json_formatter_with_extra(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="request", args=(), exc_info=None,
        )
        record.request_id = "abc123"
        record.method = "GET"
        record.path = "/api/test"
        record.status_code = 200
        record.duration_ms = 12.5
        output = formatter.format(record)
        data = json.loads(output)
        assert data["request_id"] == "abc123"
        assert data["method"] == "GET"
        assert data["duration_ms"] == 12.5
