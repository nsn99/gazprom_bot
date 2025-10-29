# Gazprom Trading Bot - Dockerfile
FROM python:3.11-slim

# Установка рабочих переменных
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование файла с зависимостями
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Экспорт порта (если нужен для health checks)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска
CMD ["python", "run.py"]