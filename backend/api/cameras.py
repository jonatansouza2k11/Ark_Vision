"""
============================================================================
backend/api/cameras.py - v1.0 - Cameras CRUD API
FastAPI Endpoints for Camera Management
============================================================================
Endpoints:
✅ POST   /api/v1/cameras/          - Create camera (ADMIN only)
✅ GET    /api/v1/cameras/          - List all cameras
✅ GET    /api/v1/cameras/{id}      - Get camera by ID
✅ PUT    /api/v1/cameras/{id}      - Update camera (ADMIN only)
✅ DELETE /api/v1/cameras/{id}      - Delete camera (ADMIN only)
✅ PATCH  /api/v1/cameras/{id}/toggle - Toggle camera enabled status (ADMIN only)
✅ GET    /api/v1/cameras/active    - Get only active cameras

Authentication: JWT Bearer Token required
Permissions: ADMIN role required for Create/Update/Delete
============================================================================
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

# Import database functions
try:
    from backend import database
    from backend.dependencies import get_current_active_user, get_current_admin_user
except ModuleNotFoundError:
    import database
    from dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger("uvicorn")

# ============================================
# ROUTER SETUP
# ============================================

router = APIRouter(
    prefix="/api/v1/cameras",
    tags=["cameras"],
    responses={404: {"description": "Camera not found"}},
)


# ============================================
# PYDANTIC MODELS
# ============================================

class CameraBase(BaseModel):
    """Base model para câmera"""
    name: str = Field(..., min_length=1, max_length=100, description="Nome da câmera")
    source: str = Field(..., min_length=1, max_length=500, description="URL RTSP/HTTP ou device ID")
    location: Optional[str] = Field(None, max_length=255, description="Localização física")
    username: Optional[str] = Field(None, max_length=100, description="Username para autenticação RTSP")
    password: Optional[str] = Field(None, max_length=255, description="Password para autenticação RTSP")
    enabled: bool = Field(True, description="Câmera ativa")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadados adicionais")

    @validator("source")
    def validate_source(cls, v):
        """Valida formato do source"""
        v = v.strip()
        if not v:
            raise ValueError("Source não pode ser vazio")
        
        # Aceita RTSP, HTTP, device ID (0, 1, 2, etc) ou arquivo
        valid_prefixes = ("rtsp://", "http://", "https://", "/dev/video")
        if not (v.startswith(valid_prefixes) or v.isdigit() or v.endswith(('.mp4', '.avi', '.mkv'))):
            logger.warning(f"⚠️ Source format may be invalid: {v}")
        
        return v

    @validator("name")
    def validate_name(cls, v):
        """Valida nome da câmera"""
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Câmera Principal",
                "source": "rtsp://admin:password@192.168.1.100:554/stream",
                "location": "Entrada Principal",
                "username": "admin",
                "password": "password123",
                "enabled": True,
                "metadata": {
                    "resolution": "1920x1080",
                    "fps": 30,
                    "codec": "h264"
                }
            }
        }


class CameraCreate(CameraBase):
    """Model para criação de câmera"""
    pass


class CameraUpdate(BaseModel):
    """Model para atualização de câmera (todos campos opcionais)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source: Optional[str] = Field(None, min_length=1, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Câmera Principal - Atualizada",
                "enabled": False
            }
        }


class CameraResponse(CameraBase):
    """Model para resposta de câmera"""
    id: int = Field(..., description="ID da câmera")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: Optional[datetime] = Field(None, description="Data de atualização")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Câmera Principal",
                "source": "rtsp://192.168.1.100:554/stream",
                "location": "Entrada Principal",
                "username": "admin",
                "password": "******",
                "enabled": True,
                "metadata": {},
                "created_at": "2026-01-11T18:00:00",
                "updated_at": "2026-01-11T18:30:00"
            }
        }


class CameraListResponse(BaseModel):
    """Model para listagem de câmeras"""
    total: int = Field(..., description="Total de câmeras")
    cameras: List[CameraResponse] = Field(..., description="Lista de câmeras")


# ============================================
# ENDPOINTS
# ============================================

