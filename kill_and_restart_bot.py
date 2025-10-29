#!/usr/bin/env python3
"""
Скрипт для принудительного завершения всех процессов Python и запуска одного экземпляра бота
"""

import os
import sys
import subprocess
import time
import signal

def kill_python_processes():
    """Завершить все процессы Python, связанные с ботом"""
    print("🔍 Поиск процессов Python...")
    
    # Находим все процессы Python
    try:
        # Для macOS/Linux
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        python_pids = []
        for line in lines:
            if 'python' in line and ('main.py' in line or 'gazprom_bot' in line):
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    try:
                        python_pids.append(int(pid))
                    except ValueError:
                        continue
        
        if python_pids:
            print(f"🔪 Найдено процессов Python: {python_pids}")
            
            # Завершаем процессы
            for pid in python_pids:
                try:
                    print(f"🔪 Завершение процесса {pid}...")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                except ProcessLookupError:
                    print(f"⚠️ Процесс {pid} уже завершен")
                except PermissionError:
                    print(f"⚠️ Нет прав для завершения процесса {pid}")
            
            # Проверяем, завершились ли процессы
            time.sleep(2)
            remaining_pids = []
            for pid in python_pids:
                try:
                    os.kill(pid, 0)  # Проверяем, существует ли процесс
                    remaining_pids.append(pid)
                except ProcessLookupError:
                    pass
            
            if remaining_pids:
                print(f"⚠️ Некоторые процессы все еще активны: {remaining_pids}")
                print("🔪 Принудительное завершение...")
                for pid in remaining_pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        else:
            print("✅ Активные процессы Python не найдены")
            
    except Exception as e:
        print(f"❌ Ошибка при поиске процессов: {e}")

def start_bot():
    """Запустить бота"""
    print("🚀 Запуск бота...")
    
    # Переходим в директорию проекта
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Запускаем бота
    try:
        subprocess.run([sys.executable, 'main.py'], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")

if __name__ == "__main__":
    print("🔄 Перезапуск Telegram бота для акций Газпром")
    print("=" * 50)
    
    # Завершаем все процессы Python
    kill_python_processes()
    
    # Ждем немного
    time.sleep(3)
    
    # Запускаем бота
    start_bot()