# План оптимизации CI/CD пайплайна для Gazprom Trading Bot

## Обзор

Этот документ описывает план оптимизации существующего CI/CD пайплайна для улучшения производительности, сокращения времени сборки и развертывания.

## Текущие проблемы

1. **Последовательное выполнение задач** - увеличивает общее время сборки
2. **Неоптимальное кэширование** - кэшируется только pip, но не Docker слои
3. **Устаревшие версии Actions** - используются старые версии GitHub Actions
4. **Избыточные операции** - установка зависимостей происходит несколько раз
5. **Отсутствие параллелизма** - тесты, безопасность и сборка не могут выполняться параллельно
6. **Неэффективная Docker сборка** - отсутствует многоэтапная сборка и оптимизация слоев

## Оптимизированная конфигурация CI/CD

### 1. Обновленный .github/workflows/ci.yml

```yaml
name: CI/CD Pipeline (Optimized)

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

# Глобальные переменные для переиспользования
env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "18"

jobs:
  # Определение измененных файлов для условного выполнения
  changes:
    runs-on: ubuntu-latest
    outputs:
      python: ${{ steps.changes.outputs.python }}
      docker: ${{ steps.changes.outputs.docker }}
      docs: ${{ steps.changes.outputs.docs }}
      tests: ${{ steps.changes.outputs.tests }}
    steps:
    - uses: actions/checkout@v4
    - uses: dorny/paths-filter@v2
      id: changes
      with:
        filters: |
          python:
            - '**/*.py'
            - 'requirements.txt'
            - 'pyproject.toml'
          docker:
            - 'Dockerfile'
            - 'docker-compose.yml'
            - '.dockerignore'
          docs:
            - '**/*.md'
          tests:
            - 'tests/**'
            - 'pytest.ini'

  # Параллельное выполнение тестов и проверки безопасности
  test:
    runs-on: ubuntu-latest
    needs: changes
    if: needs.changes.outputs.python == 'true' || needs.changes.outputs.tests == 'true'
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt', '**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest-cov pytest-xdist
    
    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Type check with mypy
      run: |
        mypy gazprom_bot --ignore-missing-imports
    
    - name: Test with pytest (parallel)
      run: |
        pytest --cov=gazprom_bot --cov-report=xml --cov-report=html -n auto
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  # Проверка безопасности (параллельно с тестами)
  security:
    runs-on: ubuntu-latest
    needs: changes
    if: needs.changes.outputs.python == 'true' || needs.changes.outputs.tests == 'true'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install security tools
      run: |
        python -m pip install --upgrade pip
        pip install safety bandit semgrep
    
    - name: Check dependencies for known security vulnerabilities
      run: |
        safety check --json --output safety-report.json || true
    
    - name: Run bandit security linter
      run: |
        bandit -r gazprom_bot -f json -o bandit-report.json || true
    
    - name: Run semgrep for advanced security analysis
      run: |
        semgrep --config=auto --json --output=semgrep-report.json . || true
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          safety-report.json
          bandit-report.json
          semgrep-report.json

  # Сборка Docker образа с оптимизированным кэшированием
  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && (needs.changes.outputs.python == 'true' || needs.changes.outputs.docker == 'true')
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: gazprom-trading-bot
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
    
    - name: Build and push Docker image (with cache)
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./Dockerfile.optimized
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        platforms: linux/amd64,linux/arm64

  # Развертывание с нулевым простоем (zero-downtime)
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production (zero-downtime)
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.PROD_HOST }}
        username: ${{ secrets.PROD_USER }}
        key: ${{ secrets.PROD_SSH_KEY }}
        script: |
          cd /opt/gazprom-bot
          
          # Создание резервной копии текущего контейнера
          docker tag gazprom-trading-bot:latest gazprom-trading-bot:backup
          
          # Плавное обновление с нулевым простоем
          docker-compose pull
          docker-compose up -d --no-deps gazprom-bot
          
          # Проверка здоровья нового контейнера
          sleep 30
          if ! curl -f http://localhost:8000/health; then
            echo "Health check failed, rolling back..."
            docker-compose down
            docker run -d --name gazprom-bot-backup gazprom-trading-bot:backup
            exit 1
          fi
          
          # Очистка
          docker system prune -f
          docker rmi gazprom-trading-bot:backup || true
    
    - name: Run health check
      run: |
        sleep 30
        curl -f ${{ secrets.PROD_URL }}/health || exit 1

  # Улучшенные уведомления
  notify:
    needs: [deploy]
    runs-on: ubuntu-latest
    if: always()
    
    steps:
    - name: Notify on success
      if: needs.deploy.result == 'success'
      uses: 8398a7/action-slack@v3
      with:
        status: success
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        text: |
          🚀 Gazprom Trading Bot deployed successfully to production!
          
          📊 Build stats:
          • Duration: ${{ job.status }}
          • Commit: ${{ github.sha }}
          • Branch: ${{ github.ref_name }}
    
    - name: Notify on failure
      if: needs.deploy.result == 'failure'
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        text: |
          ❌ Gazprom Trading Bot deployment failed!
          
          🐛 Debug info:
          • Commit: ${{ github.sha }}
          • Branch: ${{ github.ref_name }}
          • Workflow: ${{ github.workflow }}
```

### 2. Оптимизированный Dockerfile

```dockerfile
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
```

### 3. Оптимизированный docker-compose.yml

```yaml
version: '3.8'

services:
  gazprom-bot:
    build: 
      context: .
      dockerfile: Dockerfile.optimized
      cache_from:
        - gazprom-trading-bot:latest
    container_name: gazprom-trading-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - gazprom-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  # Redis для кэширования (production)
  redis:
    image: redis:7-alpine
    container_name: gazprom-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - gazprom-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

networks:
  gazprom-network:
    driver: bridge

volumes:
  redis_data:
    driver: local
  gazprom_data:
    driver: local
```

## Ожидаемые улучшения производительности

1. **Сокращение времени сборки на 40-60%** за счет:
   - Параллельного выполнения тестов и проверки безопасности
   - Улучшенного кэширования Docker слоев
   - Многоэтапной сборки Docker

2. **Уменьшение размера Docker образа на 30-40%** за счет:
   - Многоэтапной сборки
   - Удаления ненужных зависимостей
   - Оптимизации слоев

3. **Улучшение надежности развертывания** за счет:
   - Zero-downtime развертывания
   - Улучшенных health checks
   - Автоматического отката при ошибках

4. **Сокращение времени выполнения тестов** за счет:
   - Параллельного запуска тестов
   - Оптимизированного кэширования зависимостей
   - Условного выполнения тестов

## Следующие шаги

1. Обновить Dockerfile с многоэтапной сборкой
2. Обновить docker-compose.yml с оптимизациями
3. Обновить .github/workflows/ci.yml с параллельным выполнением
4. Настроить улучшенное кэширование
5. Добавить условное выполнение задач
6. Тестирование оптимизированного пайплайна
7. Мониторинг производительности после внедрения