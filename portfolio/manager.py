# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Portfolio Manager Module

Модуль для управления портфелями пользователей.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select

from config import settings
from monitoring.logger import get_logger
from database.database import get_db_manager
from database.models import User, Portfolio, Position, Transaction, Recommendation
from data.moex_client import MOEXClient


logger = get_logger(__name__)


class PortfolioManager:
    """Менеджер портфелей"""
    
    def __init__(self):
        """Инициализация менеджера портфелей"""
        self.db_manager = get_db_manager()
        self.moex_client = MOEXClient()
    
    async def create_user(
        self, 
        user_id: int, 
        username: str, 
        initial_capital: float
    ) -> User:
        """
        Создать нового пользователя с портфелем
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            initial_capital: Начальный капитал
            
        Returns:
            Объект пользователя
        """
        try:
            user = await self.db_manager.create_user(
                user_id=user_id,
                username=username,
                initial_capital=initial_capital
            )
            
            logger.info(f"Создан пользователь {user_id} с капиталом {initial_capital}")
            return user
            
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
            raise
    
    async def get_portfolio(self, user_id: int) -> Optional[Portfolio]:
        """
        Получить портфель пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Объект портфеля или None
        """
        try:
            portfolio = await self.db_manager.get_portfolio(user_id)
            
            if portfolio:
                # Получаем позиции для портфеля
                positions = await self.get_positions(portfolio.id)
                gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
                
                # Обновление текущей цены в позициях
                async with self.moex_client:
                    current_price = await self.moex_client.get_current_price("GAZP")
                if current_price and gazp_position:
                    gazp_position.current_price = current_price
                    
                    # Расчет нереализованной прибыли/убытка
                    if gazp_position.shares > 0 and gazp_position.avg_purchase_price:
                        gazp_position.unrealized_pnl = (
                            (current_price - float(gazp_position.avg_purchase_price)) * gazp_position.shares
                        )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Ошибка при получении портфеля пользователя {user_id}: {e}")
            return None
    
    async def execute_trade(
        self,
        user_id: int,
        action: str,
        ticker: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        recommendation_id: Optional[int] = None
    ) -> Transaction:
        """
        Исполнить торговую операцию
        
        Args:
            user_id: ID пользователя
            action: Действие (BUY/SELL)
            ticker: Тикер акции
            quantity: Количество акций
            price: Цена акции
            stop_loss: Стоп-лосс
            take_profit: Тейк-профит
            ai_recommendation: AI рекомендация
            
        Returns:
            Объект транзакции
        """
        try:
            # Получение пользователя и портфеля
            user = await self.db_manager.get_user(user_id)
            if not user:
                raise ValueError(f"Пользователь {user_id} не найден")
            
            portfolio = await self.db_manager.get_portfolio(user_id)
            if not portfolio:
                raise ValueError(f"Портфель пользователя {user_id} не найден")
            
            # Получаем позиции для портфеля
            positions = await self.get_positions(portfolio.id)
            gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
            
            # Если позиции нет, создаем ее
            if not gazp_position:
                gazp_position = Position(
                    portfolio_id=portfolio.id,
                    ticker="GAZP",
                    shares=0,
                    avg_purchase_price=0.0
                )
                # В реальном коде здесь нужно было бы сохранить позицию в БД
            
            total_amount = quantity * price
            
            # Проверка и исполнение сделки
            if action == "BUY":
                if float(portfolio.current_cash) < total_amount:
                    raise ValueError(f"Недостаточно средств: нужно {total_amount}, доступно {portfolio.current_cash}")
                
                # Обновление денежных средств
                portfolio.current_cash = float(portfolio.current_cash) - total_amount
                
                # Обновление позиции
                if gazp_position.shares == 0:
                    # Первая покупка
                    new_shares = quantity
                    new_avg_price = price
                else:
                    # Докупка
                    total_cost = (gazp_position.shares * float(gazp_position.avg_purchase_price)) + total_amount
                    new_shares = gazp_position.shares + quantity
                    new_avg_price = total_cost / new_shares
                
                gazp_position.shares = new_shares
                gazp_position.avg_purchase_price = new_avg_price
                
            elif action == "SELL":
                if gazp_position.shares < quantity:
                    raise ValueError(f"Недостаточно акций: нужно {quantity}, доступно {gazp_position.shares}")
                
                # Обновление денежных средств
                portfolio.current_cash = float(portfolio.current_cash) + total_amount
                
                # Обновление позиции
                gazp_position.shares -= quantity
                
                # Если все акции проданы, сброс средней цены
                if gazp_position.shares == 0:
                    gazp_position.avg_purchase_price = 0.0
            
            else:
                raise ValueError(f"Неверное действие: {action}")
            
            # Сохранение изменений
            # В реальном коде здесь нужно было бы обновить портфель и позицию в БД
            
            # Создание транзакции
            transaction = await self.db_manager.create_transaction(
                portfolio_id=portfolio.id,
                action=action,
                ticker=ticker,
                shares=quantity,
                price=price,
                total_amount=total_amount,
                recommendation_id=recommendation_id
            )
            
            logger.info(f"Исполнена сделка: {user_id} {action} {quantity} {ticker} по {price}")
            return transaction
            
        except Exception as e:
            logger.error(f"Ошибка при исполнении сделки: {e}")
            raise
    
    async def get_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Получить сводку портфеля
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Сводка портфеля
        """
        try:
            user = await self.db_manager.get_user(user_id)
            portfolio = await self.db_manager.get_portfolio(user_id)
            
            if not user or not portfolio:
                return {}
            
            # Получаем позиции для портфеля
            positions = await self.get_positions(portfolio.id)
            gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
            
            shares = gazp_position.shares if gazp_position else 0
            avg_price = float(gazp_position.avg_purchase_price) if gazp_position and gazp_position.avg_purchase_price else 0.0
            
            # Получение текущей цены
            async with self.moex_client:
                current_price = await self.moex_client.get_current_price("GAZP")
            if not current_price:
                current_price = 0.0
            
            # Расчет показателей
            shares_value = shares * current_price
            total_value = float(portfolio.current_cash) + shares_value
            pnl = total_value - float(portfolio.initial_capital)
            pnl_percent = (pnl / float(portfolio.initial_capital)) * 100 if portfolio.initial_capital > 0 else 0
            
            return {
                "user_id": user_id,
                "cash": float(portfolio.current_cash),
                "shares": shares,
                "avg_price": avg_price,
                "current_price": current_price,
                "shares_value": shares_value,
                "total_value": total_value,
                "initial_capital": float(portfolio.initial_capital),
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "unrealized_pnl": float(gazp_position.unrealized_pnl) if gazp_position and gazp_position.unrealized_pnl else 0.0
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении сводки портфеля {user_id}: {e}")
            return {}
    
    async def get_transaction_history(
        self, 
        user_id: int, 
        limit: int = 50
    ) -> List[Transaction]:
        """
        Получить историю транзакций
        
        Args:
            user_id: ID пользователя
            limit: Ограничение количества записей
            
        Returns:
            Список транзакций
        """
        try:
            return await self.db_manager.get_transaction_history(user_id, limit)
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории транзакций {user_id}: {e}")
            return []
    
    async def get_positions(self, portfolio_id: int) -> List[Position]:
        """
        Получить позиции портфеля
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список позиций
        """
        try:
            async with await self.db_manager.get_session() as session:
                stmt = select(Position).where(Position.portfolio_id == portfolio_id)
                result = await session.execute(stmt)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"Ошибка при получении позиций портфеля {portfolio_id}: {e}")
            return []
    
    async def save_recommendation(
        self,
        user_id: int,
        recommendation: Dict[str, Any]
    ) -> Recommendation:
        """
        Сохранить AI рекомендацию
        
        Args:
            user_id: ID пользователя
            recommendation: Рекомендация
            
        Returns:
            Объект рекомендации
        """
        try:
            return await self.db_manager.save_ai_recommendation(user_id, recommendation)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении рекомендации {user_id}: {e}")
            raise
    
    async def get_performance_metrics(
        self, 
        user_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Получить метрики производительности
        
        Args:
            user_id: ID пользователя
            days: Период в днях
            
        Returns:
            Метрики производительности
        """
        try:
            # Получение истории транзакций
            transactions = await self.get_transaction_history(user_id, limit=1000)
            
            if not transactions:
                return {}
            
            # Фильтрация транзакций за период
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_transactions = [
                t for t in transactions 
                if t.timestamp >= cutoff_date
            ]
            
            # Расчет метрик
            total_trades = len(recent_transactions)
            buy_trades = len([t for t in recent_transactions if t.action == "BUY"])
            sell_trades = len([t for t in recent_transactions if t.action == "SELL"])
            
            total_volume = sum(t.total_amount for t in recent_transactions)
            avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
            
            # Получение текущей стоимости портфеля
            portfolio_summary = await self.get_portfolio_summary(user_id)
            
            return {
                "period_days": days,
                "total_trades": total_trades,
                "buy_trades": buy_trades,
                "sell_trades": sell_trades,
                "total_volume": total_volume,
                "avg_trade_size": avg_trade_size,
                "current_value": portfolio_summary.get("total_value", 0),
                "pnl": portfolio_summary.get("pnl", 0),
                "pnl_percent": portfolio_summary.get("pnl_percent", 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при расчете метрик производительности {user_id}: {e}")
            return {}
    
    async def get_risk_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        Получить метрики риска
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Метрики риска
        """
        try:
            portfolio_summary = await self.get_portfolio_summary(user_id)
            
            if not portfolio_summary:
                return {}
            
            cash = portfolio_summary.get("cash", 0)
            shares = portfolio_summary.get("shares", 0)
            current_price = portfolio_summary.get("current_price", 0)
            total_value = portfolio_summary.get("total_value", 0)
            
            # Концентрация позиции
            position_value = shares * current_price
            concentration = (position_value / total_value * 100) if total_value > 0 else 0
            
            # Уровень ликвидности
            liquidity = (cash / total_value * 100) if total_value > 0 else 0
            
            # Потенциальный риск (10% падение цены)
            potential_loss = position_value * 0.1
            potential_loss_percent = (potential_loss / total_value * 100) if total_value > 0 else 0
            
            return {
                "concentration_percent": concentration,
                "liquidity_percent": liquidity,
                "potential_loss": potential_loss,
                "potential_loss_percent": potential_loss_percent,
                "risk_level": self._assess_risk_level(concentration, liquidity)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при расчете метрик риска {user_id}: {e}")
            return {}
    
    def _assess_risk_level(self, concentration: float, liquidity: float) -> str:
        """
        Оценить уровень риска
        
        Args:
            concentration: Концентрация позиции в %
            liquidity: Ликвидность в %
            
        Returns:
            Уровень риска (LOW/MEDIUM/HIGH)
        """
        if concentration > 70 or liquidity < 10:
            return "HIGH"
        elif concentration > 50 or liquidity < 20:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def update_user_settings(
        self, 
        user_id: int, 
        **kwargs
    ) -> bool:
        """
        Обновить настройки пользователя
        
        Args:
            user_id: ID пользователя
            **kwargs: Параметры для обновления
            
        Returns:
            True в случае успеха
        """
        try:
            return await self.db_manager.update_user_settings(user_id, **kwargs)
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении настроек пользователя {user_id}: {e}")
            return False
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить настройки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Настройки пользователя или None
        """
        try:
            settings_obj = await self.db_manager.get_user_settings(user_id)
            
            if settings_obj:
                return {
                    "risk_limit_percent": settings_obj.risk_limit_percent,
                    "max_position_size_percent": settings_obj.max_position_size_percent,
                    "auto_execute": settings_obj.auto_execute,
                    "notifications_enabled": settings_obj.notifications_enabled
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении настроек пользователя {user_id}: {e}")
            return None