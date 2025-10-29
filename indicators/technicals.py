"""
Технические индикаторы для 5‑минутных свечей GAZP.

Реализовано:
- SMA (скользящая средняя по окну)
- EMA (экспоненциальная средняя)
- RSI (14) по закрытиям
- MACD (12/26/9)
- attach_all(candles_df): добавляет индикаторы к датафрейму свечей

Требования к входным данным:
- candles_df: pandas.DataFrame с индексом времени (желательно end_ts) и колонками минимум 'close'.
- Для фильтра объёма: рекомендуется наличие колонки 'volume' (будет добавлен vol_sma20).

Примечания:
- Все вычисления векторизованы через pandas.
- NaN значения на старте окна — нормальная ситуация (недостаточно истории для окна).
- Имена колонок индикаторов: 'sma20', 'ema9', 'rsi14', 'macd', 'macd_signal', 'macd_hist', 'vol_sma20'.
- Функции устойчивы к NaN и отсутствующим значениям в исходных колонках.

Дисклеймер: данный код предназначен исключительно для учебных целей.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class IndicatorParams:
    sma_window: int = 20
    ema_span: int = 9
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    vol_avg_window: int = 20


class Technicals:
    """
    Набор статических методов для расчёта индикаторов и хелпер attach_all().
    """

    @staticmethod
    def compute_sma(series: pd.Series, window: int = 20) -> pd.Series:
        """
        Простой SMA по окну 'window'. Возвращает Series той же длины.
        """
        if series is None or len(series) == 0:
            return pd.Series(dtype=float)
        return pd.to_numeric(series, errors="coerce").rolling(window=window, min_periods=1).mean()

    @staticmethod
    def compute_ema(series: pd.Series, span: int = 9) -> pd.Series:
        """
        Экспоненциальная средняя EMA с параметром 'span'. adjust=False для более привычного трейдингового EMA.
        """
        if series is None or len(series) == 0:
            return pd.Series(dtype=float)
        s = pd.to_numeric(series, errors="coerce")
        return s.ewm(span=span, adjust=False, min_periods=1).mean()

    @staticmethod
    def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI по закрытиям с периодом 'period'. Реализация через EMA средних приростов/убытков.
        Формула:
          delta = close.diff()
          gains = delta.clip(lower=0)
          losses = -delta.clip(upper=0)
          avg_gain = EMA(gains, period)
          avg_loss = EMA(losses, period)
          RS = avg_gain / avg_loss
          RSI = 100 - 100 / (1 + RS)
        Граничные случаи:
          - Если avg_loss == 0 => RSI = 100
          - Если avg_gain == 0 => RSI = 0
        """
        if close is None or len(close) == 0:
            return pd.Series(dtype=float)
        c = pd.to_numeric(close, errors="coerce")
        delta = c.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Обработка деления на ноль
        rsi = rsi.where(avg_loss != 0, 100.0)
        rsi = rsi.where(avg_gain != 0, 0.0)
        return rsi

    @staticmethod
    def compute_macd(
        close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD: линия = EMA(fast) - EMA(slow), сигнал = EMA(MACD, signal), гистограмма = MACD - сигнал.
        Возвращает (macd_line, signal_line, hist).
        """
        if close is None or len(close) == 0:
            empty = pd.Series(dtype=float)
            return empty, empty, empty
        c = pd.to_numeric(close, errors="coerce")
        ema_fast = c.ewm(span=fast, adjust=False, min_periods=1).mean()
        ema_slow = c.ewm(span=slow, adjust=False, min_periods=1).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=1).mean()
        hist = macd_line - signal_line
        return macd_line, signal_line, hist

    @staticmethod
    def attach_all(candles_df: pd.DataFrame, params: Optional[IndicatorParams] = None) -> pd.DataFrame:
        """
        Добавляет индикаторы к датафрейму свечей. Возвращает новый DataFrame (копию) с добавленными колонками.

        Ожидаемые входные колонки:
        - 'close' (обязательно для большинства индикаторов)
        - 'volume' (опционально; используется для vol_sma)

        Добавляемые колонки:
        - 'sma20', 'ema9', 'rsi14', 'macd', 'macd_signal', 'macd_hist'
        - 'vol_sma20' (если есть 'volume')

        Примечание:
        - Если индекс не является DatetimeIndex, индикаторы всё равно будут рассчитаны.
        """
        if candles_df is None or len(candles_df) == 0:
            # Возврат пустого каркаса колонок
            cols = [
                "sma20",
                "ema9",
                "rsi14",
                "macd",
                "macd_signal",
                "macd_hist",
                "vol_sma20",
            ]
            return pd.DataFrame(columns=cols)

        df = candles_df.copy()

        p = params or IndicatorParams()

        # Базовые индикаторы по close
        close = pd.to_numeric(df.get("close"), errors="coerce")
        df["sma20"] = Technicals.compute_sma(close, window=p.sma_window)
        df["ema9"] = Technicals.compute_ema(close, span=p.ema_span)
        df["rsi14"] = Technicals.compute_rsi(close, period=p.rsi_period)
        macd_line, signal_line, hist = Technicals.compute_macd(
            close, fast=p.macd_fast, slow=p.macd_slow, signal=p.macd_signal
        )
        df["macd"] = macd_line
        df["macd_signal"] = signal_line
        df["macd_hist"] = hist

        # Объём: скользящее среднее объёма (если колонка существует)
        if "volume" in df.columns:
            volume = pd.to_numeric(df["volume"], errors="coerce")
            df["vol_sma20"] = Technicals.compute_sma(volume, window=p.vol_avg_window)
        else:
            df["vol_sma20"] = np.nan

        return df


__all__ = ["Technicals", "IndicatorParams"]