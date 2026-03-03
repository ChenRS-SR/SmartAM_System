"""
统一日志配置模块
================
提供统一的日志格式和输出管理
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（用于控制台输出）"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 保存原始级别名称
        original_levelname = record.levelname
        
        # 添加颜色（如果不是 Windows 或支持 ANSI）
        if sys.platform != 'win32' or 'ANSICON' in os.environ:
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        # 格式化
        result = super().format(record)
        
        # 恢复原始级别名称
        record.levelname = original_levelname
        
        return result


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件名（默认为 {name}.log）
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_dir: 日志文件保存目录
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False
    
    # 日志格式
    console_format = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    file_format = "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(console_format, datefmt=date_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器
    if file_output:
        # 创建日志目录
        if log_file is None:
            log_file = f"{name}.log"
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(file_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已配置的日志记录器（如果不存在则创建默认配置）
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果没有处理器，创建默认配置
    if not logger.handlers:
        return setup_logger(name, console_output=True, file_output=False)
    
    return logger


# 为不同模块预定义的日志记录器
def get_daq_logger() -> logging.Logger:
    """获取 DAQ 模块日志记录器"""
    return setup_logger("DAQ", "daq.log")


def get_camera_logger() -> logging.Logger:
    """获取相机模块日志记录器"""
    return setup_logger("Camera", "camera.log")


def get_inference_logger() -> logging.Logger:
    """获取推理模块日志记录器"""
    return setup_logger("Inference", "inference.log")


def get_control_logger() -> logging.Logger:
    """获取控制模块日志记录器"""
    return setup_logger("Control", "control.log")


def get_api_logger() -> logging.Logger:
    """获取 API 模块日志记录器"""
    return setup_logger("API", "api.log")


class LogContext:
    """
    日志上下文管理器
    用于在特定代码块中添加上下文信息
    """
    
    def __init__(self, logger: logging.Logger, context: str):
        self.logger = logger
        self.context = context
        self.original_formatters = []
        
    def __enter__(self):
        # 修改所有处理器的格式以添加上下文
        for handler in self.logger.handlers:
            original = handler.formatter
            self.original_formatters.append((handler, original))
            
            new_format = f"[{self.context}] {original._fmt}"
            new_formatter = logging.Formatter(new_format, datefmt=original.datefmt)
            handler.setFormatter(new_formatter)
        
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始格式
        for handler, original in self.original_formatters:
            handler.setFormatter(original)


# 便捷装饰器
def log_execution_time(logger: Optional[logging.Logger] = None, level: str = "DEBUG"):
    """
    装饰器：记录函数执行时间
    
    用法：
        @log_execution_time()
        def my_function():
            pass
    """
    def decorator(func):
        import functools
        import time
        
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                getattr(logger, level.lower())(
                    f"{func.__name__} 执行完成，耗时: {elapsed*1000:.2f}ms"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(
                    f"{func.__name__} 执行失败，耗时: {elapsed*1000:.2f}ms, 错误: {e}"
                )
                raise
        
        return wrapper
    return decorator


# 测试代码
if __name__ == "__main__":
    print("="*60)
    print("日志系统测试")
    print("="*60)
    
    # 测试基本日志
    logger = setup_logger("test", "test.log", level="DEBUG")
    
    print("\n1. 测试各级别日志:")
    logger.debug("这是一条 DEBUG 日志")
    logger.info("这是一条 INFO 日志")
    logger.warning("这是一条 WARNING 日志")
    logger.error("这是一条 ERROR 日志")
    logger.critical("这是一条 CRITICAL 日志")
    
    # 测试带上下文的日志
    print("\n2. 测试日志上下文:")
    with LogContext(logger, "CONTEXT"):
        logger.info("带上下文的日志消息")
    
    logger.info("上下文已恢复")
    
    # 测试执行时间装饰器
    print("\n3. 测试执行时间装饰器:")
    
    @log_execution_time(logger)
    def slow_function():
        import time
        time.sleep(0.1)
        return "done"
    
    result = slow_function()
    print(f"   函数返回: {result}")
    
    # 测试不同模块的日志记录器
    print("\n4. 测试模块专用日志记录器:")
    get_daq_logger().info("DAQ 模块日志")
    get_camera_logger().info("Camera 模块日志")
    get_inference_logger().info("Inference 模块日志")
    get_control_logger().info("Control 模块日志")
    get_api_logger().info("API 模块日志")
    
    print("\n5. 检查日志文件:")
    log_files = list(Path("logs").glob("*.log"))
    print(f"   找到 {len(log_files)} 个日志文件:")
    for f in log_files:
        print(f"   - {f.name}")
    
    print("\n测试完成！")
