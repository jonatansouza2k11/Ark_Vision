"""
backend/api/auth.py
Authentication Routes (Login, Register, Token)
"""

# ✅ FIX: Path para imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from datetime import timedelta
import logging

from models.auth import UserCreate, UserLogin, Token, UserResponse
from dependencies import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    limiter
)
import database
from config import settings

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()

# ============================================
# REGISTER (criar novo usuário)
# ============================================
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Max 5 registros por minuto
async def register(request: Request, user: UserCreate):
    """
    Registra novo usuário
    
    - **username**: Nome de usuário único (3-50 caracteres)
    - **email**: Email válido e único
    - **password**: Senha (mínimo 6 caracteres)
    """
    # Verifica se username já existe
    existing_user = await database.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Verifica se email já existe
    existing_email = await database.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash da senha
    password_hash = get_password_hash(user.password)
    
    # Cria usuário (primeiro usuário é admin)
    all_users = await database.get_all_users()
    role = "admin" if len(all_users) == 0 else "user"
    
    success = await database.create_user(
        username=user.username,
        email=user.email,
        password_hash=password_hash,
        role=role
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Log ação
    await database.log_system_action(
        action="user_register",
        username=user.username,
        reason=f"New user registered with role: {role}",
        ip_address=request.client.host if request.client else None
    )
    
    # Retorna usuário criado
    created_user = await database.get_user_by_username(user.username)
    
    logger.info(f"✅ New user registered: {user.username} (role: {role})")
    
    return created_user

# ============================================
# LOGIN (autenticar e gerar token)
# ============================================
@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Max 10 tentativas por minuto
async def login(request: Request, credentials: UserLogin):
    """
    Faz login e retorna token JWT
    
    - **username**: Nome de usuário
    - **password**: Senha
    
    Retorna:
    - **access_token**: Token JWT (válido por 30 dias)
    - **token_type**: "bearer"
    """
    # Autentica usuário
    user = await authenticate_user(credentials.username, credentials.password)
    
    if not user:
        # Log tentativa falhada
        await database.log_system_action(
            action="login_failed",
            username=credentials.username,
            reason="Invalid credentials",
            ip_address=request.client.host if request.client else None
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    
    # Log login bem-sucedido
    await database.log_system_action(
        action="login_success",
        username=user["username"],
        reason="User logged in successfully",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ User logged in: {user['username']}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ============================================
# GET CURRENT USER (me)
# ============================================
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_active_user)):
    """
    Retorna informações do usuário autenticado
    
    Requer: Token JWT válido
    """
    return current_user

# ============================================
# LOGOUT (invalida token - placeholder)
# ============================================
@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Faz logout do usuário
    
    Nota: JWT é stateless, então o frontend deve deletar o token.
    Este endpoint é apenas para logging.
    """
    # Log logout
    await database.log_system_action(
        action="logout",
        username=current_user["username"],
        reason="User logged out",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ User logged out: {current_user['username']}")
    
    return {"message": "Logged out successfully"}

# ============================================
# HEALTH CHECK (não requer autenticação)
# ============================================
@router.get("/health")
async def health_check():
    """
    Verifica se o serviço de autenticação está funcionando
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("🔐 ROUTES: Authentication")
    print("=" * 70)
    
    print("\n✅ Endpoints disponíveis:")
    print("\n1️⃣  POST /api/v1/auth/register")
    print("   • Registra novo usuário")
    print("   • Rate limit: 5/minuto")
    print("   • Primeiro usuário = admin")
    
    print("\n2️⃣  POST /api/v1/auth/login")
    print("   • Autentica e retorna JWT token")
    print("   • Rate limit: 10/minuto")
    print("   • Token válido por 30 dias")
    
    print("\n3️⃣  GET /api/v1/auth/me")
    print("   • Retorna dados do usuário logado")
    print("   • Requer: Bearer token")
    
    print("\n4️⃣  POST /api/v1/auth/logout")
    print("   • Faz logout (logging only)")
    print("   • Requer: Bearer token")
    
    print("\n5️⃣  GET /api/v1/auth/health")
    print("   • Health check")
    print("   • Público (sem auth)")
    
    print("\n🛡️  Segurança:")
    print("   • Rate limiting habilitado")
    print("   • Senhas hash com bcrypt")
    print("   • JWT com expiração configurável")
    print("   • Logging de todas ações")
    
    print("\n" + "=" * 70)
    print("✅ Auth routes prontas!")
    print("=" * 70)
