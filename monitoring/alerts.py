"""
Система алертов для gazprom_bot.

Обеспечивает:
- Мониторинг критических событий
- Отправка уведомлений (email, Telegram, Slack)
- Эскалация алертов
- История алертов с дедупликацией

Поддерживает различные уровни критичности и каналы доставки.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    import requests
except ImportError:
    requests = None

from gazprom_bot.utils.time_utils import now_msk


class AlertLevel(Enum):
    """Уровни критичности алертов."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Каналы доставки алертов."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"
    LOG = "log"


@dataclass
class Alert:
    """Структура алерта."""
    id: str
    level: AlertLevel
    title: str
    message: str
    component: str
    timestamp: datetime
    channels: List[AlertChannel]
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class AlertConfig:
    """Конфигурация алертов."""
    email_enabled: bool = False
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = None

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    # Настройки дедупликации
    deduplication_window_minutes: int = 5
    max_alerts_per_window: int = 3


class AlertManager:
    """
    Менеджер алертов.

    Управляет жизненным циклом алертов:
    - Создание и отправка
    - Дедупликация
    - Разрешение
    - История
    """

    def __init__(self, config: AlertConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._alert_counter = 0

    def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        component: str,
        channels: Optional[List[AlertChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> Optional[str]:
        """
        Отправить алерт.

        Args:
            level: Уровень критичности
            title: Заголовок алерта
            message: Подробное сообщение
            component: Компонент системы
            channels: Каналы доставки (если None, используются все настроенные)
            metadata: Дополнительные данные
            force: Игнорировать дедупликацию

        Returns:
            ID алерта или None если дедуплицирован
        """
        # Дедупликация
        if not force and self._should_deduplicate(title, component):
            self.logger.debug(f"Alert deduplicated: {title}")
            return None

        # Создание алерта
        alert_id = self._generate_alert_id()
        timestamp = now_msk()

        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            component=component,
            timestamp=timestamp,
            channels=channels or self._get_default_channels(level),
            metadata=metadata or {}
        )

        self.alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Отправка по каналам
        self._send_to_channels(alert)

        # Логирование
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }.get(level, logging.INFO)

        self.logger.log(log_level, f"Alert [{level.value}]: {title} - {message}")

        return alert_id

    def resolve_alert(self, alert_id: str, resolution_message: Optional[str] = None):
        """Разрешить алерт."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = now_msk()
            if resolution_message:
                alert.metadata['resolution'] = resolution_message
            self.logger.info(f"Alert resolved: {alert.title}")

    def _should_deduplicate(self, title: str, component: str) -> bool:
        """Проверить необходимость дедупликации."""
        window_start = now_msk() - timedelta(minutes=self.config.deduplication_window_minutes)
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp >= window_start and a.title == title and a.component == component
        ]

        return len(recent_alerts) >= self.config.max_alerts_per_window

    def _generate_alert_id(self) -> str:
        """Генерировать уникальный ID алерта."""
        self._alert_counter += 1
        timestamp = now_msk().strftime("%Y%m%d_%H%M%S")
        return f"alert_{timestamp}_{self._alert_counter}"

    def _get_default_channels(self, level: AlertLevel) -> List[AlertChannel]:
        """Получить каналы по умолчанию для уровня."""
        channels = []

        # Для критических алертов все каналы
        if level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            if self.config.email_enabled:
                channels.append(AlertChannel.EMAIL)
            if self.config.telegram_enabled:
                channels.append(AlertChannel.TELEGRAM)
            if self.config.slack_enabled:
                channels.append(AlertChannel.SLACK)

        # Всегда логируем
        channels.append(AlertChannel.LOG)

        return channels

    def _send_to_channels(self, alert: Alert):
        """Отправить алерт по всем каналам."""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email(alert)
                elif channel == AlertChannel.TELEGRAM:
                    self._send_telegram(alert)
                elif channel == AlertChannel.SLACK:
                    self._send_slack(alert)
                elif channel == AlertChannel.LOG:
                    pass  # Уже залогировано выше
            except Exception as e:
                self.logger.error(f"Failed to send alert to {channel.value}: {e}")

    def _send_email(self, alert: Alert):
        """Отправить алерт по email."""
        if not self.config.email_enabled or not self.config.email_recipients:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"

            body = f"""
Component: {alert.component}
Time: {alert.timestamp}
Level: {alert.level.value}

{alert.message}

Metadata: {alert.metadata}
            """.strip()

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            server.send_message(msg)
            server.quit()

        except Exception as e:
            raise Exception(f"Email send failed: {e}")

    def _send_telegram(self, alert: Alert):
        """Отправить алерт в Telegram."""
        if not self.config.telegram_enabled or not requests:
            return

        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        text = f"""
🚨 *{alert.level.value.upper()}* 🚨
*{alert.title}*

Component: `{alert.component}`
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{alert.message}
        """.strip()

        payload = {
            'chat_id': self.config.telegram_chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_slack(self, alert: Alert):
        """Отправить алерт в Slack."""
        if not self.config.slack_enabled or not requests:
            return

        payload = {
            'text': f"[{alert.level.value.upper()}] {alert.title}",
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f"*{alert.title}*\nComponent: `{alert.component}`\n{alert.message}"
                    }
                }
            ]
        }

        response = requests.post(self.config.slack_webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def get_active_alerts(self) -> List[Alert]:
        """Получить активные (нерешенные) алерты."""
        return [a for a in self.alerts.values() if not a.resolved]

    def get_alert_stats(self) -> Dict[str, int]:
        """Получить статистику алертов."""
        return {
            'total': len(self.alert_history),
            'active': len(self.get_active_alerts()),
            'resolved': len([a for a in self.alert_history if a.resolved]),
            'by_level': {
                level.value: len([a for a in self.alert_history if a.level == level])
                for level in AlertLevel
            }
        }


__all__ = ['AlertManager', 'Alert', 'AlertLevel', 'AlertChannel', 'AlertConfig']