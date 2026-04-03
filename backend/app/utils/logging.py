"""
统一日志配置模块

提供结构化日志，包含时间戳、级别、模块名、消息。
支持控制台彩色输出和文件轮转。
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from app.config import get_settings, BACKEND_DIR


# 日志格式
_LOG_FORMAT = "[%(asctime)s.%(msecs)03d] [%(levelname)-5s] [%(name)s] %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup_logging() -> None:
    """
    初始化全局日志配置。应在应用启动时调用一次。

    - 控制台输出: 彩色格式化
    - 文件输出: 按大小轮转，保留 N 个备份
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    settings = get_settings()
    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    # 根 logger 配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有的 handlers（避免重复添加）
    root_logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 handler
    log_file = settings.logging.abs_log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=settings.logging.max_bytes,
        backupCount=settings.logging.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 降低第三方库的日志级别，避免噪音
    for noisy_logger in [
        "httpcore", "httpx", "chromadb", "sentence_transformers",
        "urllib3", "asyncio", "uvicorn.access",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(log_level)

    root_logger.info(
        "日志系统初始化完成 level=%s file=%s",
        settings.logging.level, log_file,
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取指定模块的 logger。

    Args:
        name: 模块名，建议使用 __name__ 或自定义短名称

    Returns:
        配置好的 Logger 实例

    Usage:
        logger = get_logger(__name__)
        logger.info("操作完成 elapsed=%.2fs", elapsed)
    """
    return logging.getLogger(name)
