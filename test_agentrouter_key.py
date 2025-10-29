#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки API ключа AgentRouter
"""

import asyncio
import os
from config import settings

async def test_agentrouter_key():
    """Проверка API ключа AgentRouter"""
    print(f"AgentRouter API Key: {settings.agentrouter_api_key[:10]}...{settings.agentrouter_api_key[-10:] if len(settings.agentrouter_api_key) > 20 else settings.agentrouter_api_key}")
    print(f"AgentRouter Base URL: {settings.agentrouter_base_url}")
    print(f"AgentRouter Model: {settings.agentrouter_model}")
    
    # Проверка формата ключа
    if not settings.agentrouter_api_key.startswith("sk-"):
        print("❌ Неверный формат API ключа (должен начинаться с 'sk-')")
        return False
    
    if len(settings.agentrouter_api_key) < 20:
        print("❌ Слишком короткий API ключ")
        return False
    
    print("✅ API ключ имеет правильный формат")
    return True

if __name__ == "__main__":
    asyncio.run(test_agentrouter_key())