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

from ai.agentrouter_client import AgentRouterClient
from data.moex_client import MOEXClient
from ai.prompts import DEEP_ANALYSIS_PROMPT
from config import settings


async def test_analysis_length():
    """Тестирование команды /analysis с ограничением длины ответа"""
    print("🧪 Тестирование команды /analysis с ограничением длины ответа...")
    
    # Инициализация клиентов
    ai_client = AgentRouterClient(settings.agentrouter_api_key)
    moex_client = MOEXClient()
    
    try:
        # Получение рыночных данных
        print("📊 Получение рыночных данных...")
        async with moex_client:
            current_price = await moex_client.get_current_price("GAZP")
            technical_indicators = await moex_client.get_technical_indicators("GAZP")
            l1_data = await moex_client.get_marketdata_l1("GAZP")
            
        if not current_price:
            print("❌ Не удалось получить текущую цену")
            return False
            
        print(f"✅ Текущая цена GAZP: {current_price} RUB")
        
        # Подготовка данных для анализа
        day_change = 0
        if l1_data and l1_data.open_price and l1_data.open_price > 0:
            day_change = ((current_price - l1_data.open_price) / l1_data.open_price) * 100
            
        # Обрабатываем значения N/A в технических индикаторах
        def safe_get_indicator(key, default="N/A"):
            value = technical_indicators.get(key, default)
            if value == "N/A" or value is None:
                return default
            return value
        
        # Формирование запроса для углубленного анализа
        analysis_request = DEEP_ANALYSIS_PROMPT.format(
            current_price=current_price,
            day_change=f"{day_change:.2f}",
            volume=l1_data.voltoday if l1_data else 0,
            day_high=l1_data.high if l1_data else current_price,
            day_low=l1_data.low if l1_data else current_price,
            user_shares_held=0,
            user_avg_buy_price=0,
            user_cash_balance=100000,
            rsi=safe_get_indicator("rsi"),
            macd=safe_get_indicator("macd"),
            sma_20=safe_get_indicator("sma_20"),
            sma_50=safe_get_indicator("sma_50"),
            sma_200=safe_get_indicator("sma_200")
        )
        
        print(f"📝 Длина запроса к AI: {len(analysis_request)} символов")
        
        # Получение анализа от AI
        print("🤖 Запрос анализа у AI...")
        result = await ai_client.get_market_analysis(
            {"analysis_request": analysis_request},
            analysis_type="deep"
        )
        
        if not result["success"]:
            print(f"❌ Ошибка при получении анализа: {result['error']}")
            return False
            
        analysis = result["analysis"]
        print(f"✅ Анализ получен, длина: {len(analysis)} символов")
        
        # Проверка длины ответа
        max_length = 3500
        if len(analysis) > max_length:
            print(f"⚠️ Ответ AI слишком длинный: {len(analysis)} > {max_length}")
            # Обрезаем ответ
            truncated_analysis = analysis[:max_length] + "...\n\n_Анализ обрезан из-за ограничений Telegram_"
            print(f"✅ Ответ обрезан до: {len(truncated_analysis)} символов")
        else:
            print(f"✅ Длина ответа в пределах нормы: {len(analysis)} <= {max_length}")
            truncated_analysis = analysis
            
        # Очистка Markdown
        import re
        def clean_markdown(text):
            # Удаляем все HTML теги
            text = re.sub(r'<[^>]*>', '', text)
            # Удаляем оставшиеся символы Markdown
            text = re.sub(r'[_~`]', '', text)
            # Заменяем ** на *
            text = re.sub(r'\*\*', '*', text)
            # Удаляем лишние пробелы и переносы строк
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            # Удаляем некорректные символы
            text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\*\(\)\[\]\n\r@#%&+=/<>]', '', text)
            return text.strip()
            
        cleaned_analysis = clean_markdown(truncated_analysis)
        print(f"✅ Анализ очищен, итоговая длина: {len(cleaned_analysis)} символов")
        
        # Форматирование финального сообщения
        final_message = f"📊 *Углубленный анализ GAZP*\n\n{cleaned_analysis}"
        print(f"✅ Финальное сообщение готово, длина: {len(final_message)} символов")
        
        # Проверка длины финального сообщения
        if len(final_message) > 4096:  # Максимальная длина сообщения в Telegram
            print(f"⚠️ Финальное сообщение слишком длинное для Telegram: {len(final_message)} > 4096")
            return False
        else:
            print(f"✅ Финальное сообщение подходит для Telegram: {len(final_message)} <= 4096")
            
        # Вывод первых 200 символов анализа для проверки
        print("\n📄 Первые 200 символов анализа:")
        print(cleaned_analysis[:200] + "..." if len(cleaned_analysis) > 200 else cleaned_analysis)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_analysis_length())
    if success:
        print("\n✅ Тест успешно пройден!")
        sys.exit(0)
    else:
        print("\n❌ Тест не пройден!")
        sys.exit(1)