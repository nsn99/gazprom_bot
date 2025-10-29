# Getting Started with Gazprom Trading Bot

🚀 **Полное руководство по запуску и использованию Gazprom Trading Bot**

## 📋 Что вам понадобится

### Обязательные компоненты
- **Python 3.11+** - основной язык программирования
- **Telegram Bot Token** - для создания бота в Telegram
- **AgentRouter API Key** - для доступа к GPT-5
- **Git** - для клонирования репозитория

### Рекомендуемые компоненты
- **Docker** - для контейнеризации (опционально)
- **PostgreSQL** - для production базы данных (опционально)

## 🔧 Шаг 1: Получение API ключей

### 1.1 Telegram Bot Token

1. Откройте Telegram и найдите [@BotFather](https://t.me/botfather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям:
   ```
   /newbot
   BotFather: Alright, a new bot. How are we going to call it? Please choose a name for your bot.
   
   You: Gazprom Trading Bot
   BotFather: Good. Now let's choose a username for your bot. It must end in `bot`. Like this, for example: TetrisBot or tetris_bot.
   
   You: gazprom_trading_bot
   BotFather: Done! Congratulations on your new bot. You'll find it at t.me/gazprom_trading_bot. You can now add a description, about section and profile picture for your bot, see /help for a list of commands.
   
   Use this token to access the HTTP API:
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
4. Скопируйте токен (начинается с цифр и содержит двоеточие)

### 1.2 AgentRouter API Key

1. Перейдите на [agentrouter.org](https://agentrouter.org)
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в [Console → Tokens](https://agentrouter.org/console/token)
4. Нажмите "Create New Token"
5. Дайте имя токену (например, "Gazprom Bot")
6. Скопируйте ключ (начинается с `sk-`)

## 🚀 Шаг 2: Установка и настройка

### 2.1 Клонирование репозитория

```bash
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot
```

### 2.2 Создание виртуального окружения

```bash
# Создание виртуального окружения
python -m venv venv

# Активация (Linux/Mac)
source venv/bin/activate

# Активация (Windows)
venv\Scripts\activate
```

### 2.3 Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2.4 Настройка переменных окружения

```bash
# Копирование шаблона
cp .env.example .env

# Редактирование файла
nano .env  # или используйте ваш любимый редактор
```

Добавьте ваши API ключи в `.env` файл:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# AgentRouter API Configuration
AGENTROUTER_API_KEY=sk-your-agentrouter-api-key-here
AGENTROUTER_BASE_URL=https://agentrouter.org/v1

# Database Configuration
DATABASE_URL=sqlite:///./gazprom_bot.db

# Trading Configuration
DEFAULT_INITIAL_CAPITAL=100000.0
DEFAULT_RISK_LIMIT=5.0
MAX_POSITION_SIZE_PERCENT=30.0

# Logging Configuration
LOG_LEVEL=INFO
```

## 🏃‍♂️ Шаг 3: Запуск бота

### 3.1 Первый запуск

```bash
python run.py
```

Вы должны увидеть примерно такой вывод:

```
2024-10-26 16:00:00 - INFO - Starting Gazprom Trading Bot v1.0.0
2024-10-26 16:00:00 - INFO - Database initialized successfully
2024-10-26 16:00:00 - INFO - AI client connected to AgentRouter
2024-10-26 16:00:00 - INFO - Telegram bot started successfully
2024-10-26 16:00:00 - INFO - Bot is running... Press Ctrl+C to stop
```

### 3.2 Проверка работы

1. Откройте Telegram
2. Найдите вашего бота по имени пользователя
3. Отправьте команду `/start`
4. Вы должны получить приветственное сообщение

## 📱 Шаг 4: Первое использование

### 4.1 Создание портфеля

Отправьте команду:
```
/start
```

Бот создаст для вас портфель с начальным капиталом 100,000 RUB.

### 4.2 Получение рекомендации

Отправьте команду:
```
/recommend
```

Бот проанализирует текущую ситуацию и вернет рекомендацию.

### 4.3 Просмотр портфеля

Отправьте команду:
```
/portfolio
```

Вы увидите текущее состояние вашего портфеля.

## 🐳 Шаг 5: Docker развертывание (опционально)

### 5.1 Сборка образа

```bash
docker build -t gazprom-bot .
```

### 5.2 Запуск контейнера

```bash
docker run -d \
  --name gazprom-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  gazprom-bot
```

### 5.3 Использование Docker Compose

```bash
docker-compose up -d
```

## 🔧 Шаг 6: Настройка production окружения

### 6.1 PostgreSQL база данных

Измените `DATABASE_URL` в `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/gazprom_bot
```

### 6.2 Nginx конфигурация

Создайте файл `/etc/nginx/sites-available/gazprom-bot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.3 Systemd сервис

Создайте файл `/etc/systemd/system/gazprom-bot.service`:

```ini
[Unit]
Description=Gazprom Trading Bot
After=network.target

[Service]
Type=simple
User=gazprom_bot
WorkingDirectory=/opt/gazprom_bot
Environment=PATH=/opt/gazprom_bot/venv/bin
ExecStart=/opt/gazprom_bot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl enable gazprom-bot
sudo systemctl start gazprom-bot
```

## 🧪 Шаг 7: Тестирование

### 7.1 Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=.

# Конкретный модуль
pytest tests/test_portfolio_manager.py
```

### 7.2 Проверка здоровья

```bash
curl http://localhost:8000/health
```

Ответ должен быть:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-26T16:00:00Z",
  "version": "1.0.0"
}
```

## 📊 Шаг 8: Мониторинг

### 8.1 Просмотр логов

```bash
tail -f logs/bot.log
```

### 8.2 Метрики производительности

Посетите `http://localhost:8000/metrics` для просмотра метрик.

