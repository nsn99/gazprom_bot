#!/usr/bin/env python3
"""
Скрипт для принудительной остановки ВСЕХ процессов Python, связанных с ботом
"""
import os
import signal
import subprocess
import sys
import time

def force_kill_all_processes():
    """Принудительно останавливает все процессы"""
    try:
        # Используем pkill для более надежной остановки
        print("🔍 Используем pkill для остановки всех процессов...")
        
        # Останавливаем все процессы python3 с ключевыми словами
        subprocess.run(["pkill", "-f", "gazprom_bot"], check=False)
        subprocess.run(["pkill", "-f", "main.py"], check=False)
        subprocess.run(["pkill", "-f", "run_clean.py"], check=False)
        
        # Ждем немного
        time.sleep(2)
        
        # Проверяем, остались ли процессы
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        lines = result.stdout.split('\n')
        remaining_processes = []
        
        for line in lines:
            if 'python3' in line and ('gazprom_bot' in line or 'main.py' in line or 'run_clean.py' in line):
                parts = line.split()
                if len(parts) > 1:
                    pid = int(parts[1])
                    # Пропускаем текущий процесс
                    if pid != os.getpid():
                        remaining_processes.append(pid)
        
        if remaining_processes:
            print(f"⚠️ Остались процессы: {remaining_processes}")
            print("💀 Используем SIGKILL для принудительной остановки...")
            for pid in remaining_processes:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"✅ Процесс {pid} принудительно остановлен")
                except ProcessLookupError:
                    print(f"⚠️ Процесс {pid} уже не существует")
                except PermissionError:
                    print(f"❌ Нет прав для остановки процесса {pid}")
        else:
            print("✅ Все процессы успешно остановлены")
            
    except Exception as e:
        print(f"❌ Ошибка при остановке процессов: {e}")

if __name__ == "__main__":
    print("🔥 Принудительная остановка всех процессов бота...")
    force_kill_all_processes()
    print("✅ Операция завершена")