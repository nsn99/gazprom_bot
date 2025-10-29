"""
Health checks для Gazprom Trading Bot
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from monitoring.logger import get_logger
from database.database import get_db_manager
from ai.client import AgentRouterClient
from data.client import get_moex_client


logger = get_logger(__name__)
app = FastAPI(title="Gazprom Trading Bot Health API")


@app.get("/health")
async def health_check():
    """Базовый health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Детальный health check с проверкой всех компонентов"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "checks": {}
    }
    
    # Проверка базы данных
    db_status = await check_database()
    health_status["checks"]["database"] = db_status
    
    # Проверка AgentRouter API
    ai_status = await check_agentrouter()
    health_status["checks"]["agentrouter"] = ai_status
    
    # Проверка MOEX API
    moex_status = await check_moex()
    health_status["checks"]["moex"] = moex_status
    
    # Проверка памяти
    memory_status = check_memory()
    health_status["checks"]["memory"] = memory_status
    
    # Определение общего статуса
    all_healthy = all(
        check["status"] == "healthy" 
        for check in health_status["checks"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "unhealthy"
    
    return JSONResponse(
        content=health_status,
        status_code=200 if all_healthy else 503
    )


async def check_database() -> Dict[str, Any]:
    """Проверка подключения к базе данных"""
    try:
        start_time = time.time()
        db_manager = get_db_manager()
        
        # Простая проверка подключения
        session = await db_manager.get_session()
        await session.execute("SELECT 1")
        await session.close()
        
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def check_agentrouter() -> Dict[str, Any]:
    """Проверка подключения к AgentRouter API"""
    try:
        start_time = time.time()
        
        # Создание тестового клиента
        client = AgentRouterClient(settings.AGENTROUTER_API_KEY)
        
        # Тестовый запрос (можно использовать минимальные параметры)
        test_context = {
            "portfolio": {"cash": 100000, "shares": 0},
            "market_data": {"current_price": 160.0},
            "risk_settings": {"max_position_percent": 30}
        }
        
        # Ограничиваем время выполнения
        try:
            result = await asyncio.wait_for(
                client.get_trading_recommendation(test_context),
                timeout=10.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result.get("success"):
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "error": result.get("error", "Unknown error"),
                    "response_time_ms": round(response_time, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "Request timeout",
                "response_time_ms": 10000,
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"AgentRouter health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def check_moex() -> Dict[str, Any]:
    """Проверка подключения к MOEX API"""
    try:
        start_time = time.time()
        moex_client = get_moex_client()
        
        # Тестовый запрос
        async with moex_client:
            price = await asyncio.wait_for(
                moex_client.get_current_price("GAZP"),
                timeout=10.0
            )
        
        response_time = (time.time() - start_time) * 1000
        
        if price is not None:
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "current_price": price,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "error": "No price data available",
                "response_time_ms": round(response_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except asyncio.TimeoutError:
        return {
            "status": "unhealthy",
            "error": "Request timeout",
            "response_time_ms": 10000,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"MOEX health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def check_memory() -> Dict[str, Any]:
    """Проверка использования памяти"""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "status": "healthy",
            "system_memory_percent": memory.percent,
            "process_memory_mb": round(process_memory.rss / 1024 / 1024, 2),
            "available_memory_gb": round(memory.available / 1024 / 1024 / 1024, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ImportError:
        # psutil не установлен
        return {
            "status": "unknown",
            "error": "psutil not installed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/metrics")
async def metrics():
    """Базовые метрики приложения"""
    try:
        db_manager = get_db_manager()
        
        # Получение базовой статистики
        stats = await db_manager.get_daily_statistics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "daily_stats": stats,
            "uptime_seconds": time.time() - start_time
        }
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ready")
async def readiness_check():
    """Проверка готовности приложения к работе"""
    # Проверяем, что все критические компоненты работают
    db_status = await check_database()
    ai_status = await check_agentrouter()
    
    if db_status["status"] == "healthy" and ai_status["status"] in ["healthy", "degraded"]:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/live")
async def liveness_check():
    """Проверка того, что приложение работает"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


# Время запуска приложения
start_time = time.time()


if __name__ == "__main__":
    logger.info("Starting health check server")
    
    # Запуск health check сервера
    uvicorn.run(
        "health:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )