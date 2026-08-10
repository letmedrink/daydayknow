import json
import logging
import sys
import time
from datetime import datetime, timezone
from ..config import settings

# 日志级别映射
LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "none": logging.CRITICAL,
}


def get_log_level() -> int:
    level = settings.LOG_LEVEL.lower()
    return LOG_LEVEL_MAP.get(level, logging.INFO)


class JsonFormatter(logging.Formatter):
    """JSON 结构化日志格式。"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 合并 extra 字段
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "user_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """人类可读日志格式。"""

    def format(self, record):
        parts = [self.formatTime(record), record.levelname, f"[{record.name}]"]
        parts.append(record.getMessage())
        extras = {}
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            val = getattr(record, key, None)
            if val is not None:
                extras[key] = val
        if extras:
            parts.append(json.dumps(extras, ensure_ascii=False))
        if record.exc_info:
            parts.append("\n" + self.formatException(record.exc_info))
        return " ".join(parts)


# 配置根日志记录器
_use_json = settings.LOG_LEVEL == "json"
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JsonFormatter() if _use_json else TextFormatter())

root_logger = logging.getLogger()
root_logger.setLevel(get_log_level() if not _use_json else logging.INFO)
root_logger.handlers = [_handler]


class ModuleLogger:
    def __init__(self, module_name: str):
        self.logger = logging.getLogger(module_name)

    def debug(self, message: str, data=None):
        self.logger.debug(f"{message} {data}" if data else message)

    def info(self, message: str, data=None):
        self.logger.info(f"{message} {data}" if data else message)

    def warn(self, message: str, data=None):
        self.logger.warning(f"{message} {data}" if data else message)

    def error(self, message: str, error=None):
        if error and isinstance(error, Exception):
            self.logger.error(f"{message} {error}", exc_info=True)
        elif error:
            self.logger.error(f"{message} {error}")
        else:
            self.logger.error(message)


def create_module_logger(module_name: str) -> ModuleLogger:
    return ModuleLogger(module_name)
