"""
Database models
Importa todos os models para facilitar acesso
"""

from fastapi_app.models.user import User
from fastapi_app.models.alert import Alert
from fastapi_app.models.setting import Setting
from fastapi_app.models.system_log import SystemLog

__all__ = [
    "User",
    "Alert",
    "Setting",
    "SystemLog"
]
