"""
============================================================================
backend/runtime/orchestration/camera_sync.py v3.1
Camera Synchronization Service - DB to VisionSystem Bridge
============================================================================

RESPONSIBILITIES:
- Load active cameras from database
- Transform DB records to VisionSystem-compatible DTOs
- Synchronize VisionSystem state with database
- Provide reusable sync functions for startup, endpoints, and hooks
- Persist zone metadata updates (counting mode)

DOES NOT:
- Access ORM directly (uses database.py functions)
- Manage VisionSystem lifecycle (only loads/reloads data)
- Handle HTTP requests (pure service layer)
"""

import logging
from typing import List, Dict, Any, Optional
import json

from backend.adapters.storage import database
from backend.runtime.orchestration.vision_system import get_vision_system

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

    # 🔥 Metadata da câmera (default_tracker, reid_profile, etc.)
    metadata = camera_row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Invalid JSON metadata for camera {camera_id}: {e}"
            )
            metadata = {}

    # Zonas ativas desta câmera
    zones_db = await database.get_zones_by_camera_id(camera_id, active_only=True)

    zones_dto: List[dict] = []
    for zone in zones_db:
        zone_dto = await map_zone_to_dto(zone)
        if zone_dto:
            zones_dto.append(zone_dto)

    return {
        "id": camera_id,
        "name": camera_row.get("name", "Unknown Camera"),
        "source": camera_row.get("source", "0"),
        "username": camera_row.get("username"),
        "password": camera_row.get("password"),
        "zones": zones_dto,
        "metadata": metadata,  # ✅ ESSENCIAL para default_tracker / reid_profile
    }


async def map_zone_to_dto(zone: dict) -> Optional[dict]:
    """
    Mapeia zona do DB para formato DTO do VisionSystem.
    """
    try:
        # Metadata
        metadata = zone.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Invalid JSON metadata for zone {zone.get('id')}: {e}"
                )
                metadata = {}

        # Points
        points = zone.get("points", [])
        if isinstance(points, str):
            try:
                points = json.loads(points)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Invalid JSON points for zone {zone.get('id')}: {e}"
                )
                points = []

        if not points or len(points) < 3:
            logger.warning(
                f"Zone {zone.get('id')} has invalid geometry (< 3 points), skipping"
            )
            return None

        # detection_classes
        detection_classes = zone.get("detection_classes")
        if isinstance(detection_classes, str):
            try:
                detection_classes = json.loads(detection_classes)
            except json.JSONDecodeError:
                detection_classes = None

        return {
            "id": zone.get("id"),
            "name": zone.get("name", f"Zone {zone.get('id')}"),
            "points": points,
            "mode": zone.get("mode", "occupancy"),
            "color": zone.get("color", "#00FF00"),
            # Thresholds
            "empty_threshold": zone.get("empty_threshold", 0),
            "full_threshold": zone.get("full_threshold", 3),
            # Timeouts
            "empty_timeout": zone.get("empty_timeout", 5.0),
            "full_timeout": zone.get("full_timeout", 10.0),
            "email_cooldown": zone.get("email_cooldown", 600.0),
            # Detection
            "detection_classes": detection_classes,
            # Metadata
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Error mapping zone {zone.get('id')} to DTO: {e}")
        return None


# ============================================================================
# CORE SYNC FUNCTIONS
# ============================================================================


async def load_cameras_for_vision_system() -> List[dict]:
    """
    Carrega todas as câmeras ativas do banco e converte para DTOs do VisionSystem.
    """
    try:
        cameras_db = await database.get_all_cameras(active_only=True)
        if not cameras_db:
            logger.warning("⚠️ No active cameras found in database")
            return []

        cameras_dto: List[dict] = []
        for cam in cameras_db:
            camera_dto = await map_camera_to_vision_dto(cam)
            cameras_dto.append(camera_dto)

        total_zones = sum(len(cam.get("zones", [])) for cam in cameras_dto)
        logger.info(
            f"✅ Loaded {len(cameras_dto)} camera(s) with "
            f"{total_zones} zone(s) for VisionSystem"
        )

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
            f"✅ VisionSystem synchronized successfully with "
            f"{len(camera_ids)} camera(s): {camera_ids}"
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

        total_zones = sum(len(cam.get("zones", [])) for cam in cameras_data)
        logger.info(
            f"✅ VisionSystem initialized with {len(cameras_data)} camera(s) "
            f"and {total_zones} zone(s)"
        )
    except Exception as e:
        logger.error(f"❌ Error initializing VisionSystem from database: {e}")
        #raise #NÃO re-levanta a exceção aqui e server não cai


# ============================================================================
# HOOKS PARA CRUD DE CÂMERAS
# ============================================================================


async def on_camera_created(camera_id: int) -> None:
    try:
        logger.info(f"📹 Camera {camera_id} created, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera creation: {e}")


async def on_camera_updated(camera_id: int) -> None:
    try:
        logger.info(f"🔄 Camera {camera_id} updated, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera update: {e}")


async def on_camera_deleted(camera_id: int) -> None:
    try:
        logger.info(f"🗑️ Camera {camera_id} deleted, resyncing VisionSystem...")
        await sync_vision_system_from_db()
    except Exception as e:
        logger.error(f"❌ Error resyncing after camera deletion: {e}")


# ============================================================================
# ZONE METADATA PERSISTENCE
# ============================================================================


async def sync_zone_metadata_to_db() -> None:
    """
    Sincroniza metadata de zonas do VisionSystem para o banco.
    """
    try:
        vision_system = get_vision_system()
        metadata_updates = vision_system.get_zone_metadata_updates()
        if not metadata_updates:
            return

        updated_count = 0
        for zone_id, metadata in metadata_updates.items():
            try:
                logger.debug(
                    f"[SKIP] Would update metadata for zone {zone_id}: {metadata}"
                )
                # Quando implementar no adapter:
                # await database.update_zone_metadata(zone_id, metadata)
                updated_count += 1
            except Exception as e:
                logger.error(f"❌ Error updating metadata for zone {zone_id}: {e}")

        if updated_count > 0:
            logger.debug(
                f"✅ Prepared metadata sync for {updated_count} zones "
                "(DB update skipped)"
            )
    except Exception as e:
        logger.error(f"❌ Error in sync_zone_metadata_to_db: {e}")


async def get_zone_metrics_for_api(
    camera_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retorna métricas agregadas de zonas para API.
    """
    try:
        vision_system = get_vision_system()
        if camera_id:
            processor = vision_system.get_zone_processor(camera_id)
            if not processor:
                return {"error": f"Camera {camera_id} not found"}
            return processor.get_aggregate_metrics()
        else:
            all_metrics: Dict[int, Any] = {}
            for cam_id in vision_system.get_active_camera_ids():
                processor = vision_system.get_zone_processor(cam_id)
                if processor:
                    all_metrics[cam_id] = processor.get_aggregate_metrics()
            return all_metrics
    except Exception as e:
        logger.error(f"❌ Error getting zone metrics: {e}")
        return {"error": str(e)}
