#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки исправлений в боте
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import GazpromTelegramBot
from monitoring.logger import get_logger

logger = get_logger(__name__)

async def test_market_data_fix():
    """Тест исправления рыночных данных"""
    print("🔍 Тест исправления рыночных данных...")
    
    bot = GazpromTelegramBot()
    
    try:
        # Создаем тестового пользователя и портфель
        user_id = 73097766  # Ваш ID пользователя
        
        # Получаем портфель
        portfolio = await bot.portfolio_manager.get_portfolio(user_id)
        if not portfolio:
            print("❌ Портфель не найден")
            return False
        
        # Получаем текущую цену
        async with bot.moex_client:
            current_price = await bot.moex_client.get_current_price("GAZP")
        
        if not current_price:
            print("❌ Не удалось получить текущую цену")
            return False
        
        print(f"✅ Текущая цена: {current_price}")
        
        # Тестируем подготовку контекста
        context = await bot._prepare_ai_context(user_id, portfolio, current_price)
        
        print("📊 Данные контекста:")
        print(f"  - current_price: {context['market_data']['current_price']}")
        print(f"  - day_high: {context['market_data']['day_high']}")
        print(f"  - day_low: {context['market_data']['day_low']}")
        print(f"  - volume: {context['market_data']['volume']}")
        
        # Проверяем, что данные не нулевые
        if (context['market_data']['day_high'] > 0 and 
            context['market_data']['day_low'] > 0 and 
            context['market_data']['volume'] > 0):
            print("✅ Рыночные данные корректны")
            return True
        else:
            print("❌ Рыночные данные неполные")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_markdown_cleaning():
    """Тест очистки Markdown"""
    print("\n🧹 Тест очистки Markdown...")
    
    bot = GazpromTelegramBot()
    
    # Тестовый текст с некорректным Markdown
    test_text = """
    **Жирный текст** и *курсив* с `кодом`
    и _подчеркиванием_ и ~зачеркиванием~
    
    Много переносов строк
    
    
    и еще текст
    """
    
    cleaned = bot._clean_markdown(test_text)
    
    print("Оригинальный текст:")
    print(repr(test_text))
    print("\nОчищенный текст:")
    print(repr(cleaned))
    print("\nОтформатированный текст:")
    print(cleaned)
    
    # Проверяем, что опасные символы удалены
    dangerous_chars = ['_', '~', '`']
    has_dangerous = any(char in cleaned for char in dangerous_chars)
    
    if not has_dangerous:
        print("✅ Markdown успешно очищен")
        return True
    else:
        print("❌ В тексте остались опасные символы")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования исправлений...\n")
    
    # Тест 1: Рыночные данные
    market_data_ok = await test_market_data_fix()
    
    # Тест 2: Очистка Markdown
    markdown_ok = await test_markdown_cleaning()
    
    print(f"\n📋 Результаты тестирования:")
    print(f"  - Рыночные данные: {'✅' if market_data_ok else '❌'}")
    print(f"  - Очистка Markdown: {'✅' if markdown_ok else '❌'}")
    
    if market_data_ok and markdown_ok:
        print("\n🎉 Все тесты пройдены! Исправления работают корректно.")
        return True
    else:
        print("\n⚠️ Некоторые тесты не пройдены. Требуется доработка.")
        return False

if __name__ == "__main__":
    asyncio.run(main())