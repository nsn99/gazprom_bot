#!/usr/bin/env python3
"""
Базовый тест функциональности бота без запуска polling
"""

import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from telegram_bot.bot import create_application
from config.config import settings


async def test_bot_basic():
    """Тест базовой функциональности бота"""
    print("Тест базовой функциональности Telegram бота...")
    
    try:
        # Создание приложения
        print("1. Создание приложения...")
        application = create_application()
        print("   ✅ Приложение создано успешно")
        
        # Инициализация
        print("2. Инициализация приложения...")
        await application.initialize()
        print("   ✅ Приложение инициализировано")
        
        # Проверка токена
        print("3. Проверка токена бота...")
        bot_info = await application.bot.get_me()
        print(f"   ✅ Бот: {bot_info.first_name} (@{bot_info.username})")
        
        # Тестирование базовых команд
        print("4. Проверка регистрации команд...")
        handlers = application.handlers
        command_handlers = [h for h in handlers if hasattr(h, 'command')]
        print(f"   ✅ Зарегистрировано команд: {len(command_handlers)}")
        
        for handler in command_handlers:
            if hasattr(handler, 'command'):
                print(f"      - /{handler.command}")
        
        print("\n✅ Базовый тест пройден успешно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await application.shutdown()
            print("🔄 Приложение корректно завершено")
        except:
            pass


if __name__ == "__main__":
    import asyncio
    
    print(f"Telegram Bot Token: {settings.telegram_bot_token[:10]}...")
    print(f"AgentRouter API Key: {settings.agentrouter_api_key[:10]}...")
    print(f"MOEX Base URL: {settings.moex_base_url}")
    
    result = asyncio.run(test_bot_basic())
    sys.exit(0 if result else 1)