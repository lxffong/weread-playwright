import logging
import os
import sys
from pathlib import Path


def setup_logger(
    name: str = "weread",
    log_file: str = "data/weread.log",
    log_level: str = None,
) -> logging.Logger:
    """设置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR），默认从环境变量读取或使用 INFO

    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handlers
    if logger.handlers:
        return logger

    # 从环境变量读取日志级别，默认 INFO
    if log_level is None:
        log_level = os.getenv("WEREAD_LOG_LEVEL", "INFO").upper()

    level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 终端输出（始终启用）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # 文件输出（可通过环境变量禁用）
    if os.getenv("WEREAD_LOG_FILE_ENABLED", "true").lower() != "false":
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # 防止日志传播到根 logger
    logger.propagate = False

    return logger
