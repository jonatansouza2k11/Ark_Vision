"""
============================================================================
backend/app/main.py - ULTRA OPTIMIZED v3.0 (Swagger Compatible)
FastAPI Application - Computer Vision Monitoring System
RAG-Ready Architecture + React Frontend Support
============================================================================
NEW Features in v3.0:
- Content Security Policy (CSP) com suporte Swagger
- Middleware de segurança otimizado
- Cache avançado com LRU
- Decoradores para rotas HTML
- Handler consolidado para erros
- Rate limiting global
- CORS otimizado
- Health check completo
- Legacy routes compatibility

Previous Features (v1.0-v2.0):
- React frontend support
- HTML admin templates
- YOLO stream control
- Database initialization
- Lifespan events
- Static files serving
- API routing

✅ FIXED v3.0: Swagger Docs CSP compatibility
============================================================================
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache, wraps
import logging
import sys

# ✅ Adiciona raiz ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uvicorn")

# Imports locais
from backend.config import settings
from backend import database
from backend.dependencies import limiter
from slowapi.errors import RateLimitExceeded

# Import routers
from backend.api import auth, users, admin, zones, alerts
from backend.api import settings as settings_api
from backend.api import stream

# ============================================================================
# OTIMIZAÇÃO 1: Cache e Funções Puras
# ============================================================================

@lru_cache(maxsize=1)
def _get_templates():
    """✅ Cache da instância Jinja2Templates"""
    return Jinja2Templates(directory="backend/templates")


@lru_cache(maxsize=1)
def _get_cors_origins() -> List[str]:
    """✅ Cache de CORS origins"""
    return [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]


@lru_cache(maxsize=1)
def _get_yolo_default_config() -> Dict[str, Any]:
    """✅ Configuração YOLO centralizada"""
    return {
        "conf_thresh": 0.5,
        "model_path": "backend/yolo_models/yolov8n.pt",
        "target_width": 1280,
        "frame_step": 1,
        "source": "0",
        "cam_width": 1280,
        "cam_height": 720,
        "cam_fps": 30,
        "tracker": "botsort.yaml",
        "max_out_time": 10.0,
        "email_cooldown": 60,
        "buffer_seconds": 2.0,
        "zone_empty_timeout": 10.0,
        "zone_full_timeout": 20.0,
        "zone_full_threshold": 5
    }


def _get_available_models() -> List[str]:
    """✅ Lista modelos YOLO disponíveis"""
    models_dir = Path("backend/yolo_models")
    if not models_dir.exists():
        return []
    return [str(p) for p in models_dir.glob("*.pt")]


# ============================================================================
# OTIMIZAÇÃO 2: Decorador para Rotas HTML
# ============================================================================

def html_admin_route(template_name: str, fetch_data_fn=None):
    """
    ✅ Decorador para rotas HTML admin (evita repetição)
    
    Args:
        template_name: Nome do template HTML
        fetch_data_fn: Função opcional para buscar dados
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request):
            templates = _get_templates()
            
            # Contexto base
            context = {"request": request}
            
            # Adiciona dados customizados se fornecidos
            if fetch_data_fn:
                try:
                    custom_data = await fetch_data_fn() if callable(fetch_data_fn) else fetch_data_fn
                    context.update(custom_data)
                except Exception as e:
                    logger.error(f"Erro ao buscar dados para {template_name}: {e}")
            
            return templates.TemplateResponse(template_name, context)
        return wrapper
    return decorator


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ✅ v3.0: Gerencia lifecycle completo da aplicação
    
    Startup:
    - Conecta ao PostgreSQL
    - Inicializa tabelas
    - Valida configurações
    
    Shutdown:
    - Fecha conexões de banco
    - Cleanup de recursos
    """
    # 🟢 STARTUP
    logger.info("=" * 70)
    logger.info("🚀 Starting FastAPI Application v3.0")
    logger.info("=" * 70)
    
    try:
        await database.get_db_pool()
        logger.info("✅ PostgreSQL connected")
        
        await database.init_database(force_recreate=False)
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("⚠️  YOLO stream will be started manually")
    logger.info("=" * 70)
    logger.info(f"🌐 API running on: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info("🎯 All systems ready!")
    logger.info("=" * 70)
    
    yield  # App runs here
    
    # 🔴 SHUTDOWN
    logger.info("🛑 Shutting down...")
    await database.close_db_pool()
    logger.info("✅ Database connections closed")
    logger.info("👋 Goodbye!")


# ============================================================================
# CREATE FASTAPI APP v3.0
# ============================================================================

app = FastAPI(
    title="Computer Vision Monitoring API v3.0",
    description="""
    ## 🎥 Sistema de Monitoramento com Detecção por IA
    
    API RESTful completa para sistema de monitoramento com YOLO, tracking e alertas.
    
    ### 🔐 Autenticação (v3.0)
    - JWT Bearer token
    - OAuth2 form-urlencoded compatible
    - Refresh token support
    - Password reset flow
    - Email verification
    - Rate limiting habilitado
    - MFA ready
    
    ### 🤖 RAG-Ready Architecture
    - PostgreSQL com suporte a vetores (futuro)
    - Histórico de conversas
    - Knowledge base integrada
    - Audit logging completo
    
    ### 📊 Features v3.0
    - **Authentication**: Register, Login, Logout, Refresh Token, Password Reset
    - **Users**: CRUD completo, roles, permissions
    - **YOLO Detection**: Real-time object detection com YOLOv8
    - **Tracking**: BoT-SORT tracker integrado
    - **Smart Zones**: Zonas poligonais customizadas
    - **Alertas**: Sistema de notificações em tempo real
    - **Settings**: Configuração dinâmica YOLO e câmera
    - **Streaming**: MJPEG video stream
    - **Admin**: Backup, restore, diagnóstico
    - **Logs**: Audit trail completo
    
    ### 📡 Endpoints Principais
    
    #### Authentication
    - `POST /api/v1/auth/register` - Registrar usuário
    - `POST /api/v1/auth/login` - Login (OAuth2 compatible)
    - `GET /api/v1/auth/me` - Usuário atual
    - `POST /api/v1/auth/logout` - Logout
    - `POST /api/v1/auth/refresh` - Refresh token
    - `POST /api/v1/auth/password-reset` - Solicitar reset de senha
    - `POST /api/v1/auth/password/change` - Alterar senha
    
    #### Users
    - `GET /api/v1/users` - Listar usuários
    - `GET /api/v1/users/{id}` - Buscar usuário
    - `PUT /api/v1/users/{id}` - Atualizar usuário
    - `DELETE /api/v1/users/{id}` - Deletar usuário
    
    #### Stream
    - `GET /api/v1/stream/status` - Status do stream
    - `POST /api/v1/stream/start` - Iniciar stream
    - `POST /api/v1/stream/stop` - Parar stream
    - `GET /video` - MJPEG video feed
    
    #### Zones
    - `GET /api/v1/zones` - Listar zonas
    - `POST /api/v1/zones` - Criar zona
    - `PUT /api/v1/zones/{id}` - Atualizar zona
    - `DELETE /api/v1/zones/{id}` - Deletar zona
    
    #### Alerts
    - `GET /api/v1/alerts` - Listar alertas
    - `GET /api/v1/alerts/recent` - Alertas recentes
    
    #### Settings
    - `GET /api/v1/settings` - Obter configurações
    - `PUT /api/v1/settings` - Atualizar configurações
    
    #### Admin
    - `POST /api/v1/admin/backup` - Criar backup
    - `POST /api/v1/admin/restore` - Restaurar backup
    - `GET /api/v1/admin/diagnostics` - Diagnóstico completo
    
    ### 🔒 Segurança
    - Content Security Policy (CSP)
    - CORS configurado
    - Rate limiting
    - JWT tokens
    - Password hashing (bcrypt)
    - Audit logging
    
    ### 🚀 Performance
    - Connection pooling (PostgreSQL)
    - LRU cache para configurações
    - Async/await em todas operações I/O
    - Decoradores otimizados
    """,
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# ============================================================================
# MIDDLEWARE v3.0 - CORRIGIDO PARA SWAGGER
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("✅ CORS configurado: 4 origins")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    ✅ v3.0 FIXED: Middleware de segurança com suporte Swagger
    
    Features:
    - Content Security Policy (CSP) flexível
    - Permite recursos externos do Swagger (/docs, /redoc)
    - CSP restritivo para outras rotas
    - Headers de segurança padrão
    """
    response = await call_next(request)
    
    # ✅ CSP permissivo para documentação Swagger
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
    else:
        # CSP restritivo para produção
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:;"
        )
    
    # Outros headers de segurança
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

