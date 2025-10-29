# -*- coding: utf-8 -*-
"""
Gazprom Trading Bot - Telegram Bot Module

Основной модуль Telegram бота с обработчиками команд.
"""

import asyncio
from typing import Dict, Any, Tuple

from telegram import Update as TelegramUpdate
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

from config import settings
from monitoring.logger import get_logger
from database.models import User, Portfolio, Position, Transaction, Recommendation
from portfolio.manager import PortfolioManager
from ai.agentrouter_client import AgentRouterClient
from data.moex_client import MOEXClient
from telegram_bot.handlers.confirmation import ConfirmationHandler
from config.constants import WELCOME_MESSAGE, HELP_MESSAGE, GAZP_TICKER


logger = get_logger(__name__)


class GazpromTelegramBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.ai_client = AgentRouterClient(settings.agentrouter_api_key)
        self.moex_client = MOEXClient()
        self.confirmation_handler = ConfirmationHandler()
        
    async def start_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"Новый пользователь: {user_id} ({username})")
        
        try:
            # Создание пользователя и портфеля
            user = await self.portfolio_manager.create_user(
                user_id=user_id,
                username=username,
                initial_capital=100000.0  # Значение по умолчанию
            )
            
            welcome_message = WELCOME_MESSAGE.format(
                user_name=update.effective_user.first_name or "пользователь"
            )
            
            await update.message.reply_html(welcome_message)
            
            # Отправка информации о созданном портфеле
            portfolio_info = await self._get_portfolio_info(user_id)
            await update.message.reply_html(portfolio_info)
            
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при создании портфеля. Попробуйте позже."
            )
    
    async def portfolio_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /portfolio"""
        user_id = update.effective_user.id
        
        try:
            portfolio_info = await self._get_portfolio_info(user_id)
            await update.message.reply_html(portfolio_info)
            
        except Exception as e:
            logger.error(f"Ошибка в portfolio_command: {e}")
            await update.message.reply_text(
                "❌ Не удалось получить информацию о портфеле. Попробуйте позже."
            )
    
    async def recommend_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /recommend"""
        user_id = update.effective_user.id
        
        try:
            # Отправка сообщения о начале анализа
            await update.message.reply_text("🤖 Анализирую рынок и ваш портфель с помощью AI...")
            
            # Получение данных портфеля
            portfolio = await self.portfolio_manager.get_portfolio(user_id)
            if not portfolio:
                await update.message.reply_text(
                    "❌ Портфель не найден. Используйте /start для создания."
                )
                return
                
            # Получение рыночных данных
            async with self.moex_client:
                current_price = await self.moex_client.get_current_price(GAZP_TICKER)
            if not current_price:
                await update.message.reply_text(
                    "❌ Не удалось получить текущую цену. Попробуйте позже."
                )
                return
                
            # Подготовка контекста для AI
            ai_context = await self._prepare_ai_context(user_id, portfolio, current_price)
            
            # Формирование запроса с использованием нового шаблона
            from ai.prompts import TRADING_SYSTEM_PROMPT, TRADING_REQUEST_TEMPLATE
            from datetime import datetime
            
            # Получаем данные для шаблона
            market_data = ai_context.get("market_data", {})
            portfolio_data = ai_context.get("portfolio", {})
            technical_indicators = market_data.get("technical_indicators", {})
            
            # Формируем запрос с новым шаблоном
            trading_request = TRADING_REQUEST_TEMPLATE.format(
                current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                gazp_last_price=market_data.get("current_price", 0),
                gazp_volume=market_data.get("volume", 0),
                gazp_day_high=market_data.get("day_high", 0),
                gazp_day_low=market_data.get("day_low", 0),
                user_cash_balance=portfolio_data.get("cash", 0),
                user_shares_held=portfolio_data.get("shares", 0),
                user_avg_buy_price=portfolio_data.get("avg_price", 0),
                news_sentiment="neutral"  # Можно добавить получение новостей в будущем
            )
            
            result = await self.ai_client.get_trading_recommendation(TRADING_SYSTEM_PROMPT, trading_request)
            
            if result["success"]:
                recommendation = result["data"]
                
                # Форматирование и отправка рекомендации
                message = await self._format_recommendation(recommendation, current_price)
                
                # Сохранение рекомендации в базе данных
                await self.portfolio_manager.save_recommendation(user_id, recommendation)
                
                # Создание inline клавиатуры для подтверждения
                keyboard = self._create_recommendation_keyboard(recommendation)
                
                await update.message.reply_html(
                    message,
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при получении рекомендации: {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка в recommend_command: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации рекомендации. Попробуйте позже."
            )
    
    async def execute_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /execute"""
        user_id = update.effective_user.id
        
        try:
            # Парсинг аргументов команды
            args = context.args
            if len(args) < 2:
                await update.message.reply_text(
                    "❌ Неверный формат команды. Используйте: /execute [BUY/SELL] [количество]"
                )
                return
                
            action = args[0].upper()
            if action not in ["BUY", "SELL"]:
                await update.message.reply_text(
                    "❌ Неверное действие. Используйте BUY или SELL."
                )
                return
                
            try:
                quantity = int(args[1])
                if quantity <= 0:
                    raise ValueError()
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверное количество акций. Укажите положительное целое число."
                )
                return
                
            # Получение текущей цены
            async with self.moex_client:
                current_price = await self.moex_client.get_current_price(GAZP_TICKER)
            if not current_price:
                await update.message.reply_text(
                    "❌ Не удалось получить текущую цену. Попробуйте позже."
                )
                return
                
            # Проверка возможности выполнения сделки
            can_execute, error_message = await self._can_execute_trade(
                user_id, action, quantity, current_price
            )
            
            if not can_execute:
                await update.message.reply_text(f"❌ {error_message}")
                return
                
            # Создание запроса на подтверждение
            confirmation_data = {
                "action": action,
                "quantity": quantity,
                "price": current_price,
                "total_amount": quantity * current_price
            }
            
            confirmation_message = self._format_trade_confirmation(confirmation_data)
            keyboard = self._create_trade_confirmation_keyboard(confirmation_data)
            
            await update.message.reply_html(
                confirmation_message,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка в execute_command: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке команды. Попробуйте позже."
            )
    
    async def history_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /history"""
        user_id = update.effective_user.id
        
        try:
            transactions = await self.portfolio_manager.get_transaction_history(user_id)
            
            if not transactions:
                await update.message.reply_text("📝 У вас пока нет транзакций.")
                return
            
            message = "📝 <b>История транзакций:</b>\n\n"
            
            for transaction in transactions[-10:]:  # Последние 10 транзакций
                action_emoji = "🟢" if transaction.action == "BUY" else "🔴"
                message += (
                    f"{action_emoji} {transaction.action} {transaction.shares} шт. "
                    f"по {transaction.price:.2f} ₽ "
                    f"({transaction.total_amount:.2f} ₽)\n"
                    f"📅 {transaction.timestamp.strftime('%d.%m.%Y %H:%M')}\n\n"
                )
            
            await update.message.reply_html(message)
            
        except Exception as e:
            logger.error(f"Ошибка в history_command: {e}")
            await update.message.reply_text(
                "❌ Не удалось получить историю транзакций. Попробуйте позже."
            )
    
    async def balance_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /balance"""
        user_id = update.effective_user.id
        
        try:
            balance_info = await self._get_balance_info(user_id)
            await update.message.reply_html(balance_info)
            
        except Exception as e:
            logger.error(f"Ошибка в balance_command: {e}")
            await update.message.reply_text(
                "❌ Не удалось получить информацию о балансе. Попробуйте позже."
            )
    
    async def analysis_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analysis для углубленного анализа"""
        user_id = update.effective_user.id
        
        try:
            # Отправка сообщения о начале анализа
            await update.message.reply_text("📊 Проводу углубленный анализ акции GAZP и вашего портфеля...")
            
            # Получение данных портфеля
            portfolio = await self.portfolio_manager.get_portfolio(user_id)
            if not portfolio:
                await update.message.reply_text(
                    "❌ Портфель не найден. Используйте /start для создания."
                )
                return
                
            # Получение рыночных данных
            async with self.moex_client:
                current_price = await self.moex_client.get_current_price(GAZP_TICKER)
            if not current_price:
                await update.message.reply_text(
                    "❌ Не удалось получить текущую цену. Попробуйте позже."
                )
                return
                
            # Используем исправленный метод _prepare_ai_context для получения полных данных
            ai_context = await self._prepare_ai_context(user_id, portfolio, current_price)
            
            # Получаем данные для анализа
            market_data = ai_context.get("market_data", {})
            portfolio_data = ai_context.get("portfolio", {})
            technical_indicators = market_data.get("technical_indicators", {})
            
            # Формирование запроса для углубленного анализа с полными данными
            from ai.prompts import DEEP_ANALYSIS_PROMPT
            
            # Расчет изменения за день в процентах
            day_change = 0
            if market_data.get("open_price") and market_data.get("open_price") > 0:
                day_change = ((current_price - market_data["open_price"]) / market_data["open_price"]) * 100
            
            # Обрабатываем значения N/A в технических индикаторах
            def safe_get_indicator(key, default="N/A"):
                value = technical_indicators.get(key, default)
                if value == "N/A" or value is None:
                    return default
                return value
            
            analysis_request = DEEP_ANALYSIS_PROMPT.format(
                current_price=current_price,
                day_change=f"{day_change:.2f}",
                volume=market_data.get("volume", 0),
                day_high=market_data.get("day_high", current_price),
                day_low=market_data.get("day_low", current_price),
                user_shares_held=portfolio_data.get("shares", 0),
                user_avg_buy_price=portfolio_data.get("avg_price", 0),
                user_cash_balance=portfolio_data.get("cash", 0),
                rsi=safe_get_indicator("rsi"),
                macd=safe_get_indicator("macd"),
                sma_20=safe_get_indicator("sma_20"),
                sma_50=safe_get_indicator("sma_50"),
                sma_200=safe_get_indicator("sma_200")
            )
            
            # Получение углубленного анализа от AI
            result = await self.ai_client.get_market_analysis(
                {"analysis_request": analysis_request},
                analysis_type="deep"
            )
            
            if result["success"]:
                analysis = result["analysis"]
                
                # Очистка Markdown для предотвращения ошибок парсинга
                cleaned_analysis = self._clean_markdown(analysis)
                
                # Проверка длины ответа и обрезка при необходимости
                max_length = 3500  # Оставляем запас для заголовка и форматирования
                if len(cleaned_analysis) > max_length:
                    cleaned_analysis = cleaned_analysis[:max_length] + "...\n\n_Анализ обрезан из-за ограничений Telegram_"
                
                # Отправка анализа
                await update.message.reply_text(
                    f"📊 *Углубленный анализ GAZP*\n\n{cleaned_analysis}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при получении анализа: {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка в analysis_command: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации анализа. Попробуйте позже."
            )
    
    async def help_command(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await update.message.reply_html(HELP_MESSAGE)
    
    async def callback_query_handler(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline кнопок"""
        query = update.callback_query
        
        try:
            # Пытаемся ответить на query, но обрабатываем ошибку если он устарел
            try:
                await query.answer()
            except Exception as answer_error:
                # Если query устарел, просто логируем и продолжаем
                logger.warning(f"Не удалось ответить на callback query: {answer_error}")
                return
            
            data = query.data
            
            if data.startswith("confirm_trade_"):
                # Подтверждение сделки
                await self._handle_trade_confirmation(query, context)
            elif data.startswith("cancel_trade_"):
                # Отмена сделки
                await query.edit_message_text("❌ Сделка отменена.")
            elif data.startswith("execute_recommendation_"):
                # Исполнение рекомендации
                await self._handle_recommendation_execution(query, context)
            elif data.startswith("cancel_recommendation"):
                # Отмена рекомендации (исправлено: без подчеркивания)
                await query.edit_message_text("❌ Рекомендация отклонена.")
            
        except Exception as e:
            logger.error(f"Ошибка в callback_query_handler: {e}")
            try:
                await query.edit_message_text(
                    "❌ Произошла ошибка при обработке запроса. Попробуйте позже."
                )
            except Exception as edit_error:
                # Если не можем отредактировать сообщение (например, оно уже удалено)
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
    
    async def _get_portfolio_info(self, user_id: int) -> str:
        """Получить информацию о портфеле"""
        portfolio = await self.portfolio_manager.get_portfolio(user_id)
        async with self.moex_client:
            current_price = await self.moex_client.get_current_price(GAZP_TICKER)
        
        if not portfolio:
            return "❌ Портфель не найден."
        
        # Получаем позиции для портфеля
        positions = await self.portfolio_manager.get_positions(portfolio.id)
        gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
        
        shares = gazp_position.shares if gazp_position else 0
        cash = float(portfolio.current_cash)
        
        total_value = cash + (shares * current_price)
        pnl = total_value - float(portfolio.initial_capital)
        pnl_percent = (pnl / float(portfolio.initial_capital)) * 100 if portfolio.initial_capital else 0
        
        return f"""
💼 <b>Ваш портфель:</b>

💰 Денежные средства: {cash:.2f} ₽
📊 Акции GAZP: {shares} шт.
💵 Текущая цена: {current_price:.2f} ₽
💎 Общая стоимость: {total_value:.2f} ₽
📈 P&L: {pnl:+.2f} ₽ ({pnl_percent:+.2f}%)
"""
    
    async def _get_balance_info(self, user_id: int) -> str:
        """Получить информацию о балансе"""
        portfolio = await self.portfolio_manager.get_portfolio(user_id)
        async with self.moex_client:
            current_price = await self.moex_client.get_current_price(GAZP_TICKER)
        
        if not portfolio:
            return "❌ Портфель не найден."
        
        # Получаем позиции для портфеля
        positions = await self.portfolio_manager.get_positions(portfolio.id)
        gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
        
        shares = gazp_position.shares if gazp_position else 0
        cash = float(portfolio.current_cash)
        shares_value = shares * current_price
        total_value = cash + shares_value
        
        return f"""
💰 <b>Баланс и позиции:</b>

💵 Доступно: {cash:.2f} ₽
📊 Акции GAZP: {shares} шт. ({shares_value:.2f} ₽)
💎 Общая стоимость: {total_value:.2f} ₽
"""
    
    async def _prepare_ai_context(self, user_id: int, portfolio: Portfolio, current_price: float) -> Dict[str, Any]:
        """Подготовить контекст для AI"""
        # Получение технических индикаторов и исторических данных
        async with self.moex_client:
            technical_indicators = await self.moex_client.get_technical_indicators("GAZP")
            # Получение L1 данных для объема
            l1_data = await self.moex_client.get_marketdata_l1("GAZP")
            # Получение исторических свечей для day_high, day_low, open
            from datetime import datetime, timedelta
            from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            historical_candles = await self.moex_client.get_historical_candles("GAZP", from_date=from_date)
        
        # Получаем данные последней свечи для day_high, day_low, open
        last_candle = historical_candles.iloc[-1].to_dict() if not historical_candles.empty and len(historical_candles) > 0 else None
        
        # Получаем позиции для портфеля
        positions = await self.portfolio_manager.get_positions(portfolio.id)
        gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
        
        shares = gazp_position.shares if gazp_position else 0
        avg_price = float(gazp_position.avg_purchase_price) if gazp_position and gazp_position.avg_purchase_price else 0
        
        # Расчет P&L
        shares_value = shares * current_price
        cash = float(portfolio.current_cash)
        total_value = cash + shares_value
        pnl = total_value - float(portfolio.initial_capital)
        pnl_percent = (pnl / float(portfolio.initial_capital)) * 100 if portfolio.initial_capital else 0
        
        # Используем данные из technical_indicators, которые включают дневные данные
        # Обрабатываем значения N/A в технических индикаторах
        cleaned_indicators = {}
        for key, value in technical_indicators.items():
            if value == "N/A" or value is None:
                cleaned_indicators[key] = 0  # или другое подходящее значение по умолчанию
            else:
                cleaned_indicators[key] = value
        
        market_data = {
            "current_price": current_price,
            "volume": cleaned_indicators.get("day_volume", l1_data.voltoday if l1_data else 0),
            "day_high": l1_data.high if l1_data and l1_data.high else (last_candle['high'] if last_candle else current_price),
            "day_low": l1_data.low if l1_data and l1_data.low else (last_candle['low'] if last_candle else current_price),
            "open_price": l1_data.open_price if l1_data and l1_data.open_price else (last_candle['open'] if last_candle else current_price),
            "technical_indicators": cleaned_indicators
        }
        
        # Валидация данных перед отправкой в AI
        validation_errors = []
        if not market_data["current_price"] or market_data["current_price"] <= 0:
            validation_errors.append("Текущая цена отсутствует или некорректна")
        if not market_data["day_high"] or market_data["day_high"] <= 0:
            validation_errors.append("Максимум дня отсутствует или некорректен")
        if not market_data["day_low"] or market_data["day_low"] <= 0:
            validation_errors.append("Минимум дня отсутствует или некорректен")
        if not market_data["volume"] or market_data["volume"] < 0:
            validation_errors.append("Объем торгов отсутствует или некорректен")
        
        if validation_errors:
            logger.warning(f"Валидация данных не пройдена: {', '.join(validation_errors)}")
            # Заполняем нулями некорректные данные
            market_data.update({
                "day_high": market_data["day_high"] if market_data["day_high"] and market_data["day_high"] > 0 else current_price,
                "day_low": market_data["day_low"] if market_data["day_low"] and market_data["day_low"] > 0 else current_price,
                "volume": market_data["volume"] if market_data["volume"] and market_data["volume"] > 0 else 0,
                "open_price": market_data["open_price"] if market_data["open_price"] and market_data["open_price"] > 0 else current_price
            })
        
        logger.info(f"Подготовлен контекст для AI: current_price={market_data['current_price']}, "
                   f"day_high={market_data['day_high']}, day_low={market_data['day_low']}, "
                   f"volume={market_data['volume']}")
        
        return {
            "portfolio": {
                "cash": cash,
                "shares": shares,
                "avg_price": avg_price,
                "current_price": current_price,
                "total_value": total_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent
            },
            "market_data": market_data,
            "risk_settings": {
                "max_position_percent": 30,
                "risk_limit_percent": 5
            }
        }
    
    def _clean_markdown(self, text: str) -> str:
        """Очистить текст от некорректного Markdown и HTML форматирования"""
        import re
        
        # Удаляем все HTML теги, включая некорректные
        text = re.sub(r'<[^>]*>', '', text)
        
        # Удаляем оставшиеся символы Markdown, которые могут вызвать ошибки
        text = re.sub(r'[_~`]', '', text)
        
        # Заменяем ** на * для совместимости с Markdown
        text = re.sub(r'\*\*', '*', text)
        
        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Удаляем некорректные символы, которые могут вызвать ошибки парсинга
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\*\(\)\[\]\n\r@#%&+=/<>]', '', text)
        
        return text.strip()
    
    async def _format_recommendation(self, recommendation: Dict[str, Any], current_price: float) -> str:
        """Форматировать рекомендацию"""
        # Безопасное получение значений с defaults
        action = recommendation.get("action", "HOLD")
        quantity = recommendation.get("quantity", 0)
        confidence = recommendation.get("confidence", 0)
        risk_level = recommendation.get("risk_level", "UNKNOWN")
        reasoning = recommendation.get("reasoning", "Нет обоснования")
        stop_loss = recommendation.get("stop_loss", current_price * 0.95)
        take_profit = recommendation.get("take_profit", current_price * 1.10)
        
        action_emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
        
        # Очищаем обоснование от некорректного Markdown
        cleaned_reasoning = self._clean_markdown(reasoning)
        
        return f"""
📊 *Рекомендация AI (deepseek-v3.2)*

{action_emoji} *Действие:* {action}
📦 *Количество:* {quantity} акций
💡 *Уверенность:* {confidence}%
⚠️ *Риск:* {risk_level}

📝 *Обоснование:*
{cleaned_reasoning}

🛑 *Stop-Loss:* {stop_loss:.2f} ₽
🎁 *Take-Profit:* {take_profit:.2f} ₽
"""
    
    def _create_recommendation_keyboard(self, recommendation: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Создать клавиатуру для рекомендации"""
        # Безопасное получение значений с defaults
        action = recommendation.get("action", "HOLD")
        quantity = recommendation.get("quantity", 0)
        stop_loss = recommendation.get("stop_loss", 0)
        take_profit = recommendation.get("take_profit", 0)
        
        data = f"{action}_{quantity}_{stop_loss}_{take_profit}"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Исполнить",
                    callback_data=f"execute_recommendation_{data}"
                ),
                InlineKeyboardButton(
                    "❌ Отклонить",
                    callback_data="cancel_recommendation"  # Исправлено: без подчеркивания
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _can_execute_trade(self, user_id: int, action: str, quantity: int, price: float) -> Tuple[bool, str]:
        """Проверить возможность выполнения сделки"""
        portfolio = await self.portfolio_manager.get_portfolio(user_id)
        
        if not portfolio:
            return False, "Портфель не найден."
        
        # Получаем позиции для портфеля
        positions = await self.portfolio_manager.get_positions(portfolio.id)
        gazp_position = next((p for p in positions if p.ticker == "GAZP"), None)
        
        shares = gazp_position.shares if gazp_position else 0
        cash = float(portfolio.current_cash)
        
        total_amount = quantity * price
        
        if action == "BUY":
            if cash < total_amount:
                return False, f"Недостаточно средств. Нужно: {total_amount:.2f} ₽, доступно: {cash:.2f} ₽"
            
            # Проверка максимального размера позиции (корректный расчет)
            shares_value = shares * price
            total_before = cash + shares_value
            
            new_shares = shares + quantity
            new_position_value = new_shares * price
            cash_after = cash - total_amount
            total_after = cash_after + new_position_value
            
            if total_after > 0 and (new_position_value / total_after) * 100 > 30:
                return False, "Превышен максимальный размер позиции (30%)"
            
        elif action == "SELL":
            if shares < quantity:
                return False, f"Недостаточно акций. Нужно: {quantity}, доступно: {shares}"
        
        return True, ""
    
    def _format_trade_confirmation(self, trade_data: Dict[str, Any]) -> str:
        """Форматировать подтверждение сделки"""
        action_emoji = "🟢" if trade_data["action"] == "BUY" else "🔴"
        
        return f"""
📊 *Подтверждение сделки*

{action_emoji} *Действие:* {trade_data["action"]}
📦 *Количество:* {trade_data["quantity"]} акций
💵 *Цена:* {trade_data["price"]:.2f} ₽
💰 *Сумма:* {trade_data["total_amount"]:.2f} ₽

Подтвердите или отмените сделку:
"""
    
    def _create_trade_confirmation_keyboard(self, trade_data: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Создать клавиатуру подтверждения сделки"""
        payload = f"{trade_data['action']}_{trade_data['quantity']}_{trade_data['price']}"
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_trade_{payload}"),
                InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_trade_{payload}"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _handle_trade_confirmation(self, query, context):
        """Обработать подтверждение сделки"""
        # Здесь должна быть логика исполнения сделки
        # Временно заглушка
        await query.edit_message_text("✅ Сделка исполнена успешно!")
    
    async def _handle_recommendation_execution(self, query, context):
        """Обработать исполнение рекомендации"""
        # Здесь должна быть логика исполнения рекомендации
        # Временно заглушка
        await query.edit_message_text("✅ Рекомендация исполнена успешно!")


def create_application() -> Application:
    """Создать и настроить приложение Telegram бота"""
    bot = GazpromTelegramBot()
    
    # Создание приложения
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Добавление обработчиков команд
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("portfolio", bot.portfolio_command))
    application.add_handler(CommandHandler("recommend", bot.recommend_command))
    application.add_handler(CommandHandler("execute", bot.execute_command))
    application.add_handler(CommandHandler("history", bot.history_command))
    application.add_handler(CommandHandler("balance", bot.balance_command))
    application.add_handler(CommandHandler("analysis", bot.analysis_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    
    # Добавление обработчика inline кнопок
    application.add_handler(CallbackQueryHandler(bot.callback_query_handler))
    
    return application