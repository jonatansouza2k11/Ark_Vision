"""
Security utilities
JWT authentication, password hashing
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from fastapi_app.core.config import settings
from fastapi_app.core.database import get_db
from fastapi_app.models.user import User
from fastapi_app.schemas.auth import TokenData


# ============================================
# PASSWORD HASHING
# ============================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se senha está correta"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)


# ============================================
# JWT TOKEN
# ============================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria JWT token
    
    Args:
        data: Dados para incluir no token (username, user_id, role)
        expires_delta: Tempo de expiração customizado
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verifica e decodifica JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData com informações do usuário
    
    Raises:
        HTTPException: Se token inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, user_id=user_id, role=role)
        return token_data
    
    except JWTError:
        raise credentials_exception


# ============================================
# DEPENDENCIES (para usar em endpoints)
# ============================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: Retorna usuário autenticado atual
    
    Uso em endpoint:
        @router.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.username == token_data.username).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )
    
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency: Retorna usuário admin
    
    Uso em endpoint protegido:
        @router.delete("/users/{user_id}")
        def delete_user(user_id: int, admin: User = Depends(get_current_admin)):
            # Apenas admin pode deletar
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada. Apenas administradores."
        )
    
    return current_user


# ============================================
# AUTHENTICATION
# ============================================

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Autentica usuário (username/email + senha)
    
    Args:
        db: Sessão do banco
        username: Username ou email
        password: Senha plain text
    
    Returns:
        User se autenticado, None se falhar
    """
    # Buscar por username ou email
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user
