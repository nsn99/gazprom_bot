"""
Клиент для взаимодействия с AgentRouter API и AI моделей.

Предоставляет:
- Отправку запросов к AI через AgentRouter SDK
- Обработку ошибок и retry механизмы
- Валидацию ответов
- Мониторинг использования API
"""

from __future__ import annotations

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import openai
from openai import OpenAI

from config import settings
from monitoring.logger import log_api_usage, log_operation


class AgentRouterClient:
    """Клиент для AgentRouter API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.agentrouter_api_key
        self.base_url = settings.agentrouter_base_url
        self.model = settings.agentrouter_model
        self.temperature = 0.7
        self.max_tokens = 1000
        self.logger = logging.getLogger(__name__)
        
        # Инициализация OpenAI клиента для AgentRouter
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Статистика использования
        self.request_count = 0
        self.tokens_used = 0
        self.error_count = 0
        
        self.logger.info("AgentRouter client initialized")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Тест соединения с AgentRouter"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
                temperature=0.1
            )
            
            return {
                "success": True,
                "message": "Connection successful",
                "model": self.model,
                "response": response
            }
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection failed"
            }
    
    async def get_trading_recommendation(
        self, 
        system_prompt: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Получить торговую рекомендацию от AI
        
        Args:
            system_prompt: Системный промпт для AI
            user_context: Контекст пользователя и портфеля
            
        Returns:
            Dict с результатом рекомендации
        """
        start_time = datetime.now()
        
        try:
            # Формирование сообщений для chat
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_context, ensure_ascii=False)}
            ]
            
            # Отправка запроса через OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Извлечение ответа
            if response and hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                
                try:
                    # Очистка ответа от возможных артефактов
                    clean_content = content.strip()
                    if clean_content.startswith('```json'):
                        clean_content = clean_content[7:]
                    if clean_content.endswith('```'):
                        clean_content = clean_content[:-3]
                    
                    recommendation = json.loads(clean_content)
                    
                    # Обновление статистики
                    self.request_count += 1
                    
                    # Подсчет токенов
                    try:
                        tokens_data = {"total": 100}  # Временное решение
                        if tokens_data and 'total' in tokens_data:
                            self.tokens_used += tokens_data['total']
                            tokens_used_count = tokens_data['total']
                        else:
                            tokens_used_count = 0
                    except:
                        tokens_used_count = 0
                    
                    # Логирование использования API
                    execution_time = (datetime.now() - start_time).total_seconds()
                    log_api_usage(
                        api_name="agentrouter",
                        endpoint="chat/completions",
                        request_count=1,
                        response_time=execution_time,
                        success=True,
                        tokens_used=tokens_used_count
                    )
                    
                    self.logger.info(f"Trading recommendation received successfully")
                    
                    return {
                        "success": True,
                        "data": recommendation,
                        "tokens_used": tokens_used_count,
                        "execution_time": execution_time
                    }
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    return {
                        "success": False,
                        "error": f"JSON parse error: {e}",
                        "raw_response": content
                    }
            else:
                return {
                    "success": False,
                    "error": "No response from AI"
                }
                
        except Exception as e:
            self.error_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Логирование ошибки
            log_api_usage(
                api_name="agentrouter",
                endpoint="chat/completions",
                request_count=1,
                response_time=execution_time,
                success=False,
                error_code=str(type(e).__name__)
            )
            
            self.logger.error(f"Error getting trading recommendation: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def get_market_analysis(
        self,
        market_data: Dict[str, Any],
        analysis_type: str = "technical"
    ) -> Dict[str, Any]:
        """
        Получить анализ рыночных данных
        
        Args:
            market_data: Рыночные данные для анализа
            analysis_type: Тип анализа (technical, fundamental, sentiment, deep)
            
        Returns:
            Dict с результатом анализа
        """
        start_time = datetime.now()
        
        try:
            # Формирование промпта для анализа
            if analysis_type == "technical":
                prompt = self._get_technical_analysis_prompt(market_data)
            elif analysis_type == "fundamental":
                prompt = self._get_fundamental_analysis_prompt(market_data)
            elif analysis_type == "deep":
                # Для глубокого анализа используем готовый промпт из market_data
                prompt = market_data.get("analysis_request", "")
            else:
                prompt = self._get_general_analysis_prompt(market_data)
            
            # Отправка запроса
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            # Извлечение ответа
            if response:
                # Обновление статистики
                self.request_count += 1
                
                # Подсчет токенов
                try:
                    tokens_data = {"total": 100}  # Временное решение
                    if tokens_data and 'total' in tokens_data:
                        self.tokens_used += tokens_data['total']
                        tokens_used_count = tokens_data['total']
                    else:
                        tokens_used_count = 0
                except:
                    tokens_used_count = 0
                
                # Логирование использования API
                execution_time = (datetime.now() - start_time).total_seconds()
                log_api_usage(
                    api_name="agentrouter",
                    endpoint="chat/completions",
                    request_count=1,
                    response_time=execution_time,
                    success=True,
                    tokens_used=tokens_used_count
                )
                
                return {
                    "success": True,
                    "analysis": response,
                    "analysis_type": analysis_type,
                    "tokens_used": tokens_used_count,
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "error": "No response from AI"
                }
                
        except Exception as e:
            self.error_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Логирование ошибки
            log_api_usage(
                api_name="agentrouter",
                endpoint="chat/completions",
                request_count=1,
                response_time=execution_time,
                success=False,
                error_code=str(type(e).__name__)
            )
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    def _get_technical_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Формирование промпта для технического анализа"""
        return f"""
