"""
Gazprom Trading Bot

Telegram бот для торговли акциями Газпром (GAZP) на MOEX 
с использованием GPT-5 через AgentRouter API.
"""

__version__ = "1.0.0"
__author__ = "Gazprom Trading Bot Team"
__description__ = "AI-powered trading bot for Gazprom stocks on MOEX"

# Импорт основных компонентов
from config import settings, constants
from monitoring.logger import get_logger

logger = get_logger(__name__)

logger.info(f"Gazprom Trading Bot v{__version__} initialized")
