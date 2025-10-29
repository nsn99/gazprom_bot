#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для диагностики данных MOEX API по GAZP
"""

import asyncio
import json
from datetime import datetime
from data.moex_client import MOEXClient


async def debug_moex_gazp():
    """Диагностика данных MOEX по GAZP"""
    print("🔍 Диагностика MOEX API для GAZP...")
    
    async with MOEXClient() as moex:
        try:
            # 1. Тест L1 данных
            print("\n1. 📊 Тест L1 данных:")
            l1_data = await moex.get_marketdata_l1("GAZP")
            print(f"   LAST: {l1_data.last}")
            print(f"   BID: {l1_data.bid}")
            print(f"   ASK: {l1_data.ask}")
            print(f"   VOLTODAY: {l1_data.voltoday}")
            print(f"   OPEN: {l1_data.open_price}")
            print(f"   HIGH: {l1_data.high}")
            print(f"   LOW: {l1_data.low}")
            
            # 2. Тест исторических свечей
            print("\n2. 📈 Тест исторических свечей:")
            candles_df = await moex.get_historical_candles("GAZP", interval=1)
            if not candles_df.empty:
                print(f"   Последняя цена: {candles_df['close'].iloc[-1] if len(candles_df) > 0 else 'N/A'}")
                print(f"   Объем: {candles_df['volume'].iloc[-1] if len(candles_df) > 0 else 'N/A'}")
                print(f"   High: {candles_df['high'].iloc[-1] if len(candles_df) > 0 else 'N/A'}")
                print(f"   Low: {candles_df['low'].iloc[-1] if len(candles_df) > 0 else 'N/A'}")
                print(f"   Всего свечей: {len(candles_df)}")
            else:
                print("   Нет данных свечей")
            
            # 3. Тест технических индикаторов
            print("\n3. 📈 Тест технических индикаторов:")
            indicators = await moex.get_technical_indicators("GAZP")
            if indicators:
                for key, value in indicators.items():
                    print(f"   {key}: {value}")
            else:
                print("   Нет данных индикаторов")
            
            # 4. Тест информации об инструменте
            print("\n4. ℹ️ Тест информации об инструменте:")
            try:
                security_info = await moex.get_security_info("GAZP")
                print(f"   Имя: {security_info.shortname}")
                print(f"   Лот: {security_info.lotsize}")
                print(f"   Статус: {security_info.status}")
            except Exception as e:
                print(f"   Ошибка: {e}")
            
            # 5. Проверка времени работы биржи
            print(f"\n5. ⏰ Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("   Проверка, работает ли биржа в текущее время...")
            
            # 6. Тест разных эндпоинтов
            print("\n6. 🔗 Тест разных эндпоинтов:")
            
            # Тест основного эндпоинта
            try:
                main_url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/GAZP.json"
                async with moex.session.get(main_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   Основной эндпоинт статус: {response.status}")
                        if 'marketdata' in data and 'data' in data['marketdata']:
                            market_data = data['marketdata']['data']
                            if market_data:
                                print(f"   Данные найдены: {len(market_data)} записей")
                            else:
                                print("   Данные не найдены")
                        else:
                            print("   Нет marketdata в ответе")
                    else:
                        print(f"   Основной эндпоинт ошибка: {response.status}")
            except Exception as e:
                print(f"   Основной эндпоинт исключение: {e}")
            
        except Exception as e:
            print(f"\n❌ Общая ошибка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_moex_gazp())