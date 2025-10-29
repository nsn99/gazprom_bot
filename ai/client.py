"""
Gazprom Trading Bot - AI Client Module

Модуль для работы с GPT-5 через AgentRouter API.
"""

import json
import asyncio
from typing import Dict, Any, Optional
import openai
from openai import OpenAI

from config import settings
from monitoring.logger import get_logger
from ai.prompts import TRADING_SYSTEM_PROMPT


logger = get_logger(__name__)


class AgentRouterClient:
    """Клиент для работы с AgentRouter API"""
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента AgentRouter
        
        Args:
            api_key: API ключ для AgentRouter
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=settings.AGENTROUTER_BASE_URL
        )
        self.model = settings.AGENTROUTER_MODEL
        self.max_retries = settings.AI_RETRY_ATTEMPTS
        
    async def get_trading_recommendation(
        self, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Получить торговую рекомендацию от GPT-5
        
        Args:
            context: Контекст с данными портфеля и рынка
            
        Returns:
            Словарь с рекомендацией или ошибкой
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Запрос рекомендации GPT-5 (попытка {attempt + 1})")
                
                # Формирование пользовательского промпта
                user_prompt = self._format_user_prompt(context)
                
                # Вызов API
                response = await self._call_ai_api(user_prompt)
                
                # Парсинг ответа
                recommendation = self._parse_response(response)
                
                # Валидация рекомендации
                validation_result = self._validate_recommendation(recommendation)
                if not validation_result["valid"]:
                    logger.warning(f"Невалидная рекомендация: {validation_result['error']}")
                    continue
                
                logger.info(f"Получена рекомендация: {recommendation['action']} {recommendation['quantity']} шт.")
                
                return {
                    "success": True,
                    "data": recommendation,
                    "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                logger.error(f"Ошибка при получении рекомендации (попытка {attempt + 1}): {e}")
                
                if attempt == self.max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Не удалось получить рекомендацию после {self.max_retries} попыток: {str(e)}",
                        "attempts": attempt + 1
                    }
                
                # Экспоненциальный backoff
                await asyncio.sleep(2 ** attempt)
        
        return {
            "success": False,
            "error": f"Не удалось получить рекомендацию после {self.max_retries} попыток",
            "attempts": self.max_retries
        }
    
    async def _call_ai_api(self, user_prompt: str) -> Any:
        """
        Вызов AI API
        
        Args:
            user_prompt: Пользовательский промпт
            
        Returns:
            Ответ от API
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": TRADING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            return response
            
        except openai.APIError as e:
            raise Exception(f"API Error: {e}")
        except openai.RateLimitError as e:
            raise Exception(f"Rate Limit Error: {e}")
        except openai.AuthenticationError as e:
            raise Exception(f"Authentication Error: {e}")
        except Exception as e:
            raise Exception(f"Unexpected Error: {e}")
    
    def _format_user_prompt(self, context: Dict[str, Any]) -> str:
        """
        Форматирование пользовательского промпта
        
        Args:
            context: Контекст с данными
            
        Returns:
            Отформатированный промпт
        """
        portfolio = context.get("portfolio", {})
        market_data = context.get("market_data", {})
        risk_settings = context.get("risk_settings", {})
        
        # Формирование строки с техническими индикаторами
        technical_str = ""
        indicators = market_data.get("technical_indicators", {})
        if indicators:
            technical_str = f"""
ТЕХНИЧЕСКИЕ ИНДИКАТОРЫ:
- RSI(14): {indicators.get('rsi', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}
- SMA(20): {indicators.get('sma_20', 'N/A')}
- SMA(50): {indicators.get('sma_50', 'N/A')}
- SMA(200): {indicators.get('sma_200', 'N/A')}
"""
        
        user_prompt = f"""
ТЕКУЩИЙ ПОРТФЕЛЬ:
- Денежные средства: {portfolio.get('cash', 0):.2f} RUB
- Акции GAZP: {portfolio.get('shares', 0)} шт.
- Средняя цена покупки: {portfolio.get('avg_price', 0):.2f} RUB
- Текущая цена: {portfolio.get('current_price', 0):.2f} RUB
- Общая стоимость: {portfolio.get('total_value', 0):.2f} RUB
- P&L: {portfolio.get('pnl', 0):+.2f} RUB ({portfolio.get('pnl_percent', 0):+.2f}%)

РЫНОЧНЫЕ ДАННЫЕ:
- Текущая цена: {market_data.get('current_price', 0):.2f} RUB
{technical_str}

НАСТРОЙКИ РИСКА:
- Максимальный размер позиции: {risk_settings.get('max_position_percent', 30)}%
- Лимит риска: {risk_settings.get('risk_limit_percent', 5)}%

ВРЕМЯ: {context.get('timestamp', 'Unknown')}

Проанализируй текущую ситуацию и дай торговую рекомендацию в соответствии с правилами.
"""
        
        return user_prompt
    
    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Парсинг ответа от API
        
        Args:
            response: Ответ от API
            
        Returns:
            Распарсенная рекомендация
        """
        try:
            content = response.choices[0].message.content
            recommendation = json.loads(content)
            return recommendation
            
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            raise Exception(f"Ошибка парсинга ответа: {e}")
    
    def _validate_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация рекомендации
        
        Args:
            recommendation: Рекомендация для валидации
            
        Returns:
            Результат валидации
        """
        required_fields = ["action", "quantity", "reasoning", "stop_loss", "take_profit", "risk_level", "confidence"]
        
        # Проверка обязательных полей
        for field in required_fields:
            if field not in recommendation:
                return {
                    "valid": False,
                    "error": f"Отсутствует обязательное поле: {field}"
                }
        
        # Проверка значения action
        if recommendation["action"] not in ["BUY", "SELL", "HOLD"]:
            return {
                "valid": False,
                "error": f"Неверное значение action: {recommendation['action']}"
            }
        
        # Проверка количества
        try:
            quantity = int(recommendation["quantity"])
            if quantity < 0:
                return {
                    "valid": False,
                    "error": "Количество акций не может быть отрицательным"
                }
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "Количество акций должно быть целым числом"
            }
        
        # Проверка цен
        try:
            stop_loss = float(recommendation["stop_loss"])
            take_profit = float(recommendation["take_profit"])
            
            if stop_loss <= 0 or take_profit <= 0:
                return {
                    "valid": False,
                    "error": "Цены должны быть положительными числами"
                }
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "Цены должны быть числами"
            }
        
        # Проверка уровня риска
        if recommendation["risk_level"] not in ["LOW", "MEDIUM", "HIGH"]:
            return {
                "valid": False,
                "error": f"Неверный уровень риска: {recommendation['risk_level']}"
            }
        
        # Проверка уверенности
        try:
            confidence = float(recommendation["confidence"])
            if not 0 <= confidence <= 100:
                return {
                    "valid": False,
                    "error": "Уверенность должна быть в диапазоне от 0 до 100"
                }
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "Уверенность должна быть числом"
            }
        
        return {"valid": True}
    
    async def get_market_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получить анализ рынка
        
        Args:
            market_data: Данные рынка
            
        Returns:
            Анализ рынка
        """
        try:
            user_prompt = f"""
Проанализируй текущую рыночную ситуацию для акций GAZP:

ДАННЫЕ РЫНКА:
{json.dumps(market_data, ensure_ascii=False, indent=2)}

Дай краткий анализ в формате JSON:
{{
  "trend": "UP/DOWN/SIDEWAYS",
  "strength": "STRONG/MODERATE/WEAK",
  "key_factors": ["фактор1", "фактор2"],
  "short_term_outlook": "BULLISH/BEARISH/NEUTRAL",
  "analysis": "Краткий текстовый анализ"
}}
"""
            
            response = await self._call_ai_api(user_prompt)
            analysis = self._parse_response(response)
            
            return {
                "success": True,
                "data": analysis
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении анализа рынка: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_risk_assessment(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получить оценку рисков портфеля
        
        Args:
            portfolio_data: Данные портфеля
            
        Returns:
            Оценка рисков
        """
        try:
            user_prompt = f"""
Оцени риски текущего портфеля:

ДАННЫЕ ПОРТФЕЛЯ:
{json.dumps(portfolio_data, ensure_ascii=False, indent=2)}

Дай оценку рисков в формате JSON:
{{
  "overall_risk": "LOW/MEDIUM/HIGH",
  "risk_factors": ["фактор1", "фактор2"],
  "recommendations": ["рекомендация1", "рекомендация2"],
  "risk_score": <0-100>,
  "diversification_note": "Комментарий о диверсификации"
}}
"""
            
            response = await self._call_ai_api(user_prompt)
            assessment = self._parse_response(response)
            
            return {
                "success": True,
                "data": assessment
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении оценки рисков: {e}")
            return {
                "success": False,
                "error": str(e)
            }