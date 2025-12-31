"""
API v1 routes
"""

from fastapi import APIRouter
from fastapi_app.api.v1 import auth, users, alerts, settings

# Router principal v1
api_router = APIRouter()

# Incluir sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
