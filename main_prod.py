#!/usr/bin/env python3
"""
Продакшен версия основного скрипта запуска gazprom_bot.

Отличия от main.py:
- Асинхронная архитектура
- Полноценный мониторинг и алерты
- Graceful shutdown
- Метрики Prometheus
- Контейнеризация готова

Запуск:
    python -m gazprom_bot.main_prod
"""

from __future__ import annotations

import asyncio
import logging
import argparse
import signal
import sys
from pathlib import Path

from gazprom_bot.config import load_config
from gazprom_bot.logging_setup import setup_logging
from gazprom_bot.core.trading_engine import TradingEngine
from gazprom_bot.monitoring.health import HealthChecker


async def main():
    """Основная функция продакшен приложения."""
    parser = argparse.ArgumentParser(description="GAZP Trading Bot - Production")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="Logging level")
    args = parser.parse_args()

    # Загрузка конфигурации
    config = load_config()
    if args.config:
        # Здесь можно добавить загрузку из файла
        pass

    # Настройка логирования
    logger = setup_logging(config, level=getattr(logging, args.log_level))
    logger.info("Starting GAZP Trading Bot (Production)")

    # Создание компонентов
    engine = TradingEngine(config)

    # Обработчик сигналов для graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(engine.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Запуск движка
        await engine.start()

        # Ожидание завершения
        while engine.state.value in ['running', 'paused']:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Финализация
        if engine.state.value != 'stopped':
            await engine.stop()

        logger.info("GAZP Trading Bot stopped")


if __name__ == "__main__":
    # Настройка event loop для Windows (если нужно)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Запуск
    asyncio.run(main())