"""
Адаптер для интеграции существующей торговой логики с Telegram интерфейсом.

Обеспечивает:
- Интеграцию существующего TradingEngine
- Адаптацию данных для портфельного менеджера
- Преобразование сигналов в рекомендации
- Обработку исполнения сделок
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from config import settings
from portfolio.manager import PortfolioManager
from database.models import User, Portfolio, Position, Transaction
from data.moex_client import MOEXClient
from ai.agentrouter_client import AgentRouterClient

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Адаптированный торговый сигнал"""
    action: str  # BUY, SELL, HOLD
    ticker: str
    price: float
    quantity: Optional[int]
    reasoning: str
    confidence: float
    risk_level: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    technical_indicators: Dict[str, Any]
    timestamp: datetime


@dataclass
class MarketDataSnapshot:
    """Снимок рыночных данных"""
    ticker: str
    current_price: float
    bid: Optional[float]
    ask: Optional[float]
    volume: int
    daily_change: float
    high: float
    low: float
    open_price: float
    timestamp: datetime


class TradingAdapter:
    """Адаптер для интеграции торговой логики"""
    
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.moex_client = MOEXClient()
        self.ai_client = AgentRouterClient(settings.AGENTROUTER_API_KEY)
        
        logger.info("TradingAdapter initialized")
    
    def initialize_trading_engine(self):
        """Инициализация торгового движка"""
        logger.info("TradingEngine initialized (placeholder)")
        return None
    
    async def get_market_data(self, ticker: str = "GAZP") -> MarketDataSnapshot:
        """Получение текущих рыночных данных"""
        try:
            # Получение текущей цены
            async with self.moex_client:
                current_price = await self.moex_client.get_current_price(ticker)
            
            snapshot = MarketDataSnapshot(
                ticker=ticker,
                current_price=current_price or 0.0,
                bid=None,
                ask=None,
                volume=0,
                daily_change=0.0,
                high=0.0,
                low=0.0,
                open_price=0.0,
                timestamp=datetime.now()
            )
            
            logger.info(f"Market data retrieved for {ticker}: {snapshot.current_price}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error getting market data for {ticker}: {e}")
            raise
    
    async def get_technical_indicators(self, ticker: str = "GAZP", days: int = 30) -> Dict[str, Any]:
        """Получение технических индикаторов"""
        try:
            # Получение технических индикаторов от MOEX клиента
            async with self.moex_client:
                indicators = await self.moex_client.get_technical_indicators(ticker, days)
            
            logger.info(f"Technical indicators retrieved for {ticker}")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {ticker}: {e}")
            return {}
    
    async def generate_trading_signals(self, ticker: str = "GAZP") -> List[TradingSignal]:
        """Генерация торговых сигналов на основе стратегии"""
        try:
            # Получение данных для анализа
            market_data = await self.get_market_data(ticker)
            indicators = await self.get_technical_indicators(ticker)
            
            # Получение AI рекомендации
            ai_context = {
                "market_data": {
                    "current_price": market_data.current_price,
                    "technical_indicators": indicators
                }
            }
            
            ai_result = await self.ai_client.get_trading_recommendation(ai_context)
            
            if not ai_result["success"]:
                logger.warning(f"Failed to get AI recommendation: {ai_result.get('error')}")
                return []
            
            recommendation = ai_result["data"]
            
            # Преобразование AI рекомендации в торговый сигнал
            trading_signal = TradingSignal(
                action=recommendation.get("action", "HOLD"),
                ticker=ticker,
                price=market_data.current_price,
                quantity=recommendation.get("quantity", 0),
                reasoning=recommendation.get("reasoning", ""),
                confidence=recommendation.get("confidence", 0),
                risk_level=recommendation.get("risk_level", "MEDIUM"),
                stop_loss=recommendation.get("stop_loss"),
                take_profit=recommendation.get("take_profit"),
                technical_indicators=indicators,
                timestamp=datetime.now()
            )
            
            logger.info(f"Generated AI trading signal for {ticker}: {trading_signal.action}")
            return [trading_signal]
            
        except Exception as e:
            logger.error(f"Error generating trading signals for {ticker}: {e}")
            return []
    
    async def execute_trade(self, user_id: int, portfolio_id: int, action: str,
                        ticker: str, quantity: int, reason: str = None) -> Dict[str, Any]:
        """Исполнение сделки через портфельный менеджер"""
        try:
            # Получение рыночных данных
            market_data = await self.get_market_data(ticker)
            current_price = market_data.current_price
            
            if not current_price:
                return {
                    'success': False,
                    'error': 'No market data available'
                }
            
            # Исполнение сделки через портфельный менеджер
            transaction = await self.portfolio_manager.execute_trade(
                user_id=user_id,
                action=action,
                ticker=ticker,
                quantity=quantity,
                price=current_price,
                recommendation_id=None
            )
            
            logger.info(f"Executed {action} trade: {quantity} {ticker} @ {current_price}")
            
            return {
                'success': True,
                'executed_price': current_price,
                'executed_shares': quantity,
                'commission': 0.0,  # TODO: рассчитать комиссию
                'net_amount': quantity * current_price,
                'transaction': transaction
            }
            
        except Exception as e:
            logger.error(f"Error executing {action} trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def calculate_position_metrics(self, user_id: int, portfolio_id: int, ticker: str) -> Dict[str, Any]:
        """Расчет метрик позиции"""
        try:
            # Получение позиции
            positions = await self.portfolio_manager.get_positions(portfolio_id)
            position = next((p for p in positions if p.ticker == ticker), None)
            
            if not position:
                return {}
            
            # Получение текущих рыночных данных
            market_data = await self.get_market_data(ticker)
            
            # Расчет дополнительных метрик
            position_metrics = {
                'ticker': position.ticker,
                'shares': position.shares,
                'avg_purchase_price': float(position.avg_purchase_price) if position.avg_purchase_price else 0.0,
                'current_price': market_data.current_price,
                'unrealized_pnl': float(position.unrealized_pnl) if position.unrealized_pnl else 0.0,
                'pnl_percent': position.pnl_percent
            }
            
            return position_metrics
            
        except Exception as e:
            logger.error(f"Error calculating position metrics: {e}")
            return {}
    
    async def get_portfolio_performance(self, user_id: int, portfolio_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение производительности портфеля"""
        try:
            performance = await self.portfolio_manager.get_performance_metrics(user_id, days)
            
            # Добавление рыночных данных
            market_data = await self.get_market_data("GAZP")
            performance['current_market_price'] = market_data.current_price
            performance['market_daily_change'] = market_data.daily_change
            
            # TODO: Добавление бенчмарка (IMOEX)
            # performance['benchmark_return'] = await self.get_benchmark_performance(days)
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting portfolio performance: {e}")
            return {}
    
    async def get_risk_assessment(self, user_id: int, portfolio_id: int) -> Dict[str, Any]:
        """Оценка рисков портфеля"""
        try:
            portfolio = await self.portfolio_manager.get_portfolio(user_id)
            if not portfolio:
                return {}
            
            positions = await self.portfolio_manager.get_positions(portfolio_id)
            settings = await self.portfolio_manager.get_user_settings(user_id)
            
            risk_assessment = {
                'portfolio_risk_score': 0.0,
                'positions_risk': [],
                'risk_factors': [],
                'recommendations': []
            }
            
            total_risk = 0.0
            for position in positions:
                # Расчет риска для каждой позиции
                position_risk = await self.calculate_position_risk(position, settings)
                risk_assessment['positions_risk'].append(position_risk)
                total_risk += position_risk['risk_score']
            
            # Общий риск портфеля
            if len(positions) > 0:
                risk_assessment['portfolio_risk_score'] = total_risk / len(positions)
            
            # Факторы риска
            risk_assessment['risk_factors'] = await self.identify_risk_factors(portfolio, positions)
            
            # Рекомендации
            risk_assessment['recommendations'] = await self.generate_risk_recommendations(risk_assessment)
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error getting risk assessment: {e}")
            return {}
    
    async def calculate_position_risk(self, position, settings) -> Dict[str, Any]:
        """Расчет риска для позиции"""
        try:
            # Базовые метрики риска
            current_price = float(position.current_price or 0)
            entry_price = float(position.avg_purchase_price or 0)
            
            if entry_price == 0:
                return {'risk_score': 0.0, 'risk_level': 'LOW'}
            
            # Расчет P&L в процентах
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Определение уровня риска
            if pnl_percent <= -5:
                risk_level = 'HIGH'
                risk_score = 10.0
            elif pnl_percent <= -2:
                risk_level = 'MEDIUM'
                risk_score = 5.0
            else:
                risk_level = 'LOW'
                risk_score = 1.0
            
            return {
                'ticker': position.ticker,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'pnl_percent': pnl_percent,
                'unrealized_pnl': float(position.unrealized_pnl or 0),
                'days_held': 0  # Заглушка
            }
            
        except Exception as e:
            logger.error(f"Error calculating position risk: {e}")
            return {'risk_score': 0.0, 'risk_level': 'UNKNOWN'}
    
    async def identify_risk_factors(self, portfolio, positions) -> List[str]:
        """Идентификация факторов риска"""
        risk_factors = []
        
        try:
            # Концентрация риска
            if len(positions) == 1 and positions[0].ticker == 'GAZP':
                risk_factors.append("Высокая концентрация в одном активе (GAZP)")
            
            # Отсутствие диверсификации
            if len(positions) < 3:
                risk_factors.append("Недостаточная диверсификация портфеля")
            
            # Проверка размера позиций
            for position in positions:
                position_value = position.current_value or 0
                if position_value > float(portfolio.initial_capital) * 0.3:  # > 30% капитала
                    risk_factors.append(f"Крупная позиция в {position.ticker}")
            
            # TODO: Добавить дополнительные факторы риска
            # - Рыночная волатильность
            # - Геополитические риски
            # - Сезонные факторы
            
        except Exception as e:
            logger.error(f"Error identifying risk factors: {e}")
        
        return risk_factors
    
    async def generate_risk_recommendations(self, risk_assessment) -> List[str]:
        """Генерация рекомендаций по управлению рисками"""
        recommendations = []
        
        try:
            if risk_assessment['portfolio_risk_score'] > 7:
                recommendations.append("Рассмотрите сокращение позиций для снижения риска")
            
            if any('концентрация' in factor for factor in risk_assessment['risk_factors']):
                recommendations.append("Диверсифицируйте портфель для снижения концентрации риска")
            
            if any('Крупная позиция' in factor for factor in risk_assessment['risk_factors']):
                recommendations.append("Соблюдайте лимиты размера позиций (30% капитала)")
            
            # TODO: Добавить дополнительные рекомендации
            
        except Exception as e:
            logger.error(f"Error generating risk recommendations: {e}")
        
        return recommendations
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Получение статуса торговой системы"""
        return {
            'status': 'not_initialized',
            'message': 'Trading engine not initialized'
        }


# Глобальный экземпляр адаптера
trading_adapter = None


def get_trading_adapter() -> TradingAdapter:
    """Получение глобального экземпляра адаптера"""
    global trading_adapter
    if trading_adapter is None:
        trading_adapter = TradingAdapter()
    return trading_adapter