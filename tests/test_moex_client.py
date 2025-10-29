"""
Тесты для MOEX клиента
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
from gazprom_bot.data.client import MOEXClient


class TestMOEXClient:
    """Тесты клиента MOEX"""
    
    @pytest.fixture
    def client(self):
        """Фикстура для создания клиента"""
        with patch('gazprom_bot.data.client.settings') as mock_settings:
            mock_settings.MOEX_BASE_URL = "https://iss.moex.com/iss"
            mock_settings.MOEX_CACHE_TTL = 60
            mock_settings.REQUEST_TIMEOUT = 30
            
            return MOEXClient()
    
    @pytest.mark.asyncio
    async def test_get_current_price_success(self, client):
        """Тест успешного получения текущей цены"""
        mock_data = {
            "marketdata": {
                "columns": ["SECID", "LAST", "BID", "ASK"],
                "data": [
                    ["GAZP", 160.50, 160.40, 160.60]
                ]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            price = await client.get_current_price("GAZP")
            
            assert price == 160.50
            mock_request.assert_called_once_with("engines/stock/markets/shares/boards/TQBR/securities/GAZP.json")
    
    @pytest.mark.asyncio
    async def test_get_current_price_not_found(self, client):
        """Тест обработки отсутствия данных о цене"""
        mock_data = {
            "marketdata": {
                "columns": ["SECID", "LAST", "BID", "ASK"],
                "data": []  # Пустые данные
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            price = await client.get_current_price("GAZP")
            
            assert price is None
    
    @pytest.mark.asyncio
    async def test_get_current_price_api_error(self, client):
        """Тест обработки ошибки API"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API Error")
            
            price = await client.get_current_price("GAZP")
            
            assert price is None
    
    @pytest.mark.asyncio
    async def test_get_historical_data_success(self, client):
        """Тест успешного получения исторических данных"""
        mock_data = {
            "history": {
                "columns": ["TRADEDATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"],
                "data": [
                    ["2023-10-25", 158.0, 162.0, 157.0, 161.0, 1000000],
                    ["2023-10-24", 155.0, 159.0, 154.0, 158.0, 900000]
                ]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            df = await client.get_historical_data("GAZP", 30)
            
            assert df is not None
            assert len(df) == 2
            assert "OPEN" in df.columns
            assert "CLOSE" in df.columns
            assert "VOLUME" in df.columns
            assert df["CLOSE"].iloc[0] == 161.0
            assert df["CLOSE"].iloc[1] == 158.0
    
    @pytest.mark.asyncio
    async def test_get_technical_indicators(self, client):
        """Тест расчета технических индикаторов"""
        # Создание тестовых данных
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        prices = [100 + i * 0.5 + (i % 10) * 2 for i in range(100)]
        
        mock_df = pd.DataFrame({
            "TRADEDATE": dates,
            "OPEN": prices,
            "HIGH": [p + 1 for p in prices],
            "LOW": [p - 1 for p in prices],
            "CLOSE": prices,
            "VOLUME": [1000000] * 100
        })
        
        with patch.object(client, 'get_historical_data', new_callable=AsyncMock) as mock_hist:
            mock_hist.return_value = mock_df
            
            indicators = await client.get_technical_indicators("GAZP", 100)
            
            assert "rsi" in indicators
            assert "macd" in indicators
            assert "sma_20" in indicators
            assert "sma_50" in indicators
            assert "sma_200" in indicators
            assert "volatility" in indicators
            assert "volume_avg" in indicators
            assert "volume_current" in indicators
            assert "volume_ratio" in indicators
    
    def test_calculate_rsi(self, client):
        """Тест расчета RSI"""
        # Создание тестовых данных
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106])
        
        rsi = client._calculate_rsi(prices, 5)
        
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100
    
    def test_calculate_macd(self, client):
        """Тест расчета MACD"""
        # Создание тестовых данных
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107])
        
        macd_data = client._calculate_macd(prices, 5, 8, 3)
        
        assert "macd" in macd_data
        assert "macd_signal" in macd_data
        assert "macd_histogram" in macd_data
        assert isinstance(macd_data["macd"], float)
        assert isinstance(macd_data["macd_signal"], float)
        assert isinstance(macd_data["macd_histogram"], float)
    
    def test_calculate_bollinger_bands(self, client):
        """Тест расчета Bollinger Bands"""
        # Создание тестовых данных
        prices = pd.Series([100, 102, 101, 103, 102, 104, 103, 105, 104, 106, 105, 107, 106, 108, 107, 109, 108, 110, 109, 111])
        
        bb_data = client._calculate_bollinger_bands(prices, 10, 2)
        
        assert "bb_upper" in bb_data
        assert "bb_middle" in bb_data
        assert "bb_lower" in bb_data
        assert "bb_position" in bb_data
        assert isinstance(bb_data["bb_upper"], float)
        assert isinstance(bb_data["bb_middle"], float)
        assert isinstance(bb_data["bb_lower"], float)
        assert 0 <= bb_data["bb_position"] <= 1
    
    @pytest.mark.asyncio
    async def test_get_index_data_success(self, client):
        """Тест успешного получения данных индекса"""
        mock_data = {
            "marketdata": {
                "columns": ["SECID", "LAST", "LASTTOPREVPRICE"],
                "data": [
                    ["IMOEX", 3500.50, 20.30]
                ]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            data = await client.get_index_data("IMOEX")
            
            assert data is not None
            assert data["value"] == 3500.50
            assert data["change"] == 20.30
    
    @pytest.mark.asyncio
    async def test_get_market_status_open(self, client):
        """Тест получения статуса открытого рынка"""
        mock_data = {
            "boards": {
                "columns": ["BOARDID", "BOARD_STATUS"],
                "data": [
                    ["TQBR", 1]  # 1 = открыт
                ]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            status = await client.get_market_status()
            
            assert status["status"] == "open"
            assert status["board_status"] == 1
    
    @pytest.mark.asyncio
    async def test_get_market_status_closed(self, client):
        """Тест получения статуса закрытого рынка"""
        mock_data = {
            "boards": {
                "columns": ["BOARDID", "BOARD_STATUS"],
                "data": [
                    ["TQBR", 0]  # 0 = закрыт
                ]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            status = await client.get_market_status()
            
            assert status["status"] == "closed"
            assert status["board_status"] == 0
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, client):
        """Тест работы кэша"""
        mock_data = {
            "marketdata": {
                "columns": ["SECID", "LAST"],
                "data": [["GAZP", 160.50]]
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            # Первый вызов - должен сделать запрос
            price1 = await client.get_current_price("GAZP")
            assert mock_request.call_count == 1
            
            # Второй вызов - должен использовать кэш
            price2 = await client.get_current_price("GAZP")
            assert mock_request.call_count == 1  # Без дополнительного вызова
            
            assert price1 == price2 == 160.50
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self, client):
        """Тест истечения кэша"""
        mock_data = {
            "marketdata": {
                "columns": ["SECID", "LAST"],
                "data": [["GAZP", 160.50]]
            }
        }
        
        # Установка очень короткого TTL для теста
        client.cache_ttl = 0
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_data
            
            # Первый вызов
            price1 = await client.get_current_price("GAZP")
            assert mock_request.call_count == 1
            
            # Второй вызов - кэш истек, должен сделать новый запрос
            price2 = await client.get_current_price("GAZP")
            assert mock_request.call_count == 2
            
            assert price1 == price2 == 160.50