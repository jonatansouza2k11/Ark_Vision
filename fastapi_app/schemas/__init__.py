"""
Pydantic schemas para validação de dados
"""

from fastapi_app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    UserUpdate
)

from fastapi_app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertList
)

from fastapi_app.schemas.setting import (
    SettingResponse,
    SettingUpdate,
    SettingBulkUpdate
)

from fastapi_app.schemas.auth import (
    Token,
    TokenData
)

__all__ = [
    "UserCreate",
    "UserResponse",
    "UserLogin",
    "UserUpdate",
    "AlertCreate",
    "AlertResponse",
    "AlertList",
    "SettingResponse",
    "SettingUpdate",
    "SettingBulkUpdate",
    "Token",
    "TokenData",
]
