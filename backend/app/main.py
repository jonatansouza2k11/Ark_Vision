"""
============================================================================
backend/app/main.py - ULTRA OPTIMIZED v3.1 (API-FIRST, SAFE)
FastAPI Application - Computer Vision Monitoring System
============================================================================
✔ API-first (JSON por padrão)
✔ HTML Admin opcional (não quebra API)
✔ Erros 404/500 nunca derrubam o backend
✔ Swagger compatível com CSP
============================================================================
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from functools import lru_cache, wraps

from fastapi import FastAPI, Request, Response
from fastapi.responses import (
    JSONResponse,
    FileResponse,
    HTMLResponse,
)
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

# ----------------------------------------------------------------------------
# PATH & LOGGING
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("uvicorn")

# ----------------------------------------------------------------------------
# LOCAL IMPORTS
# ----------------------------------------------------------------------------
from backend.config import settings
from backend import database
from backend.dependencies import limiter
from slowapi.errors import RateLimitExceeded

from backend.api import auth, users, admin, zones, alerts
from backend.api import settings as settings_api
from backend.api import stream

# ----------------------------------------------------------------------------
# CACHE HELPERS
# ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_templates():
    return Jinja2Templates(directory="backend/templates")


@lru_cache(maxsize=1)
def _get_cors_origins() -> List[str]:
    return [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]


# ----------------------------------------------------------------------------
# HTML DECORATOR (ADMIN ONLY)
# ----------------------------------------------------------------------------
def html_admin_route(template_name: str, fetch_data_fn=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request):
            templates = _get_templates()
            context = {"request": request}

            if fetch_data_fn:
                try:
                    data = fetch_data_fn()
                    context.update(data if isinstance(data, dict) else {})
                except Exception as e:
                    logger.error(f"Admin template data error: {e}")

            return templates.TemplateResponse(template_name, context)

        return wrapper

    return decorator


# ----------------------------------------------------------------------------
# LIFESPAN
# ----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting FastAPI Application")

    try:
        await database.get_db_pool()
        await database.init_database(force_recreate=False)
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise

    yield

    logger.info("🛑 Shutting down...")
    await database.close_db_pool()
    logger.info("✅ Database closed")


# ----------------------------------------------------------------------------
# FASTAPI APP
# ----------------------------------------------------------------------------
app = FastAPI(
    title="Computer Vision Monitoring API",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ----------------------------------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    if request.url.path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'self';"

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


# ----------------------------------------------------------------------------
# RATE LIMIT HANDLER
# ----------------------------------------------------------------------------
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded"},
    )


# ----------------------------------------------------------------------------
# GLOBAL ERROR HANDLERS (CRITICAL FIX)
# ----------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "path": str(request.url),
        },
    )


# ----------------------------------------------------------------------------
# STATIC & ADMIN HTML (OPTIONAL)
# ----------------------------------------------------------------------------
if Path("backend/static").exists():
    app.mount("/static", StaticFiles(directory="backend/static"), name="static")

if Path("backend/templates").exists():
    @app.get("/admin", include_in_schema=False)
    @html_admin_route("dashboard.html")
    async def admin_dashboard(request: Request):
        pass


# ----------------------------------------------------------------------------
# ROUTERS
# ----------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(settings_api.router)
app.include_router(admin.router)
app.include_router(zones.router)
app.include_router(alerts.router)
app.include_router(stream.router)


# ----------------------------------------------------------------------------
# ROOT
# ----------------------------------------------------------------------------
@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "app": "ARK YOLO FastAPI",
        "status": "running",
        "version": "3.1.0",
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


# ----------------------------------------------------------------------------
# HEALTH
# ----------------------------------------------------------------------------
@app.get("/health")
async def health():
    try:
        pool = await database.get_db_pool()
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        db = "ok"
    except Exception as e:
        db = f"error: {e}"

    return {
        "status": "healthy" if db == "ok" else "degraded",
        "database": db,
    }


# ----------------------------------------------------------------------------
# FAVICON
# ----------------------------------------------------------------------------
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    path = Path("backend/static/favicon.ico")
    return FileResponse(path) if path.exists() else Response(status_code=204)
