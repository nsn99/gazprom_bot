#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for Gazprom Trading Bot
"""

import sys
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports...")

try:
    from config import settings
    print("✓ Config import: OK")
except Exception as e:
    print("✗ Config import error:", str(e))

try:
    from monitoring.logger import get_logger, setup_logging
    print("✓ Logger import: OK")
except Exception as e:
    print("✗ Logger import error:", str(e))

try:
    from database.database import init_database, get_db_manager
    print("✓ Database import: OK")
except Exception as e:
    print("✗ Database import error:", str(e))

try:
    from telegram.bot import create_application
    print("✓ Telegram bot import: OK")
except Exception as e:
    print("✗ Telegram bot import error:", str(e))

print("All imports tested.")