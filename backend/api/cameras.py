"""
============================================================================
backend/api/cameras.py - v1.1 - Cameras CRUD API
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

# Database and dependencies
from backend import database
from backend.dependencies import get_current_active_user, get_current_admin_user

# Hooks
from backend.services.camera_sync import (
    on_camera_created,
    on_camera_updated,
    on_camera_deleted,
)

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
    name: str = Field(..., min_length=1, max_length=100)
    source: str = Field(..., min_length=1, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    enabled: bool = Field(True)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("source")
    def validate_source(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Source não pode ser vazio")
        valid_prefixes = ("rtsp://", "http://", "https://", "/dev/video")
        if not (v.startswith(valid_prefixes) or v.isdigit() or v.endswith(('.mp4', '.avi', '.mkv'))):
            logger.warning(f"⚠️ Source format may be invalid: {v}")
        return v

    @validator("name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Nome não pode ser vazio")
        return v


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    source: Optional[str] = Field(None, min_length=1, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CameraListResponse(BaseModel):
    total: int
    cameras: List[CameraResponse]

# ============================================
# ENDPOINTS
# ============================================

# -----------------------------
# Create Camera
# -----------------------------
@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera: CameraCreate,
    current_user: dict = Depends(get_current_admin_user),
):
    try:
        camera_id = await database.create_camera(
            name=camera.name,
            source=camera.source,
            username=camera.username,
            password=camera.password,
            location=camera.location,
            enabled=camera.enabled,
            metadata=camera.metadata,
        )
        created_camera = await database.get_camera_by_id(camera_id)
        await on_camera_created(camera_id)
        return CameraResponse(**created_camera)
    except Exception as e:
        logger.error(f"❌ Error creating camera: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar câmera: {str(e)}")


# -----------------------------
# List Cameras
# -----------------------------
@router.get("/", response_model=CameraListResponse)
async def list_cameras(
    active_only: bool = False,
    current_user: dict = Depends(get_current_active_user)
):
    try:
        cameras = await database.get_all_cameras(active_only=active_only)
        return CameraListResponse(
            total=len(cameras),
            cameras=[CameraResponse(**cam) for cam in cameras]
        )
    except Exception as e:
        logger.error(f"❌ Error listing cameras: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar câmeras: {str(e)}")


# -----------------------------
# List Active Cameras
# -----------------------------
@router.get("/active", response_model=CameraListResponse)
async def list_active_cameras(
    current_user: dict = Depends(get_current_active_user)
):
    try:
        cameras = await database.get_all_cameras(active_only=True)
        return CameraListResponse(
            total=len(cameras),
            cameras=[CameraResponse(**cam) for cam in cameras]
        )
    except Exception as e:
        logger.error(f"❌ Error listing active cameras: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar câmeras ativas: {str(e)}")


# -----------------------------
# Get Camera by ID
# -----------------------------
@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    camera = await database.get_camera_by_id(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Câmera com ID {camera_id} não encontrada")
    return CameraResponse(**camera)


# -----------------------------
# Update Camera
# -----------------------------
@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")

    update_data = camera_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    success = await database.update_camera(camera_id, **update_data)
    updated_camera = await database.get_camera_by_id(camera_id)
    await on_camera_updated(camera_id)
    return CameraResponse(**updated_camera)


# -----------------------------
# Delete Camera
# -----------------------------
@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")

    await database.delete_camera(camera_id)
    await on_camera_deleted(camera_id)
    return None


# -----------------------------
# Toggle Camera Enabled Status
# -----------------------------
@router.patch("/{camera_id}/toggle", response_model=CameraResponse)
async def toggle_camera(
    camera_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    existing_camera = await database.get_camera_by_id(camera_id)
    if not existing_camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")

    new_status = not existing_camera.get("enabled", True)
    await database.update_camera(camera_id, enabled=new_status)
    updated_camera = await database.get_camera_by_id(camera_id)
    await on_camera_updated(camera_id)
    return CameraResponse(**updated_camera)
