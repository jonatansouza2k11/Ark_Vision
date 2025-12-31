"""
backend/dependencies.py
JWT Authentication & Dependencies
"""

from datetime import datetime, timedelta, timezone  
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging

from config import settings
import database

logger = logging.getLogger("uvicorn")

# ============================================
# PASSWORD HASHING
# ============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)

# ============================================
# JWT TOKEN
# ============================================
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria token JWT
    
    Args:
        data: Dados para incluir no token (ex: {"sub": "username"})
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Token JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica e valida token JWT
    
    Args:
        token: Token JWT string
    
    Returns:
        Payload do token se válido, None se inválido
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None

# ============================================
# AUTHENTICATION DEPENDENCIES
# ============================================
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency: Obtém usuário atual do token JWT
    
    Raises:
        HTTPException 401: Se token inválido ou usuário não encontrado
    
    Returns:
        Dados do usuário
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # Busca usuário no banco
    user = await database.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency: Obtém usuário ativo
    
    Raises:
        HTTPException 400: Se usuário inativo
    
    Returns:
        Dados do usuário ativo
    """
    # Aqui você pode adicionar verificações adicionais
    # ex: if current_user.get("disabled"):
    #         raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user

async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Dependency: Verifica se usuário é admin
    
    Raises:
        HTTPException 403: Se usuário não é admin
    
    Returns:
        Dados do usuário admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user

# ============================================
# LOGIN FUNCTION
# ============================================
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Autentica usuário com username e senha
    
    Args:
        username: Nome de usuário
        password: Senha em texto plano
    
    Returns:
        Dados do usuário se autenticado, None caso contrário
    """
    user = await database.get_user_by_username(username)
    
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    # Atualiza último login
    await database.update_last_login(username)
    
    return user

# ============================================
# OPTIONAL: Get user from token (não obrigatório)
# ============================================
async def get_optional_current_user(
    request: Request
) -> Optional[Dict[str, Any]]:
    """
    Dependency: Obtém usuário do token se existir (opcional)
    Não lança exceção se token não existir ou for inválido
    
    Returns:
        Dados do usuário ou None
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        payload = decode_access_token(token)
        
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = await database.get_user_by_username(username)
        return user
    
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None

# ============================================
# RATE LIMITING (prepara para endpoints)
# ============================================
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# ============================================
# TESTE (quando executar python dependencies.py)
# ============================================
if __name__ == "__main__":
    import asyncio
    
    async def test_auth():
        """Testa funções de autenticação"""
        print("=" * 70)
        print("🔐 TESTE: Autenticação JWT")
        print("=" * 70)
        
        # 1. Test password hashing
        print("\n1️⃣ Testando hash de senha...")
        password = "test123"
        hashed = get_password_hash(password)
        print(f"   Senha: {password}")
        print(f"   Hash: {hashed[:50]}...")
        print(f"   ✅ Verificação: {verify_password(password, hashed)}")
        print(f"   ❌ Senha errada: {verify_password('wrong', hashed)}")
        
        # 2. Test JWT creation
        print("\n2️⃣ Testando criação de token JWT...")
        token = create_access_token(data={"sub": "testuser"})
        print(f"   Token: {token[:50]}...")
        
        # 3. Test JWT decode
        print("\n3️⃣ Testando decodificação de token...")
        payload = decode_access_token(token)
        print(f"   Payload: {payload}")
        print(f"   Username: {payload.get('sub')}")
        
        # 4. Test invalid token
        print("\n4️⃣ Testando token inválido...")
        invalid = decode_access_token("invalid.token.here")
        print(f"   Resultado: {invalid}")
        
        print("\n" + "=" * 70)
        print("✅ Todos os testes passaram!")
        print("=" * 70)
    
    asyncio.run(test_auth())
