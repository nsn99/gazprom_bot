#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки команды /analysis в реальном времени.
Имитирует полный рабочий процесс команды /analysis.
"""

import asyncio
from ai.agentrouter_client import AgentRouterClient
from data.moex_client import MOEXClient
from database.database import DatabaseManager
from telegram_bot.bot import GazpromTelegramBot
from portfolio.manager import PortfolioManager


async def test_analysis_command():
    print('🔍 Тестирование команды /analysis в реальном времени...')
    
    # 1. Инициализация всех необходимых компонентов
    db_manager = DatabaseManager()
    moex_client = MOEXClient()
    ai_client = AgentRouterClient()
    portfolio_manager = PortfolioManager()
    bot = GazpromTelegramBot()
    
    # Задаем тестового пользователя
    test_user_id = 73097766

    # 2. Предварительная подготовка: получение портфеля и цены
    print('📊 Получение данных портфеля и рыночной цены...')
    portfolio = await portfolio_manager.get_portfolio(test_user_id)
    if not portfolio:
        print(f"❌ Портфель для пользователя {test_user_id} не найден. Убедитесь, что пользователь создан через /start.")
        return False

    # Используем асинхронный контекстный менеджер для MOEXClient
    async with moex_client:
        current_price_data = await moex_client.get_marketdata_l1()
        if not current_price_data or not current_price_data.last:
            print("❌ Не удалось получить текущую цену GAZP.")
            return False
            
        current_price = current_price_data.last
        print(f'✅ Текущая цена GAZP: {current_price} RUB')

    # 3. Подготовка контекста для AI (теперь с правильными аргументами)
    print('🔍 Подготовка контекста для AI...')
    ai_context = await bot._prepare_ai_context(test_user_id, portfolio, current_price)
    
    # Проверка на N/A
    context_str = str(ai_context)
    if 'N/A' in context_str:
        print('❌ В контексте все еще есть значения N/A')
        return False
    else:
        print('✅ В контексте нет значений N/A')

    # 4. Запрос анализа у AI
    print('🤖 Запрос анализа у AI...')
    analysis_result = await ai_client.get_market_analysis(
        market_data=ai_context, # Передаем полный контекст
        analysis_type='deep'
    )
    
    if analysis_result['success']:
        print('✅ Анализ успешно получен от AI')
        analysis_text = analysis_result["analysis"]
        print(f'📊 Длина анализа: {len(analysis_text)} символов')
        
        # Проверка ответа AI
        if 'нет данных' in analysis_text.lower() or 'недостаточно данных' in analysis_text.lower():
            print('❌ AI сообщает об отсутствии данных')
            return False
        else:
            print('✅ AI не сообщает об отсутствии данных')
        
        return True
    else:
        print(f'❌ Ошибка при получении анализа: {analysis_result["error"]}')
        return False


# Запуск теста
if __name__ == "__main__":
    result = asyncio.run(test_analysis_command())
    if result:
        print('🎉 Тест успешно пройден! Команда /analysis работает корректно.')
    else:
        print('❌ Тест не пройден. Проверьте ошибки выше.')