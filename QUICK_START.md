# Gazprom Trading Bot - Быстрый старт

🚀 **Запустите AI-бота для торговли акциями Газпрома за 5 минут**

## 🎯 Что это такое?

Gazprom Trading Bot - это Telegram бот, который использует GPT-5 для анализа рынка и генерации торговых рекомендаций по акциям ПАО "Газпром" (GAZP) на Московской бирже.

## ⚡ Быстрый запуск

### 1. Клонирование и установка

```bash
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Настройка API ключей

```bash
cp .env.example .env
```

Отредактируйте `.env` файл:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
AGENTROUTER_API_KEY=sk-ваш_api_ключ_от_agentrouter.org
```

### 3. Запуск бота

```bash
python run.py
```

## 📱 Основные команды

| Команда | Описание |
|---------|-----------|
| `/start` | Создать портфель |
| `/recommend` | Получить AI-рекомендацию |
| `/portfolio` | Посмотреть портфель |
| `/execute BUY 10` | Купить 10 акций |
| `/execute SELL 5` | Продать 5 акций |
| `/performance` | График доходности |

## 🎯 Пример работы

```
/recommend
```

**Ответ бота:**
```
📊 Рекомендация GPT-5

🎯 Действие: BUY
📦 Количество: 15 акций
💡 Уверенность: 85%
⚠️ Риск: MEDIUM

📝 Обоснование: Технические индикаторы показывают...
🛑 Stop-Loss: 165.50 RUB
🎁 Take-Profit: 185.00 RUB
```

## 🔧 Где взять API ключи?

### Telegram Bot Token
1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

### AgentRouter API Key
1. Зарегистрируйтесь на [agentrouter.org](https://agentrouter.org)
2. Перейдите в [Console → Tokens](https://agentrouter.org/console/token)
3. Создайте новый токен
4. Скопируйте ключ (начинается с `sk-`)

## 📊 Что делает бот?

- 🤖 **Анализирует рынок** с помощью GPT-5
- 📈 **Рассчитывает технические индикаторы** (RSI, MACD, MA)
- 💼 **Управляет портфелем** в симуляционном режиме
- 📊 **Создает графики** доходности
- 🔔 **Отправляет уведомления** о важных событиях

## ⚠️ Важно

- Все сделки выполняются в **симуляционном режиме**
- Бот использует **реальные рыночные данные** с MOEX
- Рекомендации не являются финансовой консультацией
- Торговля акциями сопряжена с риском потери капитала

## 🆘 Поддержка

- **Telegram**: @gazprom_bot_support
- **GitHub Issues**: [Сообщить о проблеме](https://github.com/your-repo/gazprom-trading-bot/issues)
- **Полная документация**: [README.md](README.md)

---

**🎉 Готово! Теперь у вас есть AI-ассистент для торговли акциями Газпрома!**