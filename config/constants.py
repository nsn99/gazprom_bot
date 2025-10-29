# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Constants Module

Модуль с константами для торговой системы.
"""

# Trading Constants
MAX_POSITION_SIZE_PERCENT = 30.0
STOP_LOSS_PERCENT = 5.0
TAKE_PROFIT_PERCENT = 10.0
COMMISSION_PERCENT = 0.03

# Technical Indicators
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Risk Management
MAX_DRAWDOWN_PERCENT = 20.0
MIN_CONFIDENCE = 60.0

# Trading Hours (MSK)
MARKET_OPEN_HOUR = 7
MARKET_CLOSE_HOUR = 21
NO_TRADING_FIRST_MINUTES = 15
NO_TRADING_LAST_MINUTES = 15

# API Limits
MOEX_REQUEST_LIMIT = 100
AGENTROUTER_REQUEST_LIMIT = 1000

# Database Constants
DEFAULT_INITIAL_CAPITAL = 100000.0
MIN_TRADE_AMOUNT = 1000.0

# Trading Symbols
GAZP_TICKER = "GAZP"

# Telegram Bot
MAX_MESSAGE_LENGTH = 4096
POLLING_TIMEOUT = 30

# Performance Thresholds
SLOW_OPERATION_THRESHOLD = 5.0
HEALTH_CHECK_INTERVAL = 60

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Error Messages
ERROR_MOEX_UNAVAILABLE = "MOEX API временно недоступен"
ERROR_AGENTROUTER_UNAVAILABLE = "AgentRouter API временно недоступен"
ERROR_INSUFFICIENT_FUNDS = "Недостаточно средств"
ERROR_INVALID_QUANTITY = "Неверное количество акций"
ERROR_INVALID_ACTION = "Неверное действие (допустимо: BUY/SELL)"
ERROR_CONFIG_INVALID = "Конфигурация невалидна"

# Telegram Messages
WELCOME_MESSAGE = """
👋 Добро пожаловать, {user_name}!

🤖 Я - ваш персональный торговый бот для акций Газпрома (GAZP) на MOEX.

💼 Для вас уже создан портфель с начальным капиталом 100,000 ₽.

📋 Основные команды:
/start - Показать это сообщение
/portfolio - Ваш портфель
/recommend - Получить AI-рекомендацию
/analysis - Углубленный анализ GAZP и портфеля
/execute BUY [кол-во] - Купить акции
/execute SELL [кол-во] - Продать акции
/history - История сделок
/balance - Баланс и позиции
/help - Помощь

🚀 Начнем торговлю!
"""

HELP_MESSAGE = """
📋 <b>Справка по командам:</b>

🔹 <b>/start</b> - Создать портфель и начать работу
🔹 <b>/portfolio</b> - Показать текущий портфель и P&L
🔹 <b>/recommend</b> - Получить торговую рекомендацию от AI
🔹 <b>/analysis</b> - Получить углубленный анализ GAZP и портфеля
🔹 <b>/execute BUY [кол-во]</b> - Купить указанное количество акций
🔹 <b>/execute SELL [кол-во]</b> - Продать указанное количество акций
🔹 <b>/history</b> - Показать историю последних 10 транзакций
🔹 <b>/balance</b> - Показать баланс и текущие позиции
🔹 <b>/help</b> - Показать это справочное сообщение

💡 <b>Примеры использования:</b>
• /execute BUY 10 - Купить 10 акций GAZP
• /execute SELL 5 - Продать 5 акций GAZP

📊 <b>Команда /analysis предоставляет:</b>
• Технический анализ (уровни, индикаторы, тренды)
• Фундаментальный анализ (новости, макрофакторы)
• Стратегический план на неделю
• Целевые цены и уровни стоп-лосс

⚠️ <b>Важно:</b>
• Максимальный размер позиции: 30% от капитала
• Обязательный стоп-лосс: -5% от цены входа
• Рекомендуемый тейк-профит: +10% от цены входа

🤖 <b>AI рекомендации:</b>
• AI анализирует технические индикаторы
• Учитывает рыночную ситуацию и ваши позиции
• Дает обоснование для каждого решения

❓ <b>Нужна помощь?</b>
• Используйте /help для просмотра этого сообщения
• Все сделки симулируются (без реальных денег)
"""