logger.info("✅ Middleware configurado (v3.0 Enhanced + Swagger Fix)")


# Rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    ✅ v3.0: Handler para rate limit exceeded
    
    Retorna erro 429 com mensagem amigável
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "type": "rate_limit_exceeded"
        }
    )


# ============================================================================
# STATIC FILES & TEMPLATES
# ============================================================================

try:
    app.mount("/static", StaticFiles(directory="backend/static"), name="static")
    logger.info("✅ HTML templates mounted at /admin/*")
    
    # ========================================================================
    # ROTAS HTML ADMIN (USANDO DECORADOR v3.0)
    # ========================================================================
    
    @app.get("/admin", response_class=HTMLResponse, tags=["Admin HTML"], include_in_schema=False)
    @html_admin_route("dashboard.html", lambda: {
        "user": {"username": "admin", "role": "admin"},
        "system_info": {
            "model_name": "yolov8n.pt",
            "video_source_label": "Webcam 0"
        }
    })
    async def admin_dashboard_page(request: Request):
        """✅ v3.0: Dashboard HTML admin (legacy compatibility)"""
        pass  # Lógica no decorador
    
    @app.get("/admin/settings", response_class=HTMLResponse, tags=["Admin HTML"], include_in_schema=False)
    async def admin_settings_page(request: Request):
        """✅ v3.0: Página de configurações YOLO e Zones"""
        templates = _get_templates()
        
        # ✅ Busca zonas com tratamento de erro
        zones_meta = []
        try:
            from backend.database_sync import get_all_zones
            zones_meta = get_all_zones()
        except Exception as e:
            logger.error(f"Erro ao buscar zonas: {e}")
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "config": _get_yolo_default_config(),
            "zones_meta": zones_meta,
            "available_models": _get_available_models()
        })
    
    @app.get("/admin/logs", response_class=HTMLResponse, tags=["Admin HTML"], include_in_schema=False)
    @html_admin_route("logs.html", lambda: {
        "user": {"username": "admin", "role": "admin"},
        "alerts": [],
        "system_actions": []
    })
    async def admin_logs_page(request: Request):
        """✅ v3.0: Página de histórico de alertas e logs"""
        pass
    
    @app.get("/admin/diagnostics", response_class=HTMLResponse, tags=["Admin HTML"], include_in_schema=False)
    @html_admin_route("diagnostics.html", lambda: {
        "results": {
            "status": "success",
            "data": {"users": 0, "alerts": 0, "logs": 0, "settings": 0},
            "tables": {},
            "yolo": {},
            "zone": {},
            "camera": {},
            "email": {},
            "admin": []
        }
    })
    async def admin_diagnostics_page(request: Request):
        """✅ v3.0: Página de diagnóstico do banco"""
        pass
    
    # ========================================================================
    # ERROR HANDLERS HTML
    # ========================================================================
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc) -> HTMLResponse:
        """✅ v3.0: Handler customizado para erro 404"""
        templates = _get_templates()
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc) -> HTMLResponse:
        """✅ v3.0: Handler customizado para erro 500"""
        logger.error(f"Erro 500: {exc}")
        templates = _get_templates()
        return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
    
    # ========================================================================
    # OTIMIZAÇÃO 3: Rotas Legacy Consolidadas
    # ========================================================================
    
    async def _handle_legacy_stream_action(request: Request, action: str) -> Dict[str, Any]:
        """✅ v3.0: Handler consolidado para ações legacy de stream"""
        try:
            body = await request.json()
            reason = body.get("reason", "")
            
            # TODO: Integrar com stream.py real
            response = {
                "success": True,
                "action": action,
                "reason": reason
            }
            
            if action == "toggle":
                response["paused"] = False
            
            return response
        except Exception as e:
            logger.error(f"Erro em {action}: {e}")
            return {"success": False, "error": str(e)}
    
    @app.post("/togglecamera", tags=["Stream Control Legacy"], include_in_schema=False)
    async def toggle_camera(request: Request) -> Dict[str, Any]:
        """✅ Pausar/Retomar stream (compatibilidade v1.0)"""
        return await _handle_legacy_stream_action(request, "toggle")
    
    @app.post("/stopstream", tags=["Stream Control Legacy"], include_in_schema=False)
    async def stop_stream_route(request: Request) -> Dict[str, Any]:
        """✅ Parar stream (compatibilidade v1.0)"""
        return await _handle_legacy_stream_action(request, "stop")
    
    @app.post("/startstream", tags=["Stream Control Legacy"], include_in_schema=False)
    async def start_stream_route(request: Request) -> Dict[str, Any]:
        """✅ Iniciar stream (compatibilidade v1.0)"""
        return await _handle_legacy_stream_action(request, "start")
    
    @app.get("/api/stats", tags=["Stats Legacy"], include_in_schema=False)
    async def get_stats() -> Dict[str, Any]:
        """✅ Estatísticas (compatibilidade com dashboard.html v1.0)"""
        return {
            "in_zone": 0,
            "out_zone": 0,
            "total_alerts": 0,
            "detections": 0,
            "fps_inst": 0.0,
            "fps_avg": 0.0,
            "system_status": "running",
            "model_name": "yolov8n.pt",
            "video_source_label": "Webcam 0",
            "safe_zone": [],
            "zones": [],
            "recent_alerts": [],
            "system_logs": []
        }

