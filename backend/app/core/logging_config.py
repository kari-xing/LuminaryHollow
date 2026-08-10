"""统一日志配置：控制台 + 滚动文件（logs/ 目录），支持对话级调试。"""
import logging
import os
from logging.handlers import RotatingFileHandler

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 从 backend/app/core/logging_config.py 上溯到项目根（backend → 根）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_BASE_DIR))
LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """初始化根 logger：控制台 + logs/app.log（滚动 5MB×5）。"""
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(_FMT)

    # 避免重复添加 handler（--reload 会多次加载）
    if any(getattr(h, "_luminary", False) for h in root.handlers):
        return

    os.makedirs(LOGS_DIR, exist_ok=True)

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    for h in (console, file_handler):
        h._luminary = True  # type: ignore[attr-defined]
        root.addHandler(h)


def get_chat_logger() -> logging.Logger:
    """对话日志专用 logger（记录到 logs/chat.log）。"""
    logger = logging.getLogger("luminary.chat")
    if not any(getattr(h, "_luminary", False) for h in logger.handlers):
        os.makedirs(LOGS_DIR, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, "chat.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(message)s"
        ))
        handler._luminary = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
