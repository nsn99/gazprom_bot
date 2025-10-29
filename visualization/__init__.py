"""
Модуль визуализации графиков и отчетов для Telegram бота.

Предоставляет:
- Генерацию графиков цен и технических индикаторов
- Визуализацию производительности портфеля
- Создание отчетов в формате изображений
- Интерактивные графики с Plotly
"""

from .chart_generator import (
    ChartGenerator,
    ChartData,
    PortfolioChartData,
    get_chart_generator
)

__all__ = [
    'ChartGenerator',
    'ChartData',
    'PortfolioChartData',
    'get_chart_generator'
]