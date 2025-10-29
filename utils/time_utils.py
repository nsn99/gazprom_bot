"""
Утилиты времени для контроля торговой сессии и работы с таймзонами.

Функциональность:
- now_msk(): текущее время в таймзоне Europe/Moscow (при наличии tzdata), иначе локальное.
- is_trading_time(now=None, session=None): проверка нахождения времени в окне торговой сессии.
- seconds_until_session_end(now=None, session=None): секунд до окончания сессии, либо 0 если вне сессии.

Заметки:
- Используется zoneinfo (Python 3.9+). Если tzdata недоступна в окружении, возвращается локальное время и проверка идёт по нему.
- session: экземпляр [SessionParams](gazprom_bot/config.py:1) из конфигурации. Если не передан, берутся значения по умолчанию (10:00–18:45 MSK, poll_interval=1s).
- Формат времени в SessionParams — строки 'HH:MM'. Для преобразования используется [parse_hhmm_to_time()](gazprom_bot/config.py:1).

Дисклеймер: данный код предназначен исключительно для учебных целей.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # Фолбэк на отсутствие tzdata

# Избегаем тяжёлых импортов конфигурации на уровне модуля для упрощения тестирования.
# Импортируем по необходимости внутри функций.
MSK_TZ_NAME = "Europe/Moscow"


def now_msk() -> datetime:
    """
    Возвращает текущее время в таймзоне Europe/Moscow, если доступно,
    иначе локальное системное время.

    Возвращаемое значение:
    - datetime (timezone-aware при наличии ZoneInfo; иначе naive локальное).
    """
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(MSK_TZ_NAME))
        except Exception:
            # Если tzdata недоступна в окружении (например, в урезанных контейнерах)
            return datetime.now()
    return datetime.now()


def _session_bounds_from_params(session) -> tuple[time, time]:
    """
    Вспомогательная функция: получает (session_start, session_end) из SessionParams.

    Параметры:
    - session: объект SessionParams из [gazprom_bot/config.py](gazprom_bot/config.py:1)

    Возвращает:
    - (start_time: time, end_time: time)
    """
    # Ленивая загрузка парсера HH:MM
    from gazprom_bot.config import parse_hhmm_to_time, SessionParams

    if session is None:
        session = SessionParams()

    start_t = parse_hhmm_to_time(session.session_start_hhmm)
    end_t = parse_hhmm_to_time(session.session_end_hhmm)
    return start_t, end_t


def is_trading_time(now: Optional[datetime] = None, session=None) -> bool:
    """
    Проверяет, находится ли 'now' внутри окна торговой сессии, определённой в session.

    Параметры:
    - now: datetime, можно передать конкретное время; если None, используется now_msk()
    - session: объект SessionParams; если None, используются значения по умолчанию

    Возвращает:
    - bool: True если текущее время в диапазоне [start, end], иначе False
    """
    if now is None:
        now = now_msk()

    start_t, end_t = _session_bounds_from_params(session)
    local_time = now.time()
    return start_t <= local_time <= end_t


def seconds_until_session_end(now: Optional[datetime] = None, session=None) -> int:
    """
    Возвращает количество секунд до конца торговой сессии.
    Если текущее время вне сессии — возвращает 0.

    Параметры:
    - now: datetime; если None — now_msk()
    - session: SessionParams; если None — значения по умолчанию

    Возвращает:
    - int: число секунд до окончания торговой сессии
    """
    if now is None:
        now = now_msk()

    start_t, end_t = _session_bounds_from_params(session)
    local_time = now.time()

    # Если вне сессии — 0 секунд
    if local_time < start_t or local_time > end_t:
        return 0

    # Собираем datetime конца сессии в той же дате, что и 'now'
    end_dt = datetime.combine(now.date(), end_t, tzinfo=getattr(now, "tzinfo", None))
    delta = end_dt - now
    return max(0, int(delta.total_seconds()))


def next_candle_close_ts(now: Optional[datetime] = None, interval_minutes: int = 5) -> datetime:
    """
    Вычисляет метку времени закрытия следующей свечи с заданным интервалом (минуты).
    Используется для контроля финализации текущей 5‑мин свечи в демо-режиме.

    Параметры:
    - now: datetime; если None — now_msk()
    - interval_minutes: интервал свечи в минутах (по умолчанию 5)

    Возвращает:
    - datetime: отметка времени закрытия следующей свечи
    """
    if now is None:
        now = now_msk()
    minute = (now.minute // interval_minutes + 1) * interval_minutes
    # Переход на следующий час/день при необходимости
    add_hours = 0
    add_days = 0
    if minute >= 60:
        minute = 0
        add_hours = 1
        if now.hour + add_hours >= 24:
            add_hours = 0
            add_days = 1
    close_dt = now.replace(minute=minute, second=0, microsecond=0)
    close_dt = close_dt + timedelta(hours=add_hours, days=add_days)
    return close_dt


__all__ = [
    "now_msk",
    "is_trading_time",
    "seconds_until_session_end",
    "next_candle_close_ts",
]