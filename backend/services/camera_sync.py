"""
============================================================================
backend/services/camera_sync.py v1.2
Camera Synchronization Service - DB to VisionSystem Bridge
============================================================================
RESPONSIBILITIES:
- Load active cameras from database
- Transform DB records to VisionSystem-compatible DTOs
- Synchronize VisionSystem state with database
- Provide reusable sync functions for startup, endpoints, and hooks

DOES NOT:
- Access ORM directly (uses database.py functions)
- Manage VisionSystem lifecycle (only loads/reloads data)
- Handle HTTP requests (pure service layer)

USAGE:
- Application startup (main.py)
- /api/v1/stream/reload_cameras endpoint
- Post-CRUD hooks in cameras.py (create/update/delete)
============================================================================
"""

import logging
from typing import List, Dict, Any

from backend import database
from backend.services.vision_system import get_vision_system

logger = logging.getLogger(__name__)

# ============================================================================ 
# DTO MAPPING
# ============================================================================

async def map_camera_to_vision_dto(camera_row: dict) -> dict:
    """
    Transform a database camera record into VisionSystem DTO format.
    Loads zones from database for this camera.
    """
    camera_id = camera_row.get("id")
    
    # Busca zonas ativas desta câmera no banco
    zones_db = await database.get_zones_by_camera_id(camera_id, active_only=True)
    
    # Mapeia zonas para o formato esperado pelo VisionSystem
    zones_dto = []
    for zone in zones_db:
        # ✅ Parse metadata se vier como string JSON
        metadata = zone.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        
        zones_dto.append({
            "id": zone.get("id"),
            "name": zone.get("name"),
            "points": zone.get("points", []),
            "mode": zone.get("mode", "occupancy"),
            "empty_timeout": zone.get("empty_timeout", 5.0),
            "full_timeout": zone.get("full_timeout", 10.0),
            "empty_threshold": zone.get("empty_threshold", 0),
            "full_threshold": zone.get("full_threshold", 3),
            "metadata": metadata,  
            "color": zone.get("color"),
        })
    
    return {
        "id": camera_id,
        "name": camera_row.get("name", "Unknown Camera"),
        "source": camera_row.get("source", "0"),
        "username": camera_row.get("username"),
        "password": camera_row.get("password"),
        "zones": zones_dto,
    }



# ============================================================================ 
# CORE SYNC FUNCTIONS
# ============================================================================

async def load_cameras_for_vision_system() -> List[dict]:
    """
    Carrega todas as câmeras ativas do banco e converte para DTOs do VisionSystem.
    """
    try:
        logger.info("📷 Loading cameras from database for VisionSystem...")
        cameras_db = await database.get_all_cameras(active_only=True)
        
        if not cameras_db:
            logger.warning("⚠️ No active cameras found in database")
            return []
        
        # Transform to VisionSystem DTOs (now async)
        cameras_dto = []
        for cam in cameras_db:
            camera_dto = await map_camera_to_vision_dto(cam)
            cameras_dto.append(camera_dto)
        
        logger.info(f"✅ Loaded {len(cameras_dto)} active camera(s) for VisionSystem")
        return cameras_dto
    
    except Exception as e:
        logger.error(f"❌ Error loading cameras from database: {e}")
        raise



async def sync_vision_system_from_db() -> List[int]:
    """
    Sincroniza o VisionSystem com o estado atual das câmeras no banco.
    """
    try:
        logger.info("🔄 Starting VisionSystem synchronization from database...")
        cameras_data = await load_cameras_for_vision_system()
        vision_system = get_vision_system()
        await vision_system.reload_from_db(cameras_data)
        camera_ids = [cam["id"] for cam in cameras_data]
        logger.info(
            f"✅ VisionSystem synchronized successfully with {len(camera_ids)} camera(s): {camera_ids}"
        )
        return camera_ids
    except Exception as e:
        logger.error(f"❌ Error synchronizing VisionSystem from database: {e}")
        raise

# ============================================================================ 
# INITIALIZATION HELPER
# ============================================================================

async def initialize_vision_system_from_db() -> None:
    """
    Inicializa o VisionSystem com câmeras do banco (usado no startup).
    """
    try:
        logger.info("🚀 Initializing VisionSystem from database...")
        cameras_data = await load_cameras_for_vision_system()
        vision_system = get_vision_system()
        await vision_system.initialize(cameras_data=cameras_data)
        logger.info(f"✅ VisionSystem initialized with {len(cameras_data)} camera(s)")
    except Exception as e:
        logger.error(f"❌ Error initializing VisionSystem from database: {e}")
        # Não levanta para não impedir o startup

# ============================================================================ 
# HOOKS PARA CRUD DE CÂMERAS
# ============================================================================

async def on_camera_created(camera_id: int) -> None:
    """Hook chamado após criação de câmera."""
    try:
        logger.info(f"🔄 Camera {camera_id} created, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera creation: {e}")


async def on_camera_updated(camera_id: int) -> None:
    """Hook chamado após atualização de câmera."""
    try:
        logger.info(f"🔄 Camera {camera_id} updated, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera update: {e}")


async def on_camera_deleted(camera_id: int) -> None:
    """Hook chamado após exclusão de câmera."""
    try:
        logger.info(f"🔄 Camera {camera_id} deleted, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera deletion: {e}")
