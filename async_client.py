"""
Асинхронный клиент для MOEX ISS API.

Обеспечивает:
- Асинхронные HTTP-запросы с aiohttp
- Управление соединениями и пулами
- Circuit breaker для отказоустойчивости
- Метрики производительности
- Graceful shutdown

Заменяет синхронный MoexClient для продакшен использования.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

try:
    import aiohttp
    import aiohttp.web
except ImportError:
    aiohttp = None

import pandas as pd
import numpy as np

from gazprom_bot.config import Config
from gazprom_bot.utils.time_utils import now_msk


@dataclass
class CircuitBreakerState:
    """Состояние circuit breaker."""
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open


class AsyncMoexClientError(Exception):
    """Ошибка асинхронного клиента MOEX."""
    pass


class AsyncMoexClient:
    """
    Асинхронный клиент для MOEX ISS API.

    Особенности:
    - Асинхронные запросы с aiohttp
    - Circuit breaker для отказоустойчивости
    - Метрики latency и ошибок
    - Graceful shutdown
    """

    BASE_URL = "https://iss.moex.com/iss"
    ENGINE = "stock"
    MARKET = "shares"

    def __init__(
        self,
        board: str = "TQBR",
        rate_limit_per_sec: float = 1.0,
        timeout_sec: float = 10.0,
        retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_sec: int = 60,
        config: Optional[Config] = None
    ):
        if not aiohttp:
            raise ImportError("aiohttp is required for AsyncMoexClient")

        self.board = board
        self.rate_limit_interval = 1.0 / max(0.1, rate_limit_per_sec)
        self.timeout_sec = timeout_sec
        self.retries = retries
        self.config = config

        # Circuit breaker
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = timedelta(seconds=circuit_breaker_timeout_sec)
        self.circuit_breaker = CircuitBreakerState()

        # Метрики
        self.metrics = {
            'requests_total': 0,
            'errors_total': 0,
            'latency_sum': 0.0,
            'last_request_ts': None
        }

        # HTTP клиент
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None

        # Rate limiting
        self._last_request_ts = 0.0
        self._rate_limit_lock = asyncio.Lock()

        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Инициализация HTTP клиента."""
        if self._session:
            return

        self._connector = aiohttp.TCPConnector(
            limit=10,  # Максимум 10 одновременных соединений
            limit_per_host=5,  # Максимум 5 соединений на хост
            ttl_dns_cache=300,  # Кэш DNS 5 минут
            use_dns_cache=True,
            keepalive_timeout=60,
            enable_cleanup_closed=True,
        )

        timeout = aiohttp.ClientTimeout(total=self.timeout_sec)
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={
                "User-Agent": "gazprom_bot/0.1 (+async; MOEX ISS demo client)",
                "Accept": "application/json",
            }
        )

        self.logger.info("AsyncMoexClient started")

    async def close(self):
        """Закрытие HTTP клиента."""
        if self._session:
            await self._session.close()
            self._session = None

        if self._connector:
            await self._connector.close()
            self._connector = None

        self.logger.info("AsyncMoexClient closed")

    async def _wait_rate_limit(self):
        """Ожидание rate limit."""
        async with self._rate_limit_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_ts
            remain = self.rate_limit_interval - elapsed

            if remain > 0:
                await asyncio.sleep(remain)

            self._last_request_ts = asyncio.get_event_loop().time()

    async def _check_circuit_breaker(self) -> bool:
        """Проверка circuit breaker. Возвращает True если запрос разрешен."""
        now = now_msk()

        if self.circuit_breaker.state == "open":
            # Проверяем timeout для перехода в half-open
            if (now - (self.circuit_breaker.last_failure_time or now)) > self.circuit_breaker_timeout:
                self.circuit_breaker.state = "half_open"
                self.logger.info("Circuit breaker: open -> half_open")
                return True
            else:
                return False

        elif self.circuit_breaker.state == "half_open":
            # В half-open состоянии разрешаем один запрос
            return True

        return True  # closed

    def _record_success(self):
        """Запись успешного запроса."""
        if self.circuit_breaker.state == "half_open":
            self.circuit_breaker.state = "closed"
            self.circuit_breaker.failures = 0
            self.logger.info("Circuit breaker: half_open -> closed")

    def _record_failure(self):
        """Запись неудачного запроса."""
        self.circuit_breaker.failures += 1
        self.circuit_breaker.last_failure_time = now_msk()

        if self.circuit_breaker.failures >= self.circuit_breaker_threshold:
            self.circuit_breaker.state = "open"
            self.logger.warning(f"Circuit breaker: closed -> open (failures: {self.circuit_breaker.failures})")

    async def _request_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Выполнить асинхронный GET запрос к ISS.

        Включает:
        - Rate limiting
        - Circuit breaker
        - Retry с экспоненциальной задержкой
        - Метрики
        """
        if not self._session:
            raise AsyncMoexClientError("Client not started. Call start() first.")

        # Проверка circuit breaker
        if not await self._check_circuit_breaker():
            raise AsyncMoexClientError("Circuit breaker is open")

        # Rate limiting
        await self._wait_rate_limit()

        params = params or {}
        attempt = 0
        last_exc = None

        while attempt <= self.retries:
            try:
                start_time = asyncio.get_event_loop().time()

                async with self._session.get(url, params=params) as response:
                    latency = asyncio.get_event_loop().time() - start_time

                    # Обновление метрик
                    self.metrics['requests_total'] += 1
                    self.metrics['latency_sum'] += latency
                    self.metrics['last_request_ts'] = now_msk()

                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.warning(
                            f"MOEX HTTP {response.status} for {url} params={params}; body={error_text[:300]}"
                        )
                        self._record_failure()
                        raise AsyncMoexClientError(f"HTTP {response.status}: {error_text[:200]}")

                    # Проверка Content-Type
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(
                            f"Unexpected Content-Type {content_type} for {url} params={params}; body={error_text[:300]}"
                        )
                        self._record_failure()
                        raise AsyncMoexClientError(f"Unexpected Content-Type: {content_type}")

                    # Парсинг JSON
                    try:
                        data = await response.json()
                        self._record_success()
                        return data
                    except Exception as jexc:
                        error_text = await response.text()
                        self.logger.error(
                            f"JSON decode failed for {url} params={params}; body={error_text[:300]}; err={jexc}"
                        )
                        self._record_failure()
                        raise AsyncMoexClientError(f"JSON decode error: {jexc}")

            except asyncio.TimeoutError:
                last_exc = AsyncMoexClientError("Request timeout")
            except aiohttp.ClientError as e:
                last_exc = AsyncMoexClientError(f"HTTP client error: {e}")
            except Exception as e:
                last_exc = AsyncMoexClientError(f"Unexpected error: {e}")

            # Метрики ошибок
            self.metrics['errors_total'] += 1

            # Экспоненциальная задержка
            if attempt < self.retries:
                delay = 0.5 * (2 ** attempt)
                await asyncio.sleep(delay)
            attempt += 1

        # Все попытки исчерпаны
        self._record_failure()
        raise last_exc or AsyncMoexClientError("All retry attempts failed")

    @staticmethod
    def _table_to_df(payload: Dict[str, Any], table_name: str) -> pd.DataFrame:
        """Преобразование таблицы ISS в DataFrame."""
        if table_name not in payload:
            return pd.DataFrame()

        tbl = payload[table_name]
        cols = tbl.get("columns", [])
        data = tbl.get("data", [])
        return pd.DataFrame(data=data, columns=cols)

    async def get_historical_candles(
        self,
        ticker: str,
        from_date: str,
        interval: int = 5,
    ) -> pd.DataFrame:
        """
        Получить исторические свечи асинхронно.

        Args:
            ticker: Тикер инструмента
            from_date: Дата начала в формате YYYY-MM-DD
            interval: Интервал свечи в минутах

        Returns:
            DataFrame со свечами
        """
        url = f"{self.BASE_URL}/engines/{self.ENGINE}/markets/{self.MARKET}/boards/{self.board}/securities/{ticker}/candles.json"

        params = {
            "interval": interval,
            "from": from_date,
            "iss.meta": "off",
        }

        payload = await self._request_json(url, params=params)
        df = self._table_to_df(payload, "candles")

        if df.empty:
            return df

        # Преобразование типов
        for col in ("open", "high", "low", "close", "volume", "value"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in ("begin", "end"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Установка индекса
        if "end" in df.columns:
            df = df.sort_values("end").reset_index(drop=True)
            df = df.set_index("end")

        return df

    async def get_marketdata_l1(self, ticker: str) -> Dict[str, Any]:
        """
        Получить рыночные данные уровня 1 асинхронно.

        Args:
            ticker: Тикер инструмента

        Returns:
            Словарь с данными L1
        """
        url = f"{self.BASE_URL}/engines/{self.ENGINE}/markets/{self.MARKET}/boards/{self.board}/securities/{ticker}.json"

        params = {"iss.only": "marketdata", "iss.meta": "off"}
        payload = await self._request_json(url, params=params)
        df = self._table_to_df(payload, "marketdata")

        if df.empty:
            return {}

        # Преобразование в словарь (первая строка)
        result = {}
        for col in df.columns:
            value = df[col].iloc[0] if len(df) > 0 else None
            if pd.notna(value):
                result[col] = value

        return result

    async def get_security_info(self, ticker: str) -> Dict[str, Any]:
        """
        Получить информацию об инструменте асинхронно.

        Args:
            ticker: Тикер инструмента

        Returns:
            Словарь с информацией об инструменте
        """
        url = f"{self.BASE_URL}/engines/{self.ENGINE}/markets/{self.MARKET}/boards/{self.board}/securities/{ticker}.json"

        params = {"iss.only": "securities", "iss.meta": "off"}
        payload = await self._request_json(url, params=params)
        df = self._table_to_df(payload, "securities")

        if df.empty:
            return {}

        # Поиск по SECID
        if "SECID" in df.columns:
            row = df[df["SECID"] == ticker]
            if not row.empty:
                return row.iloc[0].to_dict()

        # Фолбэк на первую строку
        return df.iloc[0].to_dict()

    def get_metrics(self) -> Dict[str, Any]:
        """Получить метрики клиента."""
        metrics = self.metrics.copy()
        if metrics['requests_total'] > 0:
            metrics['avg_latency'] = metrics['latency_sum'] / metrics['requests_total']
            metrics['error_rate'] = metrics['errors_total'] / metrics['requests_total']
        else:
            metrics['avg_latency'] = 0.0
            metrics['error_rate'] = 0.0

        metrics['circuit_breaker_state'] = self.circuit_breaker.state
        metrics['circuit_breaker_failures'] = self.circuit_breaker.failures

        return metrics


__all__ = ['AsyncMoexClient', 'AsyncMoexClientError']