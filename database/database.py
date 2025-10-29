"""
Gazprom Trading Bot - Database Module

Модуль для работы с базой данных SQLite.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from monitoring.logger import get_logger
from database.models import Base, User, Portfolio, Position, Transaction, Recommendation, UserSettings


logger = get_logger(__name__)


class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        """Инициализация менеджера базы данных"""
        self.engine = None
        self.session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализация базы данных"""
        if self._initialized:
            return
        
        try:
            # Создание асинхронного движка
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Создание фабрики сессий
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Создание таблиц
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Получить сессию базы данных"""
        if not self._initialized:
            await self.initialize()
        
        return self.session_factory()
    
    async def close(self):
        """Закрыть соединение с базой данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Соединение с базой данных закрыто")
    
    async def create_user(
        self, 
        user_id: int, 
        username: str, 
        initial_capital: float
    ) -> User:
        """
        Создать нового пользователя
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            initial_capital: Начальный капитал
            
        Returns:
            Объект пользователя
        """
        async with await self.get_session() as session:
            try:
                # Проверка существования пользователя
                existing_user = await session.get(User, user_id)
                if existing_user:
                    logger.warning(f"Пользователь {user_id} уже существует")
                    return existing_user
                
                # Создание пользователя
                user = User(
                    id=user_id,
                    telegram_username=username
                )
                
                session.add(user)
                
                # Создание портфеля
                portfolio = Portfolio(
                    user_id=user_id,
                    name="Основной",
                    initial_capital=initial_capital,
                    current_cash=initial_capital
                )
                
                session.add(portfolio)
                await session.flush()  # Получаем ID портфеля без коммита
                
                # Создание позиции
                position = Position(
                    portfolio_id=portfolio.id,
                    ticker="GAZP",
                    shares=0,
                    avg_purchase_price=0.0
                )
                
                session.add(position)
                
                # Создание настроек
                user_settings = UserSettings(
                    user_id=user_id
                )
                
                session.add(user_settings)
                
                await session.commit()
                await session.refresh(user)
                
                logger.info(f"Создан новый пользователь: {user_id}")
                return user
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при создании пользователя {user_id}: {e}")
                raise
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя по ID
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Объект пользователя или None
        """
        async with await self.get_session() as session:
            try:
                stmt = select(User).where(User.user_id == user_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
                return None
    
    async def get_portfolio(self, user_id: int) -> Optional[Portfolio]:
        """
        Получить портфель пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Объект портфеля или None
        """
        async with await self.get_session() as session:
            try:
                stmt = select(Portfolio).where(Portfolio.user_id == user_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении портфеля пользователя {user_id}: {e}")
                return None
    
    async def update_portfolio(
        self, 
        user_id: int, 
        shares: int, 
        avg_price: float
    ) -> bool:
        """
        Обновить портфель пользователя
        
        Args:
            user_id: ID пользователя
            shares: Количество акций
            avg_price: Средняя цена покупки
            
        Returns:
            True в случае успеха
        """
        async with await self.get_session() as session:
            try:
                stmt = select(Portfolio).where(Portfolio.user_id == user_id)
                result = await session.execute(stmt)
                portfolio = result.scalar_one_or_none()
                
                if not portfolio:
                    return False
                
                portfolio.shares = shares
                portfolio.avg_purchase_price = avg_price
                portfolio.updated_at = datetime.utcnow()
                
                await session.commit()
                return True
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при обновлении портфеля пользователя {user_id}: {e}")
                return False
    
    async def create_transaction(
        self,
        portfolio_id: int,
        action: str,
        ticker: str,
        shares: int,
        price: float,
        total_amount: float,
        recommendation_id: Optional[int] = None
    ) -> Transaction:
        """
        Создать транзакцию
        
        Args:
            portfolio_id: ID портфеля
            action: Действие (BUY/SELL)
            ticker: Тикер акции
            shares: Количество акций
            price: Цена акции
            total_amount: Общая сумма
            recommendation_id: ID AI рекомендации
            
        Returns:
            Объект транзакции
        """
        async with await self.get_session() as session:
            try:
                transaction = Transaction(
                    portfolio_id=portfolio_id,
                    action=action,
                    ticker=ticker,
                    shares=shares,
                    price=price,
                    total_amount=total_amount,
                    recommendation_id=recommendation_id
                )
                
                session.add(transaction)
                await session.commit()
                await session.refresh(transaction)
                
                logger.info(f"Создана транзакция: портфель {portfolio_id} {action} {shares} {ticker}")
                return transaction
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при создании транзакции: {e}")
                raise
    
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
        async with await self.get_session() as session:
            try:
                # Сначала получаем портфель пользователя
                portfolio_stmt = select(Portfolio).where(Portfolio.user_id == user_id)
                portfolio_result = await session.execute(portfolio_stmt)
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return []
                
                # Затем получаем транзакции для этого портфеля
                stmt = (
                    select(Transaction)
                    .where(Transaction.portfolio_id == portfolio.id)
                    .order_by(desc(Transaction.timestamp))
                    .limit(limit)
                )
                result = await session.execute(stmt)
                return result.scalars().all()
                
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении истории транзакций пользователя {user_id}: {e}")
                return []
    
    async def save_ai_recommendation(
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
        async with await self.get_session() as session:
            try:
                ai_rec = Recommendation(
                    user_id=user_id,
                    action=recommendation.get("action", "HOLD"),
                    quantity=recommendation.get("quantity"),
                    price=recommendation.get("price"),
                    stop_loss=recommendation.get("stop_loss"),
                    take_profit=recommendation.get("take_profit"),
                    reasoning=recommendation.get("reasoning"),
                    risk_level=recommendation.get("risk_level", "MEDIUM"),
                    confidence=recommendation.get("confidence", 50),
                    market_data=recommendation.get("market_data", {})
                )
                
                session.add(ai_rec)
                await session.commit()
                await session.refresh(ai_rec)
                
                return ai_rec
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при сохранении AI рекомендации: {e}")
                raise
    
    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Получить настройки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Настройки пользователя или None
        """
        async with await self.get_session() as session:
            try:
                stmt = select(UserSettings).where(UserSettings.user_id == user_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
                
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении настроек пользователя {user_id}: {e}")
                return None
    
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
        async with await self.get_session() as session:
            try:
                stmt = select(UserSettings).where(UserSettings.user_id == user_id)
                result = await session.execute(stmt)
                settings_obj = result.scalar_one_or_none()
                
                if not settings_obj:
                    return False
                
                for key, value in kwargs.items():
                    if hasattr(settings_obj, key):
                        setattr(settings_obj, key, value)
                
                await session.commit()
                return True
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при обновлении настроек пользователя {user_id}: {e}")
                return False
    
    async def get_daily_statistics(self) -> Dict[str, Any]:
        """
        Получить дневную статистику
        
        Returns:
            Статистика за день
        """
        async with await self.get_session() as session:
            try:
                today = datetime.utcnow().date()
                
                # Количество новых пользователей
                new_users_stmt = (
                    select(func.count(User.user_id))
                    .where(func.date(User.created_at) == today)
                )
                new_users_result = await session.execute(new_users_stmt)
                new_users = new_users_result.scalar()
                
                # Количество транзакций
                transactions_stmt = (
                    select(func.count(Transaction.id))
                    .where(func.date(Transaction.timestamp) == today)
                )
                transactions_result = await session.execute(transactions_stmt)
                transactions = transactions_result.scalar()
                
                # Количество AI рекомендаций
                recommendations_stmt = (
                    select(func.count(Recommendation.id))
                    .where(func.date(Recommendation.created_at) == today)
                )
                recommendations_result = await session.execute(recommendations_stmt)
                recommendations = recommendations_result.scalar()
                
                return {
                    "date": today.isoformat(),
                    "new_users": new_users or 0,
                    "transactions": transactions or 0,
                    "ai_recommendations": recommendations or 0
                }
                
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении дневной статистики: {e}")
                return {}
    
    async def cleanup_old_data(self, days: int = 90):
        """
        Очистка старых данных
        
        Args:
            days: Количество дней для хранения данных
        """
        async with await self.get_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Удаление старых AI рекомендаций
                old_recommendations_stmt = (
                    Recommendation.__table__
                    .delete()
                    .where(Recommendation.created_at < cutoff_date)
                )
                await session.execute(old_recommendations_stmt)
                
                await session.commit()
                logger.info(f"Удалены данные старше {days} дней")
                
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при очистке старых данных: {e}")


# Глобальный экземпляр менеджера базы данных
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Получить глобальный экземпляр менеджера базы данных"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database():
    """Инициализация базы данных"""
    db_manager = get_db_manager()
    await db_manager.initialize()


async def close_database():
    """Закрыть соединение с базой данных"""
    db_manager = get_db_manager()
    await db_manager.close()