#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование команд Telegram бота
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.getcwd())

from ai.agentrouter_client import AgentRouterClient
from data.moex_client import MOEXClient
from portfolio.manager import PortfolioManager
from database.database import get_db_manager

async def test_all_components():
    """Тест всех компонентов бота"""
    print("🧪 Тестирование компонентов Gazprom Trading Bot...")
    
    # Тест 1: MOEX Client
    print("\n1. 📊 Тест MOEX Client...")
    try:
        async with MOEXClient() as moex:
            price = await moex.get_current_price("GAZP")
            print(f"   ✅ Текущая цена GAZP: {price} RUB")
            
            indicators = await moex.get_technical_indicators("GAZP")
            print(f"   ✅ Технические индикаторы получены: RSI={indicators.get('rsi14', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Ошибка MOEX Client: {e}")
    
    # Тест 2: AgentRouter Client
    print("\n2. 🤖 Тест AgentRouter Client...")
    try:
        ai_client = AgentRouterClient()
        result = await ai_client.test_connection()
        if result["success"]:
            print(f"   ✅ Соединение с AI установлено: {result['model']}")
        else:
            print(f"   ❌ Ошибка соединения с AI: {result['error']}")
    except Exception as e:
        print(f"   ❌ Ошибка AgentRouter Client: {e}")
    
    # Тест 3: Portfolio Manager
    print("\n3. 💼 Тест Portfolio Manager...")
    try:
        db = get_db_manager()
        await db.initialize()
        
        portfolio_manager = PortfolioManager()
        
        # Тест получения портфеля для тестового пользователя
        test_user_id = 12345
        portfolio = await portfolio_manager.get_portfolio(test_user_id)
        if portfolio:
            print(f"   ✅ Портфель получен: {portfolio.name}")
        else:
            print(f"   ⚠️ Портфель не найден")
        
        # Тест создания пользователя и портфеля
        try:
            user = await portfolio_manager.create_user(test_user_id, "test_user", 100000)
            print(f"   ✅ Пользователь создан: {user.id}")
        except Exception as e:
            print(f"   ⚠️ Пользователь уже существует или ошибка: {e}")
            
    except Exception as e:
        print(f"   ❌ Ошибка Portfolio Manager: {e}")
    
    # Тест 4: AI Trading Recommendation
    print("\n4. 📈 Тест AI Trading Recommendation...")
    try:
        ai_client = AgentRouterClient()
        
        # Подготовка тестовых данных
        test_context = {
            "portfolio": {
                "cash": 50000,
                "shares": 100,
                "avg_price": 150,
                "current_price": 155,
                "total_value": 65500,
                "pnl": 500,
                "pnl_percent": 0.77
            },
            "market_data": {
                "current_price": 155,
                "open_price": 152,
                "high_price": 157,
                "low_price": 151,
                "volume": 1000000,
                "daily_change": 1.97,
                "rsi": 65,
                "macd": 0.5
            }
        }
        
        system_prompt = """
        Ты — портфельный менеджер, специализирующийся на торговле акциями 
        ПАО "Газпром" (GAZP) на Московской бирже.
        
        Дай рекомендацию в формате JSON:
        {
          "action": "BUY/SELL/HOLD",
          "quantity": <количество акций>,
          "reasoning": "<обоснование решения>",
          "stop_loss": <цена стоп-лосса>,
          "take_profit": <цена тейк-профита>,
          "risk_level": "LOW/MEDIUM/HIGH",
          "confidence": <0-100>
        }
        """
        
        result = await ai_client.get_trading_recommendation(system_prompt, test_context)
        
        if result["success"]:
            recommendation = result["data"]
            print(f"   ✅ Рекомендация получена:")
            print(f"      Действие: {recommendation.get('action', 'N/A')}")
            print(f"      Количество: {recommendation.get('quantity', 'N/A')}")
            print(f"      Уверенность: {recommendation.get('confidence', 'N/A')}%")
            print(f"      Риск: {recommendation.get('risk_level', 'N/A')}")
            print(f"      Токенов использовано: {result.get('tokens_used', 0)}")
        else:
            print(f"   ❌ Ошибка получения рекомендации: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        print(f"   ❌ Ошибка AI Recommendation: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(test_all_components())