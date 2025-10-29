#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест регистрации команд Telegram бота
"""

import asyncio
from telegram.ext import Application

from config import settings
from telegram_bot.bot import create_application


async def test_commands():
    """Тест регистрации команд"""
    print("🔍 Тест регистрации команд Telegram бота...")
    
    # Создание приложения
    application = create_application()
    
    # Проверка зарегистрированных команд
    print(f"✅ Приложение создано успешно")
    
    # Получение списка обработчиков команд
    command_handlers = []
    for group_id, handler_group in application.handlers.items():
        print(f"🔍 Группа обработчиков {group_id}:")
        for handler in handler_group:
            print(f"  - Тип обработчика: {type(handler).__name__}")
            if hasattr(handler, 'command'):
                if isinstance(handler.command, list):
                    command_handlers.extend(handler.command)
                    print(f"    Команды: {handler.command}")
                else:
                    command_handlers.append(handler.command)
                    print(f"    Команда: {handler.command}")
            elif hasattr(handler, 'callback'):
                # Для CommandHandler в python-telegram-bot 20.x
                if hasattr(handler, 'commands'):
                    command_handlers.extend(handler.commands)
                    print(f"    Команды (атрибут): {handler.commands}")
    
    print(f"📋 Зарегистрированные команды: {command_handlers}")
    print(f"📊 Всего команд: {len(command_handlers)}")
    
    # Проверка основных команд
    required_commands = ['start', 'portfolio', 'recommend', 'execute', 'history', 'balance', 'help']
    missing_commands = [cmd for cmd in required_commands if cmd not in command_handlers]
    
    if missing_commands:
        print(f"❌ Отсутствуют команды: {missing_commands}")
    else:
        print("✅ Все основные команды зарегистрированы")
    
    # Закрытие приложения
    await application.shutdown()
    print("🔄 Приложение корректно завершено")


if __name__ == "__main__":
    asyncio.run(test_commands())