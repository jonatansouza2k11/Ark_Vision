"""
============================================================================
ZONES API - CRUD Endpoints (psycopg3 async)
============================================================================
Sistema de gerenciamento de zonas para detecção de objetos (YOLO).
Arquitetura híbrida: PostgreSQL (psycopg3) + JSON fallback.

Endpoints:
- POST   /zones/          → Criar nova zona
- GET    /zones/          → Listar todas as zonas ativas
- GET    /zones/{id}      → Obter zona específica
- PUT    /zones/{id}      → Atualizar zona existente
- DELETE /zones/{id}      → Deletar zona (soft delete)

Compatibilidade:
- psycopg3 AsyncConnectionPool
- JSON sync para compatibilidade com yolo.py
- Soft delete (não remove fisicamente)
- RAG-ready (future vector support)

✨ v2.1: Corrigido campo 'active' e validações
============================================================================
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from psycopg_pool import AsyncConnectionPool

from database import get_db_pool, sync_zones_to_settings
from models.zones import ZoneCreate, ZoneUpdate, ZoneResponse
from config import settings
from dependencies import get_current_user, limiter

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

router = APIRouter(prefix="/zones", tags=["zones"])
logger = logging.getLogger(__name__)

# Garante que diretório data/ existe
DATA_DIR = settings.BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============================================================================
# ENDPOINT: CREATE ZONE
# ============================================================================

@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def create_zone(
    request: Request,
    zone: ZoneCreate,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Cria uma nova zona de detecção.
    
    Args:
        zone: Dados da zona (nome, pontos, modo, etc.)
        pool: Connection pool psycopg3 (injetado)
    
    Returns:
        ZoneResponse: Zona criada com ID gerado
    
    Raises:
        HTTPException 409: Nome duplicado
        HTTPException 500: Erro no banco de dados
    """
    async with pool.connection() as conn:
        try:
            # Verifica nome duplicado
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
                
                # ✅ CORRIGIDO: INSERT com 'active'
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
                
                logger.info(
                    f"✅ Zona criada: {row['name']} (ID: {row['id']}) "
                    f"por {current_user.get('username')}"
                )
                
                # ✅ CORRIGIDO: zone_dict com 'active'
                zone_dict = {
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
                    'deleted_at': None
                }
            
            # Sincroniza com JSON (fallback)
            zones_file = DATA_DIR / "zones.json"
            try:
                # Carrega JSON existente
                if zones_file.exists():
                    with open(zones_file, 'r', encoding='utf-8') as f:
                        zones_data = json.load(f)
                else:
                    zones_data = []
                
                # Adiciona nova zona
                zone_dict_json = zone_dict.copy()
                zone_dict_json['created_at'] = zone_dict['created_at'].isoformat()
                zone_dict_json['updated_at'] = zone_dict['updated_at'].isoformat() if zone_dict['updated_at'] else None
                zones_data.append(zone_dict_json)
                
                # Salva JSON
                with open(zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones_data, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"✅ JSON atualizado: {zones_file}")
                
            except Exception as json_error:
                logger.warning(f"⚠️ Erro ao atualizar JSON: {json_error}")
            
            # Sincroniza com settings (yolo.py)
            await sync_zones_to_settings()
            
            return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao criar zona: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao criar zona: {str(e)}"
            )


# ============================================================================
# ENDPOINT: LIST ZONES
# ============================================================================

