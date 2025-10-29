"""
Обработчики подтверждений сделок в Telegram боте.

Реализует:
- Интерактивные диалоги подтверждения сделок
- Inline клавиатуры для быстрых действий
- Обработку callback'ов от кнопок
- Валидацию параметров сделок
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

from telegram import Update as TelegramUpdate, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from database.models import TransactionAction
from portfolio.manager import PortfolioManager
from ai.agentrouter_client import AgentRouterClient
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class PendingTrade:
    """Ожидающая подтверждения сделка"""
    user_id: int
    portfolio_id: int
    action: str
    ticker: str
    quantity: int
    price: float
    reason: str
    timestamp: datetime
    recommendation_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class ConfirmationHandler:
    """Обработчик подтверждений сделок"""
    
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.agentrouter_client = AgentRouterClient(settings.agentrouter_api_key)
        
        # Хранилище ожидающих сделок (в production использовать Redis)
        self.pending_trades: Dict[str, PendingTrade] = {}
        
        # Время жизни подтверждения (5 минут)
        self.confirmation_timeout = timedelta(minutes=5)
        
        logger.info("ConfirmationHandler initialized")
    
    def create_trade_confirmation(self, user_id: int, portfolio_id: int,
                                action: str, ticker: str, quantity: int,
                                price: float, reason: str,
                                recommendation_id: Optional[int] = None) -> tuple[str, InlineKeyboardMarkup]:
        """
        Создание сообщения подтверждения сделки
        
        Returns:
            tuple: (текст сообщения, клавиатура)
        """
        try:
            # Создание ID сделки
            trade_id = f"{user_id}_{portfolio_id}_{datetime.now().timestamp()}"
            
            # Создание ожидающей сделки
            pending_trade = PendingTrade(
                user_id=user_id,
                portfolio_id=portfolio_id,
                action=action,
                ticker=ticker,
                quantity=quantity,
                price=price,
                reason=reason,
                timestamp=datetime.now(),
                recommendation_id=recommendation_id,
                expires_at=datetime.now() + self.confirmation_timeout
            )
            
            # Сохранение в хранилище
            self.pending_trades[trade_id] = pending_trade
            
            # Расчет суммы сделки
            total_amount = quantity * price
            commission = total_amount * 0.0003  # 0.03% комиссия
            total_with_commission = total_amount + commission
            
            # Формирование сообщения
            action_emoji = "🟢" if action == TransactionAction.BUY else "🔴"
            action_text = "ПОКУПКА" if action == TransactionAction.BUY else "ПРОДАЖА"
            
            message = f"""
{action_emoji} <b>Подтверждение сделки</b>

📈 <b>Инструмент:</b> {ticker}
💰 <b>Действие:</b> {action_text}
📊 <b>Количество:</b> {quantity:,} шт.
💵 <b>Цена:</b> {price:.2f} RUB
💸 <b>Сумма:</b> {total_amount:,.0f} RUB
🏦 <b>Комиссия:</b> {commission:.2f} RUB
💳 <b>Итого:</b> {total_with_commission:,.0f} RUB

📝 <b>Основание:</b>
{reason}

⏰ <b>Действительно до:</b> {pending_trade.expires_at.strftime('%H:%M:%S')}
            """
            
            # Создание клавиатуры
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"✅ Подтвердить {action_text}",
                        callback_data=f"confirm_trade:{trade_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ Отменить",
                        callback_data=f"cancel_trade:{trade_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚙️ Изменить количество",
                        callback_data=f"modify_quantity:{trade_id}"
                    )
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info(f"Created trade confirmation for user {user_id}: {action} {quantity} {ticker}")
            return message, reply_markup
            
        except Exception as e:
            logger.error(f"Error creating trade confirmation: {e}")
            raise
    
    async def handle_callback_query(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов от кнопок"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Парсинг callback_data
            callback_data = query.data
            parts = callback_data.split(':')
            
            if len(parts) < 2:
                await query.edit_message_text("❌ Неверный формат запроса")
                return
            
            action = parts[0]
            trade_id = parts[1]
            
            # Проверка существования сделки
            if trade_id not in self.pending_trades:
                await query.edit_message_text("❌ Сделка не найдена или истекла")
                return
            
            pending_trade = self.pending_trades[trade_id]
            
            # Проверка времени жизни
            if datetime.now() > pending_trade.expires_at:
                del self.pending_trades[trade_id]
                await query.edit_message_text("❌ Время подтверждения истекло")
                return
            
            # Обработка действия
            if action == "confirm_trade":
                await self._handle_confirm_trade(query, pending_trade, trade_id)
            elif action == "cancel_trade":
                await self._handle_cancel_trade(query, pending_trade, trade_id)
            elif action == "modify_quantity":
                await self._handle_modify_quantity(query, pending_trade, trade_id)
            else:
                await query.edit_message_text("❌ Неизвестное действие")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text("❌ Ошибка при обработке запроса")
    
    async def _handle_confirm_trade(self, query, pending_trade: PendingTrade, trade_id: str):
        """Обработка подтверждения сделки"""
        try:
            # Отправка сообщения об обработке
            await query.edit_message_text("⏳ Исполняю сделку...")
            
            # Исполнение сделки через менеджер портфеля
            result = await self.portfolio_manager.execute_trade(
                user_id=pending_trade.user_id,
                action=pending_trade.action,
                ticker=pending_trade.ticker,
                quantity=pending_trade.quantity,
                price=pending_trade.price,
                recommendation_id=pending_trade.recommendation_id
            )
            
            # Формируем результат в ожидаемом формате
            if result:
                result_dict = {
                    'success': True,
                    'executed_price': pending_trade.price,
                    'commission': pending_trade.quantity * pending_trade.price * 0.0003,
                    'net_amount': pending_trade.quantity * pending_trade.price * (1 + 0.0003)
                }
            else:
                result_dict = {
                    'success': False,
                    'error': 'Ошибка при исполнении сделки'
                }
            
            if result_dict['success']:
                result = result_dict
                # Обновление статуса рекомендации
                if pending_trade.recommendation_id:
                    # Обновление статуса рекомендации
                    pass  # TODO: Реализовать обновление статуса рекомендации
                
                # Формирование сообщения об успехе
                action_text = "куплены" if pending_trade.action == TransactionAction.BUY else "проданы"
                message = f"""
