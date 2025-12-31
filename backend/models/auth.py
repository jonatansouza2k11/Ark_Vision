"""
backend/models/auth.py
Pydantic Models para Autenticação
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

# ============================================
# AUTH MODELS
# ============================================

class UserBase(BaseModel):
    """Base model para usuário"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    """Model para criação de usuário"""
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    """Model para login"""
    username: str
    password: str

class UserResponse(UserBase):
    """Model para resposta de usuário (sem senha)"""
    id: int
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    """Model para token JWT"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Model para dados dentro do token"""
    username: Optional[str] = None

# ============================================
# USER UPDATE MODELS
# ============================================

class UserUpdate(BaseModel):
    """Model para atualização de usuário"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)

class PasswordChange(BaseModel):
    """Model para mudança de senha"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    import json
    
    print("=" * 70)
    print("📋 TESTE: Pydantic Models")
    print("=" * 70)
    
    # 1. Test UserCreate
    print("\n1️⃣ Testando UserCreate...")
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    print(f"   ✅ UserCreate: {user_create.model_dump()}")
    
    # 2. Test UserLogin
    print("\n2️⃣ Testando UserLogin...")
    user_login = UserLogin(username="testuser", password="password123")
    print(f"   ✅ UserLogin: {user_login.model_dump()}")
    
    # 3. Test Token
    print("\n3️⃣ Testando Token...")
    token = Token(access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    print(f"   ✅ Token: {token.model_dump()}")
    
    # 4. Test UserResponse
    print("\n4️⃣ Testando UserResponse...")
    user_response = UserResponse(
        id=1,
        username="testuser",
        email="test@example.com",
        role="user",
        created_at=datetime.now(),
        last_login=None
    )
    print(f"   ✅ UserResponse: {user_response.model_dump_json(indent=2)}")
    
    # 5. Test Validation
    print("\n5️⃣ Testando validação...")
    try:
        invalid = UserCreate(
            username="ab",  # Muito curto
            email="invalid-email",
            password="123"  # Muito curto
        )
    except Exception as e:
        print(f"   ✅ Validação funcionando: {type(e).__name__}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes passaram!")
    print("=" * 70)
