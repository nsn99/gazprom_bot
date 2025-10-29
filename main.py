"""
Gazprom Trading Bot - Main Application Module

Основной модуль приложения, содержащий главную логику
и точку входа в программу.
"""

import asyncio
import logging
from pathlib import Path

from config import settings
from monitoring.logger import get_logger, setup_logging
from database.database import init_database
from telegram_bot.bot import create_application


logger = get_logger(__name__)


async def initialize_app():
    """Инициализация приложения"""
    logger.info("Инициализация Gazprom Trading Bot...")
    
    # Настройка логирования
    setup_logging()
    logger.info("Логирование настроено")
    
    # Инициализация базы данных
    await init_database()
    logger.info("База данных инициализирована")
    
    # Создание приложения Telegram бота
    application = create_application()
    logger.info("Telegram приложение создано")
    
    return application


async def main():
    """Основная функция приложения"""
    try:
        # Инициализация приложения
        application = await initialize_app()
        
        # Запуск бота
        logger.info("Запуск Gazprom Trading Bot...")
        
        # Инициализация приложения
        await application.initialize()
        await application.start()
        
        # Запуск бота в режиме polling
        await application.updater.start_polling(
            drop_pending_updates=True
        )
        
        # Бесконечный цикл для поддержания работы бота
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Получен сигнал остановки, завершаем работу...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, остановка бота...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        logger.info("Работа бота завершена")


if __name__ == "__main__":
    # Проверка конфигурации
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не настроен")
        exit(1)
    
    # Запуск приложения
    if __name__ == "__main__":
        asyncio.run(main())