# Production Deployment Guide

Руководство по развертыванию и эксплуатации Telegram Trading Bot в production среде.

## 📋 Содержание

- [Проверка продакшена](#-проверка-продакшена)
- [CI/CD и безопасность](#-cicd-и-безопасность)
- [Оптимизация и эксплуатация](#-оптимизация-и-эксплуатация)
- [Документация и сопровождение](#-документация-и-сопровождение)
- [Адаптация и развитие](#-адаптация-и-развитие)

## 🔍 Проверка продакшена

### Безопасность конфигурации

```bash
# Проверка отсутствия токенов в коде
grep -r "sk-" . --exclude-dir=.git
grep -r "BOT_TOKEN" . --exclude-dir=.git

# Проверка .env в .gitignore
cat .gitignore | grep .env
```

### Тестирование интерфейсов

```bash
# Unit тесты
pytest tests/unit/ -v

# Интеграционные тесты
pytest tests/integration/ -v

# E2E тесты
pytest tests/e2e/ -v --timeout=300

# Нагрузочные тесты
pytest tests/load/ -v --workers=4
```

### Проверка базы данных

```bash
# Миграции
alembic upgrade head

# Резервное копирование
pg_dump gazprom_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# Проверка целостности
python -c "
from gazprom_bot.database.database import get_database_manager
import asyncio
async def check():
    db = get_database_manager()
    await db.check_connection()
    print('Database OK')
asyncio.run(check())
"
```

### Ревью логирования

```bash
# Проверка отсутствия чувствительных данных в логах
grep -r "password\|token\|key" logs/ --exclude="*.gz"

# Проверка уровня логирования
tail -f logs/gazprom_bot.log | grep -E "(ERROR|CRITICAL)"
```

## 🚀 CI/CD и безопасность

### GitHub Actions Workflow

```yaml
name: CI/CD Pipeline for Gazprom Trading Bot

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  release:
    types: [ published ]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "18"

jobs:
  # Проверка кода и тесты
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_gazprom_bot
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Lint with flake8
      run: |
        flake8 gazprom_bot --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 gazprom_bot --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Type checking with mypy
      run: |
        mypy gazprom_bot --ignore-missing-imports
    
    - name: Security check with bandit
      run: |
        bandit -r gazprom_bot -f json -o bandit-report.json
    
    - name: Run unit tests
      env:
        DATABASE__url: postgresql://postgres:test_password@localhost:5432/test_gazprom_bot
        TELEGRAM__BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN_TEST }}
        AGENTROUTER__API_KEY: ${{ secrets.AGENTROUTER_API_KEY_TEST }}
      run: |
        pytest tests/unit/ -v --cov=gazprom_bot --cov-report=xml --cov-report=html
    
    - name: Run integration tests
      env:
        DATABASE__url: postgresql://postgres:test_password@localhost:5432/test_gazprom_bot
        TELEGRAM__BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN_TEST }}
        AGENTROUTER__API_KEY: ${{ secrets.AGENTROUTER_API_KEY_TEST }}
      run: |
        pytest tests/integration/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Upload security scan
      uses: actions/upload-artifact@v3
      with:
        name: security-scan
        path: bandit-report.json

  # E2E тесты
  e2e-test:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run E2E tests
      env:
        TELEGRAM__BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN_STAGING }}
        AGENTROUTER__API_KEY: ${{ secrets.AGENTROUTER_API_KEY_STAGING }}
        ENVIRONMENT: staging
      run: |
        pytest tests/e2e/ -v --timeout=600

  # Сборка Docker образа
  build:
    runs-on: ubuntu-latest
    needs: [test, e2e-test]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ghcr.io/${{ github.repository }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  # Развертывание в staging
  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - name: Deploy to staging
      run: |
        echo "Deploying to staging environment"
        # Здесь скрипт развертывания в staging

  # Развертывание в production
  deploy-production:
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'release'
    environment: production
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deploying to production environment"
        # Здесь скрипт развертывания в production
```

### Staging среда

```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  gazprom-bot-staging:
    image: ghcr.io/your-org/gazprom-bot:develop
    environment:
      - ENVIRONMENT=staging
      - TELEGRAM__BOT_TOKEN=${TELEGRAM_BOT_TOKEN_STAGING}
      - AGENTROUTER__API_KEY=${AGENTROUTER_API_KEY_STAGING}
      - DATABASE__url=postgresql://postgres:${POSTGRES_PASSWORD}@postgres-staging:5432/gazprom_bot_staging
      - LOGGING__LEVEL=DEBUG
    depends_on:
      - postgres-staging
    restart: unless-stopped

  postgres-staging:
    image: postgres:15
    environment:
      - POSTGRES_DB=gazprom_bot_staging
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_staging_data:
```

### Production учетные данные

```bash
# Отдельные токены для production
TELEGRAM__BOT_TOKEN_PROD=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
AGENTROUTER__API_KEY_PROD=sk-prod-1234567890abcdef

# Тестовые токены для staging
TELEGRAM__BOT_TOKEN_STAGING=0987654321:ZYXwvuTSRQponmLKJihgFEDcba
AGENTROUTER__API_KEY_STAGING=sk-test-0987654321fedcba
```

## ⚡ Оптимизация и эксплуатация

### Мониторинг доступности

```python
# health_check.py
import asyncio
import aiohttp
import time
from datetime import datetime

async def check_bot_health():
    """Проверка здоровья бота"""
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Проверка Telegram API
            async with session.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
            ) as response:
                if response.status == 200:
                    telegram_status = "healthy"
                else:
                    telegram_status = "unhealthy"
            
            # Проверка AgentRouter
            async with session.post(
                "https://agentrouter.org/v1/chat/completions",
                headers={"Authorization": f"Bearer {AGENTROUTER_API_KEY}"},
                json={"model": "gpt-5", "messages": [{"role": "user", "content": "test"}]}
            ) as response:
                if response.status == 200:
                    agentrouter_status = "healthy"
                else:
                    agentrouter_status = "unhealthy"
            
            # Проверка MOEX API
            async with session.get(
                "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/GAZP.json"
            ) as response:
                if response.status == 200:
                    moex_status = "healthy"
                else:
                    moex_status = "unhealthy"
            
            response_time = time.time() - start_time
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy" if all([
                    telegram_status == "healthy",
                    agentrouter_status == "healthy",
                    moex_status == "healthy"
                ]) else "unhealthy",
                "response_time": response_time,
                "services": {
                    "telegram": telegram_status,
                    "agentrouter": agentrouter_status,
                    "moex": moex_status
                }
            }
    
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unhealthy",
            "error": str(e),
            "response_time": time.time() - start_time
        }

# Запуск мониторинга
async def monitor_health():
    while True:
        health = await check_bot_health()
        
        # Отправка алертов при проблемах
        if health["overall_status"] == "unhealthy":
            await send_alert(health)
        
        # Запись в метрики
        await record_metrics(health)
        
        await asyncio.sleep(60)  # Проверка каждую минуту
```

### Алерты для внешних сервисов

```python
# alerts.py
import smtplib
from email.mime.text import MimeText
from datetime import datetime

async def send_alert(health_data):
    """Отправка алерта о проблемах"""
    subject = f"🚨 Gazprom Bot Alert: {health_data['overall_status'].upper()}"
    
    message = f"""
    Alert Time: {health_data['timestamp']}
    Overall Status: {health_data['overall_status']}
    Response Time: {health_data.get('response_time', 'N/A')}s
    
    Service Status:
    - Telegram: {health_data.get('services', {}).get('telegram', 'unknown')}
    - AgentRouter: {health_data.get('services', {}).get('agentrouter', 'unknown')}
    - MOEX: {health_data.get('services', {}).get('moex', 'unknown')}
    
    Error: {health_data.get('error', 'N/A')}
    """
    
    # Отправка email
    await send_email(subject, message)
    
    # Отправка в Telegram
    await send_telegram_alert(message)
    
    # Отправка в Slack
    await send_slack_alert(message)

async def send_email(subject, message):
    """Отправка email алерта"""
    msg = MimeText(message)
    msg['Subject'] = subject
    msg['From'] = ALERT_EMAIL_FROM
    msg['To'] = ALERT_EMAIL_TO
    
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

async def send_telegram_alert(message):
    """Отправка алерта в Telegram"""
    # Использование отдельного бота для алертов
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ALERT_CHAT_ID,
                "text": f"🚨 {message}",
                "parse_mode": "HTML"
            }
        )
```

### Graceful Degradation

```python
# graceful_degradation.py
import asyncio
from typing import Optional
from gazprom_bot.ai.agentrouter_client import AgentRouterClient
from gazprom_bot.data.moex_client import MoexClient

class GracefulDegradationManager:
    """Менеджер graceful degradation"""
    
    def __init__(self):
        self.agentrouter_client = AgentRouterClient()
        self.moex_client = MoexClient()
        self.fallback_strategies = {}
        
    async def get_ai_recommendation(self, context: dict) -> Optional[dict]:
        """Получение AI-рекомендации с fallback"""
        try:
            # Основной источник: AgentRouter
            result = await self.agentrouter_client.get_trading_recommendation(
                system_prompt=SYSTEM_PROMPT,
                user_context=context
            )
            
            if result['success']:
                return result['data']
            
        except Exception as e:
            await self.log_error("AgentRouter failed", e)
        
        # Fallback 1: Кэшированные рекомендации
        cached_recommendation = await self.get_cached_recommendation(context)
        if cached_recommendation:
            return cached_recommendation
        
        # Fallback 2: Правила на основе технических индикаторов
        rule_based_recommendation = await self.get_rule_based_recommendation(context)
        if rule_based_recommendation:
            return rule_based_recommendation
        
        # Fallback 3: Консервативная рекомендация
        return {
            "action": "HOLD",
            "quantity": 0,
            "reasoning": "AI сервис недоступен, используется консервативная стратегия",
            "confidence": 50,
            "risk_level": "LOW"
        }
    
    async def get_market_data(self, ticker: str) -> Optional[dict]:
        """Получение рыночных данных с fallback"""
        try:
            # Основной источник: MOEX API
            data = await self.moex_client.get_market_data(ticker)
            if data:
                return data
                
        except Exception as e:
            await self.log_error("MOEX API failed", e)
        
        # Fallback 1: Альтернативные источники данных
        alternative_data = await self.get_alternative_market_data(ticker)
        if alternative_data:
            return alternative_data
        
        # Fallback 2: Кэшированные данные
        cached_data = await self.get_cached_market_data(ticker)
        if cached_data:
            return cached_data
        
        # Fallback 3: Данные по умолчанию
        return {
            "ticker": ticker,
            "price": 0.0,
            "status": "unavailable",
            "message": "Рыночные данные временно недоступны"
        }
    
    async def get_cached_recommendation(self, context: dict) -> Optional[dict]:
        """Получение кэшированной рекомендации"""
        # Реализация кэширования
        pass
    
    async def get_rule_based_recommendation(self, context: dict) -> Optional[dict]:
        """Рекомендация на основе правил"""
        # Простая логика на основе RSI
        rsi = context.get('technical_indicators', {}).get('rsi14')
        if rsi:
            if rsi < 30:
                return {
                    "action": "BUY",
                    "reasoning": f"RSI ({rsi}) указывает на перепроданность",
                    "confidence": 60,
                    "risk_level": "MEDIUM"
                }
            elif rsi > 70:
                return {
                    "action": "SELL",
                    "reasoning": f"RSI ({rsi}) указывает на перекупленность",
                    "confidence": 60,
                    "risk_level": "MEDIUM"
                }
        
        return None
    
    async def log_error(self, service: str, error: Exception):
        """Логирование ошибок degradation"""
        from gazprom_bot.monitoring.logger import get_monitoring_logger
        logger = get_monitoring_logger()
        logger.log_operation(
            'ERROR', 'graceful_degradation', 'service_failure',
            f"{service} failed: {str(error)}"
        )
```

## 📚 Документация и сопровождение

### Чек-лист код-ревью

```markdown
## Code Review Checklist

### Безопасность
- [ ] Отсутствуют токены/пароли в коде
- [ ] Валидация всех входных данных
- [ ] Использование параметризованных запросов к БД
- [ ] Правильная обработка ошибок без утечки информации

### Производительность
- [ ] Оптимизированы запросы к БД
- [ ] Используются кэширование где необходимо
- [ ] Нет блокирующих операций в async коде
- [ ] Лимиты на внешние API вызовы

### Тестирование
- [ ] Unit тесты для новой функциональности
- [ ] Интеграционные тесты для API
- [ ] E2E тесты для пользовательских сценариев
- [ ] Покрытие кода > 80%

### Документация
- [ ] Обновлен README.md
- [ ] Добавлены комментарии к сложному коду
- [ ] Обновлена API документация
- [ ] Добавлены примеры использования

### Мониторинг
- [ ] Добавлены логи для новых операций
- [ ] Настроены метрики производительности
- [ ] Добавлены алерты для критических ошибок
- [ ] Обновлен health check
```

### Инструкция для саппорта

```markdown
## Support Team Guide

### Частые проблемы

#### 1. Бот не отвечает
**Причины:**
- Отсутствует интернет-соединение
- Проблемы с Telegram API
- Критическая ошибка в приложении

**Диагностика:**
```bash
# Проверка статуса бота
curl https://api.telegram.org/bot{BOT_TOKEN}/getMe

# Проверка логов
tail -f logs/gazprom_bot.log | grep ERROR

# Проверка здоровья
python health_check.py
```

**Решение:**
1. Проверить статус Telegram API
2. Перезапустить сервис: `systemctl restart gazprom_bot`
3. Проверить логи ошибок

#### 2. Ошибки AgentRouter
**Причины:**
- Недостаточно кредитов
- Превышен лимит запросов
- Проблемы с API

**Диагностика:**
```bash
# Проверка баланса
curl -H "Authorization: Bearer {API_KEY}" https://agentrouter.org/v1/usage

# Проверка логов
grep "AgentRouter" logs/api.log | tail -10
```

**Решение:**
1. Пополнить баланс AgentRouter
2. Проверить лимиты API
3. Использовать fallback режим

#### 3. Проблемы с MOEX API
**Причины:**
- Вне времени работы биржи
- Технические проблемы на бирже
- Изменения в API

**Диагностика:**
```bash
# Проверка времени работы
curl https://iss.moex.com/iss/schedules/

# Проверка доступности тикера
curl https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/GAZP.json
```

**Решение:**
1. Проверить время работы биржи
2. Использовать кэшированные данные
3. Включить graceful degradation

### Восстановление после сбоя

1. **Остановка сервиса:**
```bash
systemctl stop gazprom_bot
```

2. **Резервное копирование:**
```bash
pg_dump gazprom_bot > backup_$(date +%Y%m%d_%H%M%S).sql
```

3. **Проверка целостности:**
```bash
python -c "
from gazprom_bot.database.database import get_database_manager
import asyncio
async def check():
    db = get_database_manager()
    await db.check_connection()
    print('Database OK')
asyncio.run(check())
"
```

4. **Запуск сервиса:**
```bash
systemctl start gazprom_bot
systemctl status gazprom_bot
```

### Контакты

- Telegram API: https://t.me/botfather
- AgentRouter Support: support@agentrouter.org
- MOEX Technical Support: +7 (495) 705-92-27
```

## 🔄 Адаптация и развитие

### Сбор метрик пользовательской активности

```python
# analytics.py
import asyncio
from datetime import datetime, timedelta
from gazprom_bot.database.database import get_database_manager

class AnalyticsCollector:
    """Сборщик аналитики"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    async def collect_user_activity(self, days: int = 7):
        """Сбор активности пользователей"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Активные пользователи
        active_users = await self.db_manager.execute_query("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM users
            WHERE last_active > %s
        """, (cutoff_date,))
        
        # Популярные команды
        popular_commands = await self.db_manager.execute_query("""
            SELECT command, COUNT(*) as usage_count
            FROM user_activity_log
            WHERE timestamp > %s
            GROUP BY command
            ORDER BY usage_count DESC
            LIMIT 10
        """, (cutoff_date,))
        
        # Точность рекомендаций
        recommendation_accuracy = await self.calculate_recommendation_accuracy(days)
        
        return {
            "active_users": active_users[0]['count'],
            "popular_commands": popular_commands,
            "recommendation_accuracy": recommendation_accuracy,
            "period_days": days
        }
    
    async def calculate_recommendation_accuracy(self, days: int):
        """Расчет точности рекомендаций"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Получение исполненных рекомендаций
        executed_recommendations = await self.db_manager.execute_query("""
            SELECT r.recommendation_json, t.action, t.price, t.timestamp
            FROM recommendations r
            JOIN transactions t ON r.id = t.recommendation_id
            WHERE r.timestamp > %s AND r.executed = true
        """, (cutoff_date,))
        
        # Расчет точности (упрощенный пример)
        correct_predictions = 0
        total_predictions = len(executed_recommendations)
        
        for rec in executed_recommendations:
            # Логика проверки правильности рекомендации
            # Сравнение предсказанного движения с фактическим
            pass
        
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        return {
            "accuracy_percent": accuracy,
            "total_recommendations": total_predictions,
            "correct_predictions": correct_predictions
        }
```

### Система обратной связи

```python
# feedback.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

class FeedbackCollector:
    """Сборщик обратной связи"""
    
    def __init__(self):
        self.feedback_data = {}
    
    def create_feedback_keyboard(self, recommendation_id: int):
        """Создание клавиатуры для обратной связи"""
        keyboard = [
            [
                InlineKeyboardButton("👍 Полезно", callback_data=f"feedback_good:{recommendation_id}"),
                InlineKeyboardButton("👎 Бесполезно", callback_data=f"feedback_bad:{recommendation_id}")
            ],
            [
                InlineKeyboardButton("💬 Комментарий", callback_data=f"feedback_comment:{recommendation_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обратной связи"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        parts = callback_data.split(':')
        
        if len(parts) < 2:
            return
        
        feedback_type = parts[0]
        recommendation_id = int(parts[1])
        
        # Сохранение обратной связи
        await self.save_feedback(
            recommendation_id=recommendation_id,
            user_id=update.effective_user.id,
            feedback_type=feedback_type,
            timestamp=datetime.now()
        )
        
        # Обновление сообщения
        if feedback_type == "feedback_good":
            await query.edit_message_text("Спасибо за обратную связь! 👍")
        elif feedback_type == "feedback_bad":
            await query.edit_message_text("Спасибо за обратную связь! Мы постараемся улучшить рекомендации.")
        elif feedback_type == "feedback_comment":
            await query.edit_message_text("Пожалуйста, напишите ваш комментарий...")
            # Здесь логика для сбора текстового комментария
    
    async def save_feedback(self, recommendation_id: int, user_id: int, 
                         feedback_type: str, timestamp: datetime):
        """Сохранение обратной связи в БД"""
        from gazprom_bot.database.database import get_database_manager
        
        db = get_database_manager()
        await db.execute_query("""
            INSERT INTO recommendation_feedback 
            (recommendation_id, user_id, feedback_type, timestamp)
            VALUES (%s, %s, %s, %s)
        """, (recommendation_id, user_id, feedback_type, timestamp))
    
    async def get_feedback_summary(self, days: int = 30):
        """Получение сводки обратной связи"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        from gazprom_bot.database.database import get_database_manager
        db = get_database_manager()
        
        feedback_stats = await db.execute_query("""
            SELECT feedback_type, COUNT(*) as count
            FROM recommendation_feedback
            WHERE timestamp > %s
            GROUP BY feedback_type
        """, (cutoff_date,))
        
        return {
            "period_days": days,
            "feedback_stats": feedback_stats,
            "total_feedback": sum(stat['count'] for stat in feedback_stats)
        }
```

### План переключения на бэкапные API

```python
# backup_apis.py
import asyncio
import aiohttp
from typing import Dict, Any, Optional

class BackupAPIManager:
    """Менеджер бэкапных API"""
    
    def __init__(self):
        self.primary_apis = {
            'moex': 'https://iss.moex.com/iss',
            'agentrouter': 'https://agentrouter.org/v1'
        }
        
        self.backup_apis = {
            'moex': [
                'https://backup-moex-api.example.com',
                'https://alternative-moex.example.com'
            ],
            'agentrouter': [
                'https://backup-agentrouter.example.com',
                'https://openai-api.example.com'  # Fallback на прямой OpenAI
            ]
        }
        
        self.current_api_status = {}
    
    async def get_market_data_with_fallback(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Получение рыночных данных с fallback на бэкапные API"""
        # Попытка основного API
        try:
            data = await self._try_primary_moex_api(ticker)
            if data:
                self.current_api_status['moex'] = 'primary'
                return data
        except Exception as e:
            await self._log_api_failure('moex', 'primary', e)
        
        # Попытка бэкапных API
        for backup_url in self.backup_apis['moex']:
            try:
                data = await self._try_backup_moex_api(backup_url, ticker)
                if data:
                    self.current_api_status['moex'] = f'backup_{backup_url}'
                    return data
            except Exception as e:
                await self._log_api_failure('moex', backup_url, e)
        
        # Все API недоступны
        self.current_api_status['moex'] = 'unavailable'
        return None
    
    async def get_ai_recommendation_with_fallback(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Получение AI-рекомендации с fallback"""
        # Попытка основного API
        try:
            result = await self._try_primary_agentrouter_api(context)
            if result:
                self.current_api_status['agentrouter'] = 'primary'
                return result
        except Exception as e:
            await self._log_api_failure('agentrouter', 'primary', e)
        
        # Попытка бэкапных API
        for backup_url in self.backup_apis['agentrouter']:
            try:
                result = await self._try_backup_agentrouter_api(backup_url, context)
                if result:
                    self.current_api_status['agentrouter'] = f'backup_{backup_url}'
                    return result
            except Exception as e:
                await self._log_api_failure('agentrouter', backup_url, e)
        
        # Все API недоступны
        self.current_api_status['agentrouter'] = 'unavailable'
        return None
    
    async def _try_primary_moex_api(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Попытка основного MOEX API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.primary_apis['moex']}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def _try_backup_moex_api(self, backup_url: str, ticker: str) -> Optional[Dict[str, Any]]:
        """Попытка бэкапного MOEX API"""
        # Реализация для конкретного бэкапного API
        pass
    
    async def _try_primary_agentrouter_api(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Попытка основного AgentRouter API"""
        # Использование основного клиента
        pass
    
    async def _try_backup_agentrouter_api(self, backup_url: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Попытка бэкапного AgentRouter API"""
        # Реализация для конкретного бэкапного API
        pass
    
    async def _log_api_failure(self, api_name: str, api_url: str, error: Exception):
        """Логирование отказа API"""
        from gazprom_bot.monitoring.logger import get_monitoring_logger
        logger = get_monitoring_logger()
        logger.log_operation(
            'ERROR', 'backup_apis', 'api_failure',
            f"{api_name} API failed: {api_url} - {str(error)}"
        )
    
    async def get_api_status(self) -> Dict[str, str]:
        """Получение текущего статуса API"""
        return self.current_api_status.copy()
```

## 📊 Заключение

Следование этим best practices обеспечит:
- **Надежность** системы в production
- **Быстрое обнаружение** и решение проблем
- **Масштабируемость** при росте пользовательской базы
- **Качество** предоставляемых рекомендаций
- **Безопасность** пользовательских данных и системы

Регулярное обновление документации и мониторинг метрик позволят поддерживать систему на высоком уровне производительности и надежности.