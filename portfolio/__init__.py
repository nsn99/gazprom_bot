"""
Модуль управления портфелями для Telegram Trading Bot.

Предоставляет функциональность для:
- Управления портфелями пользователей
- Расчета P&L и метрик
- Исполнения транзакций
- Валидации операций
"""

from .manager import PortfolioManager

__all__ = [
    'PortfolioManager',
    'get_portfolio_manager'
]