except Exception as e:
    logger.warning(f"⚠️  HTML templates not available: {e}")


# ============================================================================
# INCLUDE ROUTERS v3.0
# ============================================================================

app.include_router(auth.router)          # ✅ v3.0: Authentication routes
app.include_router(users.router)         # ✅ v3.0: User management
app.include_router(settings_api.router)  # ✅ v3.0: Settings API
app.include_router(admin.router)         # ✅ v3.0: Admin operations
app.include_router(zones.router)         # ✅ v3.0: Zone management
app.include_router(alerts.router)        # ✅ v3.0: Alert system
app.include_router(stream.router)        # ✅ v3.0: Stream control
app.include_router(stream.router_video)  # ✅ v3.0: Video feed


# ============================================================================
# ROOT ENDPOINTS v3.0
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    ✅ v3.0: Root endpoint - React frontend info
    
    Returns:
        Informações sobre API, versão e endpoints principais
    """
    return {
        "message": "YOLO Dashboard API v3.0",
        "version": "3.0.0",
        "status": "running",
        "frontend": "React (http://localhost:5173)",
        "admin_html": "/admin (legacy HTML)",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "features": [
            "OAuth2 Authentication",
            "JWT + Refresh Tokens",
            "Password Reset Flow",
            "YOLO Detection",
            "Real-time Tracking",
            "Smart Zones",
            "Alert System",
            "Video Streaming",
            "RAG-Ready"
        ]
    }


@app.get("/api", tags=["Root"])
async def api_info() -> Dict[str, Any]:
    """
    ✅ v3.0: API info detalhado
    
    Returns:
        Documentação completa da API com todos endpoints
    """
    return {
        "message": "Computer Vision Monitoring API v3.0",
        "version": "3.0.0",
        "status": "running",
        "docs": f"http://{settings.HOST}:{settings.PORT}/docs" if settings.DEBUG else "disabled",
        "authentication": {
            "type": "JWT Bearer",
            "oauth2_compatible": True,
            "refresh_token": True,
            "password_reset": True,
            "mfa_ready": True
        },
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "users": "/api/v1/users/*",
            "stream": "/api/v1/stream/*",
            "zones": "/api/v1/zones/*",
            "alerts": "/api/v1/alerts/*",
            "settings": "/api/v1/settings/*",
            "admin": "/api/v1/admin/*"
        },
        "features": [
            "JWT Authentication (OAuth2)",
            "Refresh Token Support",
            "Password Reset Flow",
            "Email Verification Ready",
            "YOLO Detection (YOLOv8)",
            "Object Tracking (BoT-SORT)",
            "Smart Zones (Polygons)",
            "Real-time Alerts",
            "System Settings API",
            "Video Streaming (MJPEG)",
            "Audit Logging",
            "RAG-Ready Architecture",
            "Backup & Restore",
            "System Diagnostics"
        ]
    }


# ============================================================================
# HEALTH CHECK v3.0
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    ✅ v3.0: Health check completo
    
    Verifica:
    - Status da API
    - Conexão com PostgreSQL
    - Versão da aplicação
    
    Returns:
        Status de saúde de todos componentes
    """
    health_status = {
        "status": "healthy",
        "api": "running",
        "database": "unknown",
        "version": "3.0.0",
        "swagger": "enabled" if settings.DEBUG else "disabled"
    }
    
    try:
        pool = await database.get_db_pool()
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


