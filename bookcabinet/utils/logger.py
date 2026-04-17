"""
Логирование — структурированный логгер на базе Python logging.

Использование:
    from bookcabinet.utils.logger import setup_logger, get_logger
    logger = get_logger('bookcabinet.mymodule')
    logger.info('Operation completed', extra={'book_rfid': rfid})

Формат: ISO timestamp - module - level - message
Вывод: консоль (DEBUG+) и файл (INFO+, путь из config.LOG_FILE).
Файл ротируется (RotatingFileHandler, 10 MB, 5 бэкапов).

Новые модули должны использовать get_logger() вместо print().
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from ..config import LOG_LEVEL, LOG_FILE

# #53: Rotation parameters. The Pi has limited disk — keep no more than
# ~60 MB of logs (10 MB current + 5 x 10 MB backups).
_LOG_MAX_BYTES = 10 * 1024 * 1024
_LOG_BACKUP_COUNT = 5


def setup_logger(name: str = 'bookcabinet') -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    try:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception:
        # File handler is best-effort; console logging always works.
        pass

    return logger


def get_logger(name: str = 'bookcabinet') -> logging.Logger:
    return logging.getLogger(name)
