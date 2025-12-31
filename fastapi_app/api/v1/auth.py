"""
Authentication endpoints
Login, Register
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.config import settings
from fastapi_app.core.security import (
    authenticate_user,
    create_access_token,
    get_password_hash
)
from fastapi_app.models.user import User
from fastapi_app.schemas.user import UserCreate, UserResponse
from fastapi_app.schemas.auth import Token


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Registrar novo usuário
    
    - **username**: Username único (3-50 caracteres)
    - **email**: Email válido e único
    - **password**: Senha (mínimo 6 caracteres)
    - **role**: "user" ou "admin" (padrão: "user")
    """
    # Verificar se username já existe
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' já está em uso"
        )
    
    # Verificar se email já existe
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' já está em uso"
        )
    
    # Criar usuário
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login e obter JWT token
    
    - **username**: Username ou email
    - **password**: Senha
    
    Retorna JWT token para usar em endpoints protegidos
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username/email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Atualizar last_login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Criar token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
