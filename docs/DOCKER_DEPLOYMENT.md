# Руководство по Docker развертыванию Gazprom Trading Bot

## 📋 Содержание

- [Обзор](#-обзор)
- [Требования](#-требования)
- [Локальное развертывание](#-локальное-развертывание)
- [Production развертывание](#-production-развертывание)
- [Docker Compose](#-docker-compose)
- [Kubernetes](#-kubernetes)
- [Мониторинг](#-мониторинг)
- [Резервное копирование](#-резервное-копирование)
- [Устранение неполадок](#-устранение-неполадок)

## 🎯 Обзор

Docker-контейнеризация Gazprom Trading Bot обеспечивает:

- **Изоляцию**: Приложение изолировано от хост-системы
- **Портативность**: Легкое развертывание на любой платформе
- **Масштабируемость**: Простое горизонтальное масштабирование
- **Версионирование**: Контроль версий через теги образов
- **Восстановление**: Быстрое восстановление после сбоев

## 📋 Требования

### Системные требования

- **Docker**: 20.10+ или Docker Desktop
- **Docker Compose**: 2.0+ (для compose развертывания)
- **Kubernetes**: 1.24+ (для K8s развертывания)
- **Память**: Минимум 512MB, рекомендуется 1GB+
- **Диск**: Минимум 1GB свободного пространства

### Переменные окружения

Обязательные переменные:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AgentRouter API
AGENTROUTER_API_KEY=sk-your_agentrouter_api_key

# База данных
DATABASE_URL=sqlite:///./data/gazprom_bot.db
```

Опциональные переменные:

```bash
# Настройки приложения
DEBUG=false
LOG_LEVEL=INFO
DEFAULT_INITIAL_CAPITAL=100000.0

# MOEX API
MOEX_CACHE_TTL=60
REQUEST_TIMEOUT=30

# AI
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
```

## 🏠 Локальное развертывание

### Сборка образа

```bash
# Клонирование репозитория
git clone https://github.com/your-repo/gazprom-trading-bot.git
cd gazprom-trading-bot

# Сборка Docker образа
docker build -t gazprom-bot:latest .
```

### Запуск контейнера

```bash
# Создание директории для данных
mkdir -p ./data

# Запуск контейнера
docker run -d \
  --name gazprom-bot \
  --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  gazprom-bot:latest
```

### Проверка работы

```bash
# Просмотр логов
docker logs -f gazprom-bot

# Проверка статуса
docker exec gazprom-bot curl -f http://localhost:8000/health

# Вход в контейнер
docker exec -it gazprom-bot /bin/bash
```

## 🚀 Production развертывание

### Подготовка

1. **Настройка production переменных**:
```bash
# Создание production .env файла
cp .env.example .env.production

# Редактирование с реальными значениями
nano .env.production
```

2. **Сборка production образа**:
```bash
# Сборка с production тегом
docker build -t gazprom-bot:production .

# Или с версией
docker build -t gazprom-bot:v1.0.0 .
```

3. **Настройка volumes**:
```bash
# Создание директорий для данных
sudo mkdir -p /opt/gazprom-bot/{data,logs,backups}
sudo chown -R 1000:1000 /opt/gazprom-bot
```

### Запуск в production

```bash
# Запуск с production конфигурацией
docker run -d \
  --name gazprom-bot-prod \
  --restart unless-stopped \
  --env-file .env.production \
  -v /opt/gazprom-bot/data:/app/data \
  -v /opt/gazprom-bot/logs:/app/logs \
  -v /opt/gazprom-bot/backups:/app/backups \
  --memory=1g \
  --cpus=0.5 \
  gazprom-bot:production
```

### Production оптимизации

```bash
# Ограничение ресурсов
docker run -d \
  --memory=512m \
  --cpus=0.25 \
  --pids-limit=50 \
  --ulimit nofile=1024:1024 \
  gazprom-bot:production

# Настройка логирования
docker run -d \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  gazprom-bot:production

# Безопасный запуск
docker run -d \
  --read-only \
  --tmpfs /tmp \
  --user 1000:1000 \
  --cap-drop ALL \
  --cap-add CHOWN \
  --cap-add SETGID \
  --cap-add SETUID \
  gazprom-bot:production
```

## 🐙 Docker Compose

### Базовый compose файл

```yaml
version: '3.8'

services:
  gazprom-bot:
    build: .
    container_name: gazprom-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8000:8000"  # Health checks
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Production compose файл

```yaml
version: '3.8'

services:
  gazprom-bot:
    image: gazprom-bot:production
    container_name: gazprom-bot-prod
    restart: unless-stopped
    env_file:
      - .env.production
    volumes:
      - /opt/gazprom-bot/data:/app/data
      - /opt/gazprom-bot/logs:/app/logs
      - /opt/gazprom-bot/backups:/app/backups
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Запуск compose

```bash
# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Пересборка и запуск
docker-compose up -d --build
```

## ☸️ Kubernetes

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gazprom-bot
  labels:
    name: gazprom-bot
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gazprom-bot-config
  namespace: gazprom-bot
data:
  DATABASE_URL: "sqlite:///./data/gazprom_bot.db"
  LOG_LEVEL: "INFO"
  MOEX_CACHE_TTL: "60"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gazprom-bot-secrets
  namespace: gazprom-bot
type: Opaque
data:
  TELEGRAM_BOT_TOKEN: <base64-encoded-token>
  AGENTROUTER_API_KEY: <base64-encoded-key>
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gazprom-bot
  namespace: gazprom-bot
  labels:
    app: gazprom-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gazprom-bot
  template:
    metadata:
      labels:
        app: gazprom-bot
    spec:
      containers:
      - name: gazprom-bot
        image: gazprom-bot:production
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: gazprom-bot-config
              key: DATABASE_URL
        - name: TELEGRAM_BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: gazprom-bot-secrets
              key: TELEGRAM_BOT_TOKEN
        - name: AGENTROUTER_API_KEY
          valueFrom:
            secretKeyRef:
              name: gazprom-bot-secrets
              key: AGENTROUTER_API_KEY
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: gazprom-bot-data
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gazprom-bot-service
  namespace: gazprom-bot
spec:
  selector:
    app: gazprom-bot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### PersistentVolume

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: gazprom-bot-data
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
```

### Развертывание

```bash
# Применение манифестов
kubectl apply -f k8s/

# Проверка статуса
kubectl get pods -n gazprom-bot

# Просмотр логов
kubectl logs -f deployment/gazprom-bot -n gazprom-bot

# Масштабирование
kubectl scale deployment gazprom-bot --replicas=3 -n gazprom-bot
```

## 📊 Мониторинг

### Health Checks

```bash
# Базовый health check
curl http://localhost:8000/health

# Детальный health check
curl http://localhost:8000/health/detailed

# Метрики
curl http://localhost:8000/metrics

# Готовность
curl http://localhost:8000/ready

# Живучесть
curl http://localhost:8000/live
```

### Логирование

```bash
# Просмотр логов контейнера
docker logs gazprom-bot

# Просмотр логов compose
docker-compose logs gazprom-bot

# Фильтрация логов
docker logs gazprom-bot | grep ERROR

# Просмотр логов в реальном времени
docker logs -f gazprom-bot
```

### Мониторинг ресурсов

```bash
# Использование памяти
docker stats gazprom-bot --no-stream

# Использование CPU
docker top gazprom-bot

# Детальная статистика
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
```

## 💾 Резервное копирование

### Резервирование данных

```bash
# Создание бэкапа данных
docker exec gazprom-bot tar -czf /tmp/data-backup.tar.gz /app/data

# Копирование бэкапа на хост
docker cp gazprom-bot:/tmp/data-backup.tar.gz ./backups/

# Автоматическое резервирование
docker run -d \
  --name gazprom-bot-backup \
  --volumes-from gazprom-bot \
  -v $(pwd)/backups:/backup \
  alpine:latest \
  tar -czf /backup/data-$(date +%Y%m%d-%H%M%S).tar.gz /app/data
```

### Восстановление

```bash
# Остановка контейнера
docker stop gazprom-bot

# Восстановление данных
docker run --rm \
  -v $(pwd)/backups/data-backup.tar.gz:/backup.tar.gz \
  -v $(pwd)/data:/data \
  alpine:latest \
  tar -xzf /backup.tar.gz -C /data

# Запуск контейнера
docker start gazprom-bot
```

## 🔧 Устранение неполадок

### Частые проблемы

1. **Контейнер не запускается**:
```bash
# Проверка логов
docker logs gazprom-bot

# Проверка переменных окружения
docker exec gazprom-bot env | grep -E "(TELEGRAM|AGENTROUTER|DATABASE)"

# Проверка прав доступа
ls -la ./data
```

2. **Нет доступа к API**:
```bash
# Проверка сети
docker network ls
docker network inspect gazprom-bot_default

# Проверка портов
docker port gazprom-bot

# Тест подключения
docker exec gazprom-bot curl -f http://localhost:8000/health
```

3. **Проблемы с базой данных**:
```bash
# Проверка volume
docker volume ls
docker volume inspect gazprom-bot_data

# Проверка прав доступа
docker exec gazprom-bot ls -la /app/data

# Пересоздание volume
docker-compose down -v
docker-compose up -d
```

4. **Высокое использование памяти**:
```bash
# Ограничение памяти
docker run -d --memory=512m gazprom-bot

# Очистка кэша
docker exec gazprom-bot rm -rf /tmp/*

# Перезапуск контейнера
docker restart gazprom-bot
```

### Диагностика

```bash
# Проверка состояния контейнера
docker inspect gazprom-bot

# Проверка событий
docker events --filter container=gazprom-bot

# Вход в контейнер для диагностики
docker exec -it gazprom-bot /bin/bash

# Проверка процессов в контейнере
docker exec gazprom-bot ps aux
```

### Обновление

```bash
# Остановка и удаление старого контейнера
docker stop gazprom-bot
docker rm gazprom-bot

# Сборка нового образа
docker build -t gazprom-bot:new .

# Запуск с новым образом
docker run -d --name gazprom-bot gazprom-bot:new

# Или через compose
docker-compose pull
docker-compose up -d
```

## 📋 Чек-лист развертывания

- [ ] Docker образ успешно собран
- [ ] Все переменные окружения настроены
- [ ] Volumes примонтированы
- [ ] Health checks работают
- [ ] Логирование настроено
- [ ] Резервное копирование настроено
- [ ] Мониторинг настроен
- [ ] Безопасность настроена
- [ ] Производительность оптимизирована
- [ ] Документация обновлена

## 📚 Дополнительные ресурсы

- [Docker документация](https://docs.docker.com/)
- [Docker Compose документация](https://docs.docker.com/compose/)
- [Kubernetes документация](https://kubernetes.io/docs/)
- [Best practices](https://docs.docker.com/develop/dev-best-practices/)