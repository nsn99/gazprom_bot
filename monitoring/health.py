"""
Модуль мониторинга здоровья системы для gazprom_bot.

Обеспечивает:
- Проверку состояния подключений (MOEX API, база данных)
- Мониторинг системных ресурсов (CPU, память, сеть)
- Отслеживание бизнес-метрик (количество сигналов, исполненных сделок)
- Сбор метрик производительности (latency запросов, rate limits)

Использует Prometheus-совместимый формат для метрик.
"""

from __future__ import annotations

import time
import psutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

from gazprom_bot.config import Config
from gazprom_bot.utils.time_utils import now_msk


@dataclass
class HealthStatus:
    """Статус здоровья компонента системы."""
    component: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    last_check: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None


@dataclass
class SystemMetrics:
    """Системные метрики."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_connections: int
    timestamp: datetime


@dataclass
class BusinessMetrics:
    """Бизнес-метрики торгового бота."""
    signals_generated: int = 0
    trades_executed: int = 0
    api_requests_total: int = 0
    api_errors_total: int = 0
    last_signal_time: Optional[datetime] = None
    last_trade_time: Optional[datetime] = None
    pnl_total: float = 0.0
    win_rate: float = 0.0


class HealthChecker:
    """
    Компонент для проверки здоровья системы.

    Основные проверки:
    - MOEX API доступность
    - Системные ресурсы
    - База данных (если используется)
    - Rate limits
    """

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.last_checks: Dict[str, HealthStatus] = {}
        self.business_metrics = BusinessMetrics()
        self._check_interval = 30  # секунд

    def check_all(self) -> Dict[str, HealthStatus]:
        """Выполнить все проверки здоровья."""
        checks = {
            'moex_api': self._check_moex_api,
            'system_resources': self._check_system_resources,
            'rate_limits': self._check_rate_limits,
        }

        results = {}
        for name, check_func in checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                results[name] = HealthStatus(
                    component=name,
                    status='unhealthy',
                    last_check=now_msk(),
                    details={},
                    error_message=str(e)
                )

        self.last_checks.update(results)
        return results

    def _check_moex_api(self) -> HealthStatus:
        """Проверка доступности MOEX API."""
        if not requests:
            return HealthStatus(
                component='moex_api',
                status='degraded',
                last_check=now_msk(),
                details={'error': 'requests library not available'},
                error_message='Missing requests dependency'
            )

        start_time = time.time()
        try:
            # Проверяем доступность основного эндпоинта
            url = "https://iss.moex.com/iss/engines/stock/markets/shares.json"
            response = requests.get(url, timeout=5)
            latency = time.time() - start_time

            if response.status_code == 200:
                status = 'healthy'
                details = {
                    'latency_ms': round(latency * 1000, 2),
                    'status_code': response.status_code
                }
            else:
                status = 'unhealthy'
                details = {
                    'status_code': response.status_code,
                    'latency_ms': round(latency * 1000, 2)
                }
        except Exception as e:
            status = 'unhealthy'
            details = {'error': str(e)}
            latency = time.time() - start_time
            details['latency_ms'] = round(latency * 1000, 2)

        return HealthStatus(
            component='moex_api',
            status=status,
            last_check=now_msk(),
            details=details
        )

    def _check_system_resources(self) -> HealthStatus:
        """Проверка системных ресурсов."""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            net_connections = len(psutil.net_connections())

            # Определяем статус на основе порогов
            if cpu > 90 or memory > 90 or disk > 95:
                status = 'unhealthy'
            elif cpu > 70 or memory > 80 or disk > 85:
                status = 'degraded'
            else:
                status = 'healthy'

            details = {
                'cpu_percent': cpu,
                'memory_percent': memory,
                'disk_percent': disk,
                'network_connections': net_connections
            }
        except Exception as e:
            status = 'unhealthy'
            details = {'error': str(e)}

        return HealthStatus(
            component='system_resources',
            status=status,
            last_check=now_msk(),
            details=details
        )

    def _check_rate_limits(self) -> HealthStatus:
        """Проверка соблюдения rate limits."""
        # В будущем можно интегрировать с MoexClient для отслеживания
        # количества запросов и задержек
        return HealthStatus(
            component='rate_limits',
            status='healthy',  # Пока считаем здоровым
            last_check=now_msk(),
            details={'note': 'Rate limit tracking not fully implemented'}
        )

    def get_system_metrics(self) -> SystemMetrics:
        """Получить текущие системные метрики."""
        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=psutil.virtual_memory().percent,
            disk_usage_percent=psutil.disk_usage('/').percent,
            network_connections=len(psutil.net_connections()),
            timestamp=now_msk()
        )

    def update_business_metrics(self, **kwargs):
        """Обновить бизнес-метрики."""
        for key, value in kwargs.items():
            if hasattr(self.business_metrics, key):
                setattr(self.business_metrics, key, value)

    def get_prometheus_metrics(self) -> str:
        """Экспорт метрик в формате Prometheus."""
        lines = []

        # Системные метрики
        sys_metrics = self.get_system_metrics()
        lines.extend([
            f'# HELP gazprom_bot_cpu_percent CPU usage percentage',
            f'# TYPE gazprom_bot_cpu_percent gauge',
            f'gazprom_bot_cpu_percent {sys_metrics.cpu_percent}',
            f'# HELP gazprom_bot_memory_percent Memory usage percentage',
            f'# TYPE gazprom_bot_memory_percent gauge',
            f'gazprom_bot_memory_percent {sys_metrics.memory_percent}',
            f'# HELP gazprom_bot_signals_generated_total Total signals generated',
            f'# TYPE gazprom_bot_signals_generated_total counter',
            f'gazprom_bot_signals_generated_total {self.business_metrics.signals_generated}',
            f'# HELP gazprom_bot_trades_executed_total Total trades executed',
            f'# TYPE gazprom_bot_trades_executed_total counter',
            f'gazprom_bot_trades_executed_total {self.business_metrics.trades_executed}',
        ])

        return '\n'.join(lines)


__all__ = ['HealthChecker', 'HealthStatus', 'SystemMetrics', 'BusinessMetrics']