#!/usr/bin/env python3
"""
Скрипт для сброса webhook бота Telegram
"""
import asyncio
import sys
from telegram import Bot
from config.config import get_settings

async def reset_webhook():
    """Сбрасывает webhook бота"""
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    
    try:
        # Сбрасываем webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook успешно сброшен")
        
        # Проверяем информацию о боте
        bot_info = await bot.get_me()
        print(f"🤖 Информация о боте: @{bot_info.username} ({bot_info.first_name})")
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе webhook: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(reset_webhook())