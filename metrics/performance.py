"""
Модуль расчёта метрик производительности для демо‑робота GAZP.

Реализовано:
- Sharpe ratio (по ряду доходностей; без годовой аппроксимации)
- Максимальная просадка (Max Drawdown) по кривой капитала
- Win rate (доля прибыльных сделок)
- Построение кривой капитала из списка закрытых сделок

Ожидаемые данные закрытых сделок:
- DataFrame с колонками как минимум:
  ['entry_ts','exit_ts','entry_price','exit_price','qty_shares','commission_rub','pnl_rub','pnl_pct']
  где:
    - pnl_rub = (exit_price - entry_price) * qty_shares - commission_rub
    - pnl_pct = (exit_price - entry_price) / entry_price   (на сделку; без учёта плеча)

Дисклеймер: учебная демо‑реализация; метрики упрощены и не годовые.
"""

from __future__ import annotations

from typing import Optional, Sequence
import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series | Sequence[float], rf: float = 0.0) -> float:
    """
    Sharpe ratio: (mean(returns - rf)) / std(returns - rf)
    Без годовой аппроксимации. Если std=0 или данных недостаточно — возвращает 0.0.

    Параметры:
    - returns: ряд доходностей (на сделку, либо на период)
    - rf: безрисковая ставка на период (обычно 0.0 для демо)

    Возвращает:
    - float: значение Sharpe
    """
    if returns is None:
        return 0.0
    r = pd.Series(returns).dropna().astype(float)
    if len(r) < 2:
        return 0.0
    excess = r - float(rf)
    std = excess.std(ddof=1)
    if std <= 0 or np.isnan(std):
        return 0.0
    return float(excess.mean() / std)


def max_drawdown(equity_curve: pd.Series | Sequence[float]) -> float:
    """
    Максимальная просадка по кривой капитала.

    Параметры:
    - equity_curve: ряд значений капитала (кумулятивный PnL или баланс)

    Возвращает:
    - float: максимальная просадка (в тех же единицах, что и equity_curve)
    """
    if equity_curve is None:
        return 0.0
    e = pd.Series(equity_curve).dropna().astype(float)
    if len(e) == 0:
        return 0.0
    running_max = e.cummax()
    drawdowns = running_max - e
    mdd = drawdowns.max()
    return float(mdd if pd.notna(mdd) else 0.0)


def win_rate(trades_df: pd.DataFrame) -> float:
    """
    Win rate: доля прибыльных сделок.

    Ожидается колонка 'pnl_rub' или 'pnl_pct'. Предпочтительно 'pnl_rub'.
    """
    if trades_df is None or len(trades_df) == 0:
        return 0.0
    df = trades_df.copy()
    if "pnl_rub" in df.columns:
        pnl = pd.to_numeric(df["pnl_rub"], errors="coerce")
    elif "pnl_pct" in df.columns:
        pnl = pd.to_numeric(df["pnl_pct"], errors="coerce")
    else:
        return 0.0
    pnl = pnl.dropna()
    if len(pnl) == 0:
        return 0.0
    wins = (pnl > 0).sum()
    return float(wins) / float(len(pnl))


def equity_from_trades(trades_df: pd.DataFrame, start_equity: float = 0.0) -> pd.Series:
    """
    Строит кривую капитала по закрытым сделкам.

    Параметры:
    - trades_df: DataFrame закрытых сделок с колонкой 'pnl_rub'
    - start_equity: начальный капитал/база (по умолчанию 0.0, т.е. кумулятивный PnL)

    Возвращает:
    - pd.Series: ряд капитала, индекс — по 'exit_ts' если доступен, иначе RangeIndex
    """
    if trades_df is None or len(trades_df) == 0:
        return pd.Series(dtype=float)

    df = trades_df.copy()
    pnl = pd.to_numeric(df.get("pnl_rub"), errors="coerce").fillna(0.0)

    # Индекс — по времени выхода сделки
    if "exit_ts" in df.columns and df["exit_ts"].notna().all():
        try:
            idx = pd.to_datetime(df["exit_ts"])
        except Exception:
            idx = None
    else:
        idx = None

    cum = pnl.cumsum() + float(start_equity)
    if idx is not None:
        cum.index = idx
    return cum


__all__ = [
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "equity_from_trades",
]