# Gazprom Trading Bot

🚀 **AI-powered Telegram бот для торговли акциями ПАО "Газпром" (GAZP) на Московской бирже (MOEX)**

Бот использует GPT-5 через AgentRouter API для анализа рынка и генерации торговых рекомендаций.

[![CI/CD](https://github.com/your-repo/gazprom-trading-bot/workflows/ci/badge.svg)](https://github.com/your-repo/gazprom-trading-bot/actions)
[![Coverage](https://codecov.io/gh/your-repo/gazprom-trading-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/your-repo/gazprom-trading-bot)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 📋 Содержание

- [Возможности](#-возможности)
- [Архитектура](#-архитектура)
- [Установка](#-установка)
- [Конфигурация](#-конфигурация)
- [Использование](#-использование)
- [Команды бота](#-команды-бота)
- [API интеграция](#-api-интеграция)
- [Развертывание](#-развертывание)
- [Мониторинг](#-мониторинг)
- [Безопасность](#-безопасность)
- [FAQ](#-часто-задаваемые-вопросы-faq)
- [Поддержка](#-поддержка)

## ✨ Возможности

### 🤖 AI-анализ
- **GPT-5 рекомендации** через AgentRouter API
- **Технический анализ** с RSI, MACD, скользящими средними
- **Управление рисками** с автоматическими стоп-лоссами
- **Обоснование решений** в естественном языке

### 📊 Торговля
- **Симуляционная торговля** акциями GAZP
- **Портфельное управление** с отслеживанием P&L
- **История транзакций** с детальной статистикой
- **Сравнение с бенчмарком** IMOEX

### 📈 Визуализация
- **Графики цен** с техническими индикаторами
- **Графики производительности** портфеля
- **Интерактивные чарты** с Plotly
- **Экспорт данных** в CSV

### 🔔 Уведомления
- **Push-уведомления** о важных событиях
- **Автоматические рекомендации** по расписанию
- **Алерты** о достижении стоп-лоссов/тейк-профитов

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram     │    │   GPT-5        │    │   MOEX API      │
│   Bot          │◄──►│   (AgentRouter) │◄──►│   (Market Data) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Portfolio    │    │   Database      │    │   Monitoring    │
│   Manager      │    │   (SQLite)     │    │   & Logging     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Установка

### Требования

- Python 3.11+
- Telegram Bot Token
- AgentRouter API Key
- Доступ к MOEX API

### Быстрый старт (5 минут)

```bash
# 1. Клонирование репозитория
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot

# 2. Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Конфигурация
cp .env.example .env
# Отредактируйте .env файл с вашими API ключами

# 5. Запуск бота
python run.py
```

### Подробная установка

#### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot
```

#### Шаг 2: Установка зависимостей

```bash
pip install -r requirements.txt
```

#### Шаг 3: Конфигурация

Скопируйте файл конфигурации:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# AgentRouter API Configuration
AGENTROUTER_API_KEY=sk-your_agentrouter_api_key_here
AGENTROUTER_BASE_URL=https://agentrouter.org/v1

# Database Configuration
DATABASE_URL=sqlite:///./gazprom_bot.db

# Trading Configuration
DEFAULT_INITIAL_CAPITAL=100000.0
DEFAULT_RISK_LIMIT=5.0
MAX_POSITION_SIZE_PERCENT=30.0
```

#### Шаг 4: Запуск

```bash
python run.py
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|-----------|---------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | - |
| `AGENTROUTER_API_KEY` | API ключ AgentRouter | - |
| `DATABASE_URL` | URL базы данных | `sqlite:///./gazprom_bot.db` |
| `DEFAULT_INITIAL_CAPITAL` | Начальный капитал | `100000.0` |
| `DEFAULT_RISK_LIMIT` | Лимит риска (%) | `5.0` |
| `MAX_POSITION_SIZE_PERCENT` | Макс. размер позиции (%) | `30.0` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

### Настройка AI

```python
# config.py
AI_TEMPERATURE = 0.7          # Температура модели
AI_MAX_TOKENS = 1000          # Макс. токенов
AI_RETRY_ATTEMPTS = 3          # Попыток повтора
```

## 📱 Использование

### Начало работы

1. **Запустите бота**: `python run.py`
2. **Найдите бота** в Telegram по @username
3. **Отправьте команду** `/start` для создания портфеля

### Примеры использования

#### 🎯 Получение AI-рекомендации

```
/recommend
```

Бот проанализирует текущую ситуацию и вернет:
```
📊 <b>Рекомендация GPT-5</b>

🎯 Действие: <b>BUY</b>
📦 Количество: 15 акций
💡 Уверенность: 85%
⚠️ Риск: MEDIUM

📝 <b>Обоснование:</b>
Технические индикаторы показывают перекупленность акции,
RSI(14) = 65, MACD пересекает сигнальную линию вверх.
Объем торгов выше среднего, что подтверждает интерес покупателей.

🛑 Stop-Loss: 165.50 RUB
🎁 Take-Profit: 185.00 RUB

Используйте /execute для исполнения сделки.
```

#### 💼 Управление портфелем

```
/portfolio
```

```
💼 <b>Ваш портфель</b>

💰 Баланс: 85,420.50 RUB
📊 Акции GAZP: 150 шт.
💵 Средняя цена: 172.30 RUB
📈 Текущая цена: 178.90 RUB
💎 Общая стоимость: 112,335.00 RUB
📊 P&L: +6,915.00 RUB (+6.57%)

🔄 Доходность vs IMOEX: +2.3%
```

#### 📈 Визуализация

```
/performance
```

Бот отправит график доходности вашего портфеля в сравнении с индексом IMOEX.

#### ⚡ Исполнение сделок

```
/execute BUY 10
```

```
✅ <b>Сделка исполнена</b>

📈 Покупка: 10 акций GAZP по 178.90 RUB
💰 Сумма: 1,789.00 RUB
🛑 Stop-Loss: 169.95 RUB
🎁 Take-Profit: 196.79 RUB

💰 Остаток: 83,631.50 RUB
```

### Основные команды

```bash
/start          # Создать портфель
/portfolio       # Посмотреть портфель
/recommend       # Получить AI-рекомендацию
/execute BUY 10  # Купить 10 акций
/execute SELL 5  # Продать 5 акций
/history         # История сделок
/performance     # График доходности
/balance         # Текущий баланс
/help            # Помощь
```

### Расширенные команды

```bash
/setinitial 150000    # Установить капитал 150000 ₽
/setrisklimit 3       # Лимит риска 3%
/subscribe daily       # Ежедневные рекомендации
/technical            # Технические индикаторы
/export               # Экспорт в CSV
```

## 🤖 Команды бота

### Основные команды

| Команда | Описание | Пример |
|---------|-----------|--------|
| `/start` | Создание портфеля | `/start` |
| `/portfolio` | Текущий портфель | `/portfolio` |
| `/recommend` | AI-рекомендация | `/recommend` |
| `/execute` | Исполнить сделку | `/execute BUY 10` |
| `/history` | История транзакций | `/history` |
| `/performance` | График доходности | `/performance` |
| `/balance` | Баланс и позиции | `/balance` |
| `/help` | Справка | `/help` |

### Настройки

| Команда | Описание | Пример |
|---------|-----------|--------|
| `/setinitial` | Начальный капитал | `/setinitial 100000` |
| `/setrisklimit` | Лимит риска | `/setrisklimit 5` |
| `/subscribe` | Автоматические рекомендации | `/subscribe daily` |

### Анализ

| Команда | Описание | Пример |
|---------|-----------|--------|
| `/technical` | Технические индикаторы | `/technical` |
| `/news` | Последние новости | `/news` |
| `/export` | Экспорт данных | `/export` |

## 🔌 API интеграция

### AgentRouter API

```python
from ai.client import AgentRouterClient

# Инициализация клиента
client = AgentRouterClient(api_key="your_api_key")

# Получение рекомендации
result = await client.get_trading_recommendation(context)
```

### MOEX API

```python
from data.client import MOEXClient

# Инициализация клиента
client = MOEXClient()

# Получение текущей цены
price = await client.get_current_price("GAZP")

# Получение технических индикаторов
indicators = await client.get_technical_indicators("GAZP")
```

## 🐳 Развертывание

### Docker

```bash
# Сборка образа
docker build -t gazprom-bot .

# Запуск контейнера
docker run -d \
  --name gazprom-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  gazprom-bot
```

### Docker Compose

```yaml
version: '3.8'
services:
  gazprom-bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gazprom-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gazprom-bot
  template:
    metadata:
      labels:
        app: gazprom-bot
    spec:
      containers:
      - name: gazprom-bot
        image: gazprom-bot:latest
        envFrom:
        - secretRef:
            name: gazprom-bot-secrets
```

## 📊 Мониторинг

### Логирование

```python
from monitoring.logger import get_logger

logger = get_logger(__name__)
logger.info("Сообщение")
```

### Метрики

- **Uptime бота**: > 99%
- **Время ответа**: < 5 секунд
- **Успешность AI запросов**: > 95%
- **Ошибки MOEX API**: < 1%

### Алерты

```python
# Мониторинг производительности
async def check_performance():
    stats = await get_daily_statistics()
    if stats["ai_recommendations"] < 10:
        send_alert("Низкое количество рекомендаций")
```

## 🔒 Безопасность

### Защита данных

- **Шифрование** чувствительных данных
- **Валидация** входных данных
- **Rate limiting** для предотвращения злоупотреблений
- **Аудит** всех операций

### Рекомендации

1. **Используйте переменные окружения** для секретов
2. **Регулярно обновляйте** зависимости
3. **Мониторьте** логи безопасности
4. **Резервируйте** базу данных

## 📝 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🤝 Contributing

1. Fork проекта
2. Создайте feature branch
3. Сделайте commit
4. Push в branch
5. Создайте Pull Request

## ❓ Часто задаваемые вопросы (FAQ)

### 🤖 Общие вопросы

**Q: Насколько точны рекомендации GPT-5?**
A: GPT-5 анализирует технические индикаторы и рыночные данные, но не может предсказать будущее с 100% точностью. Рекомендации следует использовать как дополнительный инструмент для принятия решений.

**Q: Работает ли бот в реальном времени?**
A: Бот получает данные с MOEX с задержкой 1-5 минут. Торговля выполняется в симуляционном режиме.

**Q: Можно ли подключить реальный брокерский счет?**
A: В текущей версии бота поддерживается только симуляционная торговля. Интеграция с реальными брокерами планируется в будущих версиях.

### 🔧 Технические вопросы

**Q: Что делать, если бот не отвечает?**
A: Проверьте логи в файле `logs/bot.log`. Чаще всего проблема связана с неверным API ключом или проблемами с сетью.

**Q: Как изменить параметры риска?**
A: Используйте команду `/setrisklimit X`, где X - процент риска от 1 до 10.

**Q: Можно ли использовать другие акции кроме GAZP?**
A: В текущей версии бота поддерживается только GAZP. Поддержка других тикеров планируется в будущих версиях.

### 💰 Финансовые вопросы

**Q: Сколько стоит использование бота?**
A: Сам бот бесплатный, но используются платные API:
- AgentRouter: ~$0.01 за рекомендацию
- MOEX API: бесплатно
- Telegram Bot API: бесплатно

**Q: Как рассчитывается P&L?**
A: P&L = (Текущая цена - Средняя цена покупки) × Количество акций

**Q: Что такое Stop-Loss и Take-Profit?**
A: Stop-Loss - автоматическая продажа при падении цены для ограничения убытков. Take-Profit - автоматическая продажа при достижении целевой прибыли.

## 📞 Поддержка

- **Telegram**: @gazprom_bot_support
- **Email**: support@gazprom-bot.com
- **GitHub Issues**: [Issues](https://github.com/your-repo/gazprom-trading-bot/issues)
- **Документация**: [docs/](docs/)

### 🐛 Сообщения об ошибках

При сообщении об ошибке, пожалуйста, включите:
1. Версию Python и ОС
2. Логи из `logs/bot.log`
3. Шаги для воспроизведения
4. Скриншот ошибки (если возможно)

## 🙏 Благодарности

- [AgentRouter](https://agentrouter.org) за предоставление доступа к GPT-5
- [MOEX](https://moex.com) за API биржевых данных
- [python-telegram-bot](https://python-telegram-bot.org) за отличную библиотеку
- Сообществу открытого кода за вдохновение и поддержку

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для подробностей.

---

**⚠️ Важно**: Все сделки выполняются в симуляционном режиме. Используйте рекомендации для принятия информированных решений. Торговля акциями сопряжена с риском потери капитала.

---

**⭐ Если проект вам понравился, поставьте звезду на GitHub!**