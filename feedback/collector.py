"""
Коллектор обратной связи от пользователей
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from monitoring.logger import get_logger
from database.database import get_db_manager


logger = get_logger(__name__)


class FeedbackType(Enum):
    """Типы обратной связи"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    GENERAL_FEEDBACK = "general_feedback"
    RECOMMENDATION_RATING = "recommendation_rating"
    USER_EXPERIENCE = "user_experience"


class FeedbackCollector:
    """Коллектор обратной связи"""
    
    def __init__(self):
        """Инициализация коллектора"""
        self.db_manager = get_db_manager()
    
    async def submit_feedback(
        self,
        user_id: int,
        feedback_type: FeedbackType,
        message: str,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Отправить обратную связь
        
        Args:
            user_id: ID пользователя
            feedback_type: Тип обратной связи
            message: Сообщение
            rating: Оценка (1-5)
            metadata: Дополнительные метаданные
            
        Returns:
            Результат операции
        """
        try:
            # Валидация данных
            if not message or len(message.strip()) == 0:
                return {
                    "success": False,
                    "error": "Сообщение не может быть пустым"
                }
            
            if rating is not None and (rating < 1 or rating > 5):
                return {
                    "success": False,
                    "error": "Оценка должна быть от 1 до 5"
                }
            
            # Сохранение в базу данных
            feedback_data = {
                "user_id": user_id,
                "feedback_type": feedback_type.value,
                "message": message.strip(),
                "rating": rating,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow(),
                "status": "new"
            }
            
            feedback_id = await self._save_feedback(feedback_data)
            
            logger.info(f"Received feedback from user {user_id}: {feedback_type.value}")
            
            # Отправка уведомления администраторам
            await self._notify_admins(feedback_data)
            
            return {
                "success": True,
                "feedback_id": feedback_id,
                "message": "Спасибо за обратную связь!"
            }
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            return {
                "success": False,
                "error": "Ошибка при отправке обратной связи"
            }
    
    async def get_feedback(
        self,
        user_id: Optional[int] = None,
        feedback_type: Optional[FeedbackType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получить обратную связь
        
        Args:
            user_id: ID пользователя (опционально)
            feedback_type: Тип обратной связи (опционально)
            limit: Ограничение количества
            
        Returns:
            Список обратной связи
        """
        try:
            # Здесь должна быть реализация получения из БД
            # Для примера возвращаем пустой список
            return []
            
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            return []
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Получить статистику обратной связи
        
        Returns:
            Статистика обратной связи
        """
        try:
            # Здесь должна быть реализация получения статистики из БД
            # Для примера возвращаем тестовые данные
            return {
                "total_feedback": 0,
                "by_type": {
                    "bug_report": 0,
                    "feature_request": 0,
                    "general_feedback": 0,
                    "recommendation_rating": 0,
                    "user_experience": 0
                },
                "by_rating": {
                    "1": 0,
                    "2": 0,
                    "3": 0,
                    "4": 0,
                    "5": 0
                },
                "average_rating": 0.0,
                "last_30_days": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {}
    
    async def _save_feedback(self, feedback_data: Dict[str, Any]) -> int:
        """
        Сохранить обратную связь в базу данных
        
        Args:
            feedback_data: Данные обратной связи
            
        Returns:
            ID сохраненной записи
        """
        # Здесь должна быть реализация сохранения в БД
        # Для примера возвращаем тестовый ID
        return 1
    
    async def _notify_admins(self, feedback_data: Dict[str, Any]):
        """
        Уведомить администраторов о новой обратной связи
        
        Args:
            feedback_data: Данные обратной связи
        """
        try:
            # Здесь должна быть реализация уведомления администраторов
            # Например, отправка в Telegram или email
            logger.info(f"New feedback notification: {feedback_data['feedback_type']}")
            
        except Exception as e:
            logger.error(f"Error notifying admins: {e}")
    
    async def analyze_feedback(self, days: int = 30) -> Dict[str, Any]:
        """
        Проанализировать обратную связь за период
        
        Args:
            days: Период анализа в днях
            
        Returns:
            Результаты анализа
        """
        try:
            feedback_list = await self.get_feedback(limit=1000)
            
            # Фильтрация по дате
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_feedback = [
                f for f in feedback_list 
                if f.get('timestamp', datetime.min) >= cutoff_date
            ]
            
            if not recent_feedback:
                return {
                    "period_days": days,
                    "total_feedback": 0,
                    "analysis": "Недостаточно данных для анализа"
                }
            
            # Анализ по типам
            type_counts = {}
            rating_counts = {}
            total_rating = 0
            rating_count = 0
            
            for feedback in recent_feedback:
                fb_type = feedback.get('feedback_type', 'unknown')
                type_counts[fb_type] = type_counts.get(fb_type, 0) + 1
                
                rating = feedback.get('rating')
                if rating is not None:
                    rating_str = str(rating)
                    rating_counts[rating_str] = rating_counts.get(rating_str, 0) + 1
                    total_rating += rating
                    rating_count += 1
            
            # Расчет средней оценки
            avg_rating = total_rating / rating_count if rating_count > 0 else 0
            
            # Поиск общих тем
            common_words = self._extract_common_words(recent_feedback)
            
            return {
                "period_days": days,
                "total_feedback": len(recent_feedback),
                "by_type": type_counts,
                "by_rating": rating_counts,
                "average_rating": round(avg_rating, 2),
                "common_topics": common_words[:10],  # Топ-10 тем
                "trend_analysis": self._analyze_trends(recent_feedback)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing feedback: {e}")
            return {
                "period_days": days,
                "error": str(e)
            }
    
    def _extract_common_words(self, feedback_list: List[Dict[str, Any]]) -> List[str]:
        """
        Извлечь общие слова из сообщений
        
        Args:
            feedback_list: Список обратной связи
            
        Returns:
            Список общих слов
        """
        # Простая реализация - в реальном проекте здесь должен быть
        # более сложный алгоритм анализа текста
        word_counts = {}
        
        for feedback in feedback_list:
            message = feedback.get('message', '').lower()
            words = message.split()
            
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Сортировка по частоте
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words]
    
    def _analyze_trends(self, feedback_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Проанализировать тренды в обратной связи
        
        Args:
            feedback_list: Список обратной связи
            
        Returns:
            Анализ трендов
        """
        if len(feedback_list) < 10:
            return {"message": "Недостаточно данных для анализа трендов"}
        
        # Анализ по времени
        hourly_counts = {}
        for feedback in feedback_list:
            timestamp = feedback.get('timestamp')
            if timestamp:
                hour = timestamp.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # Поиск пиковых часов
        peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Анализ по типам
        type_trend = {}
        for feedback in feedback_list:
            fb_type = feedback.get('feedback_type', 'unknown')
            if fb_type not in type_trend:
                type_trend[fb_type] = []
            type_trend[fb_type].append(feedback.get('timestamp'))
        
        return {
            "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
            "type_trends": {
                fb_type: len(trends) 
                for fb_type, trends in type_trend.items()
            },
            "insights": self._generate_insights(feedback_list)
        }
    
    def _generate_insights(self, feedback_list: List[Dict[str, Any]]) -> List[str]:
        """
        Сгенерировать инсайты на основе обратной связи
        
        Args:
            feedback_list: Список обратной связи
            
        Returns:
            Список инсайтов
        """
        insights = []
        
        # Подсчет типов
        type_counts = {}
        for feedback in feedback_list:
            fb_type = feedback.get('feedback_type', 'unknown')
            type_counts[fb_type] = type_counts.get(fb_type, 0) + 1
        
        # Генерация инсайтов
        total = len(feedback_list)
        
        if type_counts.get('bug_report', 0) > total * 0.3:
            insights.append("Высокое количество сообщений об ошибках - рекомендуется уделить внимание качеству")
        
        if type_counts.get('feature_request', 0) > total * 0.2:
            insights.append("Много запросов новых функций - пользователи активно используют бота")
        
        avg_rating = 0
        rating_count = 0
        for feedback in feedback_list:
            rating = feedback.get('rating')
            if rating is not None:
                avg_rating += rating
                rating_count += 1
        
        if rating_count > 0:
            avg_rating = avg_rating / rating_count
            if avg_rating < 3.0:
                insights.append("Низкая средняя оценка - необходимо улучшить пользовательский опыт")
            elif avg_rating > 4.5:
                insights.append("Высокая средняя оценка - пользователи довольны функционалом")
        
        return insights


# Глобальный экземпляр коллектора
_feedback_collector = None


def get_feedback_collector() -> FeedbackCollector:
    """Получить глобальный экземпляр коллектора обратной связи"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector