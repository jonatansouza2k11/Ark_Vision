"""
backend/middleware/security.py
Security Headers & CORS Middleware
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

from config import settings

logger = logging.getLogger("uvicorn")

# ============================================
# CORS MIDDLEWARE
# ============================================
def setup_cors(app: FastAPI):
    """
    Configura CORS para permitir frontend
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"✅ CORS configurado: {len(settings.cors_origins_list)} origins")


# ============================================
# SECURITY HEADERS MIDDLEWARE
# ============================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adiciona headers de segurança em todas as respostas
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Remove server header (CORRIGIDO!)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


# ============================================
# REQUEST LOGGING MIDDLEWARE
# ============================================
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Loga todas as requisições (exceto /health)
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip logging for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Log request
        logger.info(
            f"➡️  {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"⬅️  {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration:.3f}s)"
        )
        
        return response

# ============================================
# AUDIT LOGGING MIDDLEWARE (para compliance)
# ============================================
class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Loga ações importantes para auditoria
    """
    
    # Endpoints que devem ser auditados
    AUDIT_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/users",
        "/api/v1/settings",
        "/api/v1/admin",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Verifica se deve auditar
        should_audit = any(
            request.url.path.startswith(path) 
            for path in self.AUDIT_PATHS
        )
        
        if should_audit:
            # Extrai informações
            user = None
            if hasattr(request.state, "user"):
                user = request.state.user
            
            # Log antes da ação
            logger.warning(
                f"🔐 AUDIT: {request.method} {request.url.path} "
                f"by {user.get('username') if user else 'anonymous'} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            
            # TODO: Salvar no banco (audit_logs table)
            # await database.log_audit(...)
        
        response = await call_next(request)
        return response

# ============================================
# ERROR HANDLING MIDDLEWARE
# ============================================
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Captura erros não tratados e retorna JSON consistente
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        
        except Exception as e:
            logger.error(f"❌ Unhandled error: {e}", exc_info=True)
            
            # Retorna erro em formato JSON
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "type": "server_error",
                    "path": request.url.path
                }
            )

# ============================================
# SETUP ALL MIDDLEWARE
# ============================================
def setup_middleware(app: FastAPI):
    """
    Configura todos os middlewares na ordem correta
    """
    # 1. CORS (primeiro)
    setup_cors(app)
    
    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Request logging
    if settings.DEBUG:
        app.add_middleware(RequestLoggingMiddleware)
    
    # 4. Audit logging (compliance)
    app.add_middleware(AuditLoggingMiddleware)
    
    # 5. Error handling (último)
    app.add_middleware(ErrorHandlingMiddleware)
    
    logger.info("✅ Middleware configurado")

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("🛡️  TESTE: Security Middleware")
    print("=" * 70)
    
    print("\n✅ Middlewares disponíveis:")
    print("   1. CORS - Permite frontend acessar API")
    print("   2. Security Headers - Proteção XSS, clickjacking, etc")
    print("   3. Request Logging - Log de todas requisições")
    print("   4. Audit Logging - Compliance em ações sensíveis")
    print("   5. Error Handling - Tratamento consistente de erros")
    
    print("\n📋 Headers de segurança adicionados:")
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
    for key, value in headers.items():
        print(f"   • {key}: {value}")
    
    print("\n🌐 CORS Origins configurados:")
    for origin in settings.cors_origins_list:
        print(f"   • {origin}")
    
    print("\n" + "=" * 70)
    print("✅ Middleware pronto para uso!")
    print("=" * 70)
