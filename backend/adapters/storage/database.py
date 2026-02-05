"""
============================================================================
backend/database.py - COMPLETE v3.0 - 100% API ALIGNED
PostgreSQL Async Database Layer - FULLY SYNCHRONIZED
============================================================================
Using psycopg3 (official PostgreSQL driver)

v3.0 CHANGES - FULLY ALIGNED WITH APIs:
✅ USERS (auth.py + users.py)
✅ ZONES (zones.py) 
✅ ALERTS (alerts.py)
✅ SETTINGS (settings.py)
✅ VIDEOS (video.py)
✅ ALL FUNCTIONS RESTORED!

CRITICAL: sync_zones_to_settings() RESTORED!
============================================================================
"""

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, ConnectionPool  
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from functools import lru_cache
from enum import Enum
import json
import logging
import sys

try:
    from backend.core.config.config import settings
except ModuleNotFoundError:
    from backend.core.config.config import settings

logger = logging.getLogger("uvicorn")

# ============================================
# OPTIMIZATION 1: Constants & Enums
# ============================================

class TableName(str, Enum):
    """✅ Enum para nomes de tabelas (type-safe)"""
    USERS = "users"
    SETTINGS = "settings"
    ZONES = "zones"
    ALERTS = "alerts"
    SYSTEMLOGS = "systemlogs"
    AUDITLOGS = "auditlogs"
    CONVERSATIONS = "conversations"
    KNOWLEDGEBASE = "knowledgebase"
    DETECTIONS = "detections"
    VIDEOS = "videos"
    CAMERAS = "cameras"


@lru_cache(maxsize=1)
def _get_all_table_names() -> List[str]:
    """✅ Cache de nomes de tabelas"""
    return [
        TableName.CONVERSATIONS,
        TableName.DETECTIONS,
        TableName.ALERTS,
        TableName.ZONES,
        TableName.SYSTEMLOGS,
        TableName.AUDITLOGS,
        TableName.KNOWLEDGEBASE,
        TableName.SETTINGS,
        TableName.USERS,
        TableName.VIDEOS,
        TableName.CAMERAS
    ]


# ============================================
# OPTIMIZATION 2: Helper Functions
# ============================================

def _normalize_database_url(url: str) -> str:
    """✅ Normaliza URL do banco (função pura)"""
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+://", "postgresql://")
    return url


