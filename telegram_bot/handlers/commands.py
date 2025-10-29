"""
Обработчики команд Telegram бота.

Реализует:
- Основные команды бота
- Обработку пользовательского ввода
- Валидацию параметров
- Форматирование ответов
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from telegram import Update as TelegramUpdate, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ContextTypes, CommandHandler

from config import settings
from portfolio.manager import PortfolioManager
from ai.agentrouter_client import AgentRouterClient
from monitoring.logger import get_logger


logger = logging.getLogger(__name__)


async def start_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        logger.info(f"User {username} ({user_id}) started bot")
        
        # Создание портфеля для нового пользователя
        portfolio_manager = PortfolioManager()
        
        # Проверка существования пользователя
        existing_user = await portfolio_manager.get_user(user_id)
        
        if existing_user:
            message = f"""
👋 Добро пожаловать обратно, {username}!

Ваш портфель уже создан. Используйте /portfolio для просмотра текущего состояния.

Доступные команды:
/portfolio - просмотр портфеля
/recommend - получить рекомендацию
/help - справка
            """
        else:
            # Создание нового пользователя и портфеля
            user = await portfolio_manager.create_user(
                user_id=user_id,
                username=username,
                initial_capital=100000.0  # 100k RUB по умолчанию
            )
            
            if user:
                message = f"""
🎉 Добро пожаловать в Gazprom Trading Bot, {username}!

Ваш портфель успешно создан:
💰 Начальный капитал: 100,000 RUB
📊 Статус: Активен

Доступные команды:
/portfolio - просмотр портфеля
/recommend - получить AI-рекомендацию
/balance - текущий баланс
/help - все команды

⚠️ Важно: Все сделки симуляционные и не приводят к реальным финансовым операциям.
                """
            else:
                message = f"""
❌ Ошибка при создании портфеля

Пожалуйста, попробуйте еще раз или обратитесь в поддержку.
                """
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")


async def portfolio_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /portfolio"""
    try:
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested portfolio")
        
        portfolio_manager = PortfolioManager()
        
        # Получение портфеля пользователя
        portfolio = await portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получение портфеля
        portfolio = await portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получение позиций
        positions = await portfolio_manager.get_positions(portfolio.id)
        
        # Формирование сообщения
        # Получение сводки портфеля
        portfolio_summary = await portfolio_manager.get_portfolio_summary(user_id)
        
        message = f"""
📊 <b>Ваш портфель</b>

💰 <b>Общая стоимость:</b> {portfolio_summary.get('total_value', 0):,.0f} RUB
💵 <b>Доступно средств:</b> {portfolio_summary.get('cash', 0):,.0f} RUB
📈 <b>P&L:</b> {portfolio_summary.get('pnl', 0):,.0f} RUB ({portfolio_summary.get('pnl_percent', 0):+.2f}%)

<b>Позиции:</b>
        """
        
        if positions:
            for position in positions:
                pnl_sign = "📈" if position.unrealized_pnl >= 0 else "📉"
                message += f"""
{position.ticker}: {position.shares} шт. по {position.avg_purchase_price:.2f} RUB
Текущая цена: {position.current_price:.2f} RUB
P&L: {pnl_sign} {position.unrealized_pnl:.0f} RUB ({position.pnl_percent:+.2f}%)
                """
        else:
            message += "\n📭 Позиций нет"
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in portfolio_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении портфеля")


async def recommend_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /recommend"""
    try:
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested recommendation")
        
        # Отправка сообщения о начале анализа
        await update.message.reply_text(
            "🤖 Анализирую рынок и ваш портфель... Это может занять до 15 секунд.",
            parse_mode=ParseMode.HTML
        )
        
        # Получение данных для анализа
        portfolio_manager = PortfolioManager()
        ai_client = AgentRouterClient(settings.AGENTROUTER_API_KEY)
        
        # Получение портфеля
        portfolio = await portfolio_manager.get_portfolio(user_id)
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получение рыночных данных
        # В реальном коде здесь нужно получить данные от MOEX
        market_data = {"current_price": 0.0}  # Заглушка
        technical_indicators = {}  # Заглушка
        
        # Получение сводки портфеля
        portfolio_summary = await portfolio_manager.get_portfolio_summary(user_id)
        
        # Формирование контекста для AI
        ai_context = {
            "portfolio": portfolio_summary,
            "market_data": market_data,
            "technical_indicators": technical_indicators,
            "timestamp": datetime.now().isoformat()
        }
        
        # Получение рекомендации от GPT-5
        system_prompt = _get_system_prompt()
        result = await ai_client.get_trading_recommendation(ai_context)
        
        if result["success"]:
            recommendation = result["data"]
            
            # Сохранение рекомендации в БД
            await portfolio_manager.save_recommendation(
                user_id=user_id,
                recommendation=recommendation
            )
            
            # Формирование сообщения с рекомендацией
            action_emoji = "🟢" if recommendation["action"] == "BUY" else "🔴" if recommendation["action"] == "SELL" else "🟡"
            action_text = {
                "BUY": "ПОКУПКА",
                "SELL": "ПРОДАЖА", 
                "HOLD": "УДЕРЖАНИЕ"
            }.get(recommendation["action"], recommendation["action"])
            
            message = f"""
{action_emoji} <b>Рекомендация GPT-5</b>

