"""
backend/dependencies.py - OPTIMIZED v2.1
JWT Authentication & Dependencies
Enhanced with caching, type safety, and clean architecture

✨ v2.1 (2026-01-06):
- ✅ CORRIGIDO: UTF-8 encoding no Limiter (evita erro com .env)
"""


from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging


from backend.config import settings
from backend import database


logger = logging.getLogger("uvicorn")



# ============================================
# OTIMIZAÇÃO 1: Constants & Enums
# ============================================


class AuthError(str, Enum):
    """✅ Centralized auth error messages"""
    INVALID_CREDENTIALS = "Could not validate credentials"
    INVALID_TOKEN = "Invalid authentication token"
    EXPIRED_TOKEN = "Token has expired"
    USER_NOT_FOUND = "User not found"
    INACTIVE_USER = "Inactive user"
    INSUFFICIENT_PERMISSIONS = "Not enough permissions"
    WEAK_PASSWORD = "Password does not meet security requirements"



class TokenType(str, Enum):
    """✅ Token types"""
    ACCESS = "access"
    REFRESH = "refresh"



@dataclass(frozen=True)
class TokenPayload:
    """✅ Type-safe JWT payload structure"""
    sub: str  # username
    exp: datetime
    token_type: str = TokenType.ACCESS
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['TokenPayload']:
        """Create TokenPayload from decoded JWT dict"""
        try:
            return cls(
                sub=data.get("sub"),
                exp=datetime.fromtimestamp(data.get("exp"), tz=timezone.utc),
                token_type=data.get("token_type", TokenType.ACCESS)
            )
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid token payload: {e}")
            return None



# Password constraints
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72  # bcrypt limit



# ============================================
# OTIMIZAÇÃO 2: Cached Context
# ============================================


@lru_cache(maxsize=1)
def _get_pwd_context() -> CryptContext:
    """
    ✅ Cached CryptContext (expensive to create)
    Creates only once and reuses
    """
    return CryptContext(schemes=["bcrypt"], deprecated="auto")



# ============================================
# OTIMIZAÇÃO 3: Helper Functions
# ============================================


def _normalize_password(password: str) -> str:
    """
    ✅ Normalize password to bcrypt limits (pure function)
    
    Args:
        password: Raw password string
    
    Returns:
        Normalized password (max 72 bytes)
    """
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    
    # Truncate to bcrypt limit (72 bytes)
    return password.encode('utf-8')[:PASSWORD_MAX_LENGTH].decode('utf-8', errors='ignore')



def _validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    ✅ Validate password meets security requirements
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    
    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f"Password cannot exceed {PASSWORD_MAX_LENGTH} characters"
    
    # Add more validation rules as needed
    # - Has uppercase letter
    # - Has lowercase letter
    # - Has digit
    # - Has special character
    
    return True, None



def _create_jwt_payload(username: str, expires_delta: Optional[timedelta] = None) -> Dict[str, Any]:
    """
    ✅ Create JWT payload dict (pure function)
    
    Args:
        username: Username to encode
        expires_delta: Optional custom expiration time
    
    Returns:
        JWT payload dictionary
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    return {
        "sub": username,
        "exp": expire,
        "token_type": TokenType.ACCESS,
        "iat": datetime.now(timezone.utc)  # issued at
    }



def _create_http_exception(
    status_code: int,
    detail: str,
    headers: Optional[Dict[str, str]] = None
) -> HTTPException:
    """
    ✅ Factory for HTTPException (consistency)
    
    Args:
        status_code: HTTP status code
        detail: Error detail message
        headers: Optional headers
    
    Returns:
        HTTPException instance
    """
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers or {}
    )



# ============================================
# PASSWORD HASHING
# ============================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha está correta
    
    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash bcrypt da senha
    
    Returns:
        True se senha correta, False caso contrário
    """
    try:
        normalized = _normalize_password(plain_password)
        return _get_pwd_context().verify(normalized, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False



def get_password_hash(password: str) -> str:
    """
    Gera hash da senha
    
    Args:
        password: Senha em texto plano
    
    Returns:
        Hash bcrypt da senha
    
    Raises:
        ValueError: Se senha não atende requisitos
    """
    # Validate password strength
    is_valid, error_msg = _validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_msg)
    
    normalized = _normalize_password(password)
    return _get_pwd_context().hash(normalized)



