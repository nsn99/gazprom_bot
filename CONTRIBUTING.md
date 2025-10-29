# Contributing to Gazprom Trading Bot

Спасибо за ваш интерес к внесению вклада в Gazprom Trading Bot! Этот документ поможет вам начать работу.

## 🚀 Как начать

### Предварительные требования

- Python 3.11+
- Git
- Аккаунт на GitHub
- Telegram Bot Token (для тестирования)
- AgentRouter API Key (для тестирования)

### Настройка окружения

1. **Fork репозитория**
   ```bash
   # Нажмите "Fork" на GitHub, затем клонируйте ваш fork
   git clone https://github.com/nsn99/gazprom_bot.git
   cd gazprom-trading-bot
   ```

2. **Настройка upstream**
   ```bash
   git remote add upstream https://github.com/nsn99/gazprom_bot.git
   ```

3. **Создание виртуального окружения**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или venv\Scripts\activate  # Windows
   ```

4. **Установка зависимостей**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Для разработки
   ```

5. **Настройка переменных окружения**
   ```bash
   cp .env.example .env
   # Отредактируйте .env с вашими API ключами
   ```

## 📋 Процесс разработки

### 1. Создание ветки

```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/your-bug-fix
```

### 2. Внесение изменений

- Следуйте PEP 8 для форматирования кода
- Используйте `black` для автоматического форматирования
- Пишите тесты для новой функциональности
- Обновляйте документацию при необходимости

### 3. Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=.

# Форматирование кода
black .

# Линтинг
flake8 .
```

### 4. Коммит изменений

```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Push и Pull Request

```bash
git push origin feature/your-feature-name
```

Создайте Pull Request на GitHub с подробным описанием изменений.

## 📝 Стиль коммитов

