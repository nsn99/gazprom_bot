#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки исправленной команды /analysis
"""

import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import GazpromTelegramBot
from database.models import User, Portfolio
from config import settings


async def test_analysis_command():
    """Тестирование команды /analysis"""
    print("🧪 Тестирование команды /analysis...")
    
    # Инициализация бота
    bot = GazpromTelegramBot()
    
    # Создаем тестового пользователя, если не существует
    test_user_id = 123456789
    try:
        user = await bot.portfolio_manager.create_user(
            user_id=test_user_id,
            username="test_user",
            initial_capital=100000.0
        )
        print(f"✅ Создан тестовый пользователь: {user.id}")
    except Exception as e:
        print(f"⚠️ Пользователь уже существует или ошибка: {e}")
        user = await bot.portfolio_manager.get_user_by_id(test_user_id)
    
    # Получаем портфель
    portfolio = await bot.portfolio_manager.get_portfolio(test_user_id)
    if not portfolio:
        print("❌ Портфель не найден")
        return
    
    print(f"✅ Портфель найден: {portfolio.id}")
    
    # Получаем текущую цену
    try:
        async with bot.moex_client:
            current_price = await bot.moex_client.get_current_price("GAZP")
        print(f"✅ Текущая цена GAZP: {current_price}")
    except Exception as e:
        print(f"❌ Ошибка получения цены: {e}")
        return
    
    # Подготавливаем контекст для AI
    try:
        ai_context = await bot._prepare_ai_context(test_user_id, portfolio, current_price)
        print("✅ Контекст для AI подготовлен")
        
        # Проверяем наличие рыночных данных
        market_data = ai_context.get("market_data", {})
        print(f"📊 Рыночные данные:")
        print(f"   - Текущая цена: {market_data.get('current_price')}")
        print(f"   - Объем: {market_data.get('volume')}")
        print(f"   - Максимум дня: {market_data.get('day_high')}")
        print(f"   - Минимум дня: {market_data.get('day_low')}")
        
        technical_indicators = market_data.get("technical_indicators", {})
        print(f"📈 Технические индикаторы:")
        print(f"   - RSI: {technical_indicators.get('rsi')}")
        print(f"   - MACD: {technical_indicators.get('macd')}")
        print(f"   - SMA 20: {technical_indicators.get('sma_20')}")
        print(f"   - SMA 50: {technical_indicators.get('sma_50')}")
        print(f"   - SMA 200: {technical_indicators.get('sma_200')}")
        
    except Exception as e:
        print(f"❌ Ошибка подготовки контекста: {e}")
        return
    
    # Тестируем очистку Markdown
    test_text = "Это **текст** с *разным* <b>форматированием</b> и некорректными <30). символами"
    cleaned_text = bot._clean_markdown(test_text)
    print(f"🧹 Очистка Markdown:")
    print(f"   Исходный: {test_text}")
    print(f"   Очищенный: {cleaned_text}")
    
    print("✅ Тестирование команды /analysis завершено успешно!")


if __name__ == "__main__":
    asyncio.run(test_analysis_command())