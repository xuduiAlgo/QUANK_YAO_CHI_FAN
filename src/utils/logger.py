"""日志工具"""
import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def get_logger(name: Optional[str] = None, log_dir: str = "logs"):
    """
    获取配置好的logger
    
    Args:
        name: logger名称（可选）
        log_dir: 日志目录路径
    
    Returns:
        配置好的logger实例
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 移除默认handler
    logger.remove()
    
    # 控制台输出 - 只显示INFO及以上级别
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    
    # 文件输出 - 所有级别
    logger.add(
        log_path / "app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )
    
    # 错误日志单独文件
    logger.add(
        log_path / "error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
    )
    
    return logger


# 创建默认logger
default_logger = get_logger("capital_analysis")
