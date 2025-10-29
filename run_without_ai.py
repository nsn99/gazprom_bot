#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Запуск бота без AI функционала для тестирования
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings, validate_config, print_config_summary
from monitoring.logger import setup_logging
from database.database import init_database
from telegram_bot.bot import create_application


async def main():
    """Основная функция"""
    print("🚀 Запуск Gazprom Trading Bot (без AI)...")
    
    # Валидация конфигурации
    if not validate_config(settings):
        print("❌ Ошибка в конфигурации. Проверьте файл .env")
        return
    
    # Вывод сводки конфигурации
    print_config_summary(settings)
    
    # Настройка логирования
    setup_logging(settings)
    logger = logging.getLogger(__name__)
    
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_database()
        logger.info("База данных инициализирована")
        
        # Создание и запуск приложения
        logger.info("Создание Telegram приложения...")
        application = create_application()
        
        logger.info("Запуск бота (без AI функционала)...")
        print("\n✅ Бот запущен успешно!")
        print("📝 Доступные команды:")
        print("  /start - Создать портфель")
        print("  /portfolio - Показать портфель")
        print("  /balance - Показать баланс")
        print("  /history - История сделок")
        print("  /help - Помощь")
        print("\n⚠️  Команда /recommend временно отключена (проблемы с AI)")
        print("\nНажмите Ctrl+C для остановки")
        
        # Запуск бота
        await application.run_polling()
        
    except KeyboardInterrupt:
        logger.info("Остановка бота по запросу пользователя...")
        print("\n👋 Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())