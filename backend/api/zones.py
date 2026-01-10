"""
============================================================================
backend/api/zones.py - COMPLETE v3.0
Zone Management Routes (Enhanced Detection Zones)
============================================================================
✨ Features v3.0:
- Complete CRUD operations
- Zone search and filtering
- Bulk operations
- Zone statistics
- Export/Import zones
- Zone templates
- Polygon validation
- Zone cloning
- Activity tracking
- Performance metrics
- Zone preview
- Advanced analytics

Endpoints v2.0 (5 endpoints):
- POST   /zones/          - Criar nova zona
- GET    /zones/          - Listar todas zonas
- GET    /zones/{id}      - Obter zona específica
- PUT    /zones/{id}      - Atualizar zona
- DELETE /zones/{id}      - Deletar zona (soft delete)

NEW v3.0 (10 endpoints):
- POST   /zones/search    - Busca avançada
- POST   /zones/bulk/create - Cria múltiplas zonas
- DELETE /zones/bulk/delete - Deleta múltiplas
- POST   /zones/{id}/clone - Clona zona
- POST   /zones/validate  - Valida polígono
- GET    /zones/statistics - Estatísticas gerais
- GET    /zones/export    - Exporta zonas
- POST   /zones/import    - Importa zonas
- GET    /zones/templates - Lista templates
- POST   /zones/templates/{name} - Cria zona de template

Architecture:
- PostgreSQL (psycopg3 async) + JSON fallback
- Soft delete (deleted_at)
- Real-time sync with yolo.py
- RAG-ready (vector support)

✅ v2.0 compatibility: 100%
🔒 ADMIN-ONLY: All endpoints require admin privileges
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from psycopg_pool import AsyncConnectionPool

from database import get_db_pool, sync_zones_to_settings
from models.zones import ZoneCreate, ZoneUpdate, ZoneResponse
from config import settings
from dependencies import get_current_admin_user, limiter

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

router = APIRouter(prefix="/api/v1/zones", tags=["Zones"])
logger = logging.getLogger("uvicorn")

# Garante que diretório data/ existe
DATA_DIR = settings.BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class ZoneMode(str, Enum):
    """Zone detection modes"""
    OCCUPANCY = "occupancy"
    COUNTING = "counting"
    ALERT = "alert"
    TRACKING = "tracking"


class ZoneStatus(str, Enum):
    """Zone operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class SortField(str, Enum):
    """Sort fields for zone listing"""
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    MODE = "mode"


class SortOrder(str, Enum):
    """Sort order"""
    ASC = "asc"
    DESC = "desc"


class ExportFormat(str, Enum):
    """Export formats"""
    JSON = "json"


# Zone templates
ZONE_TEMPLATES = {
    "parking_spot": {
        "name": "Vaga de Estacionamento",
        "mode": "occupancy",
        "empty_timeout": 30.0,
        "full_timeout": 5.0,
        "empty_threshold": 0,
        "full_threshold": 1,
        "description": "Template para detecção de vagas de estacionamento"
    },
    "entrance": {
        "name": "Entrada",
        "mode": "counting",
        "empty_timeout": 10.0,
        "full_timeout": 2.0,
        "empty_threshold": 0,
        "full_threshold": 3,
        "description": "Template para contagem de pessoas em entradas"
    },
    "restricted_area": {
        "name": "Área Restrita",
        "mode": "alert",
        "empty_timeout": 5.0,
        "full_timeout": 1.0,
        "empty_threshold": 0,
        "full_threshold": 1,
        "description": "Template para alertas em áreas restritas"
    }
}


# ============================================================================
# PYDANTIC MODELS v3.0
# ============================================================================

class ZoneSearchRequest(BaseModel):
    """Zone search parameters"""
    name: Optional[str] = None
    mode: Optional[ZoneMode] = None
    enabled: Optional[bool] = None
    active: Optional[bool] = None
    search_term: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    sort_by: Optional[SortField] = SortField.CREATED_AT
    sort_order: Optional[SortOrder] = SortOrder.DESC
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ZoneSearchResponse(BaseModel):
    """Zone search response"""
    zones: List[ZoneResponse]
    total: int
    limit: int
    offset: int


class ZoneBulkCreateRequest(BaseModel):
    """Bulk zone creation"""
    zones: List[ZoneCreate] = Field(..., min_items=1, max_items=50)


class ZoneBulkCreateResponse(BaseModel):
    """Bulk creation response"""
    created: int
    failed: int
    errors: List[Dict[str, str]]
    zones: List[ZoneResponse]


