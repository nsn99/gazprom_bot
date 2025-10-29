# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Chart Generator Module

Модуль для генерации графиков и визуализаций.
"""

import io
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from config import settings, constants
from monitoring.logger import get_logger
from data.client import get_moex_client
from portfolio.manager import PortfolioManager


logger = get_logger(__name__)


class ChartGenerator:
    """Генератор графиков"""
    
    def __init__(self):
        """Инициализация генератора графиков"""
        self.moex_client = get_moex_client()
        self.portfolio_manager = PortfolioManager()
        
        # Настройка стилей
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    async def generate_price_chart(
        self, 
        ticker: str = constants.GAZP_TICKER,
        days: int = 30,
        include_indicators: bool = True
    ) -> Optional[bytes]:
        """
        Сгенерировать график цены
        
        Args:
            ticker: Тикер акции
            days: Период в днях
            include_indicators: Включить технические индикаторы
            
        Returns:
            Изображение в виде bytes или None
        """
        try:
            # Получение исторических данных
            df = await self.moex_client.get_historical_data(ticker, days)
            if df is None or len(df) < 10:
                logger.warning(f"Недостаточно данных для графика цены {ticker}")
                return None
            
            # Создание фигуры
            fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
            fig.suptitle(f'График цены {ticker} - {days} дней', fontsize=16, fontweight='bold')
            
            # График цены
            axes[0].plot(df.index, df['CLOSE'], linewidth=2, color='blue', label='Цена закрытия')
            
            if include_indicators:
                # Скользящие средние
                if len(df) >= 20:
                    sma_20 = df['CLOSE'].rolling(window=20).mean()
                    axes[0].plot(df.index, sma_20, linewidth=1, color='orange', label='SMA(20)')
                
                if len(df) >= 50:
                    sma_50 = df['CLOSE'].rolling(window=50).mean()
                    axes[0].plot(df.index, sma_50, linewidth=1, color='red', label='SMA(50)')
            
            axes[0].set_title('Цена закрытия', fontsize=12)
            axes[0].set_ylabel('Цена, ₽', fontsize=10)
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
            
            # График объема
            if 'VOLUME' in df.columns:
                axes[1].bar(df.index, df['VOLUME'], color='lightblue', alpha=0.7)
                axes[1].set_title('Объем торгов', fontsize=12)
                axes[1].set_ylabel('Объем', fontsize=10)
                axes[1].grid(True, alpha=0.3)
            
            # Форматирование оси X
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # Сохранение в bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации графика цены {ticker}: {e}")
            return None
    
    async def generate_portfolio_performance_chart(
        self, 
        user_id: int,
        days: int = 30
    ) -> Optional[bytes]:
        """
        Сгенерировать график производительности портфеля
        
        Args:
            user_id: ID пользователя
            days: Период в днях
            
        Returns:
            Изображение в виде bytes или None
        """
        try:
            # Получение истории транзакций
            transactions = await self.portfolio_manager.get_transaction_history(user_id, limit=1000)
            
            if not transactions:
                logger.warning(f"Нет транзакций для пользователя {user_id}")
                return None
            
            # Получение исторических данных GAZP
            df = await self.moex_client.get_historical_data(constants.GAZP_TICKER, days)
            if df is None or len(df) < 10:
                return None
            
            # Получение данных IMOEX для сравнения
            try:
                imoex_data = await self.moex_client.get_historical_data("IMOEX", days)
            except:
                imoex_data = None
            
            # Создание DataFrame с историей портфеля
            portfolio_history = self._calculate_portfolio_history(transactions, df)
            
            # Создание фигуры
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.suptitle('Производительность портфеля', fontsize=16, fontweight='bold')
            
            # График портфеля
            ax.plot(
                portfolio_history.index, 
                portfolio_history['portfolio_value'], 
                linewidth=2, 
                color='blue', 
                label='Портфель'
            )
            
            # График начального капитала
            ax.axhline(
                y=portfolio_history['initial_capital'].iloc[0], 
                color='gray', 
                linestyle='--', 
                label='Начальный капитал'
            )
            
            # График IMOEX (если доступен)
            if imoex_data is not None and len(imoex_data) > 0:
                # Нормализация IMOEX к начальному капиталу
                imoex_normalized = imoex_data['CLOSE'] / imoex_data['CLOSE'].iloc[0] * portfolio_history['initial_capital'].iloc[0]
                ax.plot(
                    imoex_data.index, 
                    imoex_normalized, 
                    linewidth=1, 
                    color='red', 
                    label='IMOEX (нормализован)'
                )
            
            ax.set_title('Стоимость портфеля во времени', fontsize=12)
            ax.set_ylabel('Стоимость, ₽', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Форматирование оси X
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # Сохранение в bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации графика производительности портфеля {user_id}: {e}")
            return None
    
    async def generate_technical_indicators_chart(
        self, 
        ticker: str = constants.GAZP_TICKER,
        days: int = 60
    ) -> Optional[bytes]:
        """
        Сгенерировать график технических индикаторов
        
        Args:
            ticker: Тикер акции
            days: Период в днях
            
        Returns:
            Изображение в виде bytes или None
        """
        try:
            # Получение исторических данных
            df = await self.moex_client.get_historical_data(ticker, days)
            if df is None or len(df) < 50:
                return None
            
            # Расчет индикаторов
            async with self.moex_client:
                indicators = await self.moex_client.get_technical_indicators(ticker, days)
            
            # Создание фигуры
            fig, axes = plt.subplots(4, 1, figsize=(12, 10))
            fig.suptitle(f'Технические индикаторы {ticker}', fontsize=16, fontweight='bold')
            
            # График цены и скользящих средних
            axes[0].plot(df.index, df['CLOSE'], linewidth=2, color='blue', label='Цена')
            
            if 'sma_20' in indicators:
                sma_20 = df['CLOSE'].rolling(window=20).mean()
                axes[0].plot(df.index, sma_20, linewidth=1, color='orange', label='SMA(20)')
            
            if 'sma_50' in indicators:
                sma_50 = df['CLOSE'].rolling(window=50).mean()
                axes[0].plot(df.index, sma_50, linewidth=1, color='red', label='SMA(50)')
            
            axes[0].set_title('Цена и скользящие средние', fontsize=12)
            axes[0].set_ylabel('Цена, ₽', fontsize=10)
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
            
            # RSI
            if 'rsi' in indicators:
                rsi = df['CLOSE'].rolling(window=14).apply(
                    lambda x: self._calculate_rsi(x), raw=True
                )
                axes[1].plot(df.index, rsi, linewidth=1, color='purple')
                axes[1].axhline(y=70, color='red', linestyle='--', alpha=0.7)
                axes[1].axhline(y=30, color='green', linestyle='--', alpha=0.7)
                axes[1].set_title('RSI (14)', fontsize=12)
                axes[1].set_ylabel('RSI', fontsize=10)
                axes[1].set_ylim(0, 100)
                axes[1].grid(True, alpha=0.3)
            
            # MACD
            if 'macd' in indicators:
                macd_data = self._calculate_macd(df['CLOSE'])
                axes[2].plot(df.index, macd_data['macd'], linewidth=1, color='blue', label='MACD')
                axes[2].plot(df.index, macd_data['signal'], linewidth=1, color='red', label='Signal')
                axes[2].bar(df.index, macd_data['histogram'], color='green', alpha=0.7, label='Histogram')
                axes[2].set_title('MACD (12, 26, 9)', fontsize=12)
                axes[2].set_ylabel('MACD', fontsize=10)
                axes[2].grid(True, alpha=0.3)
                axes[2].legend()
            
            # Объемы
            if 'VOLUME' in df.columns:
                axes[3].bar(df.index, df['VOLUME'], color='lightblue', alpha=0.7)
                axes[3].set_title('Объем торгов', fontsize=12)
                axes[3].set_ylabel('Объем', fontsize=10)
                axes[3].grid(True, alpha=0.3)
            
            # Форматирование оси X
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # Сохранение в bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации графика технических индикаторов {ticker}: {e}")
            return None
    
    async def generate_interactive_chart(
        self, 
        ticker: str = constants.GAZP_TICKER,
        days: int = 30
    ) -> Optional[str]:
        """
        Сгенерировать интерактивный график (Plotly)
        
        Args:
            ticker: Тикер акции
            days: Период в днях
            
        Returns:
            HTML код графика или None
        """
        try:
            # Получение исторических данных
            df = await self.moex_client.get_historical_data(ticker, days)
            if df is None or len(df) < 10:
                return None
            
            # Создание subplot
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=('Цена', 'Объем'),
                row_width=[0.2, 0.7]
            )
            
            # График цены
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['CLOSE'],
                    mode='lines',
                    name='Цена закрытия',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
            
            # Скользящие средние
            if len(df) >= 20:
                sma_20 = df['CLOSE'].rolling(window=20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=sma_20,
                        mode='lines',
                        name='SMA(20)',
                        line=dict(color='orange', width=1)
                    ),
                    row=1, col=1
                )
            
            if len(df) >= 50:
                sma_50 = df['CLOSE'].rolling(window=50).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=sma_50,
                        mode='lines',
                        name='SMA(50)',
                        line=dict(color='red', width=1)
                    ),
                    row=1, col=1
                )
            
            # Объемы
            if 'VOLUME' in df.columns:
                fig.add_trace(
                    go.Bar(
                        x=df.index,
                        y=df['VOLUME'],
                        name='Объем',
                        marker_color='lightblue'
                    ),
                    row=2, col=1
                )
            
            # Настройка layout
            fig.update_layout(
                title=f'Интерактивный график {ticker}',
                xaxis_rangeslider_visible=False,
                height=600
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            logger.error(f"Ошибка при генерации интерактивного графика {ticker}: {e}")
            return None
    
    def _calculate_portfolio_history(
        self, 
        transactions: List, 
        price_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Рассчитать историю портфеля
        
        Args:
            transactions: Список транзакций
            price_data: DataFrame с ценами
            
        Returns:
            DataFrame с историей портфеля
        """
        # Создание DataFrame с транзакциями
        tx_df = pd.DataFrame([
            {
                'date': t.timestamp,
                'action': t.action,
                'shares': t.shares,
                'price': t.price,
                'amount': t.total_amount
            }
            for t in transactions
        ])
        
        if tx_df.empty:
            return pd.DataFrame()
        
        # Сортировка по дате
        tx_df = tx_df.sort_values('date')
        
        # Начальный капитал (из первой транзакции)
        initial_capital = tx_df['amount'].sum()
        
        # Создание истории портфеля
        history = []
        cash = initial_capital
        shares = 0
        
        for date in price_data.index:
            # Обработка транзакций за этот день
            day_tx = tx_df[tx_df['date'].dt.date == date.date()]
            
            for _, tx in day_tx.iterrows():
                if tx['action'] == 'BUY':
                    cash -= tx['amount']
                    shares += tx['shares']
                elif tx['action'] == 'SELL':
                    cash += tx['amount']
                    shares -= tx['shares']
            
            # Расчет стоимости портфеля
            portfolio_value = cash + (shares * price_data.loc[date, 'CLOSE'])
            
            history.append({
                'date': date,
                'cash': cash,
                'shares': shares,
                'portfolio_value': portfolio_value,
                'initial_capital': initial_capital
            })
        
        return pd.DataFrame(history).set_index('date')
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Рассчитать RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50.0
    
    def _calculate_macd(
        self, 
        prices: pd.Series, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """Рассчитать MACD"""
        exp_fast = prices.ewm(span=fast).mean()
        exp_slow = prices.ewm(span=slow).mean()
        macd_line = exp_fast - exp_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }


# Глобальный экземпляр генератора графиков
_chart_generator = None


def get_chart_generator() -> ChartGenerator:
    """Получить глобальный экземпляр генератора графиков"""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGenerator()
    return _chart_generator