"""
Модуль интеграции существующей торговой логики с Telegram интерфейсом.

Предоставляет адаптеры и мосты для взаимодействия между:
- Существующим торговым движком
- Портфельным менеджером
- Telegram интерфейсом
- AI рекомендательной системой
"""

from .trading_adapter import (
    TradingAdapter,
    TradingSignal,
    MarketDataSnapshot,
    get_trading_adapter
)

__all__ = [
    'TradingAdapter',
    'TradingSignal',
    'MarketDataSnapshot',
    'get_trading_adapter'
]