✅ <b>Сделка исполнена успешно!</b>

📈 {pending_trade.quantity:,} акций {pending_trade.ticker} {action_text}
💵 Цена: {result['executed_price']:.2f} RUB
💸 Комиссия: {result['commission']:.2f} RUB
💳 Итого: {result['net_amount']:,.0f} RUB

🕐 Время: {datetime.now().strftime('%H:%M:%S')}
                """
                
                await query.edit_message_text(message, parse_mode=ParseMode.HTML)
                
                logger.info(f"Trade executed successfully: {pending_trade.action} {pending_trade.quantity} {pending_trade.ticker}")
            else:
                result = result_dict
                # Формирование сообщения об ошибке
                message = f"""
❌ <b>Ошибка при исполнении сделки</b>

📈 Инструмент: {pending_trade.ticker}
💰 Действие: {pending_trade.action}
📊 Количество: {pending_trade.quantity:,} шт.

🚨 Ошибка: {result['error']}
                """
                
                await query.edit_message_text(message, parse_mode=ParseMode.HTML)
                
                logger.error(f"Trade execution failed: {result['error']}")
            
            # Удаление из хранилища
            del self.pending_trades[trade_id]
            
        except Exception as e:
            logger.error(f"Error confirming trade: {e}")
            await query.edit_message_text("❌ Ошибка при исполнении сделки")
    
    async def _handle_cancel_trade(self, query, pending_trade: PendingTrade, trade_id: str):
        """Обработка отмены сделки"""
        try:
            # Обновление статуса рекомендации
            if pending_trade.recommendation_id:
                # Обновление статуса рекомендации
                pass  # TODO: Реализовать обновление статуса рекомендации
            
            # Формирование сообщения
            message = f"""
❌ <b>Сделка отменена</b>

📈 Инструмент: {pending_trade.ticker}
💰 Действие: {pending_trade.action}
📊 Количество: {pending_trade.quantity:,} шт.

🕐 Время: {datetime.now().strftime('%H:%M:%S')}
            """
            
            await query.edit_message_text(message, parse_mode=ParseMode.HTML)
            
            # Удаление из хранилища
            del self.pending_trades[trade_id]
            
            logger.info(f"Trade cancelled: {pending_trade.action} {pending_trade.quantity} {pending_trade.ticker}")
            
        except Exception as e:
            logger.error(f"Error cancelling trade: {e}")
            await query.edit_message_text("❌ Ошибка при отмене сделки")
    
    async def _handle_modify_quantity(self, query, pending_trade: PendingTrade, trade_id: str):
        """Обработка изменения количества акций"""
        try:
            # Создание клавиатуры для выбора количества
            current_qty = pending_trade.quantity
            step = 10  # Шаг изменения
            
            keyboard = []
            
            # Кнопки уменьшения
            decrease_row = []
            if current_qty > step:
                decrease_row.append(
                    InlineKeyboardButton(
                        f"-{step}",
                        callback_data=f"change_quantity:{trade_id}:{current_qty - step}"
                    )
                )
            if current_qty > step * 2:
                decrease_row.append(
                    InlineKeyboardButton(
                        f"-{step * 2}",
                        callback_data=f"change_quantity:{trade_id}:{current_qty - step * 2}"
                    )
                )
            if decrease_row:
                keyboard.append(decrease_row)
            
            # Текущее количество
            keyboard.append([
                InlineKeyboardButton(
                    f"Текущее: {current_qty} шт.",
                    callback_data="noop"
                )
            ])
            
            # Кнопки увеличения
            increase_row = []
            increase_row.append(
                InlineKeyboardButton(
                    f"+{step}",
                    callback_data=f"change_quantity:{trade_id}:{current_qty + step}"
                )
            )
            increase_row.append(
                InlineKeyboardButton(
                    f"+{step * 2}",
                    callback_data=f"change_quantity:{trade_id}:{current_qty + step * 2}"
                )
            )
            keyboard.append(increase_row)
            
            # Кнопки управления
            keyboard.append([
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"confirm_trade:{trade_id}"
                ),
                InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data=f"cancel_trade:{trade_id}"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Обновление сообщения
            total_amount = current_qty * pending_trade.price
            commission = total_amount * 0.0003
            total_with_commission = total_amount + commission
            
            action_emoji = "🟢" if pending_trade.action == TransactionAction.BUY else "🔴"
            action_text = "ПОКУПКА" if pending_trade.action == TransactionAction.BUY else "ПРОДАЖА"
            
            message = f"""
{action_emoji} <b>Изменение количества акций</b>

