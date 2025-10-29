"""
Система логирования и мониторинга для Telegram Trading Bot.

Предоставляет:
- Структурированное логирование всех операций
- Мониторинг производительности системы
- Отслеживание ошибок и исключений
- Метрики использования API и ресурсов
- Алерты для критических событий
"""

from __future__ import annotations

import logging
import logging.handlers
import json
import time
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import defaultdict, deque

from config import settings


@dataclass
class LogEntry:
    """Структура записи лога"""
    timestamp: datetime
    level: str
    module: str
    function: str
    message: str
    user_id: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    error_trace: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    timestamp: datetime
    module: str
    operation: str
    execution_time: float
    success: bool
    error_type: Optional[str] = None
    user_id: Optional[int] = None


@dataclass
class ApiUsageMetrics:
    """Метрики использования API"""
    timestamp: datetime
    api_name: str
    endpoint: str
    request_count: int
    response_time: float
    success: bool
    error_code: Optional[str] = None
    tokens_used: Optional[int] = None


class MonitoringLogger:
    """Расширенный логгер с мониторингом"""
    
    def __init__(self, log_dir: str = "logs"):
        self.config = settings
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Настройка основных логгеров
        self.setup_loggers()
        
        # Метрики производительности
        self.performance_metrics: deque = deque(maxlen=1000)
        self.api_usage_metrics: deque = deque(maxlen=1000)
        
        # Счетчики событий
        self.event_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        
        # Время последней очистки
        self.last_cleanup = datetime.now()
        
        # Блокировка для потокобезопасности
        self.lock = threading.Lock()
        
        # Запуск фоновой очистки
        self.start_background_cleanup()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("MonitoringLogger initialized")
    
    def setup_loggers(self):
        """Настройка логгеров"""
        # Форматеры
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        json_formatter = JsonFormatter()
        
        # Основной логгер
        main_logger = logging.getLogger('gazprom_bot')
        main_logger.setLevel(getattr(logging, self.config.logging_level))
        
        # Файловый обработчик (детальный)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'gazprom_bot.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(detailed_formatter)
        main_logger.addHandler(file_handler)
        
        # JSON обработчик (для анализа)
        json_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'gazprom_bot.json',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        json_handler.setFormatter(json_formatter)
        main_logger.addHandler(json_handler)
        
        # Консольный обработчик
        if getattr(self.config, 'logging_console_output', False):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            main_logger.addHandler(console_handler)
        
        # Отдельные логгеры для компонентов
        self.setup_component_loggers()
        
        # Логгер ошибок
        self.setup_error_logger()
        
        # Логгер производительности
        self.setup_performance_logger()
        
        # Логгер API
        self.setup_api_logger()
    
    def setup_component_loggers(self):
        """Настройка логгеров для компонентов"""
        components = [
            'database', 'portfolio', 'telegram', 'ai', 'integration', 
            'visualization', 'data', 'strategy', 'execution', 'risk'
        ]
        
        for component in components:
            logger = logging.getLogger(f'gazprom_bot.{component}')
            logger.setLevel(getattr(logging, self.config.logging_level))
            
            # Файловый обработчик для компонента
            handler = logging.handlers.RotatingFileHandler(
                self.log_dir / f'{component}.log',
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3
            )
            
            formatter = logging.Formatter(
                f'%(asctime)s - {component.upper()} - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    def setup_error_logger(self):
        """Настройка логгера ошибок"""
        error_logger = logging.getLogger('gazprom_bot.errors')
        error_logger.setLevel(getattr(logging, self.config.logging_level.upper()))
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.log',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=10
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - ERROR - %(name)s - %(funcName)s:%(lineno)d - %(message)s\n'
            '%(exc_text)s'
        )
        handler.setFormatter(formatter)
        error_logger.addHandler(handler)
    
    def setup_performance_logger(self):
        """Настройка логгера производительности"""
        perf_logger = logging.getLogger('gazprom_bot.performance')
        perf_logger.setLevel(getattr(logging, self.config.logging_level))
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'performance.log',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - PERF - %(message)s'
        )
        handler.setFormatter(formatter)
        perf_logger.addHandler(handler)
    
    def setup_api_logger(self):
        """Настройка логгера API"""
        api_logger = logging.getLogger('gazprom_bot.api')
        api_logger.setLevel(getattr(logging, self.config.logging_level))
        
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'api.log',
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - API - %(message)s'
        )
        handler.setFormatter(formatter)
        api_logger.addHandler(handler)
    
    def log_operation(self, level: str, module: str, function: str, message: str,
                     user_id: Optional[int] = None, 
                     extra_data: Optional[Dict[str, Any]] = None,
                     execution_time: Optional[float] = None,
                     error_trace: Optional[str] = None):
        """Логирование операции"""
        try:
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                module=module,
                function=function,
                message=message,
                user_id=user_id,
                extra_data=extra_data,
                execution_time=execution_time,
                error_trace=error_trace
            )
            
            # Запись в лог
            logger = logging.getLogger(f'gazprom_bot.{module}')
            log_level = getattr(logging, level.upper())
            
            # Форматирование сообщения
            log_message = f"{message}"
            if user_id:
                log_message += f" [user_id: {user_id}]"
            if execution_time:
                log_message += f" [time: {execution_time:.3f}s]"
            
            # Дополнительные данные
            extra = {}
            if extra_data:
                extra['extra_data'] = extra_data
            
            logger.log(log_level, log_message, extra=extra)
            
            # Обновление счетчиков
            with self.lock:
                self.event_counters[f"{module}.{function}"] += 1
                if level.upper() == 'ERROR':
                    self.error_counters[f"{module}.{function}"] += 1
            
        except Exception as e:
            # Fallback логирование
            print(f"Error in log_operation: {e}")
    
    def log_performance(self, module: str, operation: str, execution_time: float,
                       success: bool = True, error_type: Optional[str] = None,
                       user_id: Optional[int] = None):
        """Логирование производительности"""
        try:
            metric = PerformanceMetrics(
                timestamp=datetime.now(),
                module=module,
                operation=operation,
                execution_time=execution_time,
                success=success,
                error_type=error_type,
                user_id=user_id
            )
            
            with self.lock:
                self.performance_metrics.append(metric)
            
            # Запись в лог производительности
            perf_logger = logging.getLogger('gazprom_bot.performance')
            status = "SUCCESS" if success else "ERROR"
            perf_message = f"{module}.{operation}: {execution_time:.3f}s - {status}"
            
            if user_id:
                perf_message += f" [user_id: {user_id}]"
            if error_type:
                perf_message += f" [error: {error_type}]"
            
            perf_logger.info(perf_message)
            
            # Алерт при медленной операции
            if execution_time > getattr(self.config, 'monitoring_slow_operation_threshold', 5.0):
                self.log_operation(
                    'WARNING', 'monitoring', 'log_performance',
                    f"Slow operation detected: {module}.{operation} took {execution_time:.3f}s",
                    user_id=user_id
                )
            
        except Exception as e:
            print(f"Error in log_performance: {e}")
    
    def log_api_usage(self, api_name: str, endpoint: str, request_count: int = 1,
                     response_time: float = 0, success: bool = True,
                     error_code: Optional[str] = None, tokens_used: Optional[int] = None,
                     user_id: Optional[int] = None):
        """Логирование использования API"""
        try:
            metric = ApiUsageMetrics(
                timestamp=datetime.now(),
                api_name=api_name,
                endpoint=endpoint,
                request_count=request_count,
                response_time=response_time,
                success=success,
                error_code=error_code,
                tokens_used=tokens_used
            )
            
            with self.lock:
                self.api_usage_metrics.append(metric)
            
            # Запись в лог API
            api_logger = logging.getLogger('gazprom_bot.api')
            status = "SUCCESS" if success else "ERROR"
            api_message = f"{api_name}.{endpoint}: {request_count} requests - {status}"
            
            if response_time > 0:
                api_message += f" [{response_time:.3f}s]"
            if tokens_used:
                api_message += f" [{tokens_used} tokens]"
            if user_id:
                api_message += f" [user_id: {user_id}]"
            if error_code:
                api_message += f" [error: {error_code}]"
            
            api_logger.info(api_message)
            
            # Алерт при большом количестве запросов
            if request_count > getattr(self.config, 'api_request_threshold', 100):
                self.log_operation(
                    'WARNING', 'monitoring', 'log_api_usage',
                    f"High API usage detected: {api_name}.{endpoint} - {request_count} requests",
                    user_id=user_id
                )
            
        except Exception as e:
            print(f"Error in log_api_usage: {e}")
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Получение сводки производительности"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with self.lock:
                recent_metrics = [
                    m for m in self.performance_metrics 
                    if m.timestamp > cutoff_time
                ]
            
            if not recent_metrics:
                return {}
            
            # Агрегация по операциям
            operations = defaultdict(list)
            for metric in recent_metrics:
                key = f"{metric.module}.{metric.operation}"
                operations[key].append(metric)
            
            summary = {}
            for operation, metrics in operations.items():
                execution_times = [m.execution_time for m in metrics]
                success_count = sum(1 for m in metrics if m.success)
                
                summary[operation] = {
                    'count': len(metrics),
                    'avg_time': sum(execution_times) / len(execution_times),
                    'min_time': min(execution_times),
                    'max_time': max(execution_times),
                    'success_rate': success_count / len(metrics),
                    'error_rate': (len(metrics) - success_count) / len(metrics)
                }
            
            return summary
            
        except Exception as e:
            self.log_operation('ERROR', 'monitoring', 'get_performance_summary', str(e))
            return {}
    
    def get_api_usage_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Получение сводки использования API"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with self.lock:
                recent_metrics = [
                    m for m in self.api_usage_metrics 
                    if m.timestamp > cutoff_time
                ]
            
            if not recent_metrics:
                return {}
            
            # Агрегация по API
            apis = defaultdict(list)
            for metric in recent_metrics:
                key = f"{metric.api_name}.{metric.endpoint}"
                apis[key].append(metric)
            
            summary = {}
            for api, metrics in apis.items():
                total_requests = sum(m.request_count for m in metrics)
                total_tokens = sum(m.tokens_used or 0 for m in metrics)
                success_requests = sum(m.request_count for m in metrics if m.success)
                
                response_times = [m.response_time for m in metrics if m.response_time > 0]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                summary[api] = {
                    'total_requests': total_requests,
                    'success_requests': success_requests,
                    'success_rate': success_requests / total_requests,
                    'total_tokens': total_tokens,
                    'avg_response_time': avg_response_time
                }
            
            return summary
            
        except Exception as e:
            self.log_operation('ERROR', 'monitoring', 'get_api_usage_summary', str(e))
            return {}
    
    def get_error_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Получение сводки ошибок"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with self.lock:
                recent_errors = [
                    m for m in self.performance_metrics 
                    if m.timestamp > cutoff_time and not m.success
                ]
            
            if not recent_errors:
                return {}
            
            # Агрегация по типам ошибок
            error_types = defaultdict(int)
            error_modules = defaultdict(int)
            
            for metric in recent_errors:
                if metric.error_type:
                    error_types[metric.error_type] += 1
                error_modules[metric.module] += 1
            
            return {
                'total_errors': len(recent_errors),
                'error_types': dict(error_types),
                'error_modules': dict(error_modules),
                'error_rate': len(recent_errors) / max(len(self.performance_metrics), 1)
            }
            
        except Exception as e:
            self.log_operation('ERROR', 'monitoring', 'get_error_summary', str(e))
            return {}
    
    def start_background_cleanup(self):
        """Запуск фоновой очистки старых метрик"""
        def cleanup():
            while True:
                try:
                    time.sleep(300)  # 5 минут
                    
                    # Очистка старых метрик
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    
                    with self.lock:
                        # Очистка производительности
                        self.performance_metrics = deque(
                            [m for m in self.performance_metrics if m.timestamp > cutoff_time],
                            maxlen=1000
                        )
                        
                        # Очистка API
                        self.api_usage_metrics = deque(
                            [m for m in self.api_usage_metrics if m.timestamp > cutoff_time],
                            maxlen=1000
                        )
                    
                    self.last_cleanup = datetime.now()
                    
                except Exception as e:
                    print(f"Error in background cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def export_logs(self, start_date: datetime, end_date: datetime,
                   output_file: str) -> bool:
        """Экспорт логов за период"""
        try:
            # TODO: Реализовать экспорт логов в файл
            # Чтение лог-файлов и фильтрация по дате
            # Экспорт в CSV или JSON формат
            
            self.log_operation('INFO', 'monitoring', 'export_logs',
                             f"Exported logs from {start_date} to {end_date} to {output_file}")
            return True
            
        except Exception as e:
            self.log_operation('ERROR', 'monitoring', 'export_logs', str(e))
            return False


