"""
Тесты для модуля конфигурации
"""

import pytest
from unittest.mock import patch
from gazprom_bot.config import Settings, get_settings, constants


class TestSettings:
    """Тесты класса настроек"""
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        with patch.dict('os.environ', {}, clear=True):
            settings = Settings()
            
            assert settings.DATABASE_URL == "sqlite:///./gazprom_bot.db"
            assert settings.DEFAULT_INITIAL_CAPITAL == 100000.0
            assert settings.DEFAULT_RISK_LIMIT == 5.0
            assert settings.MAX_POSITION_SIZE_PERCENT == 30.0
            assert settings.MOEX_BASE_URL == "https://iss.moex.com/iss"
            assert settings.LOG_LEVEL == "INFO"
            assert settings.LOG_FORMAT == "json"
            assert settings.APP_NAME == "Gazprom Trading Bot"
            assert settings.APP_VERSION == "1.0.0"
            assert settings.DEBUG is False
    
    def test_log_level_validation(self):
        """Тест валидации уровня логирования"""
        with patch.dict('os.environ', {'LOG_LEVEL': 'DEBUG'}, clear=True):
            settings = Settings()
            assert settings.LOG_LEVEL == 'DEBUG'
        
        with patch.dict('os.environ', {'LOG_LEVEL': 'INVALID'}, clear=True):
            with pytest.raises(ValueError):
                Settings()
    
    def test_percentage_validation(self):
        """Тест валидации процентных значений"""
        with patch.dict('os.environ', {'DEFAULT_RISK_LIMIT': '50'}, clear=True):
            settings = Settings()
            assert settings.DEFAULT_RISK_LIMIT == 50.0
        
        with patch.dict('os.environ', {'DEFAULT_RISK_LIMIT': '150'}, clear=True):
            with pytest.raises(ValueError):
                Settings()
    
    def test_temperature_validation(self):
        """Тест валидации температуры AI"""
        with patch.dict('os.environ', {'AI_TEMPERATURE': '1.5'}, clear=True):
            settings = Settings()
            assert settings.AI_TEMPERATURE == 1.5
        
        with patch.dict('os.environ', {'AI_TEMPERATURE': '3.0'}, clear=True):
            with pytest.raises(ValueError):
                Settings()


class TestConstants:
    """Тесты констант"""
    
    def test_trading_constants(self):
        """Тест торговых констант"""
        assert constants.GAZP_TICKER == "GAZP"
        assert constants.IMOEX_TICKER == "IMOEX"
        assert constants.MOEX_BOARD == "TQBR"
    
    def test_technical_indicators(self):
        """Тест констант технических индикаторов"""
        assert constants.RSI_PERIOD == 14
        assert constants.MACD_FAST == 12
        assert constants.MACD_SLOW == 26
        assert constants.MACD_SIGNAL == 9
        assert constants.SMA_SHORT == 20
        assert constants.SMA_LONG == 50
        assert constants.SMA_200 == 200
    
    def test_limits(self):
        """Тест ограничений"""
        assert constants.MIN_TRADE_AMOUNT == 1000.0
        assert constants.MAX_DAILY_TRADES == 10


class TestGetSettings:
    """Тесты функции get_settings"""
    
    def test_get_settings_singleton(self):
        """Тест, что get_settings возвращает тот же экземпляр"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2