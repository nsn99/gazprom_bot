"""
Основной торговый движок gazprom_bot.

Обеспечивает:
- Асинхронный жизненный цикл торговли
- Интеграцию всех компонентов (стратегия, исполнение, риск, мониторинг)
- Graceful shutdown
- Управление состоянием позиции
- Метрики и алерты

Это центральный компонент продакшен-системы.
"""

from __future__ import annotations

import asyncio
import signal
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import pandas as pd

from gazprom_bot.config import Config, load_config
from gazprom_bot.async_client import AsyncMoexClient, AsyncMoexClientError
from gazprom_bot.data.cache import DataCache
from gazprom_bot.indicators.technicals import Technicals
from gazprom_bot.strategy.gazp_breakout import GazpBreakoutStrategy, Signal
from gazprom_bot.execution.simulator import ExecutionSimulator, ExecutionInput, ExecutedTrade
from gazprom_bot.risk.manager import RiskManager, DayStats, Position
from gazprom_bot.monitoring.health import HealthChecker
from gazprom_bot.monitoring.alerts import AlertManager, AlertLevel, AlertConfig
from gazprom_bot.utils.time_utils import now_msk, is_trading_time, seconds_until_session_end


class TradingState(Enum):
    """Состояния торгового движка."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class TradingSession:
    """Информация о торговой сессии."""
    start_time: datetime
    current_position: Optional[Position] = None
    day_stats: DayStats = None
    last_signal_time: Optional[datetime] = None
    last_market_data_time: Optional[datetime] = None
    total_pnl: float = 0.0

    def __post_init__(self):
        if self.day_stats is None:
            self.day_stats = DayStats()


@dataclass
class TradeRecord:
    """Запись о сделке для истории."""
    timestamp: datetime
    signal: Signal
    execution: ExecutedTrade
    position_after: Optional[Position]
    pnl_realized: Optional[float] = None


class TradingEngine:
    """
    Основной торговый движок.

    Координирует работу всех компонентов:
    - Получение данных с MOEX
    - Расчет индикаторов
    - Генерация сигналов
    - Управление рисками
    - Исполнение сделок
    - Мониторинг и алерты
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.logger = logging.getLogger(__name__)

        # Компоненты
        self.moex_client: Optional[AsyncMoexClient] = None
        self.data_cache = DataCache(interval_minutes=self.config.data.candle_interval_min)
        self.technicals = Technicals()
        self.strategy = GazpBreakoutStrategy()
        self.execution_sim = ExecutionSimulator()
        self.risk_mgr = RiskManager(self.config.risk)

        # Мониторинг
        self.health_checker = HealthChecker(self.config)
        self.alert_config = AlertConfig()  # Загружается из конфига или переменных окружения
        self.alert_mgr = AlertManager(self.alert_config)

        # Состояние
        self.state = TradingState.INITIALIZING
        self.session = TradingSession(start_time=now_msk())
        self.trade_history: List[TradeRecord] = []

        # Управление циклами
        self.main_loop_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()

        # Статистика
        self.stats = {
            'iterations': 0,
            'signals_processed': 0,
            'trades_executed': 0,
            'errors': 0,
            'last_update': None
        }

    async def start(self):
        """Запуск торгового движка."""
        self.logger.info("Starting TradingEngine...")

        try:
            # Инициализация компонентов
            self.moex_client = AsyncMoexClient(
                board=self.config.data.board,
                rate_limit_per_sec=1.0 / self.config.session.poll_interval_sec,
                config=self.config
            )
            await self.moex_client.start()

            # Проверка здоровья
            await self._check_initial_health()

            # Запуск фоновых задач
            self.state = TradingState.RUNNING
            self.main_loop_task = asyncio.create_task(self._main_trading_loop())
            self.health_check_task = asyncio.create_task(self._health_check_loop())

            # Обработка сигналов завершения
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

            self.logger.info("TradingEngine started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start TradingEngine: {e}")
            await self._emergency_shutdown()
            raise

    async def stop(self):
        """Остановка торгового движка."""
        if self.state in [TradingState.STOPPING, TradingState.STOPPED]:
            return

        self.logger.info("Stopping TradingEngine...")
        self.state = TradingState.STOPPING
        self.shutdown_event.set()

        # Остановка задач
        tasks_to_cancel = []
        if self.main_loop_task:
            tasks_to_cancel.append(self.main_loop_task)
        if self.health_check_task:
            tasks_to_cancel.append(self.health_check_task)

        for task in tasks_to_cancel:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Закрытие компонентов
        if self.moex_client:
            await self.moex_client.close()

        # Финализация данных
        await self._finalize_session()

        self.state = TradingState.STOPPED
        self.logger.info("TradingEngine stopped")

    async def _main_trading_loop(self):
        """Основной цикл торговли."""
        poll_interval = self.config.session.poll_interval_sec

        try:
            while not self.shutdown_event.is_set():
                try:
                    await self._trading_iteration()
                    self.stats['iterations'] += 1
                    self.stats['last_update'] = now_msk()

                except Exception as e:
                    self.stats['errors'] += 1
                    self.logger.error(f"Trading iteration error: {e}")
                    await self.alert_mgr.send_alert(
                        AlertLevel.ERROR,
                        "Trading Iteration Failed",
                        f"Error in main trading loop: {e}",
                        "trading_engine",
                        metadata={'error': str(e), 'iteration': self.stats['iterations']}
                    )

                # Ожидание до следующей итерации
                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            self.logger.info("Main trading loop cancelled")
            raise

    async def _trading_iteration(self):
        """Одна итерация торгового цикла."""
        now = now_msk()

        # Проверка времени торговли
        if not is_trading_time(now, self.config.session):
            if self.session.current_position:
                self.logger.warning("Trading session ended with open position!")
                await self.alert_mgr.send_alert(
                    AlertLevel.WARNING,
                    "Open Position at Session End",
                    "Session ended with open position",
                    "trading_engine",
                    metadata={'position': asdict(self.session.current_position)}
                )
            return

        # Получение рыночных данных
        try:
            market_data = await self.moex_client.get_marketdata_l1(self.config.data.ticker)
            self.session.last_market_data_time = now

            # Обновление кэша данных
            # Note: В продакшене здесь будет интеграция с реальным потоком данных
            # Пока используем симуляцию на основе L1 данных

        except AsyncMoexClientError as e:
            self.logger.warning(f"Failed to get market data: {e}")
            return

        # Финализация свечи если нужно
        self.data_cache.finalize_candle()

        # Получение актуальных свечей
        candles_df = self.data_cache.get_candles_df()
        if len(candles_df) < 30:  # Минимум для расчетов
            return

        # Расчет индикаторов
        candles_with_indicators = Technicals.attach_all(candles_df)

        # Генерация сигналов
        signals = self.strategy.generate_signals(candles_with_indicators)
        if signals:
            self.session.last_signal_time = now
            self.stats['signals_processed'] += len(signals)

        # Обработка сигналов
        for signal in signals:
            await self._process_signal(signal, market_data)

        # Проверка стоп-лоссов
        if self.session.current_position:
            await self._check_position_exits(market_data)

    async def _process_signal(self, signal: Signal, market_data: Dict[str, Any]):
        """Обработка торгового сигнала."""
        # Проверка лимитов
        if not self.risk_mgr.allow_new_trade(self.session.day_stats):
            self.logger.info("Trade rejected: daily limits exceeded")
            return

        # BUY сигнал
        if signal.type == "BUY":
            if self.session.current_position:
                self.logger.debug("Ignoring BUY signal: position already open")
                return

            # Подготовка к исполнению
            best_bid = market_data.get('BID')
            best_ask = market_data.get('OFFER')
            last_price = market_data.get('LAST') or market_data.get('OFFER')

            if not best_ask or not last_price:
                self.logger.warning("Insufficient market data for BUY execution")
                return

            # Получение LOTSIZE
            security_info = await self.moex_client.get_security_info(self.config.data.ticker)
            lot_size = int(security_info.get('LOTSIZE', 1))

            # Исполнение
            exec_input = ExecutionInput(
                ts=signal.ts,
                side="BUY",
                best_bid=best_bid,
                best_ask=best_ask,
                lot_size=lot_size,
                max_position_rub=self.config.risk.max_position_rub,
                commission_pct_per_side=self.config.execution.commission_pct_per_side,
                slippage_pct=self.config.execution.slippage_pct
            )

            executed_trade = self.execution_sim.execute(exec_input, reason=signal.reason)
            if not executed_trade:
                self.logger.warning("BUY execution failed")
                return

            # Открытие позиции
            position = Position(
                entry_price=executed_trade.exec_price,
                qty_shares=executed_trade.qty_shares
            )
            position = self.risk_mgr.assign_stops_for_long(position)
            self.session.current_position = position

            # Запись сделки
            trade_record = TradeRecord(
                timestamp=now_msk(),
                signal=signal,
                execution=executed_trade,
                position_after=position
            )
            self.trade_history.append(trade_record)

            self.stats['trades_executed'] += 1
            self.logger.info(f"Position opened: {executed_trade.qty_shares} shares at {executed_trade.exec_price}")

        # SELL/CLOSE_LONG сигналы
        elif signal.type in ["SELL", "CLOSE_LONG"]:
            if not self.session.current_position:
                self.logger.debug("Ignoring sell signal: no open position")
                return

            position = self.session.current_position
            best_bid = market_data.get('BID')
            best_ask = market_data.get('OFFER')

            if not best_bid:
                self.logger.warning("Insufficient market data for SELL execution")
                return

            security_info = await self.moex_client.get_security_info(self.config.data.ticker)
            lot_size = int(security_info.get('LOTSIZE', 1))

            exec_input = ExecutionInput(
                ts=signal.ts,
                side="SELL",
                best_bid=best_bid,
                best_ask=best_ask,
                lot_size=lot_size,
                max_position_rub=self.config.risk.max_position_rub,
                commission_pct_per_side=self.config.execution.commission_pct_per_side,
                slippage_pct=self.config.execution.slippage_pct,
                desired_position_shares=position.qty_shares
            )

            executed_trade = self.execution_sim.execute(exec_input, reason=signal.reason)
            if not executed_trade:
                self.logger.warning("SELL execution failed")
                return

            # Расчет P&L
            pnl = (executed_trade.exec_price - position.entry_price) * position.qty_shares
            pnl -= executed_trade.commission  # Комиссия выхода
            # Комиссия входа уже учтена в предыдущих записях

            # Обновление статистики
            self.session.total_pnl += pnl
            self.risk_mgr.update_day_stats_on_close(
                self.session.day_stats,
                position.entry_price,
                executed_trade.exec_price,
                position.qty_shares,
                executed_trade.commission
            )

            # Запись сделки
            trade_record = TradeRecord(
                timestamp=now_msk(),
                signal=signal,
                execution=executed_trade,
                position_after=None,
                pnl_realized=pnl
            )
            self.trade_history.append(trade_record)

            self.session.current_position = None
            self.stats['trades_executed'] += 1

            self.logger.info(f"Position closed: P&L = {pnl:.2f} RUB")

    async def _check_position_exits(self, market_data: Dict[str, Any]):
        """Проверка условий выхода из позиции."""
        if not self.session.current_position:
            return

        last_price = market_data.get('LAST')
        if not last_price:
            return

        exit_decision = self.risk_mgr.check_exit_rules_for_long(
            self.session.current_position,
            last_price
        )

        if exit_decision.action != "NONE":
            # Создание сигнала выхода
            signal = Signal(
                type="CLOSE_LONG",
                ts=pd.Timestamp(now_msk()),
                price=last_price,
                reason=exit_decision.reason
            )

            await self._process_signal(signal, market_data)

    async def _check_initial_health(self):
        """Проверка здоровья при запуске."""
        health_results = self.health_checker.check_all()

        unhealthy_components = [
            name for name, status in health_results.items()
            if status.status != 'healthy'
        ]

        if unhealthy_components:
            await self.alert_mgr.send_alert(
                AlertLevel.CRITICAL,
                "Unhealthy Components at Startup",
                f"Components with issues: {', '.join(unhealthy_components)}",
                "trading_engine"
            )
            raise RuntimeError(f"Unhealthy components: {unhealthy_components}")

    async def _health_check_loop(self):
        """Цикл проверки здоровья."""
        check_interval = 60  # каждые 60 секунд

        try:
            while not self.shutdown_event.is_set():
                try:
                    health_results = self.health_checker.check_all()

                    # Проверка критических компонентов
                    for name, status in health_results.items():
                        if status.status == 'unhealthy':
                            await self.alert_mgr.send_alert(
                                AlertLevel.CRITICAL,
                                f"Component Unhealthy: {name}",
                                status.details.get('error', 'Unknown error'),
                                "health_check",
                                metadata={'component': name, 'details': status.details}
                            )

                    # Обновление бизнес-метрик
                    self.health_checker.update_business_metrics(
                        signals_generated=self.stats['signals_processed'],
                        trades_executed=self.stats['trades_executed']
                    )

                except Exception as e:
                    self.logger.error(f"Health check error: {e}")

                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            self.logger.info("Health check loop cancelled")
            raise

    async def _finalize_session(self):
        """Финализация торговой сессии."""
        try:
            # Экспорт данных
            self.data_cache.export_csv(self.config.paths)

            # Логирование итогов
            self.logger.info("Session Summary:")
            self.logger.info(f"  Total iterations: {self.stats['iterations']}")
            self.logger.info(f"  Signals processed: {self.stats['signals_processed']}")
            self.logger.info(f"  Trades executed: {self.stats['trades_executed']}")
            self.logger.info(f"  Total P&L: {self.session.total_pnl:.2f} RUB")
            self.logger.info(f"  Errors: {self.stats['errors']}")

            # Финальный алерт
            await self.alert_mgr.send_alert(
                AlertLevel.INFO,
                "Trading Session Ended",
                f"Session completed. P&L: {self.session.total_pnl:.2f} RUB, Trades: {self.stats['trades_executed']}",
                "trading_engine",
                metadata={
                    'pnl': self.session.total_pnl,
                    'trades': self.stats['trades_executed'],
                    'signals': self.stats['signals_processed']
                }
            )

        except Exception as e:
            self.logger.error(f"Error during session finalization: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус движка."""
        return {
            'state': self.state.value,
            'session': asdict(self.session),
            'stats': self.stats,
            'health': {name: status.status for name, status in self.health_checker.last_checks.items()},
            'alerts': self.alert_mgr.get_alert_stats()
        }

    async def _emergency_shutdown(self):
        """Экстренное завершение при критических ошибках."""
        self.logger.critical("Emergency shutdown initiated")
        self.state = TradingState.STOPPING

        # Принудительное закрытие всех компонентов
        if self.moex_client:
            try:
                await self.moex_client.close()
            except Exception:
                pass

        self.state = TradingState.STOPPED


__all__ = ['TradingEngine', 'TradingState', 'TradingSession', 'TradeRecord']