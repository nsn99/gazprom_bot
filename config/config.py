# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Configuration Module

Модуль для управления конфигурацией приложения с использованием Pydantic.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Основные настройки приложения"""
    
    # Окружение
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Telegram Bot API
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_admin_user_ids: str = Field(default="", env="TELEGRAM_ADMIN_USER_IDS")
    
    # База данных
    database_url: str = Field(default="sqlite+aiosqlite:///gazprom_bot.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # AgentRouter (GPT-5)
    agentrouter_api_key: str = Field(..., env="AGENTROUTER_API_KEY")
    agentrouter_base_url: str = Field(default="https://agentrouter.org/v1", env="AGENTROUTER_BASE_URL")
    agentrouter_model: str = Field(default="deepseek-v3.2", env="AGENTROUTER_MODEL")
    
    # MOEX API
    moex_base_url: str = Field(default="https://iss.moex.com/iss", env="MOEX_BASE_URL")
    moex_board: str = Field(default="TQBR", env="MOEX_BOARD")
    
    # Риск-менеджмент
    risk_max_position_rub: float = Field(default=30000.0, env="RISK_MAX_POSITION_RUB")
    risk_max_portfolio_risk: float = Field(default=0.02, env="RISK_MAX_PORTFOLIO_RISK")
    risk_stop_loss_pct: float = Field(default=0.05, env="RISK_STOP_LOSS_PCT")
    risk_take_profit_pct: float = Field(default=0.10, env="RISK_TAKE_PROFIT_PCT")
    
    # Исполнение сделок
    execution_commission_pct_per_side: float = Field(default=0.0003, env="EXECUTION_COMMISSION_PCT_PER_SIDE")
    
    # Данные
    data_candle_interval_min: int = Field(default=1, env="DATA_CANDLE_INTERVAL_MIN")
    data_history_days: int = Field(default=30, env="DATA_HISTORY_DAYS")
    
    # Логирование
    logging_level: str = Field(default="INFO", env="LOGGING_LEVEL")
    logging_console_output: bool = Field(default=True, env="LOGGING_CONSOLE_OUTPUT")
    
    # Мониторинг
    monitoring_enabled: bool = Field(default=True, env="MONITORING_ENABLED")
    monitoring_slow_operation_threshold: float = Field(default=5.0, env="MONITORING_SLOW_OPERATION_THRESHOLD")
    
    # Визуализация
    visualization_chart_width: int = Field(default=1200, env="VISUALIZATION_CHART_WIDTH")
    visualization_chart_height: int = Field(default=800, env="VISUALIZATION_CHART_HEIGHT")
    
    # Дополнительные настройки из constants
    DEFAULT_INITIAL_CAPITAL: float = Field(default=100000.0)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Получить экземпляр настроек"""
    settings_obj = Settings()
    
    # Конвертируем строку с ID админов в список чисел
    if settings_obj.telegram_admin_user_ids:
        try:
            settings_obj.telegram_admin_user_ids = [
                int(id_str.strip()) for id_str in settings_obj.telegram_admin_user_ids.split(',')
                if id_str.strip().isdigit()
            ]
        except ValueError:
            settings_obj.telegram_admin_user_ids = []
    else:
        settings_obj.telegram_admin_user_ids = []
    
    return settings_obj


def validate_config(settings_obj: Settings) -> bool:
    """Валидация конфигурации"""
    errors = []
    
    # Проверка обязательных полей
    if not settings_obj.telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN обязателен")
    
    if not settings_obj.agentrouter_api_key:
        errors.append("AGENTROUTER_API_KEY обязателен")
    
    # Проверка формата токена Telegram
    if settings_obj.telegram_bot_token and not settings_obj.telegram_bot_token.startswith(":"):
        errors.append("Неверный формат TELEGRAM_BOT_TOKEN")
    
    # Проверка формата API ключа AgentRouter
    if settings_obj.agentrouter_api_key and not settings_obj.agentrouter_api_key.startswith("sk-"):
        errors.append("Неверный формат AGENTROUTER_API_KEY")
    
    # Проверка числовых значений
    if settings_obj.risk_max_position_rub <= 0:
        errors.append("RISK_MAX_POSITION_RUB должен быть положительным")
    
    if not 0 <= settings_obj.risk_max_portfolio_risk <= 1:
        errors.append("RISK_MAX_PORTFOLIO_RISK должен быть в диапазоне [0, 1]")
    
    if not 0 <= settings_obj.risk_stop_loss_pct <= 1:
        errors.append("RISK_STOP_LOSS_PCT должен быть в диапазоне [0, 1]")
    
    if not 0 <= settings_obj.risk_take_profit_pct <= 1:
        errors.append("RISK_TAKE_PROFIT_PCT должен быть в диапазоне [0, 1]")
    
    if errors:
        print("❌ Ошибки в конфигурации:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def print_config_summary(settings_obj: Settings):
    """Вывести сводку конфигурации"""
    print("📋 Сводка конфигурации:")
    print(f"  🌍 Окружение: {settings_obj.environment}")
    print(f"  🤖 Telegram Bot: {'✅ Настроен' if settings_obj.telegram_bot_token else '❌ Не настроен'}")
    print(f"  🧠 AgentRouter: {'✅ Настроен' if settings_obj.agentrouter_api_key else '❌ Не настроен'}")
    print(f"  💾 База данных: {settings_obj.database_url}")
    print(f"  📊 MOEX API: {settings_obj.moex_base_url}")
    print(f"  ⚠️ Макс. риск портфеля: {settings_obj.risk_max_portfolio_risk * 100:.1f}%")
    print(f"  🛑 Стоп-лосс: {settings_obj.risk_stop_loss_pct * 100:.1f}%")
    print(f"  🎯 Тейк-профит: {settings_obj.risk_take_profit_pct * 100:.1f}%")


# Глобальный экземпляр настроек
settings = get_settings()