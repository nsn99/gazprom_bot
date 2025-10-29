#!/usr/bin/env python3
"""
Тестовый скрипт для проверки команды /analysis
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import GazpromTelegramBot
from data.moex_client import MOEXClient
from portfolio.manager import PortfolioManager
from database.database import init_database


async def test_analysis_command():
    """Тестирование команды анализа"""
    print("🔍 Тестирование команды /analysis...")
    
    try:
        # Инициализация базы данных
        await init_database()
        print("✅ База данных инициализирована")
        
        # Создание экземпляров
        bot = GazpromTelegramBot()
        moex_client = MOEXClient()
        portfolio_manager = PortfolioManager()
        
        # Тестовый user_id (можно заменить на реальный)
        test_user_id = 73097766
        
        print(f"📊 Проверка данных для user_id: {test_user_id}")
        
        # Получение портфеля
        portfolio = await portfolio_manager.get_portfolio(test_user_id)
        if not portfolio:
            print("❌ Портфель не найден")
            return
        
        print(f"💰 Портфель найден: cash={portfolio.current_cash}")
        
        # Получение рыночных данных
        async with moex_client:
            current_price = await moex_client.get_current_price("GAZP")
            print(f"💵 Текущая цена GAZP: {current_price}")
            
            # Получение технических индикаторов
            technical_indicators = await moex_client.get_technical_indicators("GAZP")
            print(f"📈 Технические индикаторы: {technical_indicators}")
            
            # Получение L1 данных
            l1_data = await moex_client.get_marketdata_l1("GAZP")
            print(f"📊 L1 данные: last={l1_data.last}, voltoday={l1_data.voltoday}")
        
        # Подготовка контекста для AI
        ai_context = await bot._prepare_ai_context(test_user_id, portfolio, current_price)
        print(f"🤖 Контекст для AI: {ai_context}")
        
        # Проверка рыночных данных в контексте
        market_data = ai_context.get("market_data", {})
        print(f"\n📊 РЫНОЧНЫЕ ДАННЫЕ:")
        print(f"   Текущая цена: {market_data.get('current_price', 'N/A')}")
        print(f"   Объем: {market_data.get('volume', 'N/A')}")
        print(f"   Максимум дня: {market_data.get('day_high', 'N/A')}")
        print(f"   Минимум дня: {market_data.get('day_low', 'N/A')}")
        print(f"   Цена открытия: {market_data.get('open_price', 'N/A')}")
        
        # Проверка технических индикаторов
        tech_indicators = market_data.get("technical_indicators", {})
        print(f"\n📈 ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ:")
        print(f"   RSI: {tech_indicators.get('rsi', 'N/A')}")
        print(f"   MACD: {tech_indicators.get('macd', 'N/A')}")
        print(f"   SMA 20: {tech_indicators.get('sma_20', 'N/A')}")
        print(f"   SMA 50: {tech_indicators.get('sma_50', 'N/A')}")
        print(f"   Волатильность: {tech_indicators.get('volatility', 'N/A')}")
        
        # Проверка данных портфеля
        portfolio_data = ai_context.get("portfolio", {})
        print(f"\n💼 ДАННЫЕ ПОРТФЕЛЯ:")
        print(f"   Наличные: {portfolio_data.get('cash', 'N/A')}")
        print(f"   Акции: {portfolio_data.get('shares', 'N/A')}")
        print(f"   Средняя цена: {portfolio_data.get('avg_price', 'N/A')}")
        print(f"   P&L: {portfolio_data.get('pnl', 'N/A')}")
        
        print("\n✅ Тестирование завершено успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_analysis_command())