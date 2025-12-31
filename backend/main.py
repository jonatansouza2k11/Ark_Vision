"""
backend/main.py
FastAPI Application - Computer Vision Monitoring System
RAG-Ready Architecture
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uvicorn")

# Imports locais
from config import settings
import database
from middleware.security import setup_middleware
from dependencies import limiter
from slowapi.errors import RateLimitExceeded

# Import routers
from api.auth import router as auth_router
from api.users import router as users_router 
from api.settings import router as settings_router  
from api.admin import router as admin_router  

# ============================================
# LIFESPAN EVENTS (startup/shutdown)
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia lifecycle da aplicação
    - startup: Conecta ao banco
    - shutdown: Fecha conexões
    """
    # 🟢 STARTUP
    logger.info("=" * 70)
    logger.info("🚀 Starting FastAPI Application")
    logger.info("=" * 70)
    
    # Conectar ao banco
    try:
        await database.get_db_pool()
        logger.info("✅ PostgreSQL connected")
        
        # Criar tabelas se não existirem
        await database.init_database(force_recreate=False)
        logger.info("✅ Database tables ready")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise
    
    logger.info("=" * 70)
    logger.info(f"🌐 API running on: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info("🎯 All systems ready!")
    logger.info("=" * 70)
    
    yield  # Aplicação roda aqui
    
    # 🔴 SHUTDOWN
    logger.info("=" * 70)
    logger.info("🛑 Shutting down FastAPI Application")
    logger.info("=" * 70)
    
    # Fechar pool do banco
    await database.close_db_pool()
    logger.info("✅ Database connections closed")
    
    logger.info("👋 Goodbye!")
    logger.info("=" * 70)

# ============================================
# CREATE FASTAPI APP
# ============================================
app = FastAPI(
    title="Computer Vision Monitoring API",
    description="""
    ## 🎥 Sistema de Monitoramento com Detecção por IA
    
    API RESTful para sistema de monitoramento com YOLO, tracking e alertas.
    
    ### 🔐 Autenticação
    - JWT Bearer token
    - Rate limiting habilitado
    
    ### 🤖 RAG-Ready
    - PostgreSQL com suporte a vetores (futuro)
    - Histórico de conversas
    - Knowledge base integrada
    
    ### 📊 Features
    - Autenticação JWT
    - YOLO detection & tracking
    - Smart zones & alertas
    - Logs de auditoria
    - Backup automático
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ============================================
# SETUP MIDDLEWARE & RATE LIMITER
# ============================================
setup_middleware(app) #para testar

# ✅ Register rate limiter
app.state.limiter = limiter

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handler para rate limit exceeded"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "type": "rate_limit_exceeded"
        }
    )

# ============================================
# INCLUDE ROUTERS
# ============================================
app.include_router(auth_router)
app.include_router(users_router)  
app.include_router(settings_router)  
app.include_router(admin_router) 
# ============================================
# ROOT ENDPOINT
# ============================================
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint com informações da API
    """
    return {
        "message": "Computer Vision Monitoring API",
        "version": "1.0.0",
        "status": "running",
        "docs": f"http://{settings.HOST}:{settings.PORT}/docs" if settings.DEBUG else "disabled",
        "features": [
            "JWT Authentication",
            "YOLO Detection",
            "Object Tracking",
            "Smart Zones",
            "Real-time Alerts",
            "Audit Logging",
            "RAG-Ready Architecture"
        ]
    }

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Verifica saúde da API e dependências
    """
    health_status = {
        "status": "healthy",
        "api": "running",
        "database": "unknown",
        "version": "1.0.0"
    }
    
    # Verifica conexão com banco
    try:
        pool = await database.get_db_pool()
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

# ============================================
# MAIN (para debug com python main.py)
# ============================================
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("⚠️  MODO DEBUG - NÃO USAR EM PRODUÇÃO")
    print("=" * 70)
    print(f"Starting server at http://{settings.HOST}:{settings.PORT}")
    print(f"Docs at http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 70)
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