🎯 <b>Действие:</b> {action_text}
📦 <b>Количество:</b> {recommendation.get('quantity', 'N/A')} акций
💡 <b>Уверенность:</b> {recommendation.get('confidence', 0)}%
⚠️ <b>Риск:</b> {recommendation.get('risk_level', 'UNKNOWN')}

📝 <b>Обоснование:</b>
{recommendation.get('reasoning', 'Анализ недоступен')}

🛑 <b>Stop-Loss:</b> {recommendation.get('stop_loss', 'N/A')} RUB
🎁 <b>Take-Profit:</b> {recommendation.get('take_profit', 'N/A')} RUB

⏱️ <b>Время анализа:</b> {result.get('execution_time', 0):.2f}s
🔋 <b>Токенов использовано:</b> {result.get('tokens_used', 0)}

Используйте /execute для исполнения сделки.
            """
            
            # Создание клавиатуры для быстрых действий
            if recommendation["action"] in ["BUY", "SELL"]:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"✅ Исполнить {action_text}",
                            callback_data=f"execute_recommendation:{recommendation['action']}:{recommendation.get('quantity', 0)}"
                        ),
                        InlineKeyboardButton(
                            "❌ Отклонить",
                            callback_data="reject_recommendation"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                reply_markup = None
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            error_message = f"""
❌ <b>Ошибка при получении рекомендации</b>

🔍 <b>Причина:</b> {result.get('error', 'Неизвестная ошибка')}

