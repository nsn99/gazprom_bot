"""
Тесты для менеджера портфелей
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from gazprom_bot.portfolio.manager import PortfolioManager
from gazprom_bot.database.models import User, Portfolio, Transaction


class TestPortfolioManager:
    """Тесты менеджера портфелей"""
    
    @pytest.fixture
    def manager(self):
        """Фикстура для создания менеджера"""
        with patch('gazprom_bot.portfolio.manager.get_db_manager') as mock_db_manager, \
             patch('gazprom_bot.portfolio.manager.get_moex_client') as mock_moex_client:
            
            mock_db = MagicMock()
            mock_db_manager.return_value = mock_db
            
            mock_client = MagicMock()
            mock_moex_client.return_value = mock_client
            
            return PortfolioManager()
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, manager):
        """Тест успешного создания пользователя"""
        # Мокирование ответов от базы данных
        mock_user = User(
            user_id=12345,
            telegram_username="testuser",
            initial_capital=100000.0,
            current_cash=100000.0
        )
        
        manager.db_manager.create_user = AsyncMock(return_value=mock_user)
        
        user = await manager.create_user(12345, "testuser", 100000.0)
        
        assert user.user_id == 12345
        assert user.telegram_username == "testuser"
        assert user.initial_capital == 100000.0
        assert user.current_cash == 100000.0
        
        manager.db_manager.create_user.assert_called_once_with(
            user_id=12345,
            username="testuser",
            initial_capital=100000.0
        )
    
    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, manager):
        """Тест успешного получения портфеля"""
        # Мокирование данных портфеля
        mock_portfolio = Portfolio(
            user_id=12345,
            ticker="GAZP",
            shares=100,
            avg_purchase_price=150.0,
            current_price=160.0,
            unrealized_pnl=1000.0
        )
        
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        manager.moex_client.get_current_price = AsyncMock(return_value=160.0)
        
        portfolio = await manager.get_portfolio(12345)
        
        assert portfolio.user_id == 12345
        assert portfolio.ticker == "GAZP"
        assert portfolio.shares == 100
        assert portfolio.avg_purchase_price == 150.0
        assert portfolio.current_price == 160.0
        assert portfolio.unrealized_pnl == 1000.0
    
    @pytest.mark.asyncio
    async def test_get_portfolio_not_found(self, manager):
        """Тест получения несуществующего портфеля"""
        manager.db_manager.get_portfolio = AsyncMock(return_value=None)
        
        portfolio = await manager.get_portfolio(12345)
        
        assert portfolio is None
    
    @pytest.mark.asyncio
    async def test_execute_trade_buy_success(self, manager):
        """Тест успешной покупки"""
        # Мокирование данных
        mock_user = User(
            user_id=12345,
            current_cash=50000.0
        )
        mock_portfolio = Portfolio(
            user_id=12345,
            shares=50,
            avg_purchase_price=150.0
        )
        mock_transaction = Transaction(
            id=1,
            user_id=12345,
            action="BUY",
            ticker="GAZP",
            shares=10,
            price=160.0,
            total_amount=1600.0
        )
        
        manager.db_manager.get_user = AsyncMock(return_value=mock_user)
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        manager.db_manager.update_portfolio = AsyncMock(return_value=True)
        manager.db_manager.create_transaction = AsyncMock(return_value=mock_transaction)
        
        transaction = await manager.execute_trade(
            user_id=12345,
            action="BUY",
            ticker="GAZP",
            quantity=10,
            price=160.0
        )
        
        assert transaction.id == 1
        assert transaction.action == "BUY"
        assert transaction.ticker == "GAZP"
        assert transaction.shares == 10
        assert transaction.price == 160.0
        assert transaction.total_amount == 1600.0
        
        # Проверка обновления портфеля
        new_shares = 50 + 10  # 60
        new_avg_price = ((50 * 150.0) + 1600.0) / 60  # ~151.67
        
        manager.db_manager.update_portfolio.assert_called_once_with(
            12345, new_shares, new_avg_price
        )
    
    @pytest.mark.asyncio
    async def test_execute_trade_sell_success(self, manager):
        """Тест успешной продажи"""
        # Мокирование данных
        mock_user = User(
            user_id=12345,
            current_cash=50000.0
        )
        mock_portfolio = Portfolio(
            user_id=12345,
            shares=100,
            avg_purchase_price=150.0
        )
        mock_transaction = Transaction(
            id=2,
            user_id=12345,
            action="SELL",
            ticker="GAZP",
            shares=20,
            price=160.0,
            total_amount=3200.0
        )
        
        manager.db_manager.get_user = AsyncMock(return_value=mock_user)
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        manager.db_manager.update_portfolio = AsyncMock(return_value=True)
        manager.db_manager.create_transaction = AsyncMock(return_value=mock_transaction)
        
        transaction = await manager.execute_trade(
            user_id=12345,
            action="SELL",
            ticker="GAZP",
            quantity=20,
            price=160.0
        )
        
        assert transaction.id == 2
        assert transaction.action == "SELL"
        assert transaction.ticker == "GAZP"
        assert transaction.shares == 20
        assert transaction.price == 160.0
        assert transaction.total_amount == 3200.0
        
        # Проверка обновления портфеля
        new_shares = 100 - 20  # 80
        
        manager.db_manager.update_portfolio.assert_called_once_with(
            12345, new_shares, 150.0
        )
    
    @pytest.mark.asyncio
    async def test_execute_trade_insufficient_funds(self, manager):
        """Тест сделки с недостаточными средствами"""
        # Мокирование данных
        mock_user = User(
            user_id=12345,
            current_cash=1000.0  # Недостаточно для покупки
        )
        mock_portfolio = Portfolio(
            user_id=12345,
            shares=0
        )
        
        manager.db_manager.get_user = AsyncMock(return_value=mock_user)
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        
        with pytest.raises(ValueError, match="Недостаточно средств"):
            await manager.execute_trade(
                user_id=12345,
                action="BUY",
                ticker="GAZP",
                quantity=10,
                price=160.0  # Требуется 1600, доступно 1000
            )
    
    @pytest.mark.asyncio
    async def test_execute_trade_insufficient_shares(self, manager):
        """Тест сделки с недостаточным количеством акций"""
        # Мокирование данных
        mock_user = User(
            user_id=12345,
            current_cash=50000.0
        )
        mock_portfolio = Portfolio(
            user_id=12345,
            shares=10  # Недостаточно для продажи
        )
        
        manager.db_manager.get_user = AsyncMock(return_value=mock_user)
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        
        with pytest.raises(ValueError, match="Недостаточно акций"):
            await manager.execute_trade(
                user_id=12345,
                action="SELL",
                ticker="GAZP",
                quantity=20,  # Требуется 20, доступно 10
                price=160.0
            )
    
    @pytest.mark.asyncio
    async def test_get_portfolio_summary(self, manager):
        """Тест получения сводки портфеля"""
        # Мокирование данных
        mock_user = User(
            user_id=12345,
            current_cash=50000.0,
            initial_capital=100000.0
        )
        mock_portfolio = Portfolio(
            user_id=12345,
            shares=100,
            avg_purchase_price=150.0
        )
        
        manager.db_manager.get_user = AsyncMock(return_value=mock_user)
        manager.db_manager.get_portfolio = AsyncMock(return_value=mock_portfolio)
        manager.moex_client.get_current_price = AsyncMock(return_value=160.0)
        
        summary = await manager.get_portfolio_summary(12345)
        
        assert summary["user_id"] == 12345
        assert summary["cash"] == 50000.0
        assert summary["shares"] == 100
        assert summary["avg_price"] == 150.0
        assert summary["current_price"] == 160.0
        assert summary["shares_value"] == 16000.0  # 100 * 160
        assert summary["total_value"] == 66000.0  # 50000 + 16000
        assert summary["initial_capital"] == 100000.0
        assert summary["pnl"] == -34000.0  # 66000 - 100000
        assert summary["pnl_percent"] == -34.0  # -34000 / 100000 * 100
    
    @pytest.mark.asyncio
    async def test_get_transaction_history(self, manager):
        """Тест получения истории транзакций"""
        # Мокирование данных
        mock_transactions = [
            Transaction(
                id=1,
                user_id=12345,
                action="BUY",
                ticker="GAZP",
                shares=10,
                price=150.0,
                total_amount=1500.0,
                timestamp=datetime(2023, 10, 25, 10, 0, 0)
            ),
            Transaction(
                id=2,
                user_id=12345,
                action="SELL",
                ticker="GAZP",
                shares=5,
                price=160.0,
                total_amount=800.0,
                timestamp=datetime(2023, 10, 26, 10, 0, 0)
            )
        ]
        
        manager.db_manager.get_transaction_history = AsyncMock(return_value=mock_transactions)
        
        history = await manager.get_transaction_history(12345, 50)
        
        assert len(history) == 2
        assert history[0].action == "BUY"
        assert history[1].action == "SELL"
        
        manager.db_manager.get_transaction_history.assert_called_once_with(12345, 50)
    
    @pytest.mark.asyncio
    async def test_save_recommendation(self, manager):
        """Тест сохранения рекомендации"""
        recommendation = {
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Тестовая рекомендация",
            "stop_loss": 145.0,
            "take_profit": 175.0,
            "risk_level": "MEDIUM",
            "confidence": 75
        }
        
        mock_ai_rec = MagicMock()
        manager.db_manager.save_ai_recommendation = AsyncMock(return_value=mock_ai_rec)
        
        result = await manager.save_recommendation(12345, recommendation)
        
        assert result == mock_ai_rec
        manager.db_manager.save_ai_recommendation.assert_called_once_with(12345, recommendation)
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, manager):
        """Тест получения метрик производительности"""
        # Мокирование данных
        mock_transactions = [
            Transaction(
                id=1,
                user_id=12345,
                action="BUY",
                ticker="GAZP",
                shares=10,
                price=150.0,
                total_amount=1500.0,
                timestamp=datetime(2023, 10, 25, 10, 0, 0)
            ),
            Transaction(
                id=2,
                user_id=12345,
                action="SELL",
                ticker="GAZP",
                shares=5,
                price=160.0,
                total_amount=800.0,
                timestamp=datetime(2023, 10, 26, 10, 0, 0)
            )
        ]
        
        mock_summary = {
            "total_value": 66000.0,
            "pnl": -34000.0,
            "pnl_percent": -34.0
        }
        
        manager.db_manager.get_transaction_history = AsyncMock(return_value=mock_transactions)
        manager.get_portfolio_summary = AsyncMock(return_value=mock_summary)
        
        metrics = await manager.get_performance_metrics(12345, 30)
        
        assert metrics["period_days"] == 30
        assert metrics["total_trades"] == 2
        assert metrics["buy_trades"] == 1
        assert metrics["sell_trades"] == 1
        assert metrics["total_volume"] == 2300.0  # 1500 + 800
        assert metrics["avg_trade_size"] == 1150.0  # 2300 / 2
        assert metrics["current_value"] == 66000.0
        assert metrics["pnl"] == -34000.0
        assert metrics["pnl_percent"] == -34.0
    
    @pytest.mark.asyncio
    async def test_get_risk_metrics(self, manager):
        """Тест получения метрик риска"""
        # Мокирование данных
        mock_summary = {
            "cash": 50000.0,
            "shares": 100,
            "current_price": 160.0,
            "total_value": 66000.0
        }
        
        manager.get_portfolio_summary = AsyncMock(return_value=mock_summary)
        
        metrics = await manager.get_risk_metrics(12345)
        
        assert metrics["concentration_percent"] == 24.24  # 16000 / 66000 * 100
        assert metrics["liquidity_percent"] == 75.76  # 50000 / 66000 * 100
        assert metrics["potential_loss"] == 1600.0  # 16000 * 0.1
        assert metrics["potential_loss_percent"] == 2.42  # 1600 / 66000 * 100
        assert metrics["risk_level"] == "LOW"  # Низкий риск
    
    def test_assess_risk_level_low(self, manager):
        """Тест оценки низкого уровня риска"""
        risk_level = manager._assess_risk_level(30, 50)
        assert risk_level == "LOW"
    
    def test_assess_risk_level_medium(self, manager):
        """Тест оценки среднего уровня риска"""
        risk_level = manager._assess_risk_level(60, 20)
        assert risk_level == "MEDIUM"
    
    def test_assess_risk_level_high(self, manager):
        """Тест оценки высокого уровня риска"""
        risk_level = manager._assess_risk_level(80, 5)
        assert risk_level == "HIGH"