Мы используем [Conventional Commits](https://www.conventionalcommits.org/) формат:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Типы коммитов

- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Изменения в документации
- `style`: Форматирование кода (без изменения логики)
- `refactor`: Рефакторинг кода
- `test`: Добавление или изменение тестов
- `chore`: Обновление зависимостей, инструменты

### Примеры

```bash
feat(ai): add support for GPT-5 model
fix(telegram): resolve message parsing error
docs(readme): update installation instructions
test(portfolio): add unit tests for portfolio manager
```

## 🧪 Тестирование

### Структура тестов

```
tests/
├── unit/           # Unit тесты
├── integration/    # Интеграционные тесты
├── e2e/           # End-to-end тесты
└── fixtures/       # Тестовые данные
```

### Написание тестов

```python
import pytest
from portfolio.manager import PortfolioManager

class TestPortfolioManager:
    def test_buy_shares(self):
        manager = PortfolioManager(user_id=12345)
        result = manager.buy_shares("GAZP", 10, 170.50)
        
        assert result.success is True
        assert result.shares == 10
        assert result.price == 170.50
```

### Запуск тестов

```bash
# Все тесты
pytest

# Конкретный файл
pytest tests/test_portfolio_manager.py

# С метками
pytest -m "unit"
pytest -m "integration"

# С покрытием
pytest --cov=portfolio --cov-report=html
```

## 📖 Документация

### Обновление документации

При добавлении новой функциональности:

1. Обновите README.md при необходимости
2. Добавьте документацию в соответствующий .md файл в docs/
3. Обновите CHANGELOG.md
4. Добавьте примеры использования

### Формат документации

- Используйте Markdown
- Включайте примеры кода
- Добавляйте диаграммы при необходимости
- Следуйте структуре существующей документации

## 🐛 Сообщения о багах

При создании issue о баге, включите:

1. **Описание проблемы**
2. **Шаги для воспроизведения**
3. **Ожидаемое поведение**
4. **Фактическое поведение**
5. **Окружение** (ОС, Python версия)
6. **Логи ошибок**
7. **Скриншоты** (если применимо)

### Шаблон для баг-репорта

```markdown
## Описание проблемы
Краткое описание проблемы

## Шаги для воспроизведения
1. Запустить команду `/start`
2. Отправить `/recommend`
3. ...

## Ожидаемое поведение
Описание того, что должно произойти

## Фактическое поведение
Описание того, что произошло на самом деле

## Окружение
- OS: Ubuntu 20.04
- Python: 3.11.5
- Версия бота: 1.0.0

## Логи
```
Traceback (most recent call last):
...
```

## Дополнительная информация
Любая дополнительная информация
```

## 💡 Запросы на функциональность

При запросе новой функциональности:

1. Проверьте, что такой функциональности еще нет
2. Поищите существующие issues
3. Создайте новый issue с меткой `enhancement`

### Шаблон для запроса функциональности

```markdown
## Описание функциональности
Краткое описание новой функциональности

## Проблема, которую решает
Описание проблемы, которую решает эта функциональность

## Предложенное решение
Описание предложенного решения

## Альтернативы
Описание альтернативных решений

## Дополнительная информация
Любая дополнительная информация
```

## 🔍 Code Review

### Процесс ревью

1. **Автоматические проверки**: CI/CD запускает тесты и линтинг
2. **Ручное ревью**: Мейнтейнеры проверяют код
3. **Обсуждение**: Обсуждение изменений в комментариях
4. **Утверждение**: Требуется как минимум одно утверждение

### Что проверяют в ревью

- **Функциональность**: Работает ли код как ожидается
- **Тесты**: Достаточно ли тестов, покрывают ли они случаи
- **Документация**: Обновлена ли документация
- **Стиль кода**: Следует ли код стандартам проекта
- **Безопасность**: Есть ли потенциальные уязвимости
- **Производительность**: Не ухудшает ли производительность

### Комментарии к коду

```python
# Хорошо
def calculate_portfolio_value(self, user_id: int) -> float:
    """Рассчитывает общую стоимость портфеля пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Общая стоимость портфеля в рублях
        
    Raises:
        UserNotFoundError: Если пользователь не найден
    """
    # Получаем позиции пользователя
    positions = self.db.get_positions(user_id)
    
    # Рассчитываем общую стоимость
    total_value = sum(pos.shares * pos.current_price for pos in positions)
    
    return total_value

# Плохо
def calc(self, uid):
    # получить позиции
    p = self.db.get_positions(uid)
    
    # посчитать
    return sum(x.shares * x.price for x in p)
```

## 🏷️ Метки и приоритеты

### Метки для issues

- `bug`: Ошибки
- `enhancement`: Улучшения
- `documentation`: Документация
- `good first issue`: Хорошая задача для новичков
- `help wanted`: Требуется помощь
- `priority/high`: Высокий приоритет
- `priority/medium`: Средний приоритет
- `priority/low`: Низкий приоритет

### Приоритеты

- **High**: Критические ошибки, блокирующие функциональность
- **Medium**: Важные улучшения, некритические ошибки
- **Low**: Минорные улучшения, косметические изменения

## 🚀 Релизы

### Версионирование

Мы используем [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH`
- `MAJOR`: Обратно несовместимые изменения
- `MINOR`: Новая функциональность, обратно совместимая
- `PATCH`: Исправления ошибок, обратно совместимые

### Процесс релиза

1. **Подготовка релиза**
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b release/v1.2.0
   ```

2. **Обновление версии**
   - Обновить `__version__` в `__init__.py`
   - Обновить CHANGELOG.md
   - Создать релизные заметки

3. **Тестирование**
   ```bash
   pytest
   ```

4. **Создание релиза**
   ```bash
   git tag v1.2.0
   git push upstream v1.2.0
   ```

5. **Публикация**
   - Создать релиз на GitHub
   - Опубликовать в PyPI (если применимо)

## 🤝 Сообщество

### Каналы связи

- **GitHub Issues**: Для баг-репортов и запросов функциональности
- **GitHub Discussions**: Для общих обсуждений
- **Telegram**: @gazprom_bot_dev для разработчиков

### Поведение в сообществе

- **Уважайте других участников**
- **Будьте конструктивны**
- **Помогайте новичкам**
- **Следуйте кодексу поведения**

## 📚 Ресурсы

### Полезные ссылки

- [Python Style Guide](https://pep8.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

### Инструменты

- **IDE**: VS Code, PyCharm
- **Форматирование**: Black, isort
- **Линтинг**: flake8, pylint
- **Тестирование**: pytest, coverage
- **Документация**: MkDocs, Sphinx

## 🎉 Благодарности

Спасибо всем контрибьюторам, которые внесли вклад в проект!

### Топ контрибьюторы

- [@contributor1](https://github.com/contributor1) - Core functionality
- [@contributor2](https://github.com/contributor2) - Documentation
- [@contributor3](https://github.com/contributor3) - Bug fixes

---

**Если у вас есть вопросы, не стесняйтесь обращаться!**