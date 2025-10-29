#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки AgentRouter SDK
"""

import asyncio
import json
from client import AgentRouter
from config import settings

async def test_agentrouter_sdk():
    """Проверка работы AgentRouter SDK"""
    print("🔍 Тестирование AgentRouter SDK...")
    
    # Инициализация клиента
    client = AgentRouter(api_key=settings.agentrouter_api_key)
    
    # Тест 1: Простой вопрос
    print("\n1. Тест простого вопроса...")
    try:
        response = client.ask("Привет, как дела?", model=settings.agentrouter_model)
        print(f"✅ Ответ: {response}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    # Тест 2: Список моделей
    print("\n2. Тест получения списка моделей...")
    try:
        models = client.list_models()
        print(f"✅ Доступные модели: {models}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    # Тест 3: Chat с контекстом
    print("\n3. Тест chat с контекстом...")
    try:
        messages = [
            {"role": "system", "content": "Ты - финансовый аналитик."},
            {"role": "user", "content": "Дай краткую рекомендацию по акции Газпром в формате JSON."}
        ]
        
        response = client.chat(
            messages=messages,
            model=settings.agentrouter_model,
            temperature=0.7,
            max_tokens=200
        )
        
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            print(f"✅ Ответ: {content}")
            
            # Токены
            try:
                tokens = client.count_tokens(response)
                print(f"✅ Токены использовано: {tokens}")
            except Exception as e:
                print(f"⚠️ Ошибка подсчета токенов: {e}")
        else:
            print("❌ Нет ответа")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    # Тест 4: Потоковый ответ
    print("\n4. Тест потокового ответа...")
    try:
        print("AI отвечает: ", end="")
        for chunk in client.stream("Напиши короткое стихотворение о коде", max_tokens=50):
            print(chunk, end="", flush=True)
        print()  # Новая строка
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    print("\n✅ Все тесты AgentRouter SDK пройдены успешно!")
    return True

if __name__ == "__main__":
    asyncio.run(test_agentrouter_sdk())