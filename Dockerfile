# Gazprom Trading Bot - Оптимизированный Dockerfile с многоэтапной сборкой

# Этап 1: Сборка зависимостей
FROM python:3.11-slim as builder

# Установка рабочих переменных
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Этап 2: Финальный образ
FROM python:3.11-slim as runtime

# Установка рабочих переменных
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Установка только необходимых системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование виртуального окружения из этапа сборки
COPY --from=builder /opt/venv /opt/venv

# Создание рабочей директории
WORKDIR /app

# Копирование исходного кода
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data /app/logs

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Экспорт порта
EXPOSE 8000

# Оптимизированный health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска
CMD ["python", "run.py"]