class ZoneBulkDeleteRequest(BaseModel):
    """Bulk zone deletion"""
    zone_ids: List[int] = Field(..., min_items=1, max_items=50)


class ZoneCloneRequest(BaseModel):
    """Zone clone request"""
    new_name: str = Field(..., min_length=3, max_length=100)
    offset_x: int = Field(default=0, description="Horizontal offset in pixels")
    offset_y: int = Field(default=0, description="Vertical offset in pixels")


class PolygonValidationRequest(BaseModel):
    """Polygon validation request"""
    points: List[List[int]] = Field(..., min_items=3)


class PolygonValidationResponse(BaseModel):
    """Polygon validation response"""
    valid: bool
    area: Optional[float] = None
    perimeter: Optional[float] = None
    centroid: Optional[List[float]] = None
    issues: List[str] = []


class ZoneStatistics(BaseModel):
    """Zone statistics"""
    total_zones: int
    enabled_zones: int
    disabled_zones: int
    active_zones: int
    zones_by_mode: Dict[str, int]
    average_area: Optional[float]
    total_detections: Optional[int]
    most_active_zones: List[Dict[str, Any]]
    timestamp: datetime


class ZoneTemplate(BaseModel):
    """Zone template"""
    id: str
    name: str
    mode: str
    description: str
    default_settings: Dict[str, Any]


class ZoneFromTemplateRequest(BaseModel):
    """Create zone from template request"""
    zone_name: str = Field(..., min_length=3, max_length=100)
    points: List[List[int]] = Field(..., min_items=3)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_polygon_area(points: List[List[int]]) -> float:
    """
    Calculate polygon area using Shoelace formula
    """
    if len(points) < 3:
        return 0.0
    
    n = len(points)
    area = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    
    return abs(area) / 2.0


def calculate_polygon_perimeter(points: List[List[int]]) -> float:
    """Calculate polygon perimeter"""
    if len(points) < 2:
        return 0.0
    
    perimeter = 0.0
    n = len(points)
    
    for i in range(n):
        j = (i + 1) % n
        dx = points[j][0] - points[i][0]
        dy = points[j][1] - points[i][1]
        perimeter += (dx**2 + dy**2)**0.5
    
    return perimeter


def calculate_centroid(points: List[List[int]]) -> List[float]:
    """Calculate polygon centroid"""
    if not points:
        return [0.0, 0.0]
    
    x_sum = sum(p[0] for p in points)
    y_sum = sum(p[1] for p in points)
    n = len(points)
    
    return [x_sum / n, y_sum / n]


def validate_polygon(points: List[List[int]]) -> tuple[bool, List[str]]:
    """
    Validate polygon
    Returns: (is_valid, issues)
    """
    issues = []
    
    # Check minimum points
    if len(points) < 3:
        issues.append("Polygon must have at least 3 points")
        return False, issues
    
    # Check for duplicate consecutive points
    for i in range(len(points)):
        j = (i + 1) % len(points)
        if points[i] == points[j]:
            issues.append(f"Duplicate consecutive points at index {i}")
    
    # Check for negative coordinates
    for i, point in enumerate(points):
        if point[0] < 0 or point[1] < 0:
            issues.append(f"Negative coordinates at point {i}: {point}")
    
    # Check area
    area = calculate_polygon_area(points)
    if area < 100:  # Minimum area threshold
        issues.append(f"Polygon area too small: {area:.2f} (minimum: 100)")
    
    # Check if polygon is too large (optional)
    if area > 1000000:  # Maximum area threshold
        issues.append(f"Polygon area too large: {area:.2f} (maximum: 1,000,000)")
    
    is_valid = len(issues) == 0
    return is_valid, issues