@router.post(
    "/",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Camera",
    description="Cria uma nova câmera (requer permissão ADMIN)"
)
async def create_camera(
    camera: CameraCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Cria uma nova câmera no sistema.
    
    - **name**: Nome descritivo da câmera
    - **source**: URL RTSP/HTTP ou device ID (0, 1, 2...)
    - **location**: Localização física (opcional)
    - **username**: Credencial RTSP (opcional)
    - **password**: Credencial RTSP (opcional)
    - **enabled**: Status ativo/inativo
    - **metadata**: Metadados adicionais (JSON)
    
    **Permissões**: ADMIN
    """
    try:
        camera_id = await database.create_camera(
            name=camera.name,
            source=camera.source,
            username=camera.username,
            password=camera.password,
            location=camera.location,
            enabled=camera.enabled,
            metadata=camera.metadata
        )
        
        # Buscar câmera criada
        created_camera = await database.get_camera_by_id(camera_id)
        
        if not created_camera:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Câmera criada mas não encontrada"
            )
        
        logger.info(f"✅ Camera created: {camera.name} by {current_user['username']}")
        return CameraResponse(**created_camera)
        
    except Exception as e:
        logger.error(f"❌ Error creating camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar câmera: {str(e)}"
        )


@router.get(
    "/",
    response_model=CameraListResponse,
    summary="List Cameras",
    description="Lista todas as câmeras do sistema"
)
async def list_cameras(
    active_only: bool = False,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Lista todas as câmeras cadastradas.
    
    - **active_only**: Se True, retorna apenas câmeras ativas (enabled=True)
    
    **Permissões**: Usuário autenticado
    """
    try:
        cameras = await database.get_all_cameras(active_only=active_only)
        
        return CameraListResponse(
            total=len(cameras),
            cameras=[CameraResponse(**cam) for cam in cameras]
        )
        
    except Exception as e:
        logger.error(f"❌ Error listing cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar câmeras: {str(e)}"
        )


@router.get(
    "/active",
    response_model=CameraListResponse,
    summary="List Active Cameras",
    description="Lista apenas câmeras ativas"
)
async def list_active_cameras(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Lista apenas câmeras ativas (enabled=True).
    
    **Permissões**: Usuário autenticado
    """
    try:
        cameras = await database.get_all_cameras(active_only=True)
        
        return CameraListResponse(
            total=len(cameras),
            cameras=[CameraResponse(**cam) for cam in cameras]
        )
        
    except Exception as e:
        logger.error(f"❌ Error listing active cameras: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar câmeras ativas: {str(e)}"
        )


@router.get(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Get Camera by ID",
    description="Busca câmera específica por ID"
)
async def get_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Busca uma câmera pelo ID.
    
    - **camera_id**: ID da câmera
    
    **Permissões**: Usuário autenticado
    """
    camera = await database.get_camera_by_id(camera_id)
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    return CameraResponse(**camera)

@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Update Camera",
    description="Atualiza câmera existente (requer permissão ADMIN)"
)
async def update_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Atualiza uma câmera existente.
    
    - **camera_id**: ID da câmera
    - Todos os campos são opcionais
    
    **Permissões**: ADMIN
    """
    # Verificar se câmera existe
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    # Preparar dados para update (apenas campos não-None)
    update_data = camera_update.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )
    
    try:
        success = await database.update_camera(camera_id, **update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar câmera"
            )
        
        # Buscar câmera atualizada
        updated_camera = await database.get_camera_by_id(camera_id)
        
        logger.info(f"✅ Camera {camera_id} updated by {current_user['username']}")
        return CameraResponse(**updated_camera)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating camera {camera_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar câmera: {str(e)}"
        )


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Camera",
    description="Deleta câmera (requer permissão ADMIN)"
)
async def delete_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Deleta uma câmera permanentemente.
    
    - **camera_id**: ID da câmera
    
    **Permissões**: ADMIN
    
    ⚠️ **ATENÇÃO**: Esta ação é irreversível!
    """
    # Verificar se câmera existe
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    try:
        success = await database.delete_camera(camera_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao deletar câmera"
            )
        
        logger.info(f"✅ Camera {camera_id} deleted by {current_user['username']}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting camera {camera_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar câmera: {str(e)}"
        )


@router.patch(
    "/{camera_id}/toggle",
    response_model=CameraResponse,
    summary="Toggle Camera Status",
    description="Ativa/desativa câmera (requer permissão ADMIN)"
)
async def toggle_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Alterna o status enabled da câmera (True <-> False).
    
    - **camera_id**: ID da câmera
    
    **Permissões**: ADMIN
    """
    # Verificar se câmera existe
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Câmera com ID {camera_id} não encontrada"
        )
    
    try:
        # Inverter status
        new_status = not existing_camera.get("enabled", True)
        
        success = await database.update_camera(
            camera_id,
            enabled=new_status
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao alternar status da câmera"
            )
        
        # Buscar câmera atualizada
        updated_camera = await database.get_camera_by_id(camera_id)
        
        status_text = "ativada" if new_status else "desativada"
        logger.info(f"✅ Camera {camera_id} {status_text} by {current_user['username']}")
        
        return CameraResponse(**updated_camera)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error toggling camera {camera_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao alternar status da câmera: {str(e)}"
        )