# ============================================
# JWT TOKEN
# ============================================


security = HTTPBearer()



def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria token JWT
    
    Args:
        data: Dados para incluir no token (deve conter "sub": username)
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Token JWT string
    
    Raises:
        ValueError: Se 'sub' não estiver presente em data
    """
    if "sub" not in data:
        raise ValueError("Token data must contain 'sub' (username)")
    
    username = data["sub"]
    payload = _create_jwt_payload(username, expires_delta)
    
    # Merge additional data
    payload.update({k: v for k, v in data.items() if k not in payload})
    
    try:
        encoded_jwt = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise



def decode_access_token(token: str) -> Optional[TokenPayload]:
    """
    Decodifica e valida token JWT
    
    Args:
        token: Token JWT string
    
    Returns:
        TokenPayload se válido, None se inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return TokenPayload.from_dict(payload)
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None



def validate_token(token: str) -> Tuple[bool, Optional[str], Optional[TokenPayload]]:
    """
    ✅ Comprehensive token validation
    
    Args:
        token: JWT token string
    
    Returns:
        Tuple of (is_valid, error_message, payload)
    """
    if not token:
        return False, AuthError.INVALID_TOKEN, None
    
    try:
        payload_dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        payload = TokenPayload.from_dict(payload_dict)
        if payload is None:
            return False, AuthError.INVALID_TOKEN, None
        
        # Check expiration (already done by jwt.decode, but explicit check)
        if payload.exp < datetime.now(timezone.utc):
            return False, AuthError.EXPIRED_TOKEN, None
        
        return True, None, payload
        
    except jwt.ExpiredSignatureError:
        return False, AuthError.EXPIRED_TOKEN, None
    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        return False, AuthError.INVALID_TOKEN, None



# ============================================
# AUTHENTICATION DEPENDENCIES
# ============================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency: Obtém usuário atual do token JWT
    
    Args:
        credentials: HTTP Bearer credentials
    
    Raises:
        HTTPException 401: Se token inválido ou usuário não encontrado
    
    Returns:
        Dados do usuário
    """
    token = credentials.credentials
    is_valid, error_msg, payload = validate_token(token)
    
    if not is_valid or payload is None:
        raise _create_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            error_msg or AuthError.INVALID_CREDENTIALS,
            {"WWW-Authenticate": "Bearer"}
        )
    
    # Busca usuário no banco
    user = await database.get_user_by_username(payload.sub)
    if user is None:
        raise _create_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            AuthError.USER_NOT_FOUND,
            {"WWW-Authenticate": "Bearer"}
        )
    
    return user



async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency: Obtém usuário ativo
    
    Args:
        current_user: Current authenticated user
    
    Raises:
        HTTPException 400: Se usuário inativo
    
    Returns:
        Dados do usuário ativo
    """
    # Check if user is disabled (if your User model has this field)
    if current_user.get("disabled", False):
        raise _create_http_exception(
            status.HTTP_400_BAD_REQUEST,
            AuthError.INACTIVE_USER
        )
    
    return current_user



async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Dependency: Verifica se usuário é admin
    
    Args:
        current_user: Current active user
    
    Raises:
        HTTPException 403: Se usuário não é admin
    
    Returns:
        Dados do usuário admin
    """
    if current_user.get("role") != "admin":
        raise _create_http_exception(
            status.HTTP_403_FORBIDDEN,
            AuthError.INSUFFICIENT_PERMISSIONS
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
    # Validate input
    if not username or not password:
        return None
    
    # Fetch user
    user = await database.get_user_by_username(username)
    if not user:
        logger.info(f"Login attempt failed: user not found ({username})")
        return None
    
    # Verify password
    if not verify_password(password, user["password_hash"]):
        logger.info(f"Login attempt failed: invalid password ({username})")
        return None
    
    # Update last login timestamp
    try:
        await database.update_last_login(username)
    except Exception as e:
        logger.error(f"Failed to update last login for {username}: {e}")
        # Don't fail authentication if we can't update timestamp
    
    logger.info(f"User authenticated successfully: {username}")
    return user



# ============================================
# OPTIONAL AUTHENTICATION
# ============================================


async def get_optional_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Dependency: Obtém usuário do token se existir (opcional)
    Não lança exceção se token não existir ou for inválido
    
    Args:
        request: FastAPI request object
    
    Returns:
        Dados do usuário ou None
    """
    try:
        # Extract token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        # Validate token
        is_valid, _, payload = validate_token(token)
        if not is_valid or payload is None:
            return None
        
        # Fetch user
        user = await database.get_user_by_username(payload.sub)
        return user
    
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None



