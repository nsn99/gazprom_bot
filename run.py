#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Main Entry Point

Telegram бот для торговли акциями Газпром (GAZP) на MOEX 
с использованием GPT-5 через AgentRouter API.
"""

import asyncio
import sys
import signal
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from monitoring.logger import get_logger, setup_logging
from database.database import init_database
from telegram.bot import create_application


logger = get_logger(__name__)


class GazpromBot:
    """Основной класс приложения бота"""
    
    def __init__(self):
        self.application = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Инициализация компонентов бота"""
        logger.info("Инициализация Gazprom Trading Bot...")
        
        try:
            # Настройка логирования
            setup_logging()
            logger.info("Логирование настроено")
            
            # Инициализация базы данных
            await init_database()
            logger.info("База данных инициализирована")
            
            # Создание приложения Telegram бота
            self.application = create_application()
            logger.info("Telegram приложение создано")
            
            # Настройка обработчиков сигналов для graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("Инициализация завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, начинаю graceful shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Запуск бота"""
        try:
            await self.initialize()
            
            logger.info("Запуск Gazprom Trading Bot...")
            
            # Запуск бота с обработкой shutdown
            async with self.application:
                await self.application.start()
                logger.info("Бот успешно запущен")
                
                # Ожидание сигнала shutdown
                await self._shutdown_event.wait()
                
                logger.info("Остановка бота...")
                await self.application.stop()
                
        except Exception as e:
            logger.error(f"Критическая ошибка при запуске бота: {e}")
            raise
        finally:
            logger.info("Бот остановлен")


async def main():
    """Основная функция"""
    bot = GazpromBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt, завершение работы...")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Проверка наличия необходимых переменных окружения
    required_vars = ["TELEGRAM_BOT_TOKEN", "AGENTROUTER_API_KEY"]
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
    
    if missing_vars:
        print("❌ Отсутствуют необходимые переменные окружения:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nПожалуйста, настройте файл .env с необходимыми значениями.")
        sys.exit(1)
    
    # Запуск бота
    print("🚀 Запуск Gazprom Trading Bot...")
    asyncio.run(main())
