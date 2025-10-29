"""
Стратегия внутридневной торговли GAZP: пробой уровней + сигналы по RSI/MACD.

Реализовано:
- Генерация сигналов BUY/SELL/CLOSE_LONG по 5‑мин свечам
- Условия входа:
  1) Пробой локального сопротивления (High > swing_high_prev) и объём > средний
  2) RSI < 30 (перепроданность) + разворотная свеча (молот или бычье поглощение)
  3) Положительная дивергенция MACD (цена делает ниже минимум, MACD_hist делает выше минимум)
- Условия выхода:
  - RSI > 70 + медвежья дивергенция MACD ⇒ сигнал SELL/CLOSE_LONG
  - Примечание: формальные SL/TP и дневные лимиты применяет [RiskManager](gazprom_bot/risk/manager.py:1)

Зависимости:
- Индикаторы должны быть добавлены заранее через [Technicals.attach_all()](gazprom_bot/indicators/technicals.py:6)
  и содержать колонки: 'rsi14', 'macd', 'macd_signal', 'macd_hist', 'vol_sma20'.
- Входной датафрейм свечей содержит: 'open','high','low','close','volume'.

Выход:
- Список сигналов [Signal](gazprom_bot/strategy/gazp_breakout.py:1), каждый включает тип, время триггера, цену и причину.

Дисклеймер: учебная демо‑реализация; логика упрощена и не учитывает все рыночные нюансы.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import numpy as np


@dataclass
class StrategyParams:
    lookback_swing: int = 10            # окно для swing high/low
    volume_filter: bool = True          # требовать объём выше среднего
    rsi_oversold: float = 30.0          # порог RSI для перепроданности
    rsi_overbought: float = 70.0        # порог RSI для перекупленности
    macd_div_lookback: int = 20         # окно для поиска дивергенций
    engulf_body_ratio: float = 0.55     # минимальная доля тела текущей свечи от диапазона (для engulfing)
    hammer_tail_ratio: float = 0.6      # доля нижней тени для молота
    min_bars_for_indicators: int = 30   # минимум баров прежде чем генерировать сигналы


@dataclass
class Signal:
    """
    Торговый сигнал.
    type: 'BUY' | 'SELL' | 'CLOSE_LONG'
    ts: индекс свечи (время закрытия)
    price: ориентир цены (close текущей свечи)
    reason: текстовое описание причины
    """
    type: str
    ts: pd.Timestamp
    price: float
    reason: str


class GazpBreakoutStrategy:
    """
    Реализация стратегии пробоя уровней для GAZP.

    Основной метод:
    - [GazpBreakoutStrategy.generate_signals()](gazprom_bot/strategy/gazp_breakout.py:2)
    """

    def __init__(self, params: Optional[StrategyParams] = None) -> None:
        self.params = params or StrategyParams()

    # -----------------------
    # Вспомогательные методы
    # -----------------------

    def _swing_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает предыдущие swing high/low как экстремумы lookback окна,
        сдвинутые на 1 бар назад (чтобы текущий бар не влиял на уровень).
        """
        p = self.params
        swing_high_prev = pd.to_numeric(df["high"], errors="coerce").rolling(p.lookback_swing, min_periods=1).max().shift(1)
        swing_low_prev = pd.to_numeric(df["low"], errors="coerce").rolling(p.lookback_swing, min_periods=1).min().shift(1)
        return pd.DataFrame({"swing_high_prev": swing_high_prev, "swing_low_prev": swing_low_prev}, index=df.index)

    @staticmethod
    def _is_bullish_engulfing(prev_open: float, prev_close: float, curr_open: float, curr_close: float, curr_high: float, curr_low: float, min_body_ratio: float) -> bool:
        """
        Упрощённая проверка бычьего поглощения:
        - Предыдущая свеча медвежья (prev_close < prev_open)
        - Тело текущей свечи достаточной величины
        - Текущее тело охватывает тело предыдущей свечи (curr_open <= prev_close и curr_close >= prev_open)
        """
        if any(v is None or np.isnan(v) for v in [prev_open, prev_close, curr_open, curr_close, curr_high, curr_low]):
            return False
        prev_bear = prev_close < prev_open
        curr_body = abs(curr_close - curr_open)
        full_range = max(1e-9, curr_high - curr_low)
        body_ok = curr_body / full_range >= min_body_ratio
        engulf = (curr_open <= prev_close) and (curr_close >= prev_open)
        return prev_bear and body_ok and engulf and (curr_close > curr_open)

    @staticmethod
    def _is_hammer(curr_open: float, curr_close: float, curr_high: float, curr_low: float, min_tail_ratio: float) -> bool:
        """
        Упрощённая проверка «молота»:
        - Длинная нижняя тень: (min(open,close) - low) / (high - low) >= min_tail_ratio
        - Верхняя тень небольшая
        - Закрытие ближе к максимуму
        """
        if any(v is None or np.isnan(v) for v in [curr_open, curr_close, curr_high, curr_low]):
            return False
        rng = max(1e-9, curr_high - curr_low)
        lower_tail = (min(curr_open, curr_close) - curr_low) / rng
        upper_tail = (curr_high - max(curr_open, curr_close)) / rng
        close_near_high = (curr_high - curr_close) / rng <= 0.2
        return lower_tail >= min_tail_ratio and upper_tail <= 0.3 and close_near_high

    def _has_positive_macd_divergence(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """
        Положительная дивергенция:
        - Цена делает ниже минимум относительно предыдущего локального минимума,
          а macd_hist делает выше минимум относительно предыдущего минимума.
        Простая эвристика: сравниваем последние два локальных минимума по цене и macd_hist.
        """
        if idx < 5:
            return False
        sub = df.iloc[max(0, idx - lookback): idx + 1]
        price = pd.to_numeric(sub["close"], errors="coerce")
        macdh = pd.to_numeric(sub["macd_hist"], errors="coerce")

        # Ищем два последних локальных минимума по цене
        # Локальный минимум: close[i] < close[i-1] и close[i] < close[i+1]
        # Для простоты: используем rolling min и сравнение крайних точек
        if len(sub) < 5 or price.isna().all() or macdh.isna().all():
            return False

        # Первый минимум — минимум на первой половине окна, второй — на второй половине
        mid = len(sub) // 2
        left = price.iloc[:mid]
        right = price.iloc[mid:]

        if left.empty or right.empty:
            return False

        left_min_idx = left.idxmin()
        right_min_idx = right.idxmin()

        # Проверяем: правый минимум по цене ниже левого минимума
        price_div = price.loc[right_min_idx] < price.loc[left_min_idx]

        # Проверяем: гистограмма MACD на правом минимуме выше, чем на левом (т.е. «улучшилась»)
        macd_div = macdh.loc[right_min_idx] > macdh.loc[left_min_idx]

        return bool(price_div and macd_div)

    def _has_negative_macd_divergence(self, df: pd.DataFrame, idx: int, lookback: int) -> bool:
        """
        Медвежья дивергенция:
        - Цена делает выше максимум, а macd_hist не подтверждает (ниже на втором максимуме).
        """
        if idx < 5:
            return False
        sub = df.iloc[max(0, idx - lookback): idx + 1]
        price = pd.to_numeric(sub["close"], errors="coerce")
        macdh = pd.to_numeric(sub["macd_hist"], errors="coerce")
        if len(sub) < 5 or price.isna().all() or macdh.isna().all():
            return False

        mid = len(sub) // 2
        left = price.iloc[:mid]
        right = price.iloc[mid:]
        if left.empty or right.empty:
            return False

        left_max_idx = left.idxmax()
        right_max_idx = right.idxmax()

        price_div = price.loc[right_max_idx] > price.loc[left_max_idx]
        macd_div = macdh.loc[right_max_idx] < macdh.loc[left_max_idx]

        return bool(price_div and macd_div)

    # -------------------
    # Генерация сигналов
    # -------------------

    def generate_signals(self, candles_df: pd.DataFrame, l1_volume_avg: Optional[float] = None) -> List[Signal]:
        """
        Генерирует сигналы по свечному датафрейму с уже добавленными индикаторами.

        Параметры:
        - candles_df: DataFrame со свечами и индикаторами (см. выше)
        - l1_volume_avg: опционально средний объём L1 (если доступен отдельный поток); сейчас не используется напрямую,
                         атрибут оставлен для совместимости интерфейса.

        Возвращает:
        - Список Signal с типами 'BUY', 'SELL', 'CLOSE_LONG'

        Примечание:
        - Стратегия генерирует сигналы на закрытии свечи (используем цену close текущей свечи).
        - Фильтр объёма: volume > vol_sma20, если volume_filter=True и оба значения не NaN.
        """
        signals: List[Signal] = []
        if candles_df is None or len(candles_df) < self.params.min_bars_for_indicators:
            return signals

        df = candles_df.copy()

        # Swing уровни
        swing_levels = self._swing_levels(df)
        df = pd.concat([df, swing_levels], axis=1)

        # Основной проход по барам
        p = self.params
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            ts = df.index[i] if df.index is not None else pd.Timestamp.now()

            # Базовые поля
            open_ = float(row["open"]) if "open" in row and not pd.isna(row["open"]) else None
            high = float(row["high"]) if "high" in row and not pd.isna(row["high"]) else None
            low = float(row["low"]) if "low" in row and not pd.isna(row["low"]) else None
            close = float(row["close"]) if "close" in row and not pd.isna(row["close"]) else None
            volume = float(row["volume"]) if "volume" in row and not pd.isna(row["volume"]) else None

            # Индикаторы
            rsi = float(row["rsi14"]) if "rsi14" in row and not pd.isna(row["rsi14"]) else None
            vol_sma = float(row["vol_sma20"]) if "vol_sma20" in row and not pd.isna(row["vol_sma20"]) else None

            swing_high_prev = float(row["swing_high_prev"]) if "swing_high_prev" in row and not pd.isna(row["swing_high_prev"]) else None
            swing_low_prev = float(row["swing_low_prev"]) if "swing_low_prev" in row and not pd.isna(row["swing_low_prev"]) else None

            # Фильтр объёма
            vol_ok = True
            if p.volume_filter and volume is not None and vol_sma is not None:
                vol_ok = volume > vol_sma

            # 1) Пробой сопротивления + объём
            breakout_buy = False
            if high is not None and swing_high_prev is not None:
                breakout_buy = (high > swing_high_prev) and vol_ok

            # 2) RSI < 30 + разворотная свеча (молот или бычье поглощение)
            prev_open = float(prev["open"]) if "open" in prev and not pd.isna(prev["open"]) else None
            prev_close = float(prev["close"]) if "close" in prev and not pd.isna(prev["close"]) else None

            bull_engulf = self._is_bullish_engulfing(
                prev_open, prev_close, open_, close, high, low, min_body_ratio=p.engulf_body_ratio
            )
            hammer = self._is_hammer(open_, close, high, low, min_tail_ratio=p.hammer_tail_ratio)
            rsi_buy = (rsi is not None) and (rsi < p.rsi_oversold) and (bull_engulf or hammer)

            # 3) Положительная дивергенция MACD
            macd_pos_div = self._has_positive_macd_divergence(df, i, p.macd_div_lookback)

            # BUY сигнал при любом из условий
            if breakout_buy or rsi_buy or macd_pos_div:
                reason_parts = []
                if breakout_buy:
                    reason_parts.append("пробой сопротивления + объём")
                if rsi_buy:
                    reason_parts.append("RSI<30 + разворотная свеча")
                if macd_pos_div:
                    reason_parts.append("положительная дивергенция MACD")
                reason = "; ".join(reason_parts)
                if close is not None:
                    signals.append(Signal(type="BUY", ts=ts, price=close, reason=reason))
                continue  # приоритет входа над выходом на том же баре

            # Выход/продажа: RSI>70 + медвежья дивергенция MACD
            rsi_sell = (rsi is not None) and (rsi > p.rsi_overbought)
            macd_neg_div = self._has_negative_macd_divergence(df, i, p.macd_div_lookback)
            if rsi_sell and macd_neg_div:
                if close is not None:
                    signals.append(Signal(type="SELL", ts=ts, price=close, reason="RSI>70 + медвежья дивергенция MACD"))
                else:
                    # Фолбэк
                    if high is not None:
                        signals.append(Signal(type="SELL", ts=ts, price=high, reason="RSI>70 + медвежья дивергенция MACD"))
                continue

            # Дополнительно: если цена пробила поддержку (low < swing_low_prev) и объём высокий — можно закрыть лонг
            if low is not None and swing_low_prev is not None and vol_ok and (low < swing_low_prev):
                if close is not None:
                    signals.append(Signal(type="CLOSE_LONG", ts=ts, price=close, reason="пробой поддержки + объём"))
                else:
                    if low is not None:
                        signals.append(Signal(type="CLOSE_LONG", ts=ts, price=low, reason="пробой поддержки + объём"))

        return signals


__all__ = ["GazpBreakoutStrategy", "StrategyParams", "Signal"]