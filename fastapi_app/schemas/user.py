"""
User Schemas
Validação de dados para usuários
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


# ============================================
# REQUEST SCHEMAS (recebidos do cliente)
# ============================================

class UserCreate(BaseModel):
    """Schema para criar usuário"""
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário único")
    email: EmailStr = Field(..., description="Email válido")
    password: str = Field(..., min_length=6, max_length=100, description="Senha (mínimo 6 caracteres)")
    role: str = Field(default="user", description="Role do usuário (user ou admin)")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Valida username (apenas alfanumérico e underscore)"""
        if not v.replace('_', '').isalnum():
            raise ValueError('Username deve conter apenas letras, números e underscore')
        return v.lower()
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Valida role"""
        if v not in ('user', 'admin'):
            raise ValueError('Role deve ser "user" ou "admin"')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "joao_silva",
                "email": "joao@example.com",
                "password": "senha123",
                "role": "user"
            }
        }


class UserLogin(BaseModel):
    """Schema para login"""
    username: str = Field(..., description="Username ou email")
    password: str = Field(..., description="Senha")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123"
            }
        }


class UserUpdate(BaseModel):
    """Schema para atualizar usuário (todos campos opcionais)"""
    email: Optional[EmailStr] = Field(None, description="Novo email")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="Nova senha")
    role: Optional[str] = Field(None, description="Novo role")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Valida role"""
        if v is not None and v not in ('user', 'admin'):
            raise ValueError('Role deve ser "user" ou "admin"')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "novo_email@example.com",
                "role": "admin"
            }
        }


# ============================================
# RESPONSE SCHEMAS (enviados ao cliente)
# ============================================

class UserResponse(BaseModel):
    """Schema de resposta de usuário (SEM senha)"""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Permite criar de ORM models
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "created_at": "2025-12-30T22:00:00",
                "last_login": "2025-12-30T22:10:00"
            }
        }
