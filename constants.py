"""
Константы для Gazprom Trading Bot
"""

# Настройки торговли
MAX_POSITION_SIZE_PERCENT = 30
STOP_LOSS_PERCENT = 5
TAKE_PROFIT_PERCENT = 10
DEFAULT_INITIAL_CAPITAL = 100000.0  # 100k RUB
COMMISSION_PERCENT = 0.03  # 0.03% комиссия

# Тикеры
GAZP_TICKER = "GAZP"
IMOEX_TICKER = "IMOEX"

# Сообщения
WELCOME_MESSAGE = """
🎉 Добро пожаловать в Gazprom Trading Bot, {user_name}!

🤖 Я - ваш AI-помощник для торговли акциями Газпром (GAZP) на Московской бирже.

📊 <b>Что я умею:</b>
• Анализировать рынок с помощью GPT-5
• Давать торговые рекомендации
• Управлять вашим портфелем
• Следить за рисками

💰 <b>Ваш портфель создан:</b>
• Начальный капитал: 100,000 RUB
• Статус: Активен

⚡ <b>Основные команды:</b>
/portfolio - просмотр портфеля
/recommend - получить AI-рекомендацию
/execute [BUY/SELL] [количество] - исполнить сделку
/balance - текущий баланс
/history - история транзакций
/help - все команды

⚠️ <b>Важно:</b> Все сделки симуляционные и не приводят к реальным финансовым операциям.
"""

HELP_MESSAGE = """
🤖 <b>Gazprom Trading Bot - Справка</b>

<b>Основные команды:</b>
/start - Создание портфеля и приветствие
/portfolio - Просмотр текущего портфеля
/recommend - Получить AI-рекомендацию от GPT-5
/execute [BUY/SELL] [количество] - Исполнить сделку
/balance - Текущий баланс и средства
/history - История транзакций
/performance - График производительности

<b>Расширенные команды:</b>
/setinitial [сумма] - Установить начальный капитал
/setrisklimit [проценты] - Установить лимит риска
/chart [период] - График цены за период
/risk - Анализ рисков портфеля

<b>Примеры:</b>
/recommend - получить рекомендацию
/execute BUY 100 - купить 100 акций
/execute SELL 50 - продать 50 акций
/setinitial 200000 - установить капитал 200k RUB

<b>О боте:</b>
🤖 AI: GPT-5 через AgentRouter
📊 Анализ: Технические индикаторы + AI
🛡️ Риски: Автоматические стоп-лоссы
📈 Графики: Визуализация производительности

⚠️ <b>Важно:</b> Все сделки симуляционные и не приводят к реальным финансовым операциям.

📞 <b>Поддержка:</b> @support_bot
"""

# Настройки AgentRouter
AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"
AGENTROUTER_MODEL = "gpt-5"
AGENTROUTER_TEMPERATURE = 0.7
AGENTROUTER_MAX_TOKENS = 1000

# Настройки MOEX API
MOEX_BASE_URL = "https://iss.moex.com/iss"
MOEX_MARKET = "shares"
MOEX_BOARD = "TQBR"
MOEX_TIMEOUT = 30

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки базы данных
DATABASE_URL = "sqlite+aiosqlite:///gazprom_bot.db"

# Настройки производительности
SLOW_OPERATION_THRESHOLD = 5.0  # секунды
API_REQUEST_THRESHOLD = 100  # запросов в минуту

# Технические индикаторы
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
SMA_PERIODS = [20, 50, 200]
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2