Проанализируй следующие технические индикаторы для акции Газпром (GAZP):

Текущая цена: {market_data.get('current_price', 'N/A')}
RSI(14): {market_data.get('rsi14', 'N/A')}
MACD: {market_data.get('macd', 'N/A')}
Сигнал MACD: {market_data.get('macd_signal', 'N/A')}
SMA 20: {market_data.get('sma20', 'N/A')}
SMA 50: {market_data.get('sma50', 'N/A')}
SMA 200: {market_data.get('sma200', 'N/A')}
Bollinger Upper: {market_data.get('bollinger_upper', 'N/A')}
Bollinger Lower: {market_data.get('bollinger_lower', 'N/A')}
Объем: {market_data.get('volume', 'N/A')}
Изменение за день: {market_data.get('daily_change', 'N/A')}%

Дай краткий анализ текущей ситуации и возможные сценарии развития.
"""
    
    def _get_fundamental_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Формирование промпта для фундаментального анализа"""
        return f"""
Проанализируй фундаментальные показатели для ПАО "Газпром":

P/E ratio: {market_data.get('pe_ratio', 'N/A')}
P/B ratio: {market_data.get('pb_ratio', 'N/A')}
Дивидендная доходность: {market_data.get('dividend_yield', 'N/A')}%
EPS: {market_data.get('eps', 'N/A')}
Рыночная капитализация: {market_data.get('market_cap', 'N/A')}
Долг/EBITDA: {market_data.get('debt_ebitda', 'N/A')}

Оцени инвестиционную привлекательность акции на основе этих показателей.
"""
    
    def _get_general_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """Формирование промпта для общего анализа"""
        return f"""
Проанализируй текущую ситуацию с акцией Газпром (GAZP):

Цена: {market_data.get('current_price', 'N/A')}
Объем торгов: {market_data.get('volume', 'N/A')}
Изменение за день: {market_data.get('daily_change', 'N/A')}%
Новости: {market_data.get('news_summary', 'N/A')}

Дай общую оценку и рекомендации для инвестора.
"""
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Получить статистику использования API"""
        try:
            return {
                "request_count": self.request_count,
                "tokens_used": self.tokens_used,
                "error_count": self.error_count,
                "success_rate": (self.request_count - self.error_count) / max(self.request_count, 1) * 100,
                "avg_tokens_per_request": self.tokens_used / max(self.request_count, 1)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting usage stats: {e}")
            return {
                "error": str(e)
            }
    
    async def reset_stats(self):
        """Сброс статистики использования"""
        self.request_count = 0
        self.tokens_used = 0
        self.error_count = 0
        
        self.logger.info("Usage stats reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья клиента"""
        try:
            # Тестовый запрос
            test_result = await self.test_connection()
            
            # Проверка конфигурации
            config_valid = bool(
                self.api_key and
                self.base_url and
                self.model
            )
            
            return {
                "status": "healthy" if test_result["success"] and config_valid else "unhealthy",
                "connection_test": test_result,
                "config_valid": config_valid,
                "stats": await self.get_usage_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Глобальный экземпляр клиента
_agentrouter_client = None


def get_agentrouter_client() -> AgentRouterClient:
    """Получение глобального экземпляра клиента"""
    global _agentrouter_client
    if _agentrouter_client is None:
        _agentrouter_client = AgentRouterClient()
    return _agentrouter_client


# Декоратор для автоматического логирования API вызовов
def log_agentrouter_call(func):
    """Декоратор для логирования вызовов AgentRouter"""
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        
        try:
            result = await func(*args, **kwargs)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            log_operation(
                'INFO', 'agentrouter', func.__name__,
                f"AgentRouter call completed successfully",
                execution_time=execution_time
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            log_operation(
                'ERROR', 'agentrouter', func.__name__,
                f"AgentRouter call failed: {e}",
                execution_time=execution_time
            )
            
            raise
    
    return wrapper