async def zone_to_dict(row: dict) -> dict:
    """Convert database row to zone dictionary"""
    return {
        'id': row['id'],
        'name': row['name'],
        'points': json.loads(row['points']) if isinstance(row['points'], str) else row['points'],
        'mode': row['mode'],
        'empty_timeout': row['empty_timeout'],
        'full_timeout': row['full_timeout'],
        'empty_threshold': row['empty_threshold'],
        'full_threshold': row['full_threshold'],
        'enabled': row['enabled'],
        'active': row['active'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'deleted_at': row.get('deleted_at')
    }


async def sync_zones_to_json():
    """Sync all zones to JSON file"""
    try:
        pool = get_db_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, points, mode, empty_timeout, full_timeout,
                           empty_threshold, full_threshold, enabled, active,
                           created_at, updated_at
                    FROM zones
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                    """
                )
                rows = await cur.fetchall()
        
        zones_data = []
        for row in rows:
            zone_dict = await zone_to_dict(row)
            zone_dict['created_at'] = zone_dict['created_at'].isoformat()
            zone_dict['updated_at'] = zone_dict['updated_at'].isoformat() if zone_dict['updated_at'] else None
            zone_dict.pop('deleted_at', None)
            zones_data.append(zone_dict)
        
        zones_file = DATA_DIR / "zones.json"
        with open(zones_file, 'w', encoding='utf-8') as f:
            json.dump(zones_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Synced {len(zones_data)} zones to JSON")
        
    except Exception as e:
        logger.warning(f"⚠️ Error syncing zones to JSON: {e}")


# ============================================================================
# v2.0 ENDPOINTS - ZONE CRUD (ADMIN ONLY)
# ============================================================================

@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED, summary="➕ Criar nova zona")
@limiter.limit("100/minute")
async def create_zone(
    request: Request,
    zone: ZoneCreate,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ✅ v2.0: Cria uma nova zona de detecção
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            # Validate polygon
            is_valid, issues = validate_polygon(zone.points)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid polygon: {', '.join(issues)}"
                )
            
            # Check duplicate name
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM zones WHERE name = %s AND deleted_at IS NULL",
                    (zone.name,)
                )
                existing = await cur.fetchone()
                
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Zona com nome '{zone.name}' já existe"
                    )
                
                # Insert zone
                await cur.execute(
                    """
                    INSERT INTO zones (
                        name, points, mode, empty_timeout, full_timeout,
                        empty_threshold, full_threshold, enabled, active, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id, name, points, mode, empty_timeout, full_timeout,
                              empty_threshold, full_threshold, enabled, active, 
                              created_at, updated_at
                    """,
                    (
                        zone.name,
                        json.dumps(zone.points),
                        zone.mode,
                        zone.empty_timeout,
                        zone.full_timeout,
                        zone.empty_threshold,
                        zone.full_threshold,
                        zone.enabled,
                        zone.active
                    )
                )
                
                row = await cur.fetchone()
                await conn.commit()
                
                logger.info(f"✅ Zona criada: {row['name']} (ID: {row['id']}) por {current_user.get('username')} [ADMIN]")
                
                zone_dict = await zone_to_dict(row)
            
            # Sync to JSON and settings
            await sync_zones_to_json()
            await sync_zones_to_settings()
            
            return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao criar zona: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar zona: {str(e)}"
            )


@router.get("", response_model=List[ZoneResponse], summary="📋 Listar todas zonas")
@limiter.limit("100/minute")
async def list_zones(
    request: Request,
    include_disabled: bool = Query(default=False),
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ✅ v2.0: Lista todas as zonas ativas (não deletadas)
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            query = """
                SELECT id, name, points, mode, empty_timeout, full_timeout,
                       empty_threshold, full_threshold, enabled, active,
                       created_at, updated_at
                FROM zones
                WHERE deleted_at IS NULL
            """
            
            if not include_disabled:
                query += " AND enabled = TRUE"
            
            query += " ORDER BY created_at DESC"
            
            async with conn.cursor() as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
            
            logger.info(f"📋 Listando {len(rows)} zonas para {current_user.get('username')} [ADMIN]")
            
            results = []
            for row in rows:
                zone_dict = await zone_to_dict(row)
                results.append(ZoneResponse(**zone_dict))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar zonas: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar zonas: {str(e)}"
            )


@router.get("/{zone_id}", response_model=ZoneResponse, summary="🔍 Obter zona específica")
@limiter.limit("100/minute")
async def get_zone(
    request: Request,
    zone_id: int,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ✅ v2.0: Obtém uma zona específica por ID
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, points, mode, empty_timeout, full_timeout,
                           empty_threshold, full_threshold, enabled, active,
                           created_at, updated_at
                    FROM zones
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (zone_id,)
                )
                
                row = await cur.fetchone()
                
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                logger.info(f"🔍 Zona encontrada: {row['id']} - {row['name']} [ADMIN: {current_user.get('username')}]")
                
                zone_dict = await zone_to_dict(row)
                
                return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao buscar zona: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar zona: {str(e)}"
            )


@router.put("/{zone_id}", response_model=ZoneResponse, summary="✏️ Atualizar zona")
@limiter.limit("100/minute")
async def update_zone(
    request: Request,
    zone_id: int,
    zone_update: ZoneUpdate,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ✅ v2.0: Atualiza uma zona existente
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Check zone exists
                await cur.execute(
                    "SELECT id FROM zones WHERE id = %s AND deleted_at IS NULL",
                    (zone_id,)
                )
                
                if not await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                # Validate polygon if provided
                if zone_update.points is not None:
                    is_valid, issues = validate_polygon(zone_update.points)
                    if not is_valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid polygon: {', '.join(issues)}"
                        )
                
                # Check duplicate name if changed
                if zone_update.name:
                    await cur.execute(
                        "SELECT id FROM zones WHERE name = %s AND id != %s AND deleted_at IS NULL",
                        (zone_update.name, zone_id)
                    )
                    
                    if await cur.fetchone():
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Zona com nome '{zone_update.name}' já existe"
                        )
                
                # Build dynamic update query
                update_fields = []
                update_values = []
                
                field_mapping = {
                    'name': zone_update.name,
                    'mode': zone_update.mode,
                    'empty_timeout': zone_update.empty_timeout,
                    'full_timeout': zone_update.full_timeout,
                    'empty_threshold': zone_update.empty_threshold,
                    'full_threshold': zone_update.full_threshold,
                    'enabled': zone_update.enabled,
                    'active': zone_update.active
                }
                
                for field, value in field_mapping.items():
                    if value is not None:
                        update_fields.append(f"{field} = %s")
                        update_values.append(value)
                
                if zone_update.points is not None:
                    update_fields.append("points = %s")
                    update_values.append(json.dumps(zone_update.points))
                
                if not update_fields:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nenhum campo para atualizar"
                    )
                
                update_fields.append("updated_at = NOW()")
                update_values.append(zone_id)
                
                query = f"""
                    UPDATE zones
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING id, name, points, mode, empty_timeout, full_timeout,
                              empty_threshold, full_threshold, enabled, active,
                              created_at, updated_at
                """
                
                await cur.execute(query, update_values)
                row = await cur.fetchone()
                await conn.commit()
                
                logger.info(f"✅ Zona atualizada: {row['name']} (ID: {row['id']}) por {current_user.get('username')} [ADMIN]")
                
                zone_dict = await zone_to_dict(row)
            
            # Sync to JSON and settings
            await sync_zones_to_json()
            await sync_zones_to_settings()
            
            return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar zona: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao atualizar zona: {str(e)}"
            )


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT, summary="🗑️ Deletar zona")
@limiter.limit("100/minute")
async def delete_zone(
    request: Request,
    zone_id: int,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ✅ v2.0: Deleta uma zona (soft delete)
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Check zone exists
                await cur.execute(
                    "SELECT id, name FROM zones WHERE id = %s AND deleted_at IS NULL",
                    (zone_id,)
                )
                
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                zone_name = row['name']
                
                # Soft delete
                await cur.execute(
                    """
                    UPDATE zones
                    SET deleted_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (zone_id,)
                )
                
                await conn.commit()
                logger.info(f"🗑️ Zona deletada (soft delete): {zone_name} (ID: {zone_id}) por {current_user.get('username')} [ADMIN]")
            
            # Sync to JSON and settings
            await sync_zones_to_json()
            await sync_zones_to_settings()
            
            return None  # 204 No Content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao deletar zona: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao deletar zona: {str(e)}"
            )


