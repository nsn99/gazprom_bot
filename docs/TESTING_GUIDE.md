# Руководство по тестированию Gazprom Trading Bot

## 📋 Содержание

- [Обзор](#-обзор)
- [Настройка окружения](#-настройка-окружения)
- [Запуск тестов](#-запуск-тестов)
- [Типы тестов](#-типы-тестов)
- [Написание тестов](#-написание-тестов)
- [CI/CD](#cicd)
- [Метрики покрытия](#-метрики-покрытия)
- [Отладка тестов](#-отладка-тестов)

## 🎯 Обзор

В проекте используется комплексная стратегия тестирования для обеспечения качества и надежности Gazprom Trading Bot.

### Стек тестирования

- **Фреймворк**: pytest
- **Асинхронные тесты**: pytest-asyncio
- **Покрытие кода**: pytest-cov
- **Типизация**: mypy
- **Линтинг**: flake8
- **Форматирование**: black, isort

### Структура тестов

```
tests/
├── __init__.py
├── conft.py              # Фикстуры и общие настройки
├── test_config.py         # Тесты конфигурации
├── test_ai_client.py       # Тесты AI клиента
├── test_moex_client.py    # Тесты MOEX клиента
├── test_portfolio_manager.py # Тесты менеджера портфелей
├── test_telegram_bot.py   # Тесты Telegram бота
├── integration/           # Интеграционные тесты
└── e2e/                # End-to-end тесты
```

## ⚙️ Настройка окружения

### Локальная настройка

1. **Клонирование репозитория**:
```bash
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot
```

2. **Создание виртуального окружения**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

3. **Установка зависимостей**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Если есть
```

4. **Настройка переменных окружения**:
```bash
cp .env.example .env
# Отредактировать .env с тестовыми значениями
```

### Переменные окружения для тестов

```bash
# Тестовые переменные
TEST_DATABASE_URL=sqlite:///./test.db
TEST_TELEGRAM_BOT_TOKEN=test_token
TEST_AGENTROUTER_API_KEY=test_key
TEST_MOEX_BASE_URL=https://test.moex.com/iss
```

## 🚀 Запуск тестов

### Все тесты

```bash
pytest
```

### Конкретные тесты

```bash
# Тесты конфигурации
pytest tests/test_config.py

# Тесты AI клиента
pytest tests/test_ai_client.py

# Тесты с метками
pytest -m unit          # Только unit тесты
pytest -m integration    # Только интеграционные тесты
pytest -m slow          # Только медленные тесты
```

### С покрытием кода

```bash
pytest --cov=gazprom_bot --cov-report=html --cov-report=term
```

### Параллельный запуск

```bash
pytest -n auto  # Автоматическое определение количества ядер
```

## 📝 Типы тестов

### Unit тесты

- **Назначение**: Тестирование отдельных функций и классов
- **Изоляция**: Мокирование внешних зависимостей
- **Скорость**: Быстрое выполнение
- **Примеры**:
  - Валидация конфигурации
  - Расчет технических индикаторов
  - Форматирование промптов

### Интеграционные тесты

- **Назначение**: Тестирование взаимодействия между компонентами
- **Зависимости**: Реальные базы данных, API
- **Среда**: Изолированная тестовая среда
- **Примеры**:
  - Взаимодействие с базой данных
  - Интеграция с MOEX API
  - Обработка AI рекомендаций

### End-to-End тесты

- **Назначение**: Тестирование полных пользовательских сценариев
- **Среда**: Близкая к production
- **Примеры**:
  - Полный цикл торговли
  - Обработка команд пользователя
  - Визуализация отчетов

### Тесты производительности

- **Назначение**: Проверка производительности критических путей
- **Метрики**: Время ответа, использование памяти
- **Примеры**:
  - Время получения AI рекомендации
  - Скорость обработки рыночных данных
  - Производительность базы данных

## ✍️ Написание тестов

### Структура теста

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestModuleName:
    """Тесты модуля ModuleName"""
    
    @pytest.fixture
    def setup_data(self):
        """Фикстура для подготовки данных"""
        return {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_function_success(self, setup_data):
        """Тест успешного выполнения функции"""
        # Подготовка
        mock_data = setup_data
        
        # Мокирование зависимостей
        with patch('module.external_dependency', new_callable=AsyncMock) as mock_dep:
            mock_dep.return_value = {"result": "success"}
            
            # Выполнение
            result = await module.function_to_test(mock_data)
            
            # Проверки
            assert result["success"] is True
            assert "result" in result
            mock_dep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_function_error(self):
        """Тест обработки ошибки"""
        with patch('module.external_dependency', new_callable=AsyncMock) as mock_dep:
            mock_dep.side_effect = Exception("Test error")
            
            # Проверка обработки исключения
            with pytest.raises(Exception, match="Test error"):
                await module.function_to_test({})
```

### Лучшие практики

1. **Описательные имена тестов**:
```python
def test_portfolio_manager_buy_insufficient_funds(self):
    # Хорошо: описывает сценарий
    pass

def test_buy(self):
    # Плохо: слишком общее
    pass
```

2. **Изоляция тестов**:
```python
# Используйте фикстуры для подготовки данных
@pytest.fixture
async def sample_portfolio(self):
    return Portfolio(user_id=12345, shares=100, cash=50000)

# Не используйте глобальные состояния
```

3. **Мокирование внешних зависимостей**:
```python
# Всегда мокируйте внешние API
@pytest.mark.asyncio
async def test_moex_client_api_error(self):
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = aiohttp.ClientError("API Error")
        
        client = MOEXClient()
        price = await client.get_current_price("GAZP")
        
        assert price is None
```

4. **Проверка граничных случаев**:
```python
@pytest.mark.parametrize("input_value,expected", [
    (0, 0),           # Минимальное значение
    (100, 100),       # Нормальное значение
    (-1, ValueError),   # Отрицательное значение
    (None, ValueError),  # None значение
])
def test_validate_quantity(self, input_value, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            validate_quantity(input_value)
    else:
        assert validate_quantity(input_value) == expected
```

## 🔄 CI/CD

### GitHub Actions

Проект использует GitHub Actions для автоматизации тестирования:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest-cov
    
    - name: Run tests
      run: pytest --cov=gazprom_bot --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Локальный CI

```bash
# Запуск всех проверок как в CI
tox

# Или последовательный запуск
flake8 gazprom_bot
mypy gazprom_bot
pytest --cov=gazprom_bot
```

## 📊 Метрики покрытия

### Цели покрытия

- **Общее покрытие**: > 80%
- **Критический код**: > 90%
- **Unit тесты**: > 85%
- **Интеграционные тесты**: > 75%

### Генерация отчетов

```bash
# HTML отчет
pytest --cov=gazprom_bot --cov-report=html

# Терминальный отчет
pytest --cov=gazprom_bot --cov-report=term

# XML отчет для CI
pytest --cov=gazprom_bot --cov-report=xml
```

### Анализ покрытия

```bash
# Проверка непокрытых строк
pytest --cov=gazprom_bot --cov-report=term-missing

# Детальный отчет по модулям
pytest --cov=gazprom_bot.config --cov-report=term
```

## 🐛 Отладка тестов

### Локальная отладка

```bash
# Запуск с отладчиком
pytest --pdb

# Остановка при первом падении
pytest -x

# Подробный вывод
pytest -v -s

# Запуск конкретного теста с отладкой
pytest tests/test_portfolio_manager.py::TestPortfolioManager::test_execute_trade_buy_success --pdb
```

### Логирование в тестах

```python
import logging

# Включение логов для отладки
@pytest.fixture(autouse=True)
def enable_logging():
    logging.getLogger("gazprom_bot").setLevel(logging.DEBUG)

# Или в конкретном тесте
def test_with_logging(self):
    with patch('gazprom_bot.logger.info') as mock_log:
        # Тестовый код
        mock_log.assert_called_with("Expected message")
```

### Профилирование тестов

```bash
# Поиск медленных тестов
pytest --durations=10

# Профилирование памяти
pytest --memprof

# Анализ покрытия производительности
pytest --cov=gazprom_bot --cov-profile
```

## 📋 Чек-лист перед коммитом

- [ ] Все тесты проходят локально
- [ ] Новые тесты покрывают новый код
- [ ] Покрытие кода не уменьшилось
- [ ] Линтинг проходит без ошибок
- [ ] Типизация проверяется без ошибок
- [ ] Интеграционные тесты обновлены
- [ ] Документация обновлена

## 🔧 Устранение неполадок

### Частые проблемы

1. **Асинхронные тесты не работают**:
```python
# Добавьте декоратор
@pytest.mark.asyncio
async def test_async_function(self):
    pass
```

2. **Мокирование не работает**:
```python
# Проверьте путь к модулю
with patch('gazprom_bot.module.Class') as mock_class:
    # Не 'module.Class', а полный путь
```

3. **База данных в тестах**:
```python
# Используйте отдельную тестовую БД
@pytest.fixture
async def test_db():
    # Создание временной БД
    engine = create_async_engine("sqlite:///./test.db")
    yield engine
    # Очистка после теста
    await engine.dispose()
```

### Полезные команды

```bash
# Пересоздать тестовую БД
pytest --create-db

# Запустить только упавшие тесты
pytest --lf

# Показать самые медленные тесты
pytest --durations=20

# Запустить тесты с определенным паттерном
pytest -k "portfolio"
```

## 📚 Дополнительные ресурсы

- [pytest документация](https://docs.pytest.org/)
- [pytest-asyncio документация](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov документация](https://pytest-cov.readthedocs.io/)
- [Mock объекты в Python](https://docs.python.org/3/library/unittest.mock.html)