class JsonFormatter(logging.Formatter):
    """JSON форматтер для структурированного логирования"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage()
        }
        
        # Добавление дополнительных полей
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'extra_data'):
            log_entry['extra_data'] = record.extra_data
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        
        # Добавление информации об исключении
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


# Декораторы для автоматического логирования
def log_execution_time(module: str, operation: str):
    """Декоратор для логирования времени выполнения"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                execution_time = time.time() - start_time
                
                # Получение monitoring logger
                monitoring_logger = get_monitoring_logger()
                monitoring_logger.log_performance(
                    module=module,
                    operation=operation,
                    execution_time=execution_time,
                    success=success,
                    error_type=error_type
                )
        
        return wrapper
    return decorator


def log_api_call(api_name: str, endpoint: str):
    """Декоратор для логирования вызовов API"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_code = None
            tokens_used = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Извлечение метрик из результата
                if hasattr(result, 'get'):
                    tokens_used = result.get('tokens_used')
                
                return result
            except Exception as e:
                success = False
                error_code = getattr(e, 'code', None)
                raise
            finally:
                response_time = time.time() - start_time
                
                # Получение monitoring logger
                monitoring_logger = get_monitoring_logger()
                monitoring_logger.log_api_usage(
                    api_name=api_name,
                    endpoint=endpoint,
                    response_time=response_time,
                    success=success,
                    error_code=error_code,
                    tokens_used=tokens_used
                )
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_code = None
            tokens_used = None
            
            try:
                result = func(*args, **kwargs)
                
                # Извлечение метрик из результата
                if hasattr(result, 'get'):
                    tokens_used = result.get('tokens_used')
                
                return result
            except Exception as e:
                success = False
                error_code = getattr(e, 'code', None)
                raise
            finally:
                response_time = time.time() - start_time
                
                # Получение monitoring logger
                monitoring_logger = get_monitoring_logger()
                monitoring_logger.log_api_usage(
                    api_name=api_name,
                    endpoint=endpoint,
                    response_time=response_time,
                    success=success,
                    error_code=error_code,
                    tokens_used=tokens_used
                )
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Глобальный экземпляр мониторинга
monitoring_logger = None


def get_logger(name: str) -> logging.Logger:
    """Получение логгера"""
    return logging.getLogger(name)

def setup_logging():
    """Настройка логирования"""
    global monitoring_logger
    if monitoring_logger is None:
        monitoring_logger = MonitoringLogger()
    return monitoring_logger

def get_monitoring_logger() -> MonitoringLogger:
    """Получение глобального экземпляра мониторинга"""
    global monitoring_logger
    if monitoring_logger is None:
        monitoring_logger = MonitoringLogger()
    return monitoring_logger


# Удобные функции для логирования
def log_operation(level: str, module: str, function: str, message: str,
                 user_id: Optional[int] = None, 
                 extra_data: Optional[Dict[str, Any]] = None):
    """Логирование операции"""
    logger = get_monitoring_logger()
    logger.log_operation(level, module, function, message, user_id, extra_data)


def log_performance(module: str, operation: str, execution_time: float,
                   success: bool = True, error_type: Optional[str] = None,
                   user_id: Optional[int] = None):
    """Логирование производительности"""
    logger = get_monitoring_logger()
    logger.log_performance(module, operation, execution_time, success, error_type, user_id)


def log_api_usage(api_name: str, endpoint: str, request_count: int = 1,
                 response_time: float = 0, success: bool = True,
                 error_code: Optional[str] = None, tokens_used: Optional[int] = None,
                 user_id: Optional[int] = None):
    """Логирование использования API"""
    logger = get_monitoring_logger()
    logger.log_api_usage(api_name, endpoint, request_count, response_time, 
                        success, error_code, tokens_used, user_id)