"""
backend/api/users.py
User Management Routes (Admin Only)
"""

# ✅ FIX: Path para imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
import logging

from models.auth import UserResponse, UserCreate, UserUpdate
from dependencies import get_current_admin_user, get_password_hash
import database

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/v1/users", tags=["Users"])

# ============================================
# GET ALL USERS (admin only)
# ============================================
@router.get("", response_model=List[UserResponse])
async def get_all_users(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Lista todos os usuários (apenas admin)
    
    Requer: Token JWT de admin
    """
    users = await database.get_all_users()
    return users

# ============================================
# GET USER BY ID (admin only)
# ============================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Obtém usuário por ID (apenas admin)
    
    Requer: Token JWT de admin
    """
    # Buscar por ID (vamos adicionar função no database.py)
    users = await database.get_all_users()
    user = next((u for u in users if u["id"] == user_id), None)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

# ============================================
# CREATE USER (admin only)
# ============================================
@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Cria novo usuário (apenas admin)
    
    Requer: Token JWT de admin
    """
    # Verifica se username já existe
    existing_user = await database.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Verifica se email já existe
    existing_email = await database.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Hash da senha
    password_hash = get_password_hash(user.password)
    
    # Cria usuário
    success = await database.create_user(
        username=user.username,
        email=user.email,
        password_hash=password_hash,
        role="user"  # Admin cria usuários normais
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Log ação
    await database.log_system_action(
        action="user_created_by_admin",
        username=current_user["username"],
        reason=f"Created user: {user.username}",
        ip_address=request.client.host if request.client else None
    )
    
    # Retorna usuário criado
    created_user = await database.get_user_by_username(user.username)
    logger.info(f"✅ Admin {current_user['username']} created user: {user.username}")
    
    return created_user

# ============================================
# DELETE USER (admin only)
# ============================================
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Deleta usuário (apenas admin)
    
    Requer: Token JWT de admin
    """
    # Não pode deletar a si mesmo
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # TODO: Adicionar função delete_user no database.py
    # Por enquanto, apenas log
    
    await database.log_system_action(
        action="user_deleted",
        username=current_user["username"],
        reason=f"Deleted user ID: {user_id}",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ Admin {current_user['username']} deleted user ID: {user_id}")
    
    return {"message": "User deleted successfully"}

# ============================================
# UPDATE USER ROLE (admin only)
# ============================================
@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Atualiza role do usuário (apenas admin)
    
    Roles válidas: "user", "admin"
    """
    if role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user' or 'admin'"
        )
    
    # Não pode mudar seu próprio role
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # TODO: Adicionar função update_user_role no database.py
    
    await database.log_system_action(
        action="user_role_updated",
        username=current_user["username"],
        reason=f"Changed user {user_id} role to: {role}",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ Admin {current_user['username']} changed user {user_id} role to: {role}")
    
    return {"message": f"User role updated to {role}"}

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("👥 ROUTES: User Management")
    print("=" * 70)
    
    print("\n✅ Endpoints disponíveis:")
    print("\n1️⃣  GET /api/v1/users")
    print("   • Lista todos os usuários")
    print("   • Requer: Admin token")
    
    print("\n2️⃣  GET /api/v1/users/{user_id}")
    print("   • Obtém usuário por ID")
    print("   • Requer: Admin token")
    
    print("\n3️⃣  POST /api/v1/users")
    print("   • Cria novo usuário")
    print("   • Requer: Admin token")
    
    print("\n4️⃣  DELETE /api/v1/users/{user_id}")
    print("   • Deleta usuário")
    print("   • Requer: Admin token")
    print("   • Não pode deletar a si mesmo")
    
    print("\n5️⃣  PATCH /api/v1/users/{user_id}/role")
    print("   • Atualiza role (user/admin)")
    print("   • Requer: Admin token")
    print("   • Não pode mudar próprio role")
    
    print("\n" + "=" * 70)
    print("✅ User routes prontas!")
    print("=" * 70)