@router.get("/", response_model=List[ZoneResponse])
@limiter.limit("100/minute")
async def list_zones(
    request: Request,
    include_disabled: bool = False,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Lista todas as zonas ativas (não deletadas).
    
    Args:
        include_disabled: Se True, inclui zonas desabilitadas (enabled=False)
        pool: Connection pool psycopg3 (injetado)
    
    Returns:
        List[ZoneResponse]: Lista de zonas
    
    Raises:
        HTTPException 500: Erro no banco de dados
    """
    async with pool.connection() as conn:
        try:
            # ✅ CORRIGIDO: Query com 'active' e 'deleted_at'
            query = """
                SELECT id, name, points, mode, empty_timeout, full_timeout,
                       empty_threshold, full_threshold, enabled, active,
                       created_at, updated_at
                FROM zones
                WHERE deleted_at IS NULL
            """
            
            # Filtro de habilitação
            if not include_disabled:
                query += " AND enabled = TRUE"
            
            query += " ORDER BY created_at DESC"
            
            async with conn.cursor() as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
            
            logger.info(f"📋 Listando {len(rows)} zonas para {current_user.get('username')}")
            
            # ✅ CORRIGIDO: Converte rows com 'active'
            results = []
            for row in rows:
                zone_dict = {
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
                    'deleted_at': None
                }
                results.append(ZoneResponse(**zone_dict))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar zonas: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao listar zonas: {str(e)}"
            )


# ============================================================================
# ENDPOINT: GET ZONE BY ID
# ============================================================================

@router.get("/{zone_id}", response_model=ZoneResponse)
@limiter.limit("100/minute")
async def get_zone(
    request: Request,
    zone_id: int,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Obtém uma zona específica por ID.
    
    Args:
        zone_id: ID da zona
        pool: Connection pool psycopg3 (injetado)
    
    Returns:
        ZoneResponse: Dados da zona
    
    Raises:
        HTTPException 404: Zona não encontrada
        HTTPException 500: Erro no banco de dados
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # ✅ CORRIGIDO: SELECT com 'active'
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
                
                logger.info(f"🔍 Zona encontrada: {row['id']} - {row['name']}")
                
                # ✅ CORRIGIDO: zone_dict com 'active'
                zone_dict = {
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
                    'deleted_at': None
                }
                
                return ZoneResponse(**zone_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao buscar zona: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar zona: {str(e)}"
            )


# ============================================================================
# ENDPOINT: UPDATE ZONE
# ============================================================================

@router.put("/{zone_id}", response_model=ZoneResponse)
@limiter.limit("100/minute")
async def update_zone(
    request: Request,
    zone_id: int,
    zone_update: ZoneUpdate,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Atualiza uma zona existente.
    
    Args:
        zone_id: ID da zona
        zone_update: Campos a serem atualizados (todos opcionais)
        pool: Connection pool psycopg3 (injetado)
    
    Returns:
        ZoneResponse: Zona atualizada
    
    Raises:
        HTTPException 404: Zona não encontrada
        HTTPException 409: Nome duplicado
        HTTPException 500: Erro no banco de dados
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Verifica se zona existe
                await cur.execute(
                    "SELECT id FROM zones WHERE id = %s AND deleted_at IS NULL",
                    (zone_id,)
                )
                
                if not await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                # Verifica nome duplicado (se nome foi alterado)
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
                
                # Monta query dinâmica (apenas campos fornecidos)
                update_fields = []
                update_values = []
                
                if zone_update.name is not None:
                    update_fields.append("name = %s")
                    update_values.append(zone_update.name)
                
                if zone_update.points is not None:
                    update_fields.append("points = %s")
                    update_values.append(json.dumps(zone_update.points))
                
                if zone_update.mode is not None:
                    update_fields.append("mode = %s")
                    update_values.append(zone_update.mode)
                
                if zone_update.empty_timeout is not None:
                    update_fields.append("empty_timeout = %s")
                    update_values.append(zone_update.empty_timeout)
                
                if zone_update.full_timeout is not None:
                    update_fields.append("full_timeout = %s")
                    update_values.append(zone_update.full_timeout)
                
                if zone_update.empty_threshold is not None:
                    update_fields.append("empty_threshold = %s")
                    update_values.append(zone_update.empty_threshold)
                
                if zone_update.full_threshold is not None:
                    update_fields.append("full_threshold = %s")
                    update_values.append(zone_update.full_threshold)
                
                if zone_update.enabled is not None:
                    update_fields.append("enabled = %s")
                    update_values.append(zone_update.enabled)
                
                # ✅ ADICIONAR: Suporte para atualizar 'active'
                if zone_update.active is not None:
                    update_fields.append("active = %s")
                    update_values.append(zone_update.active)
                
                if not update_fields:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nenhum campo para atualizar"
                    )
                
                # Adiciona updated_at e zone_id
                update_fields.append("updated_at = NOW()")
                update_values.append(zone_id)
                
                # ✅ CORRIGIDO: RETURNING com 'active'
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
                
                logger.info(
                    f"✅ Zona atualizada: {row['name']} (ID: {row['id']}) "
                    f"por {current_user.get('username')}"
                )
                
                # ✅ CORRIGIDO: zone_dict com 'active'
                zone_dict = {
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
                    'deleted_at': None
                }
            
            # Atualiza JSON
            zones_file = DATA_DIR / "zones.json"
            try:
                with open(zones_file, 'r', encoding='utf-8') as f:
                    zones_data = json.load(f)
                
                # Atualiza zona no JSON
                for i, z in enumerate(zones_data):
                    if z['id'] == zone_id:
                        zone_dict_json = zone_dict.copy()
                        zone_dict_json['created_at'] = zone_dict['created_at'].isoformat()
                        zone_dict_json['updated_at'] = zone_dict['updated_at'].isoformat() if zone_dict['updated_at'] else None
                        zones_data[i] = zone_dict_json
                        break
                
                with open(zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones_data, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"✅ JSON atualizado: zona {zone_id}")
                
            except Exception as json_error:
                logger.warning(f"⚠️ Erro ao atualizar JSON: {json_error}")
            
            # Sincroniza com settings
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


# ============================================================================
# ENDPOINT: DELETE ZONE (SOFT DELETE)
# ============================================================================

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("100/minute")
async def delete_zone(
    request: Request,
    zone_id: int,
    current_user: dict = Depends(get_current_user),
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Deleta uma zona (soft delete).
    
    Args:
        zone_id: ID da zona
        pool: Connection pool psycopg3 (injetado)
    
    Returns:
        None (204 No Content)
    
    Raises:
        HTTPException 404: Zona não encontrada
        HTTPException 500: Erro no banco de dados
    """
    async with pool.connection() as conn:
        try:
            async with conn.cursor() as cur:
                # Verifica se zona existe
                await cur.execute(
                    "SELECT id FROM zones WHERE id = %s AND deleted_at IS NULL",
                    (zone_id,)
                )
                
                if not await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Zona {zone_id} não encontrada"
                    )
                
                # ✅ CORRIGIDO: Soft delete usando deleted_at
                await cur.execute(
                    """
                    UPDATE zones
                    SET deleted_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (zone_id,)
                )
                
                await conn.commit()
                logger.info(
                    f"🗑️ Zona deletada (soft delete): {zone_id} "
                    f"por {current_user.get('username')}"
                )
            
            # Atualiza JSON
            zones_file = DATA_DIR / "zones.json"
            try:
                with open(zones_file, 'r', encoding='utf-8') as f:
                    zones_data = json.load(f)
                
                # Remove zona do JSON
                zones_data = [z for z in zones_data if z['id'] != zone_id]
                
                with open(zones_file, 'w', encoding='utf-8') as f:
                    json.dump(zones_data, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"✅ JSON atualizado: zona {zone_id} removida")
                
            except FileNotFoundError:
                logger.warning(f"⚠️ Arquivo JSON não encontrado: {zones_file}")
            except Exception as json_error:
                logger.warning(f"⚠️ Erro ao atualizar JSON: {json_error}")
            
            # Sincroniza com settings (yolo.py)
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
# TESTE: Verifica se módulo pode ser executado diretamente
# ============================================================================
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Adiciona diretório raiz ao PYTHONPATH
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))
    
    print("=" * 70)
    print("📋 TESTE: Zone API Endpoints (psycopg3 async) v2.1")
    print("=" * 70)
    print(f"\n📂 Diretório raiz: {root_dir}")
    print("\n✅ Router configurado com sucesso!")
    print(f"   Prefix: {router.prefix}")
    print(f"   Tags: {router.tags}")
    print(f"   Database: psycopg3 AsyncConnectionPool")
    print(f"\n📍 Endpoints disponíveis:")
    for route in router.routes:
        methods = ', '.join(route.methods)
        print(f"   [{methods:8}] {route.path}")
    print("\n" + "=" * 70)
    print("✅ Módulo validado! Pronto para import no main.py")
    print("=" * 70)