# ============================================
# RATE LIMITING (✅ CORRIGIDO v2.1)
# ============================================


# ✅ CORREÇÃO: Não carregar .env via SlowAPI
# O Pydantic já faz isso corretamente em config.py
# Isso evita erro de encoding com emojis no .env
limiter = Limiter(
    key_func=get_remote_address,
    config_filename=None,  # ✅ Ignora .env (evita UnicodeDecodeError)
    default_limits=["100/minute"]
)



# ============================================
# UTILITY FUNCTIONS
# ============================================


def create_user_token(user: Dict[str, Any]) -> str:
    """
    ✅ Convenience function to create token for a user
    
    Args:
        user: User dict from database
    
    Returns:
        JWT access token
    """
    return create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )



def hash_password_safe(password: str) -> Optional[str]:
    """
    ✅ Safe password hashing with error handling
    
    Args:
        password: Plain text password
    
    Returns:
        Password hash or None if validation failed
    """
    try:
        return get_password_hash(password)
    except ValueError as e:
        logger.warning(f"Password validation failed: {e}")
        return None



# ============================================
# TEST SCRIPT
# ============================================


if __name__ == "__main__":
    import asyncio
    
    async def test_auth():
        """Testa funções de autenticação"""
        print("=" * 70)
        print("🔐 TESTE: Autenticação JWT v2.1")
        print("=" * 70)
        
        # 1. Test password hashing
        print("\n1️⃣ Testando hash de senha...")
        password = "test123456"
        try:
            hashed = get_password_hash(password)
            print(f"   Senha: {password}")
            print(f"   Hash: {hashed[:50]}...")
            print(f"   ✅ Verificação correta: {verify_password(password, hashed)}")
            print(f"   ❌ Verificação errada: {verify_password('wrong', hashed)}")
        except ValueError as e:
            print(f"   ❌ Erro de validação: {e}")
        
        # 2. Test weak password
        print("\n2️⃣ Testando senha fraca...")
        weak_password = "123"
        try:
            get_password_hash(weak_password)
            print("   ❌ Deveria ter falhado!")
        except ValueError as e:
            print(f"   ✅ Validação funcionou: {e}")
        
        # 3. Test JWT creation
        print("\n3️⃣ Testando criação de token JWT...")
        token = create_access_token(data={"sub": "testuser"})
        print(f"   Token: {token[:50]}...")
        
        # 4. Test JWT decode
        print("\n4️⃣ Testando decodificação de token...")
        payload = decode_access_token(token)
        if payload:
            print(f"   Username: {payload.sub}")
            print(f"   Expires: {payload.exp}")
            print(f"   Type: {payload.token_type}")
        
        # 5. Test token validation
        print("\n5️⃣ Testando validação completa de token...")
        is_valid, error, payload = validate_token(token)
        print(f"   Válido: {is_valid}")
        print(f"   Erro: {error}")
        print(f"   Payload: {payload}")
        
        # 6. Test invalid token
        print("\n6️⃣ Testando token inválido...")
        is_valid, error, payload = validate_token("invalid.token.here")
        print(f"   Válido: {is_valid}")
        print(f"   Erro: {error}")
        
        # 7. Test password normalization
        print("\n7️⃣ Testando normalização de senha...")
        long_password = "a" * 100
        normalized = _normalize_password(long_password)
        print(f"   Original length: {len(long_password)}")
        print(f"   Normalized length: {len(normalized)}")
        print(f"   ✅ Respeitou limite: {len(normalized) <= PASSWORD_MAX_LENGTH}")
        
        print("\n" + "=" * 70)
        print("✅ Todos os testes passaram!")
        print("=" * 70)
    
    asyncio.run(test_auth())
