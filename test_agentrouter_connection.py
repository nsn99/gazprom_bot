#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки соединения с AgentRouter API
"""

import asyncio
import json
from ai.agentrouter_client import AgentRouterClient

async def test_agentrouter_connection():
    """Проверка соединения с AgentRouter"""
    print("🔍 Тестирование соединения с AgentRouter...")
    
    client = AgentRouterClient()
    
    # Тест соединения
    print("\n1. Тест базового соединения...")
    connection_result = await client.test_connection()
    
    if connection_result["success"]:
        print("✅ Соединение установлено успешно")
        print(f"   Модель: {connection_result['model']}")
        print(f"   Ответ: {connection_result['response']}")
    else:
        print(f"❌ Ошибка соединения: {connection_result['error']}")
        return False
    
    # Тест запроса рекомендации
    print("\n2. Тест запроса рекомендации...")
    test_context = {
        "portfolio": {
            "cash": 100000.0,
            "shares": 10,
            "avg_price": 150.0,
            "current_price": 155.0,
            "total_value": 101550.0,
            "pnl": 1550.0,
            "pnl_percent": 1.55
        },
        "market_data": {
            "current_price": 155.0,
            "technical_indicators": {
                "rsi": 55.0,
                "macd": {
                    "macd": 2.5,
                    "signal": 2.0,
                    "histogram": 0.5
                }
            }
        },
        "risk_settings": {
            "max_position_percent": 30,
            "risk_limit_percent": 5
        }
    }
    
    from ai.prompts import TRADING_SYSTEM_PROMPT
    
    recommendation_result = await client.get_trading_recommendation(
        TRADING_SYSTEM_PROMPT, 
        test_context
    )
    
    if recommendation_result["success"]:
        print("✅ Рекомендация получена успешно")
        print(f"   Токенов использовано: {recommendation_result['tokens_used']}")
        print(f"   Время выполнения: {recommendation_result['execution_time']:.2f} сек")
        print(f"   Рекомендация: {json.dumps(recommendation_result['data'], ensure_ascii=False, indent=2)}")
    else:
        print(f"❌ Ошибка получения рекомендации: {recommendation_result['error']}")
        return False
    
    # Получение статистики
    print("\n3. Статистика использования...")
    stats = await client.get_usage_stats()
    print(f"   Запросов: {stats['request_count']}")
    print(f"   Токенов использовано: {stats['tokens_used']}")
    print(f"   Успешность: {stats['success_rate']:.1f}%")
    
    print("\n✅ Все тесты пройдены успешно!")
    return True

if __name__ == "__main__":
    asyncio.run(test_agentrouter_connection())