#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с MOEX API
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from data.moex_client import MOEXClient
from config.config import settings


async def test_moex_integration():
    """Тестирование интеграции с MOEX API"""
    print("Тестирование интеграции с MOEX API...")
    
    # Получаем конфигурацию
    print(f"MOEX Base URL: {settings.moex_base_url}")
    print(f"MOEX Board: {settings.moex_board}")
    
    # Создаем клиент
    client = MOEXClient()
    
    try:
        # Используем контекстный менеджер для клиента
        async with client:
            # Тест получения текущей цены
            print("\n1. Получение текущей цены GAZP...")
            l1_data = await client.get_marketdata_l1("GAZP")
            if l1_data and l1_data.last:
                print(f"   Текущая цена GAZP: {l1_data.last} RUB")
                print(f"   Bid: {l1_data.bid} RUB")
                print(f"   Ask: {l1_data.ask} RUB")
                print(f"   Объем: {l1_data.voltoday}")
            else:
                print("   Не удалось получить текущую цену")
            
            # Тест получения исторических данных
            print("\n2. Получение исторических данных GAZP...")
            historical_data = await client.get_historical_candles("GAZP", from_date="2024-10-01")
            if historical_data is not None and not historical_data.empty:
                print(f"   Получено {len(historical_data)} записей")
                print(f"   Последняя запись:\n{historical_data.tail(1).to_string()}")
            else:
                print("   Не удалось получить исторические данные")
            
            # Тест получения индекса IMOEX
            print("\n3. Получение данных индекса IMOEX...")
            imoex_data = await client.get_index_data("IMOEX")
            if imoex_data:
                print(f"   Текущее значение IMOEX: {imoex_data.get('last', 'N/A')}")
                print(f"   Изменение: {imoex_data.get('change', 'N/A')}")
                print(f"   Изменение %: {imoex_data.get('change_percent', 'N/A')}")
            else:
                print("   Не удалось получить данные индекса IMOEX")
        
        print("\n✅ Тестирование MOEX API завершено успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании MOEX API: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_moex_integration())