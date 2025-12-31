"""
ARK YOLO FastAPI Application - Main Entry Point

Este é o ponto de entrada da aplicação FastAPI.
Equivalente ao app.py do Flask, mas com arquitetura assíncrona.

Autor: Você
Data: 30/12/2024
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Importar configurações
from fastapi_app.core.config import settings, validate_settings, print_settings


# ============================================
# LIFESPAN: Gerencia startup/shutdown
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação
    
    Equivalente a:
    - Flask: if __name__ == "__main__"
    - Startup: Código que roda antes de aceitar requests
    - Shutdown: Código que roda ao desligar servidor
    """
    
    # ========== STARTUP ==========
    print("\n" + "="*70)
    print("🚀 ARK YOLO FastAPI - INICIANDO")
    print("="*70)
    
    # Exibir configurações
    print_settings()
    
    # Validar configurações
    errors, warnings = validate_settings()
    
    if errors:
        print("\n❌ ERROS CRÍTICOS:")
        for error in errors:
            print(f"  {error}")
        print("\n⚠️  Servidor NÃO iniciado devido a erros!")
        raise RuntimeError("Configuração inválida")
    
    if warnings:
        print("\n⚠️  AVISOS:")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n✅ Servidor pronto para aceitar requisições!")
    print("="*70 + "\n")
    
    # Aqui a aplicação roda (yield = pausa aqui)
    yield
    
    # ========== SHUTDOWN ==========
    print("\n" + "="*70)
    print("🛑 ARK YOLO FastAPI - DESLIGANDO")
    print("="*70)
    print("✅ Shutdown completo!")
    print("="*70 + "\n")


# ============================================
# CRIAR APLICAÇÃO FASTAPI
# ============================================
app = FastAPI(
    title="ARK YOLO API",
    description="Sistema de Detecção de Pessoas e Monitoramento de Zonas em Tempo Real",
    version="2.0.0",
    
    # Documentação automática (Swagger UI)
    docs_url="/docs",           # http://localhost:8000/docs
    redoc_url="/redoc",          # http://localhost:8000/redoc
    openapi_url="/openapi.json", # Schema OpenAPI
    
    # Lifecycle events
    lifespan=lifespan
)


# ============================================
# MIDDLEWARES
# ============================================

# 1. CORS - Permitir acesso de outros domínios
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # De .env.fastapi
    allow_credentials=True,                     # Cookies/Auth
    allow_methods=["*"],                        # GET, POST, PUT, DELETE, etc
    allow_headers=["*"],                        # Todos os headers
)

# 2. GZip - Compressão de respostas
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Comprimir respostas > 1KB
)


# ============================================
# ROTAS BÁSICAS (vamos expandir depois)
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """
    Rota raiz - Informações básicas da API
    
    Returns:
        dict: Mensagem de boas-vindas e links úteis
    """
    return {
        "message": "🎮 ARK YOLO API v2.0",
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health Check - Verifica se o servidor está respondendo
    
    Usado por:
    - Docker health checks
    - Kubernetes liveness probes
    - Load balancers
    
    Returns:
        dict: Status do servidor
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "2.0.0"
    }


@app.get("/info", tags=["Info"])
async def info():
    """
    Informações do sistema
    
    Returns:
        dict: Configurações não-sensíveis
    """
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "yolo_model": settings.YOLO_MODEL_PATH,
        "video_source": settings.VIDEO_SOURCE,
        "database": settings.DATABASE_URL.split("///")[-1],  # Só o nome do arquivo
    }


# ============================================
# ENTRY POINT (quando executar diretamente)
# ============================================
if __name__ == "__main__":
    """
    Roda o servidor com Uvicorn
    
    Uso:
        python -m fastapi_app.main
    
    OU (desenvolvimento com hot-reload):
        uvicorn fastapi_app.main:app --reload
    """
    
    uvicorn.run(
        "fastapi_app.main:app",  # Caminho para a aplicação
        host=settings.HOST,       # 0.0.0.0 = aceita conexões de qualquer IP
        port=settings.PORT,       # 8000
        reload=settings.DEBUG,    # Auto-reload em desenvolvimento
        log_level="info"          # info, debug, warning, error
    )
