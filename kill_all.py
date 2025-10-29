#!/usr/bin/env python3
"""
Скрипт для принудительной остановки всех процессов Python, связанных с ботом
"""
import os
import signal
import subprocess
import sys

def find_and_kill_bot_processes():
    """Находит и останавливает все процессы, связанные с ботом"""
    try:
        # Находим все процессы Python, запущенные из директории gazprom_bot
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        lines = result.stdout.split('\n')
        pids_to_kill = []
        
        for line in lines:
            if 'python3' in line and ('gazprom_bot' in line or 'main.py' in line or 'run_clean.py' in line):
                parts = line.split()
                if len(parts) > 1:
                    pid = int(parts[1])
                    # Пропускаем текущий процесс
                    if pid != os.getpid():
                        pids_to_kill.append(pid)
        
        # Останавливаем найденные процессы
        for pid in pids_to_kill:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"✅ Процесс {pid} остановлен")
            except ProcessLookupError:
                print(f"⚠️ Процесс {pid} уже не существует")
            except PermissionError:
                print(f"❌ Нет прав для остановки процесса {pid}")
        
        if pids_to_kill:
            print(f"🛑 Всего остановлено процессов: {len(pids_to_kill)}")
        else:
            print("ℹ️ Активные процессы бота не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка при поиске процессов: {e}")

if __name__ == "__main__":
    print("🔍 Поиск активных процессов бота...")
    find_and_kill_bot_processes()
    print("✅ Операция завершена")