## 🚨 Шаг 9: Решение проблем

### 9.1 Частые проблемы

**Проблема**: `Invalid token` при запуске бота
**Решение**: Проверьте правильность Telegram Bot Token в `.env`

**Проблема**: `Authentication failed` при запросе к AI
**Решение**: Проверьте AgentRouter API Key в `.env`

**Проблема**: Бот не отвечает на команды
**Решение**: Проверьте логи в `logs/bot.log`

### 9.2 Получение помощи

1. Проверьте [FAQ](README.md#-часто-задаваемые-вопросы-faq)
2. Посмотрите [Issues](https://github.com/your-repo/gazprom-trading-bot/issues)
3. Создайте новый Issue с подробным описанием проблемы

## 🎯 Шаг 10: Дальнейшие действия

### 10.1 Изучение возможностей

- Изучите [все команды бота](README.md#-команды-бота)
- Настройте [автоматические уведомления](README.md#-уведомления)
- Попробуйте [технический анализ](README.md#-технический-анализ)

### 10.2 Кастомизация

- Измените [параметры риска](README.md#-управление-рисками)
- Настройте [собственные стратегии](docs/STRATEGY_DEVELOPMENT.md)
- Интегрируйте [дополнительные индикаторы](docs/INDICATOR_DEVELOPMENT.md)

### 10.3 Вклад в проект

- Посмотрите [CONTRIBUTING.md](CONTRIBUTING.md)
- Создайте [Pull Request](https://github.com/your-repo/gazprom-trading-bot/pulls)
- Участвуйте в [обсуждениях](https://github.com/your-repo/gazprom-trading-bot/discussions)

## 🎉 Поздравляем!

Вы успешно запустили Gazprom Trading Bot! Теперь у вас есть мощный AI-ассистент для торговли акциями Газпрома.

### Что дальше?

1. **Попробуйте бота в действии** - получите первую рекомендацию
2. **Изучите документацию** - узнайте о всех возможностях
3. **Присоединитесь к сообществу** - делитесь опытом и идеями
4. **Вносите вклад** - помогите улучшить проект

---

**🚀 Удачной торговли с Gazprom Trading Bot!**