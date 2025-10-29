"""
Gazprom Trading Bot - AI Module

Модуль для работы с GPT-5 через AgentRouter API.
"""

from .agentrouter_client import AgentRouterClient
from .prompts import (
    TRADING_SYSTEM_PROMPT,
    TRADING_REQUEST_TEMPLATE,
    DEEP_ANALYSIS_PROMPT
)

__all__ = [
    "AgentRouterClient",
    "TRADING_SYSTEM_PROMPT",
    "TRADING_REQUEST_TEMPLATE",
    "DEEP_ANALYSIS_PROMPT"
]