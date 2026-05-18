import logging
import sys
from datetime import datetime
from ..config import settings

# 日志级别映射
LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "none": logging.CRITICAL
}

def get_log_level() -> int:
    """获取日志级别"""
    level = settings.LOG_LEVEL.lower()
    return LOG_LEVEL_MAP.get(level, logging.INFO)

# 配置根日志记录器
logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str = None):
    """获取日志记录器"""
    return logging.getLogger(name)

# 模块化日志记录器
class ModuleLogger:
    def __init__(self, module_name: str):
        self.logger = logging.getLogger(module_name)
    
    def debug(self, message: str, data=None):
        if data:
            self.logger.debug(f"{message} {data}")
        else:
            self.logger.debug(message)
    
    def info(self, message: str, data=None):
        if data:
            self.logger.info(f"{message} {data}")
        else:
            self.logger.info(message)
    
    def warn(self, message: str, data=None):
        if data:
            self.logger.warning(f"{message} {data}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, error=None):
        if error:
            if isinstance(error, Exception):
                self.logger.error(f"{message} {error}", exc_info=True)
            else:
                self.logger.error(f"{message} {error}")
        else:
            self.logger.error(message)

def create_module_logger(module_name: str) -> ModuleLogger:
    """创建模块化日志记录器"""
    return ModuleLogger(module_name)