🔄 Попробуйте еще раз через несколько минут.
            """
            
            await update.message.reply_text(error_message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in recommend_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении рекомендации")


async def execute_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /execute"""
    try:
        user_id = update.effective_user.id
        
        # Парсинг аргументов команды
        args = context.args if context.args else []
        
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: /execute [BUY/SELL] [количество]",
                parse_mode=ParseMode.HTML
            )
            return
        
        action = args[0].upper()
        quantity = args[1]
        
        # Валидация параметров
        if action not in ["BUY", "SELL"]:
            await update.message.reply_text(
                "❌ Неверное действие. Используйте BUY или SELL.",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            await update.message.reply_text(
                "❌ Неверное количество. Используйте положительное число.",
                parse_mode=ParseMode.HTML
            )
            return
        
        logger.info(f"User {user_id} wants to {action} {quantity} shares")
        
        # Получение портфеля
        portfolio_manager = PortfolioManager()
        portfolio = await portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Исполнение сделки через менеджер портфеля
        # Сначала получаем текущую цену
        # В реальном коде здесь нужно получить цену от MOEX
        current_price = 300.0  # Заглушка
        
        result = await portfolio_manager.execute_trade(
            user_id=user_id,
            action=action,
            ticker="GAZP",
            quantity=quantity,
            price=current_price,
            reason=f"Manual execution via /execute command"
        )
        
        # Формируем результат в ожидаемом формате
        if result:
            result_dict = {
                "success": True,
                "executed_shares": quantity,
                "executed_price": current_price,
                "commission": quantity * current_price * 0.0003,
                "net_amount": quantity * current_price * (1 + 0.0003)
            }
        else:
            result_dict = {
                "success": False,
                "error": "Ошибка при исполнении сделки"
            }
        
        if result_dict["success"]:
            result = result_dict
            message = f"""
✅ <b>Сделка исполнена успешно!</b>

📈 <b>Инструмент:</b> GAZP
💰 <b>Действие:</b> {action}
📦 <b>Количество:</b> {result['executed_shares']} акций
💵 <b>Цена:</b> {result['executed_price']:.2f} RUB
💸 <b>Комиссия:</b> {result['commission']:.2f} RUB
💳 <b>Итого:</b> {result['net_amount']:,.0f} RUB

🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
            """
        else:
            result = result_dict
            message = f"""
❌ <b>Ошибка при исполнении сделки</b>

📈 <b>Инструмент:</b> GAZP
💰 <b>Действие:</b> {action}
📦 <b>Количество:</b> {quantity} шт.

🚨 <b>Ошибка:</b> {result['error']}
            """
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in execute_command: {e}")
        await update.message.reply_text("❌ Ошибка при исполнении сделки")


async def balance_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /balance"""
    try:
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested balance")
        
        portfolio_manager = PortfolioManager()
        portfolio = await portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получение сводки портфеля
        portfolio_summary = await portfolio_manager.get_portfolio_summary(user_id)
        
        message = f"""
💰 <b>Баланс портфеля</b>

💵 <b>Доступно средств:</b> {portfolio_summary.get('cash', 0):,.0f} RUB
📊 <b>Общая стоимость:</b> {portfolio_summary.get('total_value', 0):,.0f} RUB
📈 <b>Общий P&L:</b> {portfolio_summary.get('pnl', 0):,.0f} RUB ({portfolio_summary.get('pnl_percent', 0):+.2f}%)

🔄 <b>Обновлено:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        """
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in balance_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении баланса")


async def history_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history"""
    try:
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested history")
        
        portfolio_manager = PortfolioManager()
        portfolio = await portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            await update.message.reply_text(
                "❌ Портфель не найден. Используйте /start для создания.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Получение истории транзакций
        transactions = await portfolio_manager.get_transaction_history(
            user_id=user_id,
            limit=10
        )
        
        if not transactions:
            message = "📭 <b>История транзакций пуста</b>"
        else:
            message = "📜 <b>Последние транзакции:</b>\n\n"
            
            for tx in transactions:
                action_emoji = "🟢" if tx.action == "BUY" else "🔴"
                message += f"""
{action_emoji} <b>{tx.action}</b> {tx.shares} шт. по {tx.price:.2f} RUB
💰 Сумма: {tx.total_amount:,.0f} RUB
📅 Дата: {tx.timestamp.strftime('%d.%m.%Y %H:%M')}
                """
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in history_command: {e}")
        await update.message.reply_text("❌ Ошибка при получении истории")


async def performance_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /performance"""
    try:
        user_id = update.effective_user.id
        
        logger.info(f"User {user_id} requested performance")
        
        portfolio_manager = PortfolioManager()
        
        # Получение производительности портфеля
        performance = await portfolio_manager.get_performance_metrics(
            user_id=user_id,
            days=30
        )
        
        if not performance:
            await update.message.reply_text(
                "❌ Недостаточно данных для анализа производительности.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # TODO: Реализовать генерацию графиков
        await update.message.reply_text(
            "📈 <b>Функция графиков временно недоступна</b>\n\n"
            "Мы работаем над восстановлением этой функции.",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Error in performance_command: {e}")
        await update.message.reply_text("❌ Ошибка при построении графика")


async def help_command(update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    try:
        message = """
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
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке справки")


def _get_system_prompt() -> str:
    """Получение системного промпта для GPT-5"""
    return """
Ты — портфельный менеджер, специализирующийся на торговле акциями 
ПАО "Газпром" (GAZP) на Московской бирже.

ПРАВИЛА ТОРГОВЛИ:
1. Максимальный размер одной позиции: 30% от капитала
2. Стоп-лосс: обязателен при любой покупке (-5% от цены входа)
3. Тейк-профит: минимум +10% от цены входа
4. Не торговать в первые/последние 15 минут торговой сессии
5. Учитывать геополитические риски и новости о компании

ФОРМАТ ОТВЕТА:
Дай рекомендацию в формате JSON:
{
  "action": "BUY/SELL/HOLD",
  "quantity": <количество акций>,
  "reasoning": "<обоснование решения>",
  "stop_loss": <цена стоп-лосса>,
  "take_profit": <цена тейк-профита>,
  "risk_level": "LOW/MEDIUM/HIGH",
  "confidence": <0-100>
}
    """


def register_command_handlers(application):
    """Регистрация обработчиков команд"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CommandHandler("execute", execute_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("performance", performance_command))
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Command handlers registered")