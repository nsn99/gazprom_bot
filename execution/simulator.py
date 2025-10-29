"""
Симулятор исполнения заявок по лучшему bid/ask на триггерной 5‑мин свече.

Модель исполнения (агрессивная):
- BUY: цена исполнения = best_ask * (1 + slippage_pct)
- SELL: цена исполнения = best_bid * (1 - slippage_pct)
- Комиссия: commission_pct_per_side от оборота сделки
- Проскальзывание: учитывается в цене исполнения (относительно лучшего bid/ask)
- Размер позиции: не превышает max_position_rub (стоимость входа), округление в целые лоты LOTSIZE

Интерфейсы:
- [class ExecutionSimulator](gazprom_bot/execution/simulator.py:1)
  - [ExecutionSimulator.position_value_limit_sizing()](gazprom_bot/execution/simulator.py:1)
  - [ExecutionSimulator.calc_exec_price()](gazprom_bot/execution/simulator.py:1)
  - [ExecutionSimulator.execute()](gazprom_bot/execution/simulator.py:1)

Зависимости:
- Конфигурация комиссий и лимитов: [Config](gazprom_bot/config.py:1)
- Стратегические сигналы: см. [Signal](gazprom_bot/strategy/gazp_breakout.py:1)

Дисклеймер: учебная демо‑реализация; модель исполнения упрощена.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any
import math
import pandas as pd


Side = Literal["BUY", "SELL"]


@dataclass
class ExecutionInput:
    """
    Входные данные для исполнения.
    - ts: метка времени (обычно время закрытия триггерной свечи)
    - side: 'BUY' или 'SELL'
    - best_bid: лучший bid (float) на момент триггера
    - best_ask: лучший ask (float) на момент триггера
    - lot_size: размер лота инструмента (int, например 10 для GAZP)
    - max_position_rub: лимит стоимости позиции в рублях (например 100_000)
    - commission_pct_per_side: комиссия на одну сторону (например 0.0003)
    - slippage_pct: относительное проскальзывание (например 0.002)
    - desired_position_shares: желаемое количество акций (опционально); если не задано — рассчитывается по лимиту
    """
    ts: pd.Timestamp
    side: Side
    best_bid: Optional[float]
    best_ask: Optional[float]
    lot_size: int
    max_position_rub: float
    commission_pct_per_side: float
    slippage_pct: float
    desired_position_shares: Optional[int] = None


@dataclass
class ExecutedTrade:
    """
    Результаты исполнения сделки.
    - ts: метка времени исполнения
    - side: 'BUY'/'SELL'
    - exec_price: цена исполнения с учётом проскальзывания
    - qty_lots: исполненное кол-во лотов
    - qty_shares: исполненное кол-во акций
    - gross_value: оборот сделки (exec_price * qty_shares)
    - commission: комиссия на сторону (gross_value * commission_pct_per_side)
    - slippage_value: суммарная стоимость проскальзывания (руб) относительно лучшего bid/ask
    - net_value: итоговая стоимость с учётом комиссии (для BUY — затраты, для SELL — поступления)
    - reason: текст причины (передаётся из стратегии/контроллера)
    """
    ts: pd.Timestamp
    side: Side
    exec_price: float
    qty_lots: int
    qty_shares: int
    gross_value: float
    commission: float
    slippage_value: float
    net_value: float
    reason: str = ""


class ExecutionSimulator:
    """
    Симулятор исполнения заявок по лучшему bid/ask с проскальзыванием и комиссиями.

    Основные методы:
    - [ExecutionSimulator.position_value_limit_sizing()](gazprom_bot/execution/simulator.py:1)
    - [ExecutionSimulator.calc_exec_price()](gazprom_bot/execution/simulator.py:1)
    - [ExecutionSimulator.execute()](gazprom_bot/execution/simulator.py:1)
    """

    @staticmethod
    def position_value_limit_sizing(price: Optional[float], lot_size: int, cash_limit_rub: float) -> tuple[int, int]:
        """
        Рассчитывает максимум лотов и акций, укладывающийся в лимит стоимости позиции.

        Вход:
        - price: ориентир цены за 1 акцию (float)
        - lot_size: кол-во акций в лоте (int)
        - cash_limit_rub: лимит стоимости позиции в рублях

        Выход:
        - (qty_lots, qty_shares)
        """
        if price is None or price <= 0 or lot_size <= 0 or cash_limit_rub <= 0:
            return 0, 0
        max_shares = int(cash_limit_rub // price)
        qty_lots = max_shares // lot_size
        qty_lots = max(0, qty_lots)
        qty_shares = qty_lots * lot_size
        return qty_lots, qty_shares

    @staticmethod
    def calc_exec_price(side: Side, best_bid: Optional[float], best_ask: Optional[float], slippage_pct: float) -> Optional[float]:
        """
        Возвращает цену исполнения в зависимости от стороны и проскальзывания.
        BUY  => best_ask * (1 + slippage)
        SELL => best_bid * (1 - slippage)
        """
        if side == "BUY":
            if best_ask is None or best_ask <= 0:
                return None
            return float(best_ask) * (1.0 + float(slippage_pct))
        else:
            if best_bid is None or best_bid <= 0:
                return None
            return float(best_bid) * (1.0 - float(slippage_pct))

    def execute(self, inp: ExecutionInput, reason: str = "") -> Optional[ExecutedTrade]:
        """
        Исполняет сделку по заданным параметрам и возвращает результат.

        Алгоритм:
        1) Рассчитывает цену исполнения с учётом проскальзывания
        2) Определяет кол-во в лотах/акциях:
           - если desired_position_shares задано, округляет вниз до целых лотов
           - иначе рассчитывает по лимиту стоимости позиции
        3) Рассчитывает оборот, комиссию, стоимость проскальзывания и чистую стоимость.

        Возвращает:
        - [ExecutedTrade](gazprom_bot/execution/simulator.py:1) или None, если исполнение невозможно (нет котировки)
        """
        exec_price = self.calc_exec_price(inp.side, inp.best_bid, inp.best_ask, inp.slippage_pct)
        if exec_price is None:
            return None

        # Определение количества
        if inp.desired_position_shares and inp.desired_position_shares > 0:
            qty_lots = int(inp.desired_position_shares // inp.lot_size)
            qty_lots = max(0, qty_lots)
            qty_shares = qty_lots * inp.lot_size
            # Проверка лимита стоимости
            if qty_shares * exec_price > inp.max_position_rub:
                # Урежем до лимита
                lim_lots, lim_shares = self.position_value_limit_sizing(exec_price, inp.lot_size, inp.max_position_rub)
                qty_lots, qty_shares = lim_lots, lim_shares
        else:
            qty_lots, qty_shares = self.position_value_limit_sizing(exec_price, inp.lot_size, inp.max_position_rub)

        if qty_shares <= 0:
            return None

        # Стоимость сделки
        gross_value = exec_price * qty_shares
        commission = gross_value * float(inp.commission_pct_per_side)

        # Стоимость проскальзывания (опциональная метрика): разница относительно лучшего bid/ask
        if inp.side == "BUY":
            best_ref = inp.best_ask
            slip_unit = exec_price - (best_ref or exec_price)
        else:
            best_ref = inp.best_bid
            slip_unit = (best_ref or exec_price) - exec_price
        slip_unit = max(0.0, float(slip_unit))
        slippage_value = slip_unit * qty_shares

        # Чистая стоимость: для BUY — расход (gross + commission), для SELL — приход (gross - commission)
        if inp.side == "BUY":
            net_value = -(gross_value + commission)
        else:
            net_value = (gross_value - commission)

        trade = ExecutedTrade(
            ts=inp.ts,
            side=inp.side,
            exec_price=float(exec_price),
            qty_lots=int(qty_lots),
            qty_shares=int(qty_shares),
            gross_value=float(gross_value),
            commission=float(commission),
            slippage_value=float(slippage_value),
            net_value=float(net_value),
            reason=reason or "",
        )
        return trade


__all__ = [
    "ExecutionSimulator",
    "ExecutionInput",
    "ExecutedTrade",
    "Side",
]