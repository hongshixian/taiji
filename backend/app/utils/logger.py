"""统一日志模块"""

import logging
import sys

# 日志格式：时间 [级别] 模块: 消息
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """获取一个已配置好的 logger 实例，输出到 stdout

    Args:
        name: logger 名称，通常用 __name__

    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # 默认 INFO 级别
    logger.setLevel(logging.INFO)

    return logger