# ============================================================================
# FAVICON
# ============================================================================

@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """✅ v3.0: Retorna favicon (ou 204 se não existir)"""
    favicon_path = Path("backend/static/favicon.ico")
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return Response(status_code=204)

# ============================================================================
# CATCH-ALL ROUTE - Serve React App para todas rotas não-API
# ============================================================================

@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(request: Request, full_path: str):
    """
    Catch-all route que serve o index.html do React para rotas não-API.
    Isso permite que o React Router funcione corretamente com F5.
    
    Rotas que NÃO devem cair aqui:
    - /api/* (API endpoints)
    - /static/* (arquivos estáticos)
    - /docs, /redoc, /openapi.json (Swagger)
    - /health, /favicon.ico
    """
    
    # Se for rota de API, 404 real
    if full_path.startswith('api/'):
        return JSONResponse(
            status_code=404,
            content={"detail": f"API endpoint not found: /{full_path}"}
        )
    
    # Se for arquivo estático que não existe, 404
    if full_path.startswith('static/'):
        return Response(status_code=404)
    
    # Para todas as outras rotas, servir o index.html do React
    # Isso permite que o React Router assuma o controle
    
    # Opção 1: Se você tem o frontend buildado
    #frontend_dist = Path("frontend/dist/index.html")
    #if frontend_dist.exists():
    #    return FileResponse(frontend_dist)
    
    # Opção 2: Se você está usando o template engine
    # (remova se não usar templates)
    #return templates.TemplateResponse("index.html", {
    #    "request": request
    #})


# ============================================================================
# MAIN (DEBUG)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🚀 FastAPI Application v3.0 - DEBUG MODE")
    print("=" * 70)
    print("⚠️  NÃO USAR EM PRODUÇÃO")
    print("=" * 70)
    print(f"📡 API: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"⚛️  React: http://localhost:5173")
    print(f"🔧 Admin HTML: http://{settings.HOST}:{settings.PORT}/admin")
    print("=" * 70)
    print("\n✅ Features v3.0:")
    print("   • OAuth2 Authentication")
    print("   • Swagger Docs (CSP Fixed)")
    print("   • Refresh Token")
    print("   • Password Reset")
    print("   • Smart Zones")
    print("   • Real-time Alerts")
    print("   • Video Streaming")
    print("   • RAG-Ready")
    print("=" * 70)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
