# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Config Module

Модуль конфигурации приложения.
"""

from .constants import *
from .config import get_settings, settings, validate_config, print_config_summary


def get_moex_config():
    """Получить конфигурацию для MOEX API"""
    return {
        'base_url': settings.moex_base_url,
        'board': settings.moex_board,
        'timeout': 30
    }


__all__ = [
    'get_settings',
    'settings',
    'validate_config',
    'print_config_summary',
    'get_moex_config',
    'MAX_POSITION_SIZE_PERCENT',
    'STOP_LOSS_PERCENT',
    'TAKE_PROFIT_PERCENT',
    'COMMISSION_PERCENT',
    'RSI_PERIOD',
    'MACD_FAST',
    'MACD_SLOW',
    'MACD_SIGNAL'
]