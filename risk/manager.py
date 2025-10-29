"""
Риск‑менеджмент для демо‑робота GAZP.

Функциональность:
- Контроль дневных лимитов: максимум сделок/день, дневной лимит потерь
- Назначение стоп‑лосса и тейк‑профита для позиции в рамках конфигурации
- Проверка правил выхода (срабатывание SL/TP)
- Обновление дневной статистики по закрытию сделки

Зависимости:
- Параметры риска из [RiskLimits](gazprom_bot/config.py:1) и общая [Config](gazprom_bot/config.py:1)

Дисклеймер: учебная демо‑реализация. На реальном рынке применяются более сложные методы контроля риска.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

import math


ExitAction = Literal["NONE", "STOP", "TAKE"]


@dataclass
class DayStats:
    """
    Дневная статистика для контроля лимитов.
    - trades_count: количество совершённых сделок (включая закрытия)
    - realized_pnl_rub: реализованный PnL (руб) за день
    - realized_loss_rub: суммарный реализованный убыток (руб) — для лимита потерь
    """
    trades_count: int = 0
    realized_pnl_rub: float = 0.0
    realized_loss_rub: float = 0.0


@dataclass
class Position:
    """
    Простая модель лонг‑позиции.
    - entry_price: цена входа за акцию
    - qty_shares: количество акций
    - sl_price: стоп‑лосс цена (ниже entry_price для лонга)
    - tp_price: тейк‑профит цена (выше entry_price для лонга)
    """
    entry_price: float
    qty_shares: int
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None


@dataclass
class ExitDecision:
    """
    Решение по выходу из позиции.
    - action: NONE | STOP | TAKE
    - exit_price: цена выхода (если применимо)
    - reason: причина выхода
    """
    action: ExitAction
    exit_price: Optional[float] = None
    reason: str = ""


class RiskManager:
    """
    Риск‑менеджер с правилами:
    - Максимум сделок в день
    - Лимит дневного убытка
    - SL/TP для позиции: 0.8–1.0% и 1.5–2.0%, R:R ≥ 1:1.5
    """

    def __init__(self, risk_limits) -> None:
        """
        Параметры:
        - risk_limits: экземпляр [RiskLimits](gazprom_bot/config.py:1)
        """
        self.risk = risk_limits

    # ---------------------------
    # Проверки лимитов и допуск
    # ---------------------------

    def allow_new_trade(self, stats: DayStats) -> bool:
        """
        Проверяет, разрешено ли открывать новую сделку с учётом дневных лимитов.
        """
        if stats.trades_count >= self.risk.max_trades_per_day:
            return False
        if stats.realized_loss_rub >= self.risk.daily_loss_limit_rub:
            return False
        return True

    # --------------------------
    # Назначение SL/TP для лонга
    # --------------------------

    def assign_stops_for_long(self, pos: Position) -> Position:
        """
        Назначает SL/TP для лонг‑позиции в рамках конфигурации и поддерживает R:R ≥ min_rr.

        Алгоритм:
        - Выбираем SL как верхнюю границу (строже): stop_loss_pct_max
        - Выбираем TP как максимум из take_profit_pct_min и min_rr * SL; ограничиваем максимумом take_profit_pct_max
        - Рассчитываем абсолютные цены sl_price и tp_price по entry_price
        """
        sl_pct = float(self.risk.stop_loss_pct_max)
        tp_pct = max(float(self.risk.take_profit_pct_min), float(self.risk.min_rr) * sl_pct)
        tp_pct = min(tp_pct, float(self.risk.take_profit_pct_max))

        pos.sl_price = pos.entry_price * (1.0 - sl_pct)
        pos.tp_price = pos.entry_price * (1.0 + tp_pct)
        return pos

    # --------------------------
    # Проверка выхода по SL/TP
    # --------------------------

    def check_exit_rules_for_long(self, pos: Position, last_price: Optional[float]) -> ExitDecision:
        """
        Проверяет срабатывание стоп‑лосса/тейк‑профита для лонг‑позиции.
        Возвращает ExitDecision.
        """
        if last_price is None or last_price <= 0 or pos.qty_shares <= 0:
            return ExitDecision(action="NONE")

        # SL
        if pos.sl_price and last_price <= pos.sl_price:
            return ExitDecision(action="STOP", exit_price=pos.sl_price, reason="Стоп‑лосс достигнут")

        # TP
        if pos.tp_price and last_price >= pos.tp_price:
            return ExitDecision(action="TAKE", exit_price=pos.tp_price, reason="Тейк‑профит достигнут")

        return ExitDecision(action="NONE")

    # ------------------------------------
    # Обновление дневной статистики (PnL)
    # ------------------------------------

    def update_day_stats_on_close(self, stats: DayStats, entry_price: float, exit_price: float, qty_shares: int, commission_rub: float = 0.0) -> DayStats:
        """
        Обновляет дневную статистику при закрытии позиции.

        PnL:
        - Для лонга: pnl = (exit_price - entry_price) * qty_shares - commission_rub
        - Комиссию учитываем как расход

        Также:
        - Увеличиваем trades_count на 1
        - Если pnl < 0, увеличиваем realized_loss_rub
        """
        pnl = (exit_price - entry_price) * qty_shares - commission_rub
        stats.realized_pnl_rub += pnl
        stats.trades_count += 1
        if pnl < 0:
            stats.realized_loss_rub += abs(pnl)
        return stats


__all__ = [
    "RiskManager",
    "DayStats",
    "Position",
    "ExitDecision",
    "ExitAction",
]