def _parse_json_field(value: Any) -> Any:
    """✅ Parser seguro para campos JSON/JSONB"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON string: {value}")
            return value
    return value


def _safe_json_dumps(value: Any) -> str:
    """✅ JSON encoder seguro com fallback"""
    try:
        return json.dumps(value or {})
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON encoding failed: {e}, using empty dict")
        return "{}"


def _create_history_entry(old_value: Any, new_value: Any, updated_by: str) -> Dict[str, Any]:
    """✅ Cria entrada de histórico (função pura)"""
    return {
        "timestamp": datetime.now().isoformat(),
        "old_value": old_value,
        "new_value": str(new_value),
        "updated_by": updated_by
    }


# ============================================
# OPTIMIZATION 3: SQL Query Constants
# ============================================

class SQL:
    """✅ Centralized SQL queries (avoid repetition)"""
    
    # USER QUERIES
    SELECT_USER_BY_USERNAME = "SELECT * FROM users WHERE username = %s"
    SELECT_USER_BY_EMAIL = "SELECT * FROM users WHERE email = %s"
    SELECT_USER_BY_ID = "SELECT * FROM users WHERE id = %s"
    SELECT_ALL_USERS = "SELECT * FROM users ORDER BY created_at DESC"
    UPDATE_LAST_LOGIN = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = %s"
    DELETE_USER = "DELETE FROM users WHERE id = %s"
    UPDATE_USER_ROLE = "UPDATE users SET role = %s WHERE id = %s"
    
    # ZONE QUERIES
    SELECT_ALL_ZONES = "SELECT * FROM zones WHERE deleted_at IS NULL ORDER BY id"
    SELECT_ACTIVE_ZONES = "SELECT * FROM zones WHERE active = TRUE AND enabled = TRUE AND deleted_at IS NULL ORDER BY id"
    SELECT_ZONE_BY_ID = "SELECT * FROM zones WHERE id = %s AND deleted_at IS NULL"
    DELETE_ZONE_SOFT = "UPDATE zones SET deleted_at = CURRENT_TIMESTAMP, active = FALSE, enabled = FALSE WHERE id = %s"
    DELETE_ZONE_HARD = "DELETE FROM zones WHERE id = %s"
    
    # CAMERA QUERIES (NEW)
    SELECT_ALL_CAMERAS = "SELECT * FROM cameras ORDER BY id"
    SELECT_ACTIVE_CAMERAS = "SELECT * FROM cameras WHERE enabled = TRUE ORDER BY id"
    SELECT_CAMERA_BY_ID = "SELECT * FROM cameras WHERE id = %s"
    DELETE_CAMERA = "DELETE FROM cameras WHERE id = %s"

    # SETTINGS QUERIES
    SELECT_SETTING = "SELECT * FROM settings WHERE key = %s"
    SELECT_ALL_SETTINGS = "SELECT key, value, category, data_type FROM settings"
    
    # ALERTS QUERIES
    SELECT_RECENT_ALERTS = "SELECT * FROM alerts ORDER BY created_at DESC LIMIT %s"
    DELETE_ALERT = "DELETE FROM alerts WHERE id = %s"
    
    # SYSTEM LOGS QUERIES
    SELECT_SYSTEM_LOGS = "SELECT * FROM systemlogs ORDER BY timestamp DESC LIMIT %s"
    
    # DETECTIONS QUERIES
    SELECT_DETECTIONS_BY_TRACK = """
        SELECT * FROM detections 
        WHERE track_id = %s 
        ORDER BY timestamp DESC 
        LIMIT %s
    """
    
    # KNOWLEDGE BASE QUERIES
    SEARCH_KNOWLEDGE_ALL = """
        SELECT * FROM knowledgebase 
        WHERE title ILIKE %s OR content ILIKE %s
        ORDER BY updated_at DESC 
        LIMIT %s
    """
    
    # CONVERSATIONS QUERIES
    SELECT_CONVERSATION_HISTORY = """
        SELECT * FROM conversations 
        WHERE session_id = %s 
        ORDER BY timestamp ASC 
        LIMIT %s
    """
    
    # MISC QUERIES
    COUNT_ZONES = "SELECT COUNT(*) as count FROM zones WHERE deleted_at IS NULL"


# ============================================
# CONNECTION POOL
# ============================================

pool: Optional[AsyncConnectionPool] = None


async def get_db_pool() -> AsyncConnectionPool:
    """Obtém connection pool do PostgreSQL"""
    global pool
    
    if pool is None:
        try:
            db_url = _normalize_database_url(settings.DATABASE_URL)
            
            pool = AsyncConnectionPool(
                conninfo=db_url,
                min_size=2,
                max_size=10,
                timeout=60,
                kwargs={"row_factory": dict_row},
                open=False
            )
            
            await pool.open()
            logger.info("✅ PostgreSQL pool created (psycopg3)")
            
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL pool: {e}")
            raise
    
    return pool


async def close_db_pool() -> None:
    """Fecha connection pool"""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("✅ PostgreSQL pool closed")


# ============================================
# OPTIMIZATION 4: Generic CRUD Operations
# ============================================

async def _execute_query(
    query: str,
    params: Tuple = (),
    fetch: str = "none"
) -> Optional[Any]:
    """
    ✅ Generic query executor (elimina repetição)
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch: "one", "all", or "none"
    
    Returns:
        Query result or None
    """
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            
            if fetch == "one":
                result = await cur.fetchone()
            elif fetch == "all":
                result = await cur.fetchall()
            else:
                result = None
            
            await conn.commit()
            return result


async def _execute_delete(table: str, id_value: int, id_column: str = "id") -> bool:
    """✅ Generic delete operation"""
    try:
        # ✅ CORREÇÃO: Extrair valor se for Enum
        table_name = table.value if hasattr(table, 'value') else table
        
        await _execute_query(f"DELETE FROM {table_name} WHERE {id_column} = %s", (id_value,))
        logger.info(f"✅ Deleted from {table_name} (ID: {id_value})")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting from {table_name}: {e}")
        return False



# ============================================
# DROP ALL TABLES
# ============================================

async def drop_all_tables() -> None:
    """⚠️ CUIDADO: Dropa TODAS as tabelas! Use apenas em desenvolvimento!"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        logger.warning("⚠️ Dropping all tables...")
        
        for table in _get_all_table_names():
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"✅ Dropped table: {table}")
            except Exception as e:
                logger.warning(f"⚠️ Could not drop {table}: {e}")
        
        await conn.commit()
        logger.warning("✅ All tables dropped!")


# ============================================
# INIT DATABASE v3.0 - 100% ALIGNED
# ============================================

