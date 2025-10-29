#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для чистого запуска бота без конфликтов
"""

import os
import sys
import signal
import subprocess
import time

def kill_existing_bots():
    """Завершить все существующие процессы бота"""
    print("🔍 Поиск существующих процессов бота...")
    
    # Поиск и завершение процессов python3 main.py
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            if 'python3 main.py' in line and 'grep' not in line:
                pid = line.split()[1]
                processes.append(pid)
        
        if processes:
            print(f"🛑 Найдено процессов: {len(processes)}")
            for pid in processes:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"  ✅ Завершен процесс {pid}")
                except:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"  🔒 Принудительно завершен процесс {pid}")
                    except:
                        print(f"  ❌ Не удалось завершить процесс {pid}")
            
            # Даем время на завершение
            time.sleep(2)
        else:
            print("✅ Активных процессов не найдено")
            
    except Exception as e:
        print(f"❌ Ошибка при поиске процессов: {e}")

def main():
    """Основная функция"""
    print("🚀 Запуск Gazprom Trading Bot (чистый запуск)...")
    
    # Завершаем существующие процессы
    kill_existing_bots()
    
    # Устанавливаем переменные окружения
    os.environ['PYTHONPATH'] = os.getcwd()
    
    print("📋 Запуск бота...")
    
    # Запускаем бота
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    main()