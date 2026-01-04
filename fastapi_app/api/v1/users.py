"""
Users endpoints
CRUD operations for users
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, get_current_admin, get_password_hash
from fastapi_app.models.user import User
from fastapi_app.schemas.user import UserResponse, UserUpdate


router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Obter informações do usuário autenticado atual
    
    Requer: Token JWT válido
    """
    return current_user


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Listar todos os usuários (apenas admin)
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Máximo de registros a retornar
    
    Requer: Token JWT de admin
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obter usuário por ID
    
    - Usuários normais: apenas podem ver próprio perfil
    - Admins: podem ver qualquer perfil
    
    Requer: Token JWT válido
    """
    # Verificar permissão
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode ver seu próprio perfil"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {user_id} não encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar usuário
    
    - Usuários normais: apenas podem atualizar próprio perfil (exceto role)
    - Admins: podem atualizar qualquer perfil
    
    Requer: Token JWT válido
    """
    # Buscar usuário
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {user_id} não encontrado"
        )
    
    # Verificar permissão
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode atualizar seu próprio perfil"
        )
    
    # Usuário normal não pode mudar próprio role
    if current_user.role != "admin" and user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não pode alterar seu próprio role"
        )
    
    # Atualizar campos
    if user_update.email is not None:
        # Verificar se email já existe
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_update.email}' já está em uso"
            )
        user.email = user_update.email
    
    if user_update.password is not None:
        user.password_hash = get_password_hash(user_update.password)
    
    if user_update.role is not None:
        user.role = user_update.role
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)  # Apenas admin
):
    """
    Deletar usuário (apenas admin)
    
    Requer: Token JWT de admin
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário {user_id} não encontrado"
        )
    
    # Não permitir deletar a si mesmo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode deletar sua própria conta"
        )
    
    db.delete(user)
    db.commit()
    
    return None
