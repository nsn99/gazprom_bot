"""
Модуль базы данных для Telegram Trading Bot.

Предоставляет:
- Модели данных SQLAlchemy
- Управление базой данных
- CRUD операции
- Миграции схемы
"""

from .models import (
    Base, User, Portfolio, Position, Transaction, Recommendation, 
    UserSettings, AnalyticsEvent, PerformanceMetric,
    RiskProfile, RecommendationStatus, TransactionAction, NotificationFrequency
)
from .database import DatabaseManager, get_db_manager, init_database

__all__ = [
    # Models
    'Base',
    'User',
    'Portfolio', 
    'Position',
    'Transaction',
    'Recommendation',
    'UserSettings',
    'AnalyticsEvent',
    'PerformanceMetric',
    'RiskProfile',
    'RecommendationStatus',
    'TransactionAction',
    'NotificationFrequency',
    
    # Database management
    'DatabaseManager',
    'get_db_manager',
    'init_database'
]