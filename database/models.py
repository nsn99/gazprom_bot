"""
Модели данных для SQLite базы данных Telegram Trading Bot.

Использует SQLAlchemy для ORM и определения схемы базы данных.
Поддерживает миграции и версии схемы.

Таблицы:
- users: информация о пользователях Telegram
- portfolios: портфели пользователей
- positions: текущие позиции
- transactions: история транзакций
- recommendations: AI рекомендации от GPT-5
- user_settings: настройки пользователей
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    Column, BigInteger, String, DateTime, Boolean, Integer, 
    DECIMAL, ForeignKey, JSON, Text, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    telegram_username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Отношения
    portfolios = relationship("Portfolio", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    recommendations = relationship("Recommendation", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.telegram_username})>"


class Portfolio(Base):
    """Модель портфеля"""
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), default='Основной')
    initial_capital = Column(DECIMAL(15, 2), default=100000.00)
    current_cash = Column(DECIMAL(15, 2), default=100000.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")
    
    @property
    def total_value(self) -> float:
        """Общая стоимость портфеля"""
        positions_value = sum(pos.current_value or 0 for pos in self.positions)
        return float(self.current_cash or 0) + positions_value
    
    @property
    def total_pnl(self) -> float:
        """Общий P&L портфеля"""
        return self.total_value - float(self.initial_capital or 0)
    
    @property
    def total_pnl_percent(self) -> float:
        """Общий P&L портфеля в процентах"""
        if self.initial_capital and self.initial_capital > 0:
            return (self.total_pnl / float(self.initial_capital)) * 100
        return 0.0
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Position(Base):
    """Модель позиции"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    ticker = Column(String(10), default='GAZP')
    shares = Column(Integer, default=0)
    avg_purchase_price = Column(DECIMAL(10, 2))
    current_price = Column(DECIMAL(10, 2))
    unrealized_pnl = Column(DECIMAL(15, 2), default=0.00)
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    portfolio = relationship("Portfolio", back_populates="positions")
    
    @property
    def current_value(self) -> Optional[float]:
        """Текущая стоимость позиции"""
        if self.shares and self.current_price:
            return float(self.shares) * float(self.current_price)
        return None
    
    @property
    def pnl_percent(self) -> float:
        """P&L в процентах"""
        if self.avg_purchase_price and self.avg_purchase_price > 0 and self.current_price:
            return ((float(self.current_price) - float(self.avg_purchase_price)) / 
                   float(self.avg_purchase_price)) * 100
        return 0.0
    
    def __repr__(self):
        return f"<Position(id={self.id}, ticker={self.ticker}, shares={self.shares})>"


class Transaction(Base):
    """Модель транзакции"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    action = Column(String(4), nullable=False)  # BUY или SELL
    ticker = Column(String(10), default='GAZP')
    shares = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    commission = Column(DECIMAL(10, 2), default=0.00)
    slippage = Column(DECIMAL(10, 2), default=0.00)
    reason = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'))
    
    # Отношения
    portfolio = relationship("Portfolio", back_populates="transactions")
    recommendation = relationship("Recommendation", back_populates="transactions")
    
    @property
    def net_amount(self) -> float:
        """Чистая сумма с учетом комиссии"""
        if self.action == 'BUY':
            return float(self.total_amount) + float(self.commission or 0)
        else:
            return float(self.total_amount) - float(self.commission or 0)
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, action={self.action}, shares={self.shares})>"


class Recommendation(Base):
    """Модель AI рекомендации"""
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    action = Column(String(4), nullable=False)  # BUY, SELL, HOLD
    quantity = Column(Integer)
    price = Column(DECIMAL(10, 2))
    stop_loss = Column(DECIMAL(10, 2))
    take_profit = Column(DECIMAL(10, 2))
    reasoning = Column(String(2000))
    risk_level = Column(String(10))  # LOW, MEDIUM, HIGH
    confidence = Column(Integer)  # 0-100
    status = Column(String(20), default='pending')  # pending, confirmed, rejected, expired
    market_data = Column(JSON)  # Рыночные данные в JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Отношения
    user = relationship("User", back_populates="recommendations")
    transactions = relationship("Transaction", back_populates="recommendation")
    
    @property
    def is_expired(self) -> bool:
        """Проверка истечения срока действия"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def __repr__(self):
        return f"<Recommendation(id={self.id}, action={self.action}, status={self.status})>"


class UserSettings(Base):
    """Модель настроек пользователя"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, unique=True)
    risk_profile = Column(String(20), default='medium')  # conservative, moderate, aggressive
    max_position_size = Column(DECIMAL(15, 2), default=30000.00)
    stop_loss_pct = Column(DECIMAL(5, 4), default=0.0080)  # 0.8%
    take_profit_pct = Column(DECIMAL(5, 4), default=0.0150)  # 1.5%
    auto_confirm = Column(Boolean, default=False)
    notification_frequency = Column(String(20), default='manual')  # manual, daily, weekly
    preferences = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(id={self.id}, user_id={self.user_id}, risk_profile={self.risk_profile})>"


class AnalyticsEvent(Base):
    """Модель для аналитики событий"""
    __tablename__ = 'analytics_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    event_type = Column(String(50))
    event_data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, event_type={self.event_type})>"


class PerformanceMetric(Base):
    """Модель для метрик производительности"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'))
    date = Column(DateTime)
    total_return = Column(DECIMAL(10, 4))
    benchmark_return = Column(DECIMAL(10, 4))
    alpha = Column(DECIMAL(10, 4))
    volatility = Column(DECIMAL(10, 4))
    sharpe_ratio = Column(DECIMAL(10, 4))
    max_drawdown = Column(DECIMAL(10, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PerformanceMetric(id={self.id}, date={self.date}, total_return={self.total_return})>"


# Перечисления для улучшения типизации
class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TransactionAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class NotificationFrequency(str, Enum):
    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"


__all__ = [
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
    'NotificationFrequency'
]