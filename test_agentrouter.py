#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с AgentRouter API
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from ai.agentrouter_client import AgentRouterClient
from config.config import settings


async def test_agentrouter_integration():
    """Тестирование интеграции с AgentRouter API"""
    print("Тестирование интеграции с AgentRouter API...")
    
    # Получаем конфигурацию
    print(f"AgentRouter Base URL: {settings.agentrouter_base_url}")
    print(f"AgentRouter Model: {settings.agentrouter_model}")
    
    # Создаем клиент
    client = AgentRouterClient()
    
    try:
        # Тестовый промпт для GPT-5
        test_prompt = """
        Ты - торговый аналитик. Проанализируй текущую ситуацию с акциями Газпрома и дай краткую рекомендацию.
        
        Текущая цена: 116.76 RUB
        Изменение за день: -1.2%
        Объем торгов: 29,155,040
        
        Дай ответ в формате JSON:
        {
          "action": "BUY/SELL/HOLD",
          "reasoning": "Краткое обоснование",
          "confidence": 0-100
        }
        """
        
        print("\n1. Отправка тестового запроса к GPT-5...")
        result = await client.get_trading_recommendation(
            system_prompt="Ты - профессиональный торговый аналитик.",
            user_context={"prompt": test_prompt}
        )
        
        if result["success"]:
            recommendation = result["data"]
            print(f"   ✅ Ответ получен успешно!")
            print(f"   📊 Рекомендация: {recommendation.get('action', 'N/A')}")
            print(f"   💡 Обоснование: {recommendation.get('reasoning', 'N/A')}")
            print(f"   🎯 Уверенность: {recommendation.get('confidence', 'N/A')}%")
            print(f"   🔢 Использовано токенов: {result.get('tokens_used', 'N/A')}")
        else:
            print(f"   ❌ Ошибка: {result.get('error', 'Unknown error')}")
        
        print("\n✅ Тестирование AgentRouter API завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании AgentRouter API: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agentrouter_integration())