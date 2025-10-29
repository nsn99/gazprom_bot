"""
Модуль настройки логирования для демо-робота GAZP.

Функции:
- setup_logging(config): настраивает логирование в файл и консоль.
- get_logger(name): возвращает именованный логгер в рамках общей конфигурации.

Логи:
- Файл логов: берётся из config.paths["log_file"] (по умолчанию logs/trading.log)
- Формат: время, уровень, источник, сообщение
- Кодировка: UTF-8

Дисклеймер: данный код предназначен исключительно для учебных целей.
"""

import logging
import os
import sys
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(config, level: int = logging.INFO, console: bool = True) -> logging.Logger:
    """
    Настраивает корневой логгер приложения и возвращает основной логгер.

    Параметры:
    - config: объект конфигурации [Config](gazprom_bot/config.py:1), должен содержать paths["log_file"]
    - level: минимальный уровень логирования (INFO по умолчанию)
    - console: добавлять ли вывод в консоль (True по умолчанию)

    Возвращает:
    - logging.Logger: основной логгер 'gazprom_bot'
    """
    log_file_path = config.paths.get("log_file", os.path.join("logs", "trading.log"))
    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("gazprom_bot")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # Файловый обработчик
    file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Консольный обработчик (опционально)
    if console:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logger.info("Логирование инициализировано. Файл: %s", log_file_path)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает именованный логгер в рамках настроенной иерархии.
    Если имя не указано, вернётся основной логгер 'gazprom_bot'.
    """
    if not name:
        return logging.getLogger("gazprom_bot")
    return logging.getLogger(f"gazprom_bot.{name}")


__all__ = ["setup_logging", "get_logger"]