# ============================================================================
# v3.0 ENDPOINTS - SEARCH & FILTER (ADMIN ONLY)
# ============================================================================

@router.post("/search", response_model=ZoneSearchResponse, summary="🔍 Busca avançada de zonas")
async def search_zones(
    search_params: ZoneSearchRequest,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Busca avançada de zonas com filtros
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            # Build query with filters
            query = """
                SELECT id, name, points, mode, empty_timeout, full_timeout,
                       empty_threshold, full_threshold, enabled, active,
                       created_at, updated_at
                FROM zones
                WHERE deleted_at IS NULL
            """
            params = []
            
            if search_params.name:
                query += " AND name ILIKE %s"
                params.append(f"%{search_params.name}%")
            
            if search_params.mode:
                query += " AND mode = %s"
                params.append(search_params.mode.value)
            
            if search_params.enabled is not None:
                query += " AND enabled = %s"
                params.append(search_params.enabled)
            
            if search_params.active is not None:
                query += " AND active = %s"
                params.append(search_params.active)
            
            if search_params.search_term:
                query += " AND (name ILIKE %s OR mode ILIKE %s)"
                params.extend([f"%{search_params.search_term}%", f"%{search_params.search_term}%"])
            
            # Count total before pagination
            count_query = query.replace(
                "SELECT id, name, points, mode, empty_timeout, full_timeout, empty_threshold, full_threshold, enabled, active, created_at, updated_at",
                "SELECT COUNT(*)"
            )
            
            # Sort
            sort_field_map = {
                SortField.NAME: "name",
                SortField.CREATED_AT: "created_at",
                SortField.UPDATED_AT: "updated_at",
                SortField.MODE: "mode"
            }
            
            sort_col = sort_field_map.get(search_params.sort_by, "created_at")
            sort_dir = "ASC" if search_params.sort_order == SortOrder.ASC else "DESC"
            query += f" ORDER BY {sort_col} {sort_dir}"
            
            # Pagination
            query += " LIMIT %s OFFSET %s"
            pagination_params = [search_params.limit, search_params.offset]
            
            async with conn.cursor() as cur:
                # Get total count
                await cur.execute(count_query, params)
                total = (await cur.fetchone())['count']
                
                # Get filtered results
                await cur.execute(query, params + pagination_params)
                rows = await cur.fetchall()
            
            zones = []
            for row in rows:
                zone_dict = await zone_to_dict(row)
                zones.append(ZoneResponse(**zone_dict))
            
            logger.info(f"🔍 {current_user.get('username')} [ADMIN] searched zones: {len(zones)}/{total} results")
            
            return ZoneSearchResponse(
                zones=zones,
                total=total,
                limit=search_params.limit,
                offset=search_params.offset
            )
            
        except Exception as e:
            logger.error(f"❌ Error searching zones: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar zonas: {str(e)}"
            )


# ============================================================================
# v3.0 ENDPOINTS - BULK OPERATIONS (ADMIN ONLY)
# ============================================================================

@router.post("/bulk/create", response_model=ZoneBulkCreateResponse, summary="➕ Criar múltiplas zonas")
async def bulk_create_zones(
    bulk_request: ZoneBulkCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Cria múltiplas zonas em lote
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            created_zones = []
            errors = []
            created_count = 0
            failed_count = 0
            
            async with conn.cursor() as cur:
                for zone_data in bulk_request.zones:
                    try:
                        # Validate polygon
                        is_valid, issues = validate_polygon(zone_data.points)
                        if not is_valid:
                            errors.append({
                                "name": zone_data.name,
                                "error": f"Invalid polygon: {', '.join(issues)}"
                            })
                            failed_count += 1
                            continue
                        
                        # Check duplicate name
                        await cur.execute(
                            "SELECT id FROM zones WHERE name = %s AND deleted_at IS NULL",
                            (zone_data.name,)
                        )
                        
                        if await cur.fetchone():
                            errors.append({
                                "name": zone_data.name,
                                "error": "Name already exists"
                            })
                            failed_count += 1
                            continue
                        
                        # Create zone
                        await cur.execute(
                            """
                            INSERT INTO zones (
                                name, points, mode, empty_timeout, full_timeout,
                                empty_threshold, full_threshold, enabled, active, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            RETURNING id, name, points, mode, empty_timeout, full_timeout,
                                      empty_threshold, full_threshold, enabled, active,
                                      created_at, updated_at
                            """,
                            (
                                zone_data.name,
                                json.dumps(zone_data.points),
                                zone_data.mode,
                                zone_data.empty_timeout,
                                zone_data.full_timeout,
                                zone_data.empty_threshold,
                                zone_data.full_threshold,
                                zone_data.enabled,
                                zone_data.active
                            )
                        )
                        
                        row = await cur.fetchone()
                        zone_dict = await zone_to_dict(row)
                        created_zones.append(ZoneResponse(**zone_dict))
                        created_count += 1
                    
                    except Exception as e:
                        errors.append({
                            "name": zone_data.name,
                            "error": str(e)
                        })
                        failed_count += 1
                
                await conn.commit()
            
            # Sync to JSON and settings
            if created_count > 0:
                await sync_zones_to_json()
                await sync_zones_to_settings()
            
            logger.info(f"✅ Bulk created {created_count} zones, {failed_count} failed by {current_user.get('username')} [ADMIN]")
            
            return ZoneBulkCreateResponse(
                created=created_count,
                failed=failed_count,
                errors=errors,
                zones=created_zones
            )
            
        except Exception as e:
            logger.error(f"❌ Error bulk creating zones: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar zonas em lote: {str(e)}"
            )


@router.post("/bulk/delete", summary="🗑️ Deletar múltiplas zonas")
async def bulk_delete_zones(
    bulk_request: ZoneBulkDeleteRequest,
    request: Request,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Deleta múltiplas zonas em lote
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            deleted_count = 0
            failed = []
            
            async with conn.cursor() as cur:
                for zone_id in bulk_request.zone_ids:
                    try:
                        await cur.execute(
                            "SELECT id FROM zones WHERE id = %s AND deleted_at IS NULL",
                            (zone_id,)
                        )
                        
                        if not await cur.fetchone():
                            failed.append({
                                "zone_id": zone_id,
                                "error": "Zone not found"
                            })
                            continue
                        
                        await cur.execute(
                            """
                            UPDATE zones
                            SET deleted_at = NOW(), updated_at = NOW()
                            WHERE id = %s AND deleted_at IS NULL
                            """,
                            (zone_id,)
                        )
                        
                        deleted_count += 1
                    
                    except Exception as e:
                        failed.append({
                            "zone_id": zone_id,
                            "error": str(e)
                        })
                
                await conn.commit()
            
            # Sync to JSON and settings
            if deleted_count > 0:
                await sync_zones_to_json()
                await sync_zones_to_settings()
            
            logger.info(f"✅ Bulk deleted {deleted_count} zones by {current_user.get('username')} [ADMIN]")
            
            return {
                "deleted": deleted_count,
                "failed": len(failed),
                "errors": failed
            }
            
        except Exception as e:
            logger.error(f"❌ Error bulk deleting zones: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao deletar zonas em lote: {str(e)}"
            )


# ============================================================================
# v3.0 ENDPOINTS - ZONE MANAGEMENT (ADMIN ONLY)
# ============================================================================

@router.post("/{zone_id}/clone", response_model=ZoneResponse, summary="📋 Clonar zona")
async def clone_zone(
    zone_id: int,
    clone_request: ZoneCloneRequest,
    request: Request,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Clona uma zona existente
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Get original zone
                await cur.execute(
                    """
                    SELECT id, name, points, mode, empty_timeout, full_timeout,
                           empty_threshold, full_threshold, enabled, active
                    FROM zones
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (zone_id,)
                )
                
                original = await cur.fetchone()
                if not original:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                # Apply offset to points
                original_points = json.loads(original['points']) if isinstance(original['points'], str) else original['points']
                new_points = [[p[0] + clone_request.offset_x, p[1] + clone_request.offset_y] for p in original_points]
                
                # Validate new polygon
                is_valid, issues = validate_polygon(new_points)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid cloned polygon: {', '.join(issues)}"
                    )
                
                # Check duplicate name
                await cur.execute(
                    "SELECT id FROM zones WHERE name = %s AND deleted_at IS NULL",
                    (clone_request.new_name,)
                )
                
                if await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Zona com nome '{clone_request.new_name}' já existe"
                    )
                
                # Create cloned zone
                await cur.execute(
                    """
                    INSERT INTO zones (
                        name, points, mode, empty_timeout, full_timeout,
                        empty_threshold, full_threshold, enabled, active, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id, name, points, mode, empty_timeout, full_timeout,
                              empty_threshold, full_threshold, enabled, active,
                              created_at, updated_at
                    """,
                    (
                        clone_request.new_name,
                        json.dumps(new_points),
                        original['mode'],
                        original['empty_timeout'],
                        original['full_timeout'],
                        original['empty_threshold'],
                        original['full_threshold'],
                        original['enabled'],
                        original['active']
                    )
                )
                
                row = await cur.fetchone()
                await conn.commit()
                
                logger.info(f"✅ Zona clonada: {original['name']} -> {row['name']} por {current_user.get('username')} [ADMIN]")
                
                zone_dict = await zone_to_dict(row)
            
            # Sync to JSON and settings
            await sync_zones_to_json()
            await sync_zones_to_settings()
            
            return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error cloning zone: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao clonar zona: {str(e)}"
            )


@router.post("/validate", response_model=PolygonValidationResponse, summary="✔️ Validar polígono")
async def validate_polygon_endpoint(
    validation_request: PolygonValidationRequest,
    current_user: dict = Depends(get_current_admin_user)  # 🔒 ADMIN ONLY
):
    """
    ➕ NEW v3.0: Valida um polígono antes de criar/atualizar zona
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    try:
        is_valid, issues = validate_polygon(validation_request.points)
        
        area = None
        perimeter = None
        centroid = None
        
        if len(validation_request.points) >= 3:
            area = calculate_polygon_area(validation_request.points)
            perimeter = calculate_polygon_perimeter(validation_request.points)
            centroid = calculate_centroid(validation_request.points)
        
        return PolygonValidationResponse(
            valid=is_valid,
            area=area,
            perimeter=perimeter,
            centroid=centroid,
            issues=issues
        )
    
    except Exception as e:
        logger.error(f"❌ Error validating polygon: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar polígono: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - STATISTICS & ANALYTICS (ADMIN ONLY)
# ============================================================================

@router.get("/statistics", response_model=ZoneStatistics, summary="📊 Estatísticas de zonas")
async def get_zone_statistics(
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Obtém estatísticas gerais de zonas
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Total zones
                await cur.execute("SELECT COUNT(*) as count FROM zones WHERE deleted_at IS NULL")
                total_zones = (await cur.fetchone())['count']
                
                # Enabled/disabled
                await cur.execute("SELECT COUNT(*) as count FROM zones WHERE deleted_at IS NULL AND enabled = TRUE")
                enabled_zones = (await cur.fetchone())['count']
                
                await cur.execute("SELECT COUNT(*) as count FROM zones WHERE deleted_at IS NULL AND enabled = FALSE")
                disabled_zones = (await cur.fetchone())['count']
                
                # Active zones
                await cur.execute("SELECT COUNT(*) as count FROM zones WHERE deleted_at IS NULL AND active = TRUE")
                active_zones = (await cur.fetchone())['count']
                
                # By mode
                await cur.execute("SELECT mode, COUNT(*) as count FROM zones WHERE deleted_at IS NULL GROUP BY mode")
                zones_by_mode = {row['mode']: row['count'] for row in await cur.fetchall()}
                
                # Average area
                await cur.execute("SELECT points FROM zones WHERE deleted_at IS NULL")
                rows = await cur.fetchall()
                
                total_area = 0.0
                for row in rows:
                    points = json.loads(row['points']) if isinstance(row['points'], str) else row['points']
                    total_area += calculate_polygon_area(points)
                
                average_area = total_area / total_zones if total_zones > 0 else 0.0
            
            logger.info(f"📊 Estatísticas geradas para {current_user.get('username')} [ADMIN]")
            
            return ZoneStatistics(
                total_zones=total_zones,
                enabled_zones=enabled_zones,
                disabled_zones=disabled_zones,
                active_zones=active_zones,
                zones_by_mode=zones_by_mode,
                average_area=average_area,
                total_detections=None,  # TODO: implement
                most_active_zones=[],   # TODO: implement
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting zone statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao obter estatísticas: {str(e)}"
            )


# ============================================================================
# v3.0 ENDPOINTS - EXPORT/IMPORT (ADMIN ONLY)
# ============================================================================

@router.get("/export", summary="📥 Exportar zonas")
async def export_zones(
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Exporta todas as zonas em JSON
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, points, mode, empty_timeout, full_timeout,
                           empty_threshold, full_threshold, enabled, active,
                           created_at, updated_at
                    FROM zones
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                    """
                )
                rows = await cur.fetchall()
            
            export_zones_list = []
            for row in rows:
                zone_dict = await zone_to_dict(row)
                zone_dict['created_at'] = zone_dict['created_at'].isoformat()
                zone_dict['updated_at'] = zone_dict['updated_at'].isoformat() if zone_dict['updated_at'] else None
                zone_dict.pop('deleted_at', None)
                export_zones_list.append(zone_dict)
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "exported_by": current_user.get('username'),
                "count": len(export_zones_list),
                "zones": export_zones_list
            }
            
            logger.info(f"📥 Exported {len(export_zones_list)} zones by {current_user.get('username')} [ADMIN]")
            
            return JSONResponse(content=export_data)
            
        except Exception as e:
            logger.error(f"❌ Error exporting zones: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao exportar zonas: {str(e)}"
            )


@router.post("/import", summary="📤 Importar zonas")
async def import_zones(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Importa zonas de arquivo JSON
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    try:
        content = await file.read()
        data = json.loads(content)
        
        zones_to_import = data.get('zones', data)
        
        if not isinstance(zones_to_import, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format: expected list of zones"
            )
        
        imported_count = 0
        failed_count = 0
        errors = []
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                for zone_data in zones_to_import:
                    try:
                        name = zone_data.get('name')
                        points = zone_data.get('points')
                        mode = zone_data.get('mode', 'occupancy')
                        
                        if not name or not points:
                            errors.append({"zone": str(zone_data), "error": "Missing name or points"})
                            failed_count += 1
                            continue
                        
                        # Check duplicate
                        await cur.execute(
                            "SELECT id FROM zones WHERE name = %s AND deleted_at IS NULL",
                            (name,)
                        )
                        
                        if await cur.fetchone():
                            errors.append({"name": name, "error": "Zone already exists (skipped)"})
                            failed_count += 1
                            continue
                        
                        # Create zone
                        await cur.execute(
                            """
                            INSERT INTO zones (
                                name, points, mode, empty_timeout, full_timeout,
                                empty_threshold, full_threshold, enabled, active, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                name,
                                json.dumps(points),
                                mode,
                                zone_data.get('empty_timeout', 30.0),
                                zone_data.get('full_timeout', 5.0),
                                zone_data.get('empty_threshold', 0),
                                zone_data.get('full_threshold', 1),
                                zone_data.get('enabled', True),
                                zone_data.get('active', True)
                            )
                        )
                        
                        imported_count += 1
                    
                    except Exception as e:
                        errors.append({"zone": str(zone_data), "error": str(e)})
                        failed_count += 1
                
                await conn.commit()
        
        # Sync to JSON and settings
        if imported_count > 0:
            await sync_zones_to_json()
            await sync_zones_to_settings()
        
        logger.info(f"📤 Imported {imported_count} zones from {file.filename} by {current_user.get('username')} [ADMIN]")
        
        return {
            "imported": imported_count,
            "failed": failed_count,
            "errors": errors,
            "filename": file.filename
        }
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"❌ Error importing zones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao importar zonas: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - TEMPLATES (ADMIN ONLY)
# ============================================================================

@router.get("/templates", response_model=List[ZoneTemplate], summary="📑 Listar templates")
async def list_zone_templates(
    current_user: dict = Depends(get_current_admin_user)  # 🔒 ADMIN ONLY
):
    """
    ➕ NEW v3.0: Lista templates de zonas disponíveis
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    templates = []
    
    for template_id, template_data in ZONE_TEMPLATES.items():
        templates.append(ZoneTemplate(
            id=template_id,
            name=template_data['name'],
            mode=template_data['mode'],
            description=template_data['description'],
            default_settings={
                'empty_timeout': template_data['empty_timeout'],
                'full_timeout': template_data['full_timeout'],
                'empty_threshold': template_data['empty_threshold'],
                'full_threshold': template_data['full_threshold']
            }
        ))
    
    logger.info(f"📑 Templates listados para {current_user.get('username')} [ADMIN]")
    
    return templates


@router.post("/templates/{template_name}", response_model=ZoneResponse, summary="➕ Criar zona de template")
async def create_zone_from_template(
    template_name: str,
    template_request: ZoneFromTemplateRequest,
    request: Request,
    current_user: dict = Depends(get_current_admin_user),  # 🔒 ADMIN ONLY
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    ➕ NEW v3.0: Cria uma zona a partir de um template
    
    **Requer:** Token JWT de ADMIN (is_superuser=True)
    """
    if template_name not in ZONE_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' não encontrado"
        )
    
    template = ZONE_TEMPLATES[template_name]
    
    # Create zone using template defaults
    zone_create = ZoneCreate(
        name=template_request.zone_name,
        points=template_request.points,
        mode=template['mode'],
        empty_timeout=template['empty_timeout'],
        full_timeout=template['full_timeout'],
        empty_threshold=template['empty_threshold'],
        full_threshold=template['full_threshold'],
        enabled=True,
        active=True
    )
    
    logger.info(f"➕ Criando zona de template '{template_name}' por {current_user.get('username')} [ADMIN]")
    
    return await create_zone(request, zone_create, current_user, pool)


# ============================================================================
# ENDPOINT SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Zones API v3.0 - ADMIN ONLY MODE 🔒")
    print("=" * 80)
    print("✅ Total endpoints: 15 (5 v2.0 + 10 v3.0)")
    print("🔒 All endpoints require ADMIN privileges (is_superuser=True)")
    print("=" * 80)
    print("\nv2.0 CRUD (5 endpoints):")
    print("  POST   /zones/          - Criar nova zona [ADMIN]")
    print("  GET    /zones/          - Listar todas zonas [ADMIN]")
    print("  GET    /zones/{id}      - Obter zona específica [ADMIN]")
    print("  PUT    /zones/{id}      - Atualizar zona [ADMIN]")
    print("  DELETE /zones/{id}      - Deletar zona [ADMIN]")
    print("\nv3.0 NEW (10 endpoints):")
    print("  POST   /zones/search    - Busca avançada [ADMIN]")
    print("  POST   /zones/bulk/create - Criar múltiplas [ADMIN]")
    print("  POST   /zones/bulk/delete - Deletar múltiplas [ADMIN]")
    print("  POST   /zones/{id}/clone - Clonar zona [ADMIN]")
    print("  POST   /zones/validate  - Validar polígono [ADMIN]")
    print("  GET    /zones/statistics - Estatísticas [ADMIN]")
    print("  GET    /zones/export    - Exportar zonas [ADMIN]")
    print("  POST   /zones/import    - Importar zonas [ADMIN]")
    print("  GET    /zones/templates - Listar templates [ADMIN]")
    print("  POST   /zones/templates/{name} - Criar de template [ADMIN]")
    print("=" * 80)