📈 <b>Инструмент:</b> {pending_trade.ticker}
💰 <b>Действие:</b> {action_text}
📊 <b>Количество:</b> {current_qty:,} шт.
💵 <b>Цена:</b> {pending_trade.price:.2f} RUB
💸 <b>Сумма:</b> {total_amount:,.0f} RUB
🏦 <b>Комиссия:</b> {commission:.2f} RUB
💳 <b>Итого:</b> {total_with_commission:,.0f} RUB

⏰ <b>Действительно до:</b> {pending_trade.expires_at.strftime('%H:%M:%S')}
            """
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error modifying quantity: {e}")
            await query.edit_message_text("❌ Ошибка при изменении количества")
    
    async def handle_quantity_change(self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE):
        """Обработка изменения количества"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Парсинг callback_data
            callback_data = query.data
            parts = callback_data.split(':')
            
            if len(parts) < 3 or parts[0] != "change_quantity":
                return
            
            trade_id = parts[1]
            new_quantity = int(parts[2])
            
            # Проверка существования сделки
            if trade_id not in self.pending_trades:
                await query.edit_message_text("❌ Сделка не найдена или истекла")
                return
            
            pending_trade = self.pending_trades[trade_id]
            
            # Проверка времени жизни
            if datetime.now() > pending_trade.expires_at:
                del self.pending_trades[trade_id]
                await query.edit_message_text("❌ Время подтверждения истекло")
                return
            
            # Обновление количества
            pending_trade.quantity = new_quantity
            
            # Повторное создание сообщения подтверждения
            message, reply_markup = self.create_trade_confirmation(
                user_id=pending_trade.user_id,
                portfolio_id=pending_trade.portfolio_id,
                action=pending_trade.action,
                ticker=pending_trade.ticker,
                quantity=new_quantity,
                price=pending_trade.price,
                reason=pending_trade.reason,
                recommendation_id=pending_trade.recommendation_id
            )
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error handling quantity change: {e}")
            await query.edit_message_text("❌ Ошибка при изменении количества")
    
    def cleanup_expired_trades(self):
        """Очистка истекших сделок"""
        try:
            current_time = datetime.now()
            expired_trades = []
            
            for trade_id, pending_trade in self.pending_trades.items():
                if current_time > pending_trade.expires_at:
                    expired_trades.append(trade_id)
                    
                    # Обновление статуса рекомендации
                    if pending_trade.recommendation_id:
                        # Обновление статуса рекомендации
                        pass  # TODO: Реализовать обновление статуса рекомендации
            
            # Удаление истекших сделок
            for trade_id in expired_trades:
                del self.pending_trades[trade_id]
            
            if expired_trades:
                logger.info(f"Cleaned up {len(expired_trades)} expired trades")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired trades: {e}")
    
    def get_pending_trades_count(self, user_id: int) -> int:
        """Получение количества ожидающих сделок пользователя"""
        count = 0
        for pending_trade in self.pending_trades.values():
            if pending_trade.user_id == user_id:
                count += 1
        return count
    
    def get_pending_trade(self, trade_id: str) -> Optional[PendingTrade]:
        """Получение ожидающей сделки по ID"""
        return self.pending_trades.get(trade_id)


# Глобальный экземпляр обработчика
confirmation_handler = None


def get_confirmation_handler() -> ConfirmationHandler:
    """Получение глобального экземпляра обработчика подтверждений"""
    global confirmation_handler
    if confirmation_handler is None:
        confirmation_handler = ConfirmationHandler()
    return confirmation_handler


# Регистрация обработчиков для Telegram бота
def register_confirmation_handlers(application):
    """Регистрация обработчиков подтверждений в приложении"""
    confirmation_handler = get_confirmation_handler()
    
    # Основной обработчик callback запросов
    application.add_handler(CallbackQueryHandler(
        confirmation_handler.handle_callback_query,
        pattern=r'^(confirm_trade|cancel_trade|modify_quantity):'
    ))
    
    # Обработчик изменения количества
    application.add_handler(CallbackQueryHandler(
        confirmation_handler.handle_quantity_change,
        pattern=r'^change_quantity:'
    ))
    
    logger.info("Confirmation handlers registered")