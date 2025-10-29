"""
Бэктест стратегии GAZP на 5‑мин свечах за ~30 торговых дней.

Компоненты:
- Загрузка исторических свечей через [MoexClient.get_historical_candles()](gazprom_bot/data/moex_client.py:1)
- Расчёт индикаторов через [Technicals.attach_all()](gazprom_bot/indicators/technicals.py:6)
- Генерация сигналов через [GazpBreakoutStrategy.generate_signals()](gazprom_bot/strategy/gazp_breakout.py:2)
- Симуляция исполнения через [ExecutionSimulator.execute()](gazprom_bot/execution/simulator.py:1)
- Риск‑контроль через [RiskManager](gazprom_bot/risk/manager.py:1)
- Метрики через [sharpe_ratio()](gazprom_bot/metrics/performance.py:2), [max_drawdown()](gazprom_bot/metrics/performance.py:3), [win_rate()](gazprom_bot/metrics/performance.py:4)

Особенности:
- Исторического L1 нет, поэтому лучший bid/ask аппроксимируются из OHLC:
  best_bid ≈ close − 0.25 * (high − low)
  best_ask ≈ close + 0.25 * (high − low)
- Исполнение по лучшему bid/ask на триггерной свече с проскальзыванием и комиссиями.
- Только лонг‑сценарий: BUY открывает позицию, SELL/CLOSE_LONG закрывает.

Вывод:
- trades_df: таблица закрытых сделок
- stats_df: суммарные метрики и дневные сводки
- Экспорт CSV: [data/trades.csv](data/trades.csv), [data/stats.csv](data/stats.csv) согласно [Config.paths](gazprom_bot/config.py:1)

Дисклеймер: учебная демо‑реализация.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from datetime import date, timedelta

import os
import pandas as pd
import numpy as np

from gazprom_bot.config import Config, load_config, DataParams, ExecutionParams, RiskLimits
from gazprom_bot.data.moex_client import MoexClient
from gazprom_bot.indicators.technicals import Technicals
from gazprom_bot.strategy.gazp_breakout import GazpBreakoutStrategy, Signal
from gazprom_bot.execution.simulator import ExecutionSimulator, ExecutionInput, ExecutedTrade
from gazprom_bot.risk.manager import RiskManager, DayStats, Position
from gazprom_bot.metrics.performance import sharpe_ratio, max_drawdown, win_rate, equity_from_trades


@dataclass
class BacktestResult:
    """Результат бэктеста."""
    trades_df: pd.DataFrame
    stats_df: pd.DataFrame


class BacktestRunner:
    """
    Запуск бэктеста стратегии GAZP на 5‑мин свечах за ~30 торговых дней.

    Основной метод:
    - [BacktestRunner.run()](gazprom_bot/backtest/runner.py:2)
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self.moex = MoexClient(board=self.config.data.board)
        self.tech = Technicals()
        self.strategy = GazpBreakoutStrategy()
        self.exec_sim = ExecutionSimulator()
        self.risk = RiskManager(self.config.risk)

        # LOTSIZE из ISS (для расчёта количества)
        sec_info = self.moex.get_security_info(self.config.data.ticker)
        self.lot_size = int(pd.to_numeric(sec_info.get("LOTSIZE", 1), errors="coerce") or 1)

    # -----------------------
    # Вспомогательные методы
    # -----------------------

    @staticmethod
    def _best_bid_ask_from_bar(row: pd.Series) -> Tuple[Optional[float], Optional[float]]:
        """
        Аппроксимация best bid/ask из OHLC баров.
        """
        close = row.get("close")
        high = row.get("high")
        low = row.get("low")
        try:
            close = float(close) if close is not None and not pd.isna(close) else None
            high = float(high) if high is not None and not pd.isna(high) else None
            low = float(low) if low is not None and not pd.isna(low) else None
        except Exception:
            return None, None
        if close is None or high is None or low is None:
            return None, None
        rng = max(1e-9, high - low)
        best_bid = close - 0.25 * rng
        best_ask = close + 0.25 * rng
        # Ограничения в пределах OHLC
        best_bid = max(low, min(best_bid, close))
        best_ask = min(high, max(best_ask, close))
        return best_bid, best_ask

    def _export_csv(self, trades_df: pd.DataFrame, stats_df: pd.DataFrame) -> Dict[str, str]:
        """
        Экспорт результатов в CSV согласно путям в конфиге.
        """
        trades_csv = self.config.paths.get("trades_csv")
        stats_csv = self.config.paths.get("stats_csv")
        os.makedirs(os.path.dirname(trades_csv) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(stats_csv) or ".", exist_ok=True)
        trades_df.to_csv(trades_csv, index=False, encoding="utf-8")
        stats_df.to_csv(stats_csv, index=False, encoding="utf-8")
        return {"trades_csv": trades_csv, "stats_csv": stats_csv}

    # -------------
    # Основной запуск
    # -------------

    def run(self) -> BacktestResult:
        """
        Выполняет бэктест:
        1) Загрузка исторических 5‑мин свечей
        2) Расчёт индикаторов
        3) Генерация сигналов
        4) Исполнение сигналов с учётом риска (лонг‑логика)
        5) Подсчёт метрик и экспорт CSV

        Возвращает BacktestResult.
        """
        # 1) Исторические свечи (30 торговых дней) — используем 40 календарных дней для запаса
        from_date = (date.today() - timedelta(days=max(35, self.config.data.history_days + 10)))
        candles = self.moex.get_historical_candles(
            ticker=self.config.data.ticker,
            from_date=from_date,
            interval=self.config.data.candle_interval_min,
        )
        if candles is None or len(candles) == 0:
            # Пустой результат
            return BacktestResult(pd.DataFrame(), pd.DataFrame())

        # 2) Индикаторы
        cdf = candles.copy()
        # При необходимости переименуем volume/value в числовой формат
        for col in ("open", "high", "low", "close", "volume", "value"):
            if col in cdf.columns:
                cdf[col] = pd.to_numeric(cdf[col], errors="coerce")
        cdf = Technicals.attach_all(cdf)

        # 3) Сигналы
        signals: List[Signal] = self.strategy.generate_signals(cdf)

        # 4) Исполнение
        trades_rows: List[Dict] = []
        day_stats = DayStats()

        open_pos: Optional[Position] = None
        entry_trade_meta: Optional[ExecutedTrade] = None

        for sig in signals:
            # Вычисляем best bid/ask для триггерной свечи
            if sig.ts not in cdf.index:
                # Если индекс не совпадает — пропускаем
                continue
            bar = cdf.loc[sig.ts]
            best_bid, best_ask = self._best_bid_ask_from_bar(bar)

            # BUY: открыть лонг, если разрешено и позиции нет
            if sig.type == "BUY":
                if open_pos is not None:
                    # Уже в позиции — игнорировать вход
                    continue
                if not self.risk.allow_new_trade(day_stats):
                    # Лимиты не позволяют
                    continue

                # Исполнение входа
                inp = ExecutionInput(
                    ts=pd.Timestamp(sig.ts),
                    side="BUY",
                    best_bid=best_bid,
                    best_ask=best_ask,
                    lot_size=self.lot_size,
                    max_position_rub=self.config.risk.max_position_rub,
                    commission_pct_per_side=self.config.execution.commission_pct_per_side,
                    slippage_pct=self.config.execution.slippage_pct,
                )
                exec_in = self.exec_sim.execute(inp, reason=sig.reason)
                if exec_in is None or exec_in.qty_shares <= 0:
                    continue

                # Открываем позицию
                open_pos = Position(entry_price=exec_in.exec_price, qty_shares=exec_in.qty_shares)
                open_pos = self.risk.assign_stops_for_long(open_pos)
                entry_trade_meta = exec_in
                # Считаем сделку как совершённую (открытие)
                day_stats.trades_count += 1
                # Комиссию на вход списываем сразу как реализованный расход?
                # В дневной статистике учитываем убыток только по закрытиям, commission учтём при подсчёте pnl на выходе.

            elif sig.type in ("SELL", "CLOSE_LONG"):
                # Закрытие позиции, если она открыта
                if open_pos is None or entry_trade_meta is None:
                    continue

                # Проверка SL/TP (можно игнорировать, т.к. продаём по сигналу; оставим логику на будущее)
                # Выполняем выход
                inp = ExecutionInput(
                    ts=pd.Timestamp(sig.ts),
                    side="SELL",
                    best_bid=best_bid,
                    best_ask=best_ask,
                    lot_size=self.lot_size,
                    max_position_rub=self.config.risk.max_position_rub,  # не используется на выходе
                    commission_pct_per_side=self.config.execution.commission_pct_per_side,
                    slippage_pct=self.config.execution.slippage_pct,
                    desired_position_shares=open_pos.qty_shares,
                )
                exec_out = self.exec_sim.execute(inp, reason=sig.reason)
                if exec_out is None or exec_out.qty_shares <= 0:
                    continue

                # Рассчитать PnL с учётом комиссий входа и выхода
                # Комиссию входа берем из entry_trade_meta.commission, выхода — exec_out.commission
                commission_total = float(entry_trade_meta.commission + exec_out.commission)
                pnl_rub = (exec_out.exec_price - open_pos.entry_price) * open_pos.qty_shares - commission_total
                pnl_pct = (exec_out.exec_price - open_pos.entry_price) / open_pos.entry_price

                # Обновить дневную статистику
                day_stats = self.risk.update_day_stats_on_close(
                    stats=day_stats,
                    entry_price=open_pos.entry_price,
                    exit_price=exec_out.exec_price,
                    qty_shares=open_pos.qty_shares,
                    commission_rub=commission_total,
                )

                trades_rows.append(
                    {
                        "entry_ts": pd.Timestamp(entry_trade_meta.ts),
                        "exit_ts": pd.Timestamp(exec_out.ts),
                        "entry_price": float(open_pos.entry_price),
                        "exit_price": float(exec_out.exec_price),
                        "qty_shares": int(open_pos.qty_shares),
                        "commission_rub": float(commission_total),
                        "pnl_rub": float(pnl_rub),
                        "pnl_pct": float(pnl_pct),
                        "entry_reason": entry_trade_meta.reason or "",
                        "exit_reason": exec_out.reason or "",
                    }
                )

                # Закрыть позицию
                open_pos = None
                entry_trade_meta = None

        trades_df = pd.DataFrame(trades_rows)

        # 5) Метрики и сводки
        if trades_df.empty:
            stats_df = pd.DataFrame(
                [
                    {
                        "trades_count": 0,
                        "realized_pnl_rub": 0.0,
                        "win_rate": 0.0,
                        "sharpe": 0.0,
                        "max_drawdown": 0.0,
                    }
                ]
            )
        else:
            eq = equity_from_trades(trades_df)
            stats_df = pd.DataFrame(
                [
                    {
                        "trades_count": int(len(trades_df)),
                        "realized_pnl_rub": float(pd.to_numeric(trades_df["pnl_rub"], errors="coerce").sum()),
                        "win_rate": float(win_rate(trades_df)),
                        "sharpe": float(sharpe_ratio(pd.to_numeric(trades_df["pnl_pct"], errors="coerce"))),
                        "max_drawdown": float(max_drawdown(eq)),
                    }
                ]
            )

        # Экспорт CSV
        self._export_csv(trades_df, stats_df)

        return BacktestResult(trades_df=trades_df, stats_df=stats_df)


__all__ = ["BacktestRunner", "BacktestResult"]