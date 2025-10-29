"""
Тесты для AI клиента
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from gazprom_bot.ai.client import AgentRouterClient


class TestAgentRouterClient:
    """Тесты клиента AgentRouter"""
    
    @pytest.fixture
    def client(self):
        """Фикстура для создания клиента"""
        with patch('gazprom_bot.ai.client.settings') as mock_settings:
            mock_settings.AGENTROUTER_BASE_URL = "https://test.agentrouter.org/v1"
            mock_settings.AGENTROUTER_MODEL = "gpt-5-test"
            mock_settings.AI_RETRY_ATTEMPTS = 3
            mock_settings.AI_TEMPERATURE = 0.7
            mock_settings.AI_MAX_TOKENS = 1000
            
            return AgentRouterClient("test-api-key")
    
    @pytest.mark.asyncio
    async def test_get_trading_recommendation_success(self, client):
        """Тест успешного получения рекомендации"""
        # Мокирование ответа API
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Тестовое обоснование",
            "stop_loss": 150.0,
            "take_profit": 180.0,
            "risk_level": "MEDIUM",
            "confidence": 75
        })
        mock_response.usage.total_tokens = 100
        
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            context = {
                "portfolio": {"cash": 100000, "shares": 0},
                "market_data": {"current_price": 160.0},
                "risk_settings": {"max_position_percent": 30}
            }
            
            result = await client.get_trading_recommendation(context)
            
            assert result["success"] is True
            assert result["data"]["action"] == "BUY"
            assert result["data"]["quantity"] == 10
            assert result["tokens_used"] == 100
            assert result["attempt"] == 1
    
    @pytest.mark.asyncio
    async def test_get_trading_recommendation_api_error(self, client):
        """Тест обработки ошибки API"""
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            context = {"portfolio": {}, "market_data": {}, "risk_settings": {}}
            
            result = await client.get_trading_recommendation(context)
            
            assert result["success"] is False
            assert "API Error" in result["error"]
            assert result["attempts"] == 3
    
    @pytest.mark.asyncio
    async def test_get_trading_recommendation_invalid_response(self, client):
        """Тест обработки невалидного ответа"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "invalid json"
        
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            context = {"portfolio": {}, "market_data": {}, "risk_settings": {}}
            
            result = await client.get_trading_recommendation(context)
            
            assert result["success"] is False
            assert "не удалось получить рекомендацию" in result["error"]
    
    def test_format_user_prompt(self, client):
        """Тест форматирования пользовательского промпта"""
        context = {
            "portfolio": {
                "cash": 100000.0,
                "shares": 50,
                "avg_price": 150.0,
                "current_price": 160.0,
                "total_value": 108000.0,
                "pnl": 8000.0,
                "pnl_percent": 8.0
            },
            "market_data": {
                "current_price": 160.0,
                "technical_indicators": {
                    "rsi": 55.0,
                    "macd": 2.5,
                    "sma_20": 155.0,
                    "sma_50": 150.0
                }
            },
            "risk_settings": {
                "max_position_percent": 30,
                "risk_limit_percent": 5
            },
            "timestamp": "2023-10-26T10:00:00"
        }
        
        prompt = client._format_user_prompt(context)
        
        assert "100000.00 RUB" in prompt
        assert "50 шт." in prompt
        assert "160.00 RUB" in prompt
        assert "RSI(14): 55.0" in prompt
        assert "30%" in prompt
        assert "2023-10-26T10:00:00" in prompt
    
    def test_parse_response_success(self, client):
        """Тест успешного парсинга ответа"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "action": "SELL",
            "quantity": 20,
            "reasoning": "Тестовая продажа",
            "stop_loss": 170.0,
            "take_profit": 140.0,
            "risk_level": "HIGH",
            "confidence": 85
        })
        
        result = client._parse_response(mock_response)
        
        assert result["action"] == "SELL"
        assert result["quantity"] == 20
        assert result["reasoning"] == "Тестовая продажа"
        assert result["stop_loss"] == 170.0
        assert result["take_profit"] == 140.0
        assert result["risk_level"] == "HIGH"
        assert result["confidence"] == 85
    
    def test_parse_response_invalid_json(self, client):
        """Тест парсинга невалидного JSON"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "invalid json"
        
        with pytest.raises(Exception):
            client._parse_response(mock_response)
    
    def test_validate_recommendation_success(self, client):
        """Тест успешной валидации рекомендации"""
        recommendation = {
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Тестовое обоснование",
            "stop_loss": 150.0,
            "take_profit": 180.0,
            "risk_level": "MEDIUM",
            "confidence": 75
        }
        
        result = client._validate_recommendation(recommendation)
        
        assert result["valid"] is True
    
    def test_validate_recommendation_missing_field(self, client):
        """Тест валидации с отсутствующим полем"""
        recommendation = {
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Тестовое обоснование",
            # Отсутствуют обязательные поля
        }
        
        result = client._validate_recommendation(recommendation)
        
        assert result["valid"] is False
        assert "stop_loss" in result["error"]
    
    def test_validate_recommendation_invalid_action(self, client):
        """Тест валидации с неверным действием"""
        recommendation = {
            "action": "INVALID",
            "quantity": 10,
            "reasoning": "Тестовое обоснование",
            "stop_loss": 150.0,
            "take_profit": 180.0,
            "risk_level": "MEDIUM",
            "confidence": 75
        }
        
        result = client._validate_recommendation(recommendation)
        
        assert result["valid"] is False
        assert "Неверное значение action" in result["error"]
    
    def test_validate_recommendation_negative_quantity(self, client):
        """Тест валидации с отрицательным количеством"""
        recommendation = {
            "action": "BUY",
            "quantity": -10,
            "reasoning": "Тестовое обоснование",
            "stop_loss": 150.0,
            "take_profit": 180.0,
            "risk_level": "MEDIUM",
            "confidence": 75
        }
        
        result = client._validate_recommendation(recommendation)
        
        assert result["valid"] is False
        assert "не может быть отрицательным" in result["error"]
    
    def test_validate_recommendation_invalid_confidence(self, client):
        """Тест валидации с невалидной уверенностью"""
        recommendation = {
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Тестовое обоснование",
            "stop_loss": 150.0,
            "take_profit": 180.0,
            "risk_level": "MEDIUM",
            "confidence": 150  # > 100
        }
        
        result = client._validate_recommendation(recommendation)
        
        assert result["valid"] is False
        assert "Уверенность должна быть в диапазоне от 0 до 100" in result["error"]