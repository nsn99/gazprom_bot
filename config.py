"""
Конфигурация Gazprom Trading Bot
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Settings(BaseModel):
    """Настройки приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(default="your_telegram_bot_token_here")
    
    # AgentRouter
    AGENTROUTER_API_KEY: str = Field(default="sk-your_agentrouter_api_key_here")
    AGENTROUTER_BASE_URL: str = Field(default="https://agentrouter.org/v1")
    AGENTROUTER_MODEL: str = Field(default="gpt-5")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///gazprom_bot.db")
    
    # MOEX API
    MOEX_BASE_URL: str = Field(default="https://iss.moex.com/iss")
    
    # Trading Settings
    DEFAULT_INITIAL_CAPITAL: float = Field(default=100000.0)
    MAX_POSITION_SIZE_PERCENT: float = Field(default=30.0)
    STOP_LOSS_PERCENT: float = Field(default=5.0)
    TAKE_PROFIT_PERCENT: float = Field(default=10.0)
    COMMISSION_PERCENT: float = Field(default=0.03)
    
    # Performance
    SLOW_OPERATION_THRESHOLD: float = Field(default=5.0)
    API_REQUEST_THRESHOLD: int = Field(default=100)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Technical Indicators
    RSI_PERIOD: int = Field(default=14)
    MACD_FAST: int = Field(default=12)
    MACD_SLOW: int = Field(default=26)
    MACD_SIGNAL: int = Field(default=9)
    
    # Development
    DEBUG: bool = Field(default=False)
    TEST_MODE: bool = Field(default=False)

def get_settings() -> Settings:
    """Получить настройки приложения"""
    return Settings(
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here"),
        AGENTROUTER_API_KEY=os.getenv("AGENTROUTER_API_KEY", "sk-your_agentrouter_api_key_here"),
        AGENTROUTER_BASE_URL=os.getenv("AGENTROUTER_BASE_URL", "https://agentrouter.org/v1"),
        AGENTROUTER_MODEL=os.getenv("AGENTROUTER_MODEL", "gpt-5"),
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///gazprom_bot.db"),
        MOEX_BASE_URL=os.getenv("MOEX_BASE_URL", "https://iss.moex.com/iss"),
        DEFAULT_INITIAL_CAPITAL=float(os.getenv("DEFAULT_INITIAL_CAPITAL", "100000.0")),
        MAX_POSITION_SIZE_PERCENT=float(os.getenv("MAX_POSITION_SIZE_PERCENT", "30.0")),
        STOP_LOSS_PERCENT=float(os.getenv("STOP_LOSS_PERCENT", "5.0")),
        TAKE_PROFIT_PERCENT=float(os.getenv("TAKE_PROFIT_PERCENT", "10.0")),
        COMMISSION_PERCENT=float(os.getenv("COMMISSION_PERCENT", "0.03")),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        TEST_MODE=os.getenv("TEST_MODE", "false").lower() == "true"
    )


def get_moex_config() -> dict:
    """Получить конфигурацию MOEX API"""
    return {
        "base_url": os.getenv("MOEX_BASE_URL", "https://iss.moex.com/iss"),
        "board": os.getenv("MOEX_BOARD", "TQBR"),
        "market": "shares",
        "timeout": 30
    }

# Глобальный экземпляр настроек
settings = get_settings()

def validate_config() -> bool:
    """
    Проверить корректность конфигурации
    
    Returns:
        bool: True если конфигурация валидна
    """
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "AGENTROUTER_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        print("📝 Пожалуйста, создайте файл .env с этими переменными:")
        print("TELEGRAM_BOT_TOKEN=your_telegram_bot_token")
        print("AGENTROUTER_API_KEY=your_agentrouter_api_key")
        return False
    
    # Проверить формат токена Telegram
    if not settings.TELEGRAM_BOT_TOKEN.startswith("") or len(settings.TELEGRAM_BOT_TOKEN) < 10:
        print("❌ Неверный формат Telegram Bot Token")
        return False
    
    # Проверить формат AgentRouter API ключа
    if not settings.AGENTROUTER_API_KEY.startswith("sk-") or len(settings.AGENTROUTER_API_KEY) < 10:
        print("❌ Неверный формат AgentRouter API Key")
        return False
    
    print("✅ Конфигурация проверена успешно")
    return True

def print_config_summary():
    """Вывести краткую информацию о конфигурации"""
    print("\n📋 Конфигурация Gazprom Trading Bot:")
    print(f"🤖 Telegram Bot: {'✅ Настроен' if settings.TELEGRAM_BOT_TOKEN else '❌ Отсутствует'}")
    print(f"🧠 AgentRouter: {'✅ Настроен' if settings.AGENTROUTER_API_KEY else '❌ Отсутствует'}")
    print(f"💾 База данных: {settings.DATABASE_URL}")
    print(f"📊 MOEX API: {settings.MOEX_BASE_URL}")
    print(f"💰 Начальный капитал: {settings.DEFAULT_INITIAL_CAPITAL:,} RUB")
    print(f"🛡️ Макс. позиция: {settings.MAX_POSITION_SIZE_PERCENT}%")
    print(f"📈 Режим отладки: {'✅ Включен' if settings.DEBUG else '❌ Выключен'}")
    print(f"🧪 Тестовый режим: {'✅ Включен' if settings.TEST_MODE else '❌ Выключен'}")
    print()

if __name__ == "__main__":
    # Проверить конфигурацию при прямом запуске
    if validate_config():
        print_config_summary()
    else:
        print("❌ Конфигурация невалидна. Пожалуйста, исправьте ошибки.")