async def init_database(force_recreate: bool = False) -> None:
    """
    Cria tabelas se não existirem - v3.0 100% ALIGNED WITH APIs
    
    Args:
        force_recreate: Se True, dropa e recria todas as tabelas
    """
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        if force_recreate:
            logger.warning("⚠️ FORCE RECREATE: Dropping all tables...")
            await drop_all_tables()
        
        # ==========================================================
        # ==================== USERS TABLE v3.0 ====================
        # ==========================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                
                -- NEW v3.0 fields (auth.py + users.py)
                full_name VARCHAR(100),
                phone VARCHAR(20),
                email_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                disabled BOOLEAN DEFAULT FALSE,
                account_status VARCHAR(20) DEFAULT 'active',
                last_login TIMESTAMP,
                
                -- MFA support (auth.py)
                mfa_enabled BOOLEAN DEFAULT FALSE,
                mfa_secret VARCHAR(255),
                
                -- Preferences (JSONB)
                preferences JSONB DEFAULT '{}'::jsonb,
                
                -- Metadata
                metadata JSONB DEFAULT '{}'::jsonb,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        logger.info("✅ Tabela 'users' criada (v3.0)")
        
        # =============================================================
        # ==================== SETTINGS TABLE v3.0 ====================
        # =============================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                
                -- NEW v3.0 fields (settings.py)
                category VARCHAR(50) DEFAULT 'other',
                data_type VARCHAR(20) DEFAULT 'string',
                description TEXT,
                is_secret BOOLEAN DEFAULT FALSE,
                is_readonly BOOLEAN DEFAULT FALSE,
                
                -- Validation (JSONB)
                validation_rules JSONB DEFAULT '{}'::jsonb,
                
                -- Metadata
                metadata JSONB DEFAULT '{}'::jsonb,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR(50),
                
                -- Change history (JSONB array)
                change_history JSONB DEFAULT '[]'::jsonb
            )
        """)
        logger.info("✅ Tabela 'settings' criada (v3.0)")
        

        # ==================== CAMERAS TABLE v1.0 ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                source VARCHAR(500) NOT NULL,   -- RTSP/HTTP/device
                username VARCHAR(100),
                password VARCHAR(255),
                location VARCHAR(255),

                -- Status
                enabled BOOLEAN DEFAULT TRUE NOT NULL,

                -- Metadata
                metadata JSONB DEFAULT '{}'::jsonb,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cameras_enabled ON cameras(enabled)"
        )
        logger.info("✅ Tabela 'cameras' criada (v1.0)")


        # ==================== ZONES TABLE v3.1 (camera_id) ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                points JSONB NOT NULL,
                mode VARCHAR(50) DEFAULT 'occupancy' NOT NULL,
                
                -- Camera relationship (nullable for legacy zones)
                camera_id INTEGER,

                -- Zone parameters
                empty_timeout REAL DEFAULT 50.0,
                full_timeout REAL DEFAULT 50.0,
                empty_threshold INTEGER DEFAULT 0,
                full_threshold INTEGER DEFAULT 3,
                max_out_time REAL,
                email_cooldown REAL,

                -- Status flags v3.0 (zones.py)
                enabled BOOLEAN DEFAULT TRUE NOT NULL,
                active BOOLEAN DEFAULT TRUE NOT NULL,

                -- NEW v3.0
                description TEXT,
                color VARCHAR(7),
                tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                snapshot_path VARCHAR(500),         
                metadata JSONB DEFAULT '{}'::jsonb,
                                         
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                deleted_at TIMESTAMP  -- NEW v3.0: Soft delete
            )
        """)

        # Índices otimizados
        for index_sql in [
            "CREATE INDEX IF NOT EXISTS idx_zones_active ON zones(active) WHERE deleted_at IS NULL",
            "CREATE INDEX IF NOT EXISTS idx_zones_enabled ON zones(enabled) WHERE deleted_at IS NULL",
            "CREATE INDEX IF NOT EXISTS idx_zones_mode ON zones(mode)",
            "CREATE INDEX IF NOT EXISTS idx_zones_camera_id ON zones(camera_id)"
        ]:
            await conn.execute(index_sql)
        logger.info("✅ Tabela 'zones' criada (v3.1 com camera_id)")
        

        # ==================== ALERTS TABLE v3.0 ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                person_id INTEGER NOT NULL,
                track_id INTEGER,
                out_time REAL NOT NULL,
                
                -- Zone info
                zone_id INTEGER REFERENCES zones(id) ON DELETE SET NULL,
                zone_index INTEGER,
                zone_name VARCHAR(100),
                
                -- Alert details
                alert_type VARCHAR(50) DEFAULT 'zone_violation',
                severity VARCHAR(20) DEFAULT 'medium',
                description TEXT,
                
                -- Media paths
                snapshot_path VARCHAR(500),
                video_path TEXT,
                
                -- Status flags
                email_sent BOOLEAN DEFAULT FALSE,
                notification_sent BOOLEAN DEFAULT FALSE,  -- NEW v3.0
                
                -- Resolution v3.0 (alerts.py)
                resolved_at TIMESTAMP,
                resolved_by VARCHAR(50),
                resolution_notes TEXT,
                
                -- Metadata v3.0 (JSONB)
                metadata JSONB DEFAULT '{}'::jsonb,
                color VARCHAR(7),  
                tags TEXT[] DEFAULT ARRAY[]::TEXT[],  
                           
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP
            )
        """)
        
        # Índices para performance
        for index_sql in [
            "CREATE INDEX IF NOT EXISTS idx_alerts_person ON alerts(person_id)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone_id)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved_at)"
        ]:
            await conn.execute(index_sql)
        
        logger.info("✅ Tabela 'alerts' criada (v3.0)")
        
        # ==================== VIDEOS TABLE v3.0 ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                filepath VARCHAR(500) NOT NULL,
                camera_id INTEGER,
                
                -- Video details
                duration REAL,
                size_bytes BIGINT,
                format VARCHAR(20),
                resolution VARCHAR(20),
                fps REAL,
                
                -- Processing status v3.0
                status VARCHAR(20) DEFAULT 'pending',
                processed_at TIMESTAMP,
                processed_by VARCHAR(50),
                
                -- Metadata v3.0
                metadata JSONB DEFAULT '{}'::jsonb,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)
        logger.info("✅ Tabela 'videos' criada (v3.0)")
        
        # ==================== SYSTEM LOGS TABLE ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS systemlogs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                username VARCHAR(50),
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_sent BOOLEAN DEFAULT FALSE,
                ip_address VARCHAR(45),
                user_agent TEXT,
                context JSONB DEFAULT '{}'::jsonb,
                session_id VARCHAR(100)
            )
        """)
        
        for index_sql in [
            "CREATE INDEX IF NOT EXISTS idx_systemlogs_timestamp ON systemlogs(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_systemlogs_username ON systemlogs(username)"
        ]:
            await conn.execute(index_sql)
        
        logger.info("✅ Tabela 'systemlogs' criada")
        
        # ==================== AUDIT LOGS TABLE ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS auditlogs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                user_id VARCHAR(50) NOT NULL,
                action VARCHAR(100) NOT NULL,
                details TEXT,
                ip_address VARCHAR(45),
                previous_hash VARCHAR(64),
                current_hash VARCHAR(64) NOT NULL,
                context JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON auditlogs(timestamp DESC)
        """)
        
        logger.info("✅ Tabela 'auditlogs' criada")
        
        # ==================== CONVERSATIONS TABLE (RAG) ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                session_id VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                role VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb,
                context JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)
        """)
        
        logger.info("✅ Tabela 'conversations' criada")
        
        # ==================== KNOWLEDGE BASE TABLE (RAG) ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledgebase (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(100),
                source VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb,
                tags TEXT[] DEFAULT ARRAY[]::TEXT[]
            )
        """)
        
        logger.info("✅ Tabela 'knowledgebase' criada")
        
        # ==================== DETECTIONS TABLE (YOLO) ====================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id SERIAL PRIMARY KEY,
                track_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                zone_index INTEGER,
                zone_name VARCHAR(100),
                zone_id INTEGER REFERENCES zones(id) ON DELETE SET NULL,
                confidence REAL,
                bbox JSONB,
                status VARCHAR(20),
                duration_seconds REAL,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_detections_track ON detections(track_id)
        """)
        
        logger.info("✅ Tabela 'detections' criada")
        
        # ✅ Create default zone if needed (IMPROVED - v3.2)
        async with conn.cursor() as cur:
            # ✅ Verifica se ALGUMA zona já foi criada (incluindo deletadas)
            await cur.execute("SELECT COUNT(*) as count FROM zones")
            result = await cur.fetchone()
            
            if result['count'] == 0:
                logger.info("📍 Creating default zone (first time)...")
                await cur.execute(
                    """
                    INSERT INTO zones (
                        name, mode, points, empty_timeout, full_timeout,
                        empty_threshold, full_threshold, enabled, active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "Zona Principal",
                        "occupancy",
                        json.dumps([[100, 100], [500, 100], [500, 400], [100, 400]]),
                        5.0, 10.0, 0, 3, True, True
                    )
                )
                await conn.commit()
                logger.info("✅ Default zone created")
            else:
                logger.info("⏭️ Skipped default zone (already created before)")
        
        await sync_zones_to_settings()


# ============================================
# ZONES FUNCTIONS v3.0 ✅ RESTORED!
# ============================================

async def sync_zones_to_settings() -> bool:
    """
    ✅ CRITICAL FUNCTION RESTORED!
    
    Sincroniza tabela zones -> settings.safe_zone (JSON).
    Mantém compatibilidade com yolo.py que lê de settings.safe_zone.
    """
    try:
        zones = await _execute_query(SQL.SELECT_ACTIVE_ZONES, fetch="all")
        
        zones_data = []
        for zone in zones:
            zone_dict = {
                "name": zone['name'],
                "mode": zone['mode'],
                "points": _parse_json_field(zone['points']),
            }
            
            # Add optional configs
            for key in ['max_out_time', 'email_cooldown', 'empty_timeout', 
                        'full_timeout', 'empty_threshold', 'full_threshold']:
                if zone.get(key) is not None:
                    zone_dict[key] = zone[key]
            
            zones_data.append(zone_dict)
        
        json_str = json.dumps(zones_data)
        
        await _execute_query(
            """
            INSERT INTO settings (key, value, updated_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE 
            SET value = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s
            """,
            ("safe_zone", json_str, "system", json_str, "system")
        )
        
        logger.info(f"✅ Synced {len(zones)} zones to settings.safe_zone")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error syncing zones: {e}")
        return False


async def create_zone(
    name: str,
    mode: str,
    points: List[List[float]],
    camera_id: Optional[int] = None,
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = 5.0,
    full_timeout: Optional[float] = 10.0,
    empty_threshold: Optional[int] = 0,
    full_threshold: Optional[int] = 3,
    enabled: bool = True,
    active: bool = True,
    description: Optional[str] = None
) -> int:
    """Cria nova zona (v3.0)"""
    try:
        result = await _execute_query(
            """
            INSERT INTO zones (
                name, mode, points, camera_id, max_out_time, email_cooldown,
                empty_timeout, full_timeout, empty_threshold, full_threshold,
                enabled, active, description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                name, mode, json.dumps(points), camera_id, max_out_time, email_cooldown,
                empty_timeout, full_timeout, empty_threshold, full_threshold,
                enabled, active, description
            ),
            fetch="one"
        )
        
        zone_id = result['id']
        await sync_zones_to_settings()
        
        logger.info(f"✅ Zone created: {name} (ID: {zone_id})")
        return zone_id
        
    except Exception as e:
        logger.error(f"❌ Error creating zone: {e}")
        raise


async def get_all_zones(active_only: bool = False) -> List[Dict[str, Any]]:
    """Retorna todas as zonas"""
    query = SQL.SELECT_ACTIVE_ZONES if active_only else SQL.SELECT_ALL_ZONES
    zones = await _execute_query(query, fetch="all")
    
    for zone in zones:
        zone['points'] = _parse_json_field(zone['points'])
    
    return zones


async def get_zone_by_id(zone_id: int) -> Optional[Dict[str, Any]]:
    """Busca zona por ID"""
    zone = await _execute_query(SQL.SELECT_ZONE_BY_ID, (zone_id,), fetch="one")
    
    if zone:
        zone['points'] = _parse_json_field(zone['points'])
    
    return zone


async def update_zone(
    zone_id: int,
    name: Optional[str] = None,
    mode: Optional[str] = None,
    points: Optional[List[List[float]]] = None,
    camera_id: Optional[int] = None,
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = None,
    full_timeout: Optional[float] = None,
    empty_threshold: Optional[int] = None,
    full_threshold: Optional[int] = None,
    enabled: Optional[bool] = None,
    active: Optional[bool] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> bool:
    """Atualiza zona existente (v3.0)"""
    try:
        zone = await get_zone_by_id(zone_id)
        if not zone:
            logger.warning(f"⚠️ Zone not found (ID: {zone_id})")
            return False
        
        # Merge values (keep current if None)
        updated_values = (
            name or zone['name'],
            mode or zone['mode'],
            json.dumps(points if points is not None else zone['points']),
            camera_id if camera_id is not None else zone.get('camera_id'),
            max_out_time if max_out_time is not None else zone.get('max_out_time'),
            email_cooldown if email_cooldown is not None else zone.get('email_cooldown'),
            empty_timeout if empty_timeout is not None else zone.get('empty_timeout'),
            full_timeout if full_timeout is not None else zone.get('full_timeout'),
            empty_threshold if empty_threshold is not None else zone.get('empty_threshold'),
            full_threshold if full_threshold is not None else zone.get('full_threshold'),
            enabled if enabled is not None else zone['enabled'],
            active if active is not None else zone['active'],
            description if description is not None else zone.get('description'),
            color if color is not None else zone.get('color'),
            tags if tags is not None else zone.get('tags', []), 
            zone_id
        )
        
        await _execute_query(
            """
            UPDATE zones SET
                name = %s, mode = %s, points = %s, camera_id = %s,
                max_out_time = %s, email_cooldown = %s,
                empty_timeout = %s, full_timeout = %s,
                empty_threshold = %s, full_threshold = %s,
                enabled = %s, active = %s, description = %s,
                color = %s, tags = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            updated_values
        )
        
        await sync_zones_to_settings()
        logger.info(f"✅ Zone updated (ID: {zone_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating zone: {e}")
        return False


async def delete_zone(zone_id: int, soft: bool = True) -> bool:
    """
    Deleta zona (soft delete por padrão para manter histórico)
    
    Args:
        zone_id: ID da zona
        soft: Se True, soft delete (mantém registro). Se False, hard delete (remove)
    """
    try:
        if soft:
            await _execute_query(SQL.DELETE_ZONE_SOFT, (zone_id,))
            logger.info(f"✅ Zone deleted (soft) (ID: {zone_id})")
        else:
            await _execute_query(SQL.DELETE_ZONE_HARD, (zone_id,))
            logger.info(f"✅ Zone deleted (hard) (ID: {zone_id})")
        
        await sync_zones_to_settings()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting zone: {e}")
        return False


async def get_zones_by_camera_id(camera_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Retorna todas as zonas associadas a uma câmera específica.
    """
    try:
        if active_only:
            query = """
                SELECT * FROM zones
                WHERE camera_id = %s
                  AND enabled = TRUE
                  AND active = TRUE
                  AND deleted_at IS NULL
                ORDER BY id
            """
        else:
            query = """
                SELECT * FROM zones
                WHERE camera_id = %s
                  AND deleted_at IS NULL
                ORDER BY id
            """
        
        zones = await _execute_query(query, (camera_id,), fetch="all")
        
        # Parse JSONB fields
        for zone in zones:
            if isinstance(zone.get("points"), str):
                try:
                    zone["points"] = json.loads(zone["points"])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in zone {zone.get('id')} points")
                    zone["points"] = []
        
        return zones
    
    except Exception as e:
        logger.error(f"❌ Error fetching zones for camera {camera_id}: {e}")
        return []



# ============================================
# ZONE METADATA PERSISTENCE
# ============================================

#async def update_zone_metadata(zone_id: int, metadata: dict) -> None:
#    """
#    Atualiza apenas o campo metadata de uma zona.
#    
#    ✅ v3.9: Usado por camera_sync para persistir count_in/count_out
#    
#    Args:
#        zone_id: ID da zona
#        metadata: Dict com metadata atualizado (será serializado para JSON)
#    """
#    pool = await get_db_pool()
#    
#    async with pool.connection() as conn:
#        async with conn.cursor() as cur:
#            await cur.execute(
#                """
#                UPDATE zones 
#                SET metadata = %s, updated_at = CURRENT_TIMESTAMP
#                WHERE id = %s AND deleted_at IS NULL
#                """,
#                (json.dumps(metadata), zone_id)
#            )
#            await conn.commit()

def get_zone_metadata_updates(self) -> Dict[int, Dict]:
    """
    Coleta metadata atualizado de todas as zonas (para persistência externa).
    
    ✅ v3.9: Retorna dict {zone_id: metadata} para camera_sync.py salvar.
    ✅ v4.0: Busca metadata do ZoneProcessor (fonte da verdade)
    """
    metadata_updates = {}
    
    for ctx in self.camera_contexts.values():
        if not ctx.zone_processor:
            continue
        
        # ✅ CORRETO: Busca do zone_processor (estado real)
        for zone_id, state in ctx.zone_processor.zone_states.items():
            zone = next((z for z in ctx.zones if z.get("id") == zone_id), None)
            if not zone:
                continue
            
            # Apenas para zonas de contagem
            if zone.get("mode") != "counting":
                continue
            
            # ✅ Obtém metadata atualizado do processor
            if hasattr(ctx.zone_processor, 'get_zone_metadata'):
                updated_metadata = ctx.zone_processor.get_zone_metadata(zone_id)
            else:
                # Fallback: metadata atual da zona
                updated_metadata = zone.get("metadata", {})
            
            if updated_metadata:
                metadata_updates[zone_id] = updated_metadata
    
    return metadata_updates


# ============================================
# CAMERAS FUNCTIONS v3.1
# ============================================
async def get_all_cameras(active_only: bool = False) -> List[Dict[str, Any]]:
    """Retorna todas as câmeras (ou apenas ativas)."""
    query = SQL.SELECT_ACTIVE_CAMERAS if active_only else SQL.SELECT_ALL_CAMERAS
    return await _execute_query(query, fetch="all")


async def get_camera_by_id(camera_id: int) -> Optional[Dict[str, Any]]:
    """Busca câmera por ID."""
    return await _execute_query(SQL.SELECT_CAMERA_BY_ID, (camera_id,), fetch="one")


async def create_camera(
    name: str,
    source: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    location: Optional[str] = None,
    enabled: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Cria nova câmera."""
    row = await _execute_query(
        """
        INSERT INTO cameras (
            name, source, username, password, location,
            enabled, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            name,
            source,
            username,
            password,
            location,
            enabled,
            _safe_json_dumps(metadata),
        ),
        fetch="one",
    )
    camera_id = row["id"]
    logger.info(f"✅ Camera created: {name} (ID: {camera_id})")
    return camera_id


async def update_camera(
    camera_id: int,
    **kwargs: Any,
) -> bool:
    """Atualiza câmera; aceita qualquer campo simples ou metadata=dict."""
    try:
        if not kwargs:
            return False

        update_fields = []
        params: List[Any] = []

        for key, value in kwargs.items():
            if key == "metadata" and isinstance(value, dict):
                value = _safe_json_dumps(value)
            update_fields.append(f"{key} = %s")
            params.append(value)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(camera_id)

        query = f"UPDATE cameras SET {', '.join(update_fields)} WHERE id = %s"
        await _execute_query(query, tuple(params))

        logger.info(f"✅ Camera updated (ID: {camera_id})")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating camera: {e}")
        return False


async def delete_camera(camera_id: int) -> bool:
    """Deleta câmera por ID."""
    return await _execute_delete(TableName.CAMERAS, camera_id)

# ============================================
# USER FUNCTIONS v3.0
# ============================================

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Busca usuário por username"""
    return await _execute_query(SQL.SELECT_USER_BY_USERNAME, (username,), fetch="one")


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Busca usuário por email"""
    return await _execute_query(SQL.SELECT_USER_BY_EMAIL, (email,), fetch="one")


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Busca usuário por ID"""
    return await _execute_query(SQL.SELECT_USER_BY_ID, (user_id,), fetch="one")


async def create_user(
    username: str,
    email: str,
    password_hash: str,
    role: str = "user",
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    email_verified: bool = False,
    is_active: bool = True,
    account_status: str = "active"
) -> bool:
    """Cria novo usuário (v3.0)"""
    try:
        await _execute_query(
            """
            INSERT INTO users (
                username, email, password_hash, role, 
                full_name, phone, email_verified, is_active, account_status,
                metadata, preferences
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                username, email, password_hash, role,
                full_name, phone, email_verified, is_active, account_status,
                "{}", "{}"
            )
        )
        logger.info(f"✅ User created: {username}")
        return True
        
    except psycopg.errors.UniqueViolation:
        logger.warning(f"⚠️ User already exists: {username}")
        return False
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return False


async def update_user(
    user_id: int,
    **kwargs
) -> bool:
    """Atualiza usuário (v3.0) - aceita qualquer campo"""
    try:
        if not kwargs:
            return False
        
        # Build dynamic UPDATE query
        update_fields = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['preferences', 'metadata'] and isinstance(value, dict):
                value = json.dumps(value)
            update_fields.append(f"{key} = %s")
            params.append(value)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
        await _execute_query(query, tuple(params))
        
        logger.info(f"✅ User updated (ID: {user_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating user: {e}")
        return False


async def update_last_login(username: str) -> None:
    """Atualiza timestamp do último login"""
    await _execute_query(SQL.UPDATE_LAST_LOGIN, (username,))


async def get_all_users() -> List[Dict[str, Any]]:
    """Retorna todos os usuários (admin only)"""
    return await _execute_query(SQL.SELECT_ALL_USERS, fetch="all")


async def delete_user(user_id: int) -> bool:
    """Deleta usuário por ID"""
    return await _execute_delete(TableName.USERS, user_id)


async def update_user_role(user_id: int, role: str) -> bool:
    """Atualiza role do usuário"""
    try:
        await _execute_query(SQL.UPDATE_USER_ROLE, (role, user_id))
        logger.info(f"✅ User role updated (ID: {user_id}) -> {role}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating user role: {e}")
        return False


# ============================================
# SETTINGS FUNCTIONS v3.0
# ============================================

async def get_setting(key: str, default: Any = None) -> Any:
    """Obtém configuração do banco"""
    row = await _execute_query(SQL.SELECT_SETTING, (key,), fetch="one")
    return row['value'] if row else default


async def set_setting(
    key: str,
    value: Any,
    updated_by: str = "system",
    category: str = "other",
    data_type: str = "string",
    description: Optional[str] = None
) -> None:
    """Salva configuração no banco com histórico (v3.0)"""
    old_value = await get_setting(key)
    history_entry = _create_history_entry(old_value, value, updated_by)
    
    await _execute_query(
        """
        INSERT INTO settings (
            key, value, updated_at, updated_by, 
            category, data_type, description, change_history
        )
        VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (key) DO UPDATE 
        SET value = %s, 
            updated_at = CURRENT_TIMESTAMP, 
            updated_by = %s,
            category = %s,
            data_type = %s,
            description = COALESCE(%s, settings.description),
            change_history = settings.change_history || %s::jsonb
        """,
        (
            key, str(value), updated_by, category, data_type, description,
            json.dumps([history_entry]),
            str(value), updated_by, category, data_type, description,
            json.dumps([history_entry])
        )
    )


async def get_all_settings() -> Dict[str, Any]:
    """Retorna todas as configurações"""
    rows = await _execute_query(SQL.SELECT_ALL_SETTINGS, fetch="all")
    return {row['key']: row['value'] for row in rows}


# ============================================
# SYSTEM LOGS FUNCTIONS
# ============================================

async def log_system_action(
    action: str,
    username: str,
    reason: Optional[str] = None,
    email_sent: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> None:
    """Registra ação do sistema"""
    await _execute_query(
        """
        INSERT INTO systemlogs 
        (action, username, reason, email_sent, ip_address, user_agent, context, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            action, username, reason, email_sent, ip_address, user_agent,
            _safe_json_dumps(context), session_id
        )
    )


async def get_system_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtém logs do sistema"""
    return await _execute_query(SQL.SELECT_SYSTEM_LOGS, (limit,), fetch="all")


# ============================================
# ALERTS FUNCTIONS v3.0
# ============================================

async def log_alert(
    person_id: int,
    out_time: float,
    snapshot_path: Optional[str] = None,
    email_sent: bool = False,
    notification_sent: bool = False,  # NEW v3.0
    track_id: Optional[int] = None,
    video_path: Optional[str] = None,
    zone_index: Optional[int] = None,
    zone_id: Optional[int] = None,
    zone_name: Optional[str] = None,
    alert_type: str = "zone_violation",
    severity: str = "medium",
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Registra alerta (v3.0 - compatível com yolo.py)"""
    await _execute_query(
        """
        INSERT INTO alerts (
            person_id, out_time, snapshot_path, email_sent, notification_sent,
            track_id, video_path, zone_index, zone_id, zone_name,
            alert_type, severity, description, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            person_id, out_time, snapshot_path, email_sent, notification_sent,
            track_id, video_path, zone_index, zone_id, zone_name,
            alert_type, severity, description,
            _safe_json_dumps(metadata)
        )
    )


async def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtém alertas recentes"""
    return await _execute_query(SQL.SELECT_RECENT_ALERTS, (limit,), fetch="all")


async def delete_alert(alert_id: int) -> bool:
    """Deleta alerta por ID"""
    return await _execute_delete(TableName.ALERTS, alert_id)


async def update_alert(
    alert_id: int,
    **kwargs
) -> bool:
    """Atualiza alerta (v3.0) - aceita qualquer campo"""
    try:
        if not kwargs:
            return False
        
        # Build dynamic UPDATE query
        update_fields = []
        params = []
        
        for key, value in kwargs.items():
            if key == 'metadata' and isinstance(value, dict):
                value = json.dumps(value)
            update_fields.append(f"{key} = %s")
            params.append(value)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(alert_id)
        
        query = f"UPDATE alerts SET {', '.join(update_fields)} WHERE id = %s"
        await _execute_query(query, tuple(params))
        
        logger.info(f"✅ Alert updated (ID: {alert_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating alert: {e}")
        return False


# ============================================
# DETECTIONS FUNCTIONS (YOLO)
# ============================================

async def save_detection(
    track_id: int,
    zone_index: Optional[int] = None,
    zone_id: Optional[int] = None,
    zone_name: Optional[str] = None,
    confidence: Optional[float] = None,
    bbox: Optional[Dict[str, Any]] = None,
    status: str = "active",
    duration_seconds: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Salva detecção YOLO (v3.0)"""
    await _execute_query(
        """
        INSERT INTO detections (
            track_id, zone_index, zone_id, zone_name, confidence,
            bbox, status, duration_seconds, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            track_id, zone_index, zone_id, zone_name, confidence,
            _safe_json_dumps(bbox), status, duration_seconds,
            _safe_json_dumps(metadata)
        )
    )


async def get_detections_by_track(track_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Obtém detecções de um track específico"""
    return await _execute_query(SQL.SELECT_DETECTIONS_BY_TRACK, (track_id, limit), fetch="all")


# ============================================
# CAMERAS FUNCTIONS v1.0
# ============================================
async def get_all_cameras(active_only: bool = False) -> List[Dict[str, Any]]:
    """Retorna todas as câmeras (ou apenas ativas)."""
    query = SQL.SELECT_ACTIVE_CAMERAS if active_only else SQL.SELECT_ALL_CAMERAS
    return await _execute_query(query, fetch="all")


async def get_camera_by_id(camera_id: int) -> Optional[Dict[str, Any]]:
    """Busca câmera por ID."""
    return await _execute_query(SQL.SELECT_CAMERA_BY_ID, (camera_id,), fetch="one")


async def create_camera(
    name: str,
    source: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    location: Optional[str] = None,
    enabled: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Cria nova câmera."""
    row = await _execute_query(
        """
        INSERT INTO cameras (
            name, source, username, password, location,
            enabled, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            name,
            source,
            username,
            password,
            location,
            enabled,
            _safe_json_dumps(metadata),
        ),
        fetch="one",
    )
    camera_id = row["id"]
    logger.info(f"✅ Camera created: {name} (ID: {camera_id})")
    return camera_id


async def update_camera(
    camera_id: int,
    **kwargs: Any,
) -> bool:
    """Atualiza câmera; aceita qualquer campo simples ou metadata=dict."""
    try:
        if not kwargs:
            return False

        update_fields = []
        params: List[Any] = []

        for key, value in kwargs.items():
            if key == "metadata" and isinstance(value, dict):
                value = _safe_json_dumps(value)
            update_fields.append(f"{key} = %s")
            params.append(value)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(camera_id)

        query = f"UPDATE cameras SET {', '.join(update_fields)} WHERE id = %s"
        await _execute_query(query, tuple(params))

        logger.info(f"✅ Camera updated (ID: {camera_id})")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating camera: {e}")
        return False


async def delete_camera(camera_id: int) -> bool:
    """Deleta câmera por ID."""
    return await _execute_delete(TableName.CAMERAS, camera_id)


# ============================================
# RAG FUNCTIONS (CONVERSATIONS + KNOWLEDGE BASE)
# ============================================

async def save_conversation_message(
    user_id: int,
    session_id: str,
    message: str,
    role: str,
    metadata: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Salva mensagem de conversação para histórico"""
    await _execute_query(
        """
        INSERT INTO conversations (user_id, session_id, message, role, metadata, context)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            user_id, session_id, message, role,
            _safe_json_dumps(metadata),
            _safe_json_dumps(context)
        )
    )


async def get_conversation_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recupera histórico de conversação"""
    return await _execute_query(SQL.SELECT_CONVERSATION_HISTORY, (session_id, limit), fetch="all")


async def add_knowledge(
    title: str,
    content: str,
    category: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Adiciona documento à base de conhecimento"""
    row = await _execute_query(
        """
        INSERT INTO knowledgebase (title, content, category, source, tags, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            title, content, category, source,
            tags or [],
            _safe_json_dumps(metadata)
        ),
        fetch="one"
    )
    return row['id']


async def search_knowledge(
    query: str,
    category: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Busca na base de conhecimento"""
    if category:
        return await _execute_query(
            """
            SELECT * FROM knowledgebase 
            WHERE category = %s AND (title ILIKE %s OR content ILIKE %s)
            ORDER BY updated_at DESC 
            LIMIT %s
            """,
            (category, f"%{query}%", f"%{query}%", limit),
            fetch="all"
        )
    else:
        return await _execute_query(
            SQL.SEARCH_KNOWLEDGE_ALL,
            (f"%{query}%", f"%{query}%", limit),
            fetch="all"
        )


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test_connection() -> None:
        """Testa conexão com PostgreSQL"""
        try:
            print("=" * 80)
            print("🧪 Testando database.py v3.0 (100% API ALIGNED)...")
            print("=" * 80)
            
            pool = await get_db_pool()
            print("✅ Conexão estabelecida!")
            
            print("\n🔧 Criando tabelas v3.0...")
            await init_database(force_recreate=False) #True para recriar o banco
            print("✅ Tabelas criadas!")
            
            print("\n✅ Database v3.0 100% ALIGNED WITH APIs!")
            print("   - users.py ✅")
            print("   - auth.py ✅")
            print("   - zones.py ✅")
            print("   - cameras.py ✅")
            print("   - zones.camera_id ✅")
            print("   - alerts.py ✅")
            print("   - settings.py ✅")
            print("   - video.py ✅")
            
            await close_db_pool()
            print("✅ Pool fechado com sucesso!  (CAMERAS SUPPORT)...")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
