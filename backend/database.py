"""
============================================================================
backend/database.py
PostgreSQL Async Database Layer - RAG-READY + ZONES + ALERTS
============================================================================
Usando psycopg3 (driver oficial do PostgreSQL)

v2.2: Adicionado zone_id na tabela alerts
============================================================================
"""

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
import sys

# Importa settings
try:
    from backend.config import settings
except ModuleNotFoundError:
    from config import settings

logger = logging.getLogger("uvicorn")

# Fix para Windows
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ============================================================================
# CONNECTION POOL
# ============================================================================

pool: Optional[AsyncConnectionPool] = None


async def get_db_pool() -> AsyncConnectionPool:
    """Obtém connection pool do PostgreSQL"""
    global pool
    
    if pool is None:
        try:
            # Remove 'asyncpg' da URL se presente
            db_url = settings.DATABASE_URL #.replace("asyncpg", "")
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            db_url = db_url.replace("postgresql+://", "postgresql://")
            
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


async def close_db_pool():
    """Fecha connection pool"""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("✅ PostgreSQL pool closed")


# ============================================================================
# DROP ALL TABLES (DEVELOPMENT ONLY)
# ============================================================================

async def drop_all_tables():
    """⚠️ CUIDADO: Dropa TODAS as tabelas! Use apenas em desenvolvimento!"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        logger.warning("⚠️ Dropping all tables...")
        
        # Lista de tabelas (antigas do Flask + novas do FastAPI)
        tables = [
            "arky",  # Flask antigo
            "conversations",  # RAG novo
            "detections",  # Novo
            "alerts",  # Flask + FastAPI
            "zones",  # NOVO
            "systemlogs",  # Flask + FastAPI
            "auditlogs",  # Novo
            "knowledgebase",  # RAG novo
            "settings",  # Flask + FastAPI
            "users"  # Flask + FastAPI
        ]
        
        for table in tables:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"✅ Dropped table: {table}")
            except Exception as e:
                logger.warning(f"⚠️ Could not drop {table}: {e}")
        
        await conn.commit()
        logger.warning("✅ All tables dropped!")


# ============================================================================
# INIT DATABASE
# ============================================================================

async def init_database(force_recreate: bool = False):
    """
    Cria tabelas se não existirem - RAG-READY + ZONES
    
    Args:
        force_recreate: Se True, dropa e recria todas as tabelas
    """
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        # Se force_recreate, dropar tabelas antigas
        if force_recreate:
            logger.warning("⚠️ FORCE RECREATE: Dropping all tables...")
            await drop_all_tables()
        
        # ====================================================================
        # TABELA: USERS
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb,
                preferences JSONB DEFAULT '{}'::jsonb
            )
        """)
        logger.info("✅ Tabela 'users' criada")
        
        # ====================================================================
        # TABELA: SETTINGS
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR(50),
                change_history JSONB DEFAULT '[]'::jsonb
            )
        """)
        logger.info("✅ Tabela 'settings' criada")
        
        # ====================================================================
        # TABELA: ZONES (NOVO - v2.1 com smart zones)
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                mode VARCHAR(50) DEFAULT 'GENERIC' NOT NULL,
                points JSONB NOT NULL,
                max_out_time REAL,
                email_cooldown REAL,
                empty_timeout REAL DEFAULT 5,
                full_timeout REAL DEFAULT 10,
                empty_threshold INTEGER DEFAULT 0,
                full_threshold INTEGER DEFAULT 3,
                enabled BOOLEAN DEFAULT TRUE NOT NULL,
                active BOOLEAN DEFAULT TRUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                deleted_at TIMESTAMP
            )
        """)
        
        # Índices para performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_zones_active 
            ON zones(active) WHERE deleted_at IS NULL
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_zones_enabled 
            ON zones(enabled) WHERE deleted_at IS NULL
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_zones_mode ON zones(mode)
        """)
        
        logger.info("✅ Tabela 'zones' criada")
        
        # ====================================================================
        # TABELA: ALERTS (compatível com yolo.py + FastAPI)
        # ✅ v2.2: ADICIONADO zone_id
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                person_id INTEGER NOT NULL,
                track_id INTEGER,
                out_time REAL NOT NULL,
                snapshot_path VARCHAR(500),
                video_path TEXT,
                email_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                zone_index INTEGER,
                zone_id INTEGER REFERENCES zones(id) ON DELETE SET NULL,
                zone_name VARCHAR(100),
                alert_type VARCHAR(50) DEFAULT 'zone_violation',
                severity VARCHAR(20) DEFAULT 'medium',
                description TEXT,
                metadata JSONB DEFAULT '{}'::jsonb,
                resolved_at TIMESTAMP,
                resolved_by VARCHAR(50),
                resolution_notes TEXT
            )
        """)
        
        # Índices para performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_person ON alerts(person_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved_at)
        """)
        
        logger.info("✅ Tabela 'alerts' criada (com zone_id)")
        
        # ====================================================================
        # TABELA: SYSTEMLOGS
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS systemlogs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(50) NOT NULL,
                username VARCHAR(50),
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_sent BOOLEAN DEFAULT FALSE,
                ip_address VARCHAR(45),
                context JSONB DEFAULT '{}'::jsonb,
                session_id VARCHAR(100)
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_systemlogs_timestamp 
            ON systemlogs(timestamp DESC)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_systemlogs_username 
            ON systemlogs(username)
        """)
        
        logger.info("✅ Tabela 'systemlogs' criada")
        
        # ====================================================================
        # TABELA: AUDITLOGS
        # ====================================================================
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
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON auditlogs(timestamp DESC)
        """)
        
        logger.info("✅ Tabela 'auditlogs' criada")
        
        # ====================================================================
        # TABELA: CONVERSATIONS (RAG)
        # ====================================================================
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
            CREATE INDEX IF NOT EXISTS idx_conversations_session 
            ON conversations(session_id)
        """)
        
        logger.info("✅ Tabela 'conversations' criada")
        
        # ====================================================================
        # TABELA: KNOWLEDGEBASE (RAG)
        # ====================================================================
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
        
        # ====================================================================
        # TABELA: DETECTIONS (YOLO)
        # ====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id SERIAL PRIMARY KEY,
                track_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                zone_index INTEGER,
                zone_name VARCHAR(100),
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
        
        await conn.commit()
        logger.info("✅ Database tables initialized (RAG-ready + Zones v2.2)")
        
        # ====================================================================
        # CRIA ZONA PADRÃO SE NÃO EXISTIR
        # ====================================================================
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) as count FROM zones")
            result = await cur.fetchone()
            
            if result['count'] == 0:
                logger.info("📍 Creating default zone...")
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
                        "GENERIC",
                        json.dumps([[100, 100], [500, 100], [500, 400], [100, 400]]),
                        5.0,
                        10.0,
                        0,
                        3,
                        True,
                        True
                    )
                )
                await conn.commit()
                logger.info("✅ Default zone created")
        
        # Sincroniza com settings.safe_zone
        await sync_zones_to_settings()


# ============================================================================
# ZONES FUNCTIONS
# ============================================================================

async def sync_zones_to_settings():
    """
    Sincroniza tabela zones -> settings.safe_zone (JSON).
    Mantém compatibilidade com yolo.py que lê de settings.safe_zone.
    
    Formato:
    [
        {
            "name": "...",
            "mode": "...",
            "points": [[x,y], ...],
            ...
        },
        ...
    ]
    """
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            # Busca todas as zonas ativas e habilitadas
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT * FROM zones 
                    WHERE active = TRUE 
                    AND enabled = TRUE 
                    AND deleted_at IS NULL
                    ORDER BY id
                """)
                zones = await cur.fetchall()
            
            # Monta JSON no formato esperado pelo yolo.py
            zones_data = []
            for zone in zones:
                zone_dict = {
                    "name": zone['name'],
                    "mode": zone['mode'],
                    "points": zone['points'] if isinstance(zone['points'], list) else json.loads(zone['points']),
                }
                
                # Adiciona configs opcionais se não None
                if zone.get('max_out_time') is not None:
                    zone_dict['max_out_time'] = zone['max_out_time']
                if zone.get('email_cooldown') is not None:
                    zone_dict['email_cooldown'] = zone['email_cooldown']
                if zone.get('empty_timeout') is not None:
                    zone_dict['empty_timeout'] = zone['empty_timeout']
                if zone.get('full_timeout') is not None:
                    zone_dict['full_timeout'] = zone['full_timeout']
                if zone.get('empty_threshold') is not None:
                    zone_dict['empty_threshold'] = zone['empty_threshold']
                if zone.get('full_threshold') is not None:
                    zone_dict['full_threshold'] = zone['full_threshold']
                
                zones_data.append(zone_dict)
            
            # Atualiza settings.safe_zone
            json_str = json.dumps(zones_data)
            
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO settings (key, value, updated_by)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key) DO UPDATE 
                    SET value = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s
                    """,
                    ("safe_zone", json_str, "system", json_str, "system")
                )
                await conn.commit()
            
            logger.info(f"✅ Synced {len(zones)} zones to settings.safe_zone")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error syncing zones: {e}")
        return False


async def create_zone(
    name: str,
    mode: str,
    points: List[List[float]],
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = 5.0,
    full_timeout: Optional[float] = 10.0,
    empty_threshold: Optional[int] = 0,
    full_threshold: Optional[int] = 3,
    enabled: bool = True,
    active: bool = True
) -> int:
    """Cria nova zona"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO zones (
                        name, mode, points, max_out_time, email_cooldown,
                        empty_timeout, full_timeout, empty_threshold, full_threshold,
                        enabled, active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        name, mode, json.dumps(points), max_out_time, email_cooldown,
                        empty_timeout, full_timeout, empty_threshold, full_threshold,
                        enabled, active
                    )
                )
                
                result = await cur.fetchone()
                zone_id = result['id']
                await conn.commit()
        
        # Sincroniza com settings.safe_zone
        await sync_zones_to_settings()
        
        logger.info(f"✅ Zone created: {name} (ID: {zone_id})")
        return zone_id
        
    except Exception as e:
        logger.error(f"❌ Error creating zone: {e}")
        raise


async def get_all_zones(active_only: bool = False) -> List[Dict[str, Any]]:
    """Retorna todas as zonas"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if active_only:
                await cur.execute("""
                    SELECT * FROM zones 
                    WHERE active = TRUE AND deleted_at IS NULL
                    ORDER BY id
                """)
            else:
                await cur.execute("SELECT * FROM zones ORDER BY id")
            
            zones = await cur.fetchall()
    
    # Converte JSONB points para list
    for zone in zones:
        if isinstance(zone['points'], str):
            zone['points'] = json.loads(zone['points'])
    
    return zones


async def get_zone_by_id(zone_id: int) -> Optional[Dict[str, Any]]:
    """Busca zona por ID"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM zones WHERE id = %s AND deleted_at IS NULL",
                (zone_id,)
            )
            zone = await cur.fetchone()
    
    if zone and isinstance(zone['points'], str):
        zone['points'] = json.loads(zone['points'])
    
    return zone


async def update_zone(
    zone_id: int,
    name: Optional[str] = None,
    mode: Optional[str] = None,
    points: Optional[List[List[float]]] = None,
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = None,
    full_timeout: Optional[float] = None,
    empty_threshold: Optional[int] = None,
    full_threshold: Optional[int] = None,
    enabled: Optional[bool] = None,
    active: Optional[bool] = None
) -> bool:
    """Atualiza zona existente"""
    pool = await get_db_pool()
    
    try:
        # Busca zona atual
        zone = await get_zone_by_id(zone_id)
        if not zone:
            logger.warning(f"⚠️ Zone not found (ID: {zone_id})")
            return False
        
        # Prepara valores atualizados (mantém valores atuais se None)
        updated_name = name if name is not None else zone['name']
        updated_mode = mode if mode is not None else zone['mode']
        updated_points = points if points is not None else zone['points']
        updated_maxout = max_out_time if max_out_time is not None else zone.get('max_out_time')
        updated_emailcd = email_cooldown if email_cooldown is not None else zone.get('email_cooldown')
        updated_empty = empty_timeout if empty_timeout is not None else zone.get('empty_timeout')
        updated_full = full_timeout if full_timeout is not None else zone.get('full_timeout')
        updated_emptythresh = empty_threshold if empty_threshold is not None else zone.get('empty_threshold')
        updated_fullthresh = full_threshold if full_threshold is not None else zone.get('full_threshold')
        updated_enabled = enabled if enabled is not None else zone['enabled']
        updated_active = active if active is not None else zone['active']
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE zones SET
                        name = %s, mode = %s, points = %s,
                        max_out_time = %s, email_cooldown = %s,
                        empty_timeout = %s, full_timeout = %s,
                        empty_threshold = %s, full_threshold = %s,
                        enabled = %s, active = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        updated_name, updated_mode, json.dumps(updated_points),
                        updated_maxout, updated_emailcd,
                        updated_empty, updated_full,
                        updated_emptythresh, updated_fullthresh,
                        updated_enabled, updated_active,
                        zone_id
                    )
                )
                await conn.commit()
        
        # Sincroniza com settings.safe_zone
        await sync_zones_to_settings()
        
        logger.info(f"✅ Zone updated (ID: {zone_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating zone: {e}")
        return False


async def delete_zone(zone_id: int) -> bool:
    """Deleta zona (soft delete - marca como inativa e deletada)"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Soft delete (marca como inativa e adiciona deleted_at)
                await cur.execute(
                    """
                    UPDATE zones 
                    SET active = FALSE, enabled = FALSE, 
                        deleted_at = CURRENT_TIMESTAMP, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (zone_id,)
                )
                await conn.commit()
        
        # Sincroniza com settings.safe_zone
        await sync_zones_to_settings()
        
        logger.info(f"✅ Zone deleted (soft) (ID: {zone_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting zone: {e}")
        return False


async def delete_zone_permanent(zone_id: int) -> bool:
    """Deleta zona permanentemente (hard delete)"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM zones WHERE id = %s", (zone_id,))
                await conn.commit()
        
        # Sincroniza com settings.safe_zone
        await sync_zones_to_settings()
        
        logger.info(f"✅ Zone deleted (permanent) (ID: {zone_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error permanently deleting zone: {e}")
        return False


# ============================================================================
# USER FUNCTIONS
# ============================================================================

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Busca usuário por username"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM users WHERE username = %s",
                (username,)
            )
            row = await cur.fetchone()
    
    return row if row else None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Busca usuário por email"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            row = await cur.fetchone()
    
    return row if row else None


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Busca usuário por ID"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM users WHERE id = %s",
                (user_id,)
            )
            row = await cur.fetchone()
    
    return row if row else None


async def create_user(
    username: str,
    email: str,
    password_hash: str,
    role: str = "user"
) -> bool:
    """Cria novo usuário"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (username, email, password_hash, role, json.dumps({}))
                )
                await conn.commit()
        
        logger.info(f"✅ User created: {username}")
        return True
        
    except psycopg.errors.UniqueViolation:
        logger.warning(f"⚠️ User already exists: {username}")
        return False
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        return False


async def update_last_login(username: str):
    """Atualiza timestamp do último login"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = %s",
                (username,)
            )
            await conn.commit()


async def get_all_users() -> List[Dict[str, Any]]:
    """Retorna todos os usuários (admin only)"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = await cur.fetchall()
    
    return rows


async def delete_user(user_id: int) -> bool:
    """Deleta usuário por ID"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                await conn.commit()
        
        logger.info(f"✅ User deleted (ID: {user_id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting user: {e}")
        return False


async def update_user_role(user_id: int, role: str) -> bool:
    """Atualiza role do usuário"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET role = %s WHERE id = %s",
                    (role, user_id)
                )
                await conn.commit()
        
        logger.info(f"✅ User role updated (ID: {user_id}) -> {role}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating user role: {e}")
        return False


# ============================================================================
# SETTINGS FUNCTIONS
# ============================================================================

async def get_setting(key: str, default: Any = None) -> Any:
    """Obtém configuração do banco"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT value FROM settings WHERE key = %s",
                (key,)
            )
            row = await cur.fetchone()
    
    return row['value'] if row else default


async def set_setting(key: str, value: Any, updated_by: str = "system"):
    """Salva configuração no banco com histórico"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        # Busca valor anterior
        old_value = await get_setting(key)
        
        # Prepara entrada de histórico
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_value": old_value,
            "new_value": str(value),
            "updated_by": updated_by
        }
        
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO settings (key, value, updated_at, updated_by, change_history)
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s::jsonb)
                ON CONFLICT (key) DO UPDATE 
                SET value = %s, 
                    updated_at = CURRENT_TIMESTAMP, 
                    updated_by = %s,
                    change_history = settings.change_history || %s::jsonb
                """,
                (
                    key, str(value), updated_by, json.dumps([history_entry]),
                    str(value), updated_by, json.dumps([history_entry])
                )
            )
            await conn.commit()


async def get_all_settings() -> Dict[str, Any]:
    """Retorna todas as configurações"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT key, value FROM settings")
            rows = await cur.fetchall()
    
    return {row['key']: row['value'] for row in rows}


# ============================================================================
# SYSTEM LOGS FUNCTIONS
# ============================================================================

async def log_system_action(
    action: str,
    username: str,
    reason: Optional[str] = None,
    email_sent: bool = False,
    ip_address: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
):
    """Registra ação do sistema"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO systemlogs 
                (action, username, reason, email_sent, ip_address, context, session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    action, username, reason, email_sent, ip_address,
                    json.dumps(context or {}), session_id
                )
            )
            await conn.commit()


async def get_system_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Obtém logs do sistema"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM systemlogs ORDER BY timestamp DESC LIMIT %s",
                (limit,)
            )
            return await cur.fetchall()


# ============================================================================
# ALERTS FUNCTIONS
# ✅ v2.2: Adicionado zone_id
# ============================================================================

async def log_alert(
    person_id: int,
    out_time: float,
    snapshot_path: Optional[str] = None,
    email_sent: bool = False,
    track_id: Optional[int] = None,
    video_path: Optional[str] = None,
    zone_index: Optional[int] = None,
    zone_id: Optional[int] = None,  # ✅ NOVO
    zone_name: Optional[str] = None,
    alert_type: str = "zone_violation",
    severity: str = "medium",
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Registra alerta (compatível com yolo.py)"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO alerts (
                    person_id, out_time, snapshot_path, email_sent,
                    track_id, video_path, zone_index, zone_id, zone_name,
                    alert_type, severity, description, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    person_id, out_time, snapshot_path, email_sent,
                    track_id, video_path, zone_index, zone_id, zone_name,
                    alert_type, severity, description,
                    json.dumps(metadata or {})
                )
            )
            await conn.commit()


async def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtém alertas recentes"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            return await cur.fetchall()


async def delete_alert(alert_id: int) -> bool:
    """Deleta alerta por ID"""
    pool = await get_db_pool()
    
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
                await conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting alert: {e}")
        return False


# ============================================================================
# DETECTIONS FUNCTIONS (YOLO)
# ============================================================================

async def save_detection(
    track_id: int,
    zone_index: Optional[int] = None,
    zone_name: Optional[str] = None,
    confidence: Optional[float] = None,
    bbox: Optional[Dict[str, Any]] = None,
    status: str = "active",
    duration_seconds: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Salva detecção YOLO"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO detections (
                    track_id, zone_index, zone_name, confidence,
                    bbox, status, duration_seconds, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    track_id, zone_index, zone_name, confidence,
                    json.dumps(bbox or {}), status, duration_seconds,
                    json.dumps(metadata or {})
                )
            )
            await conn.commit()


async def get_detections_by_track(track_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Obtém detecções de um track específico"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM detections 
                WHERE track_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
                """,
                (track_id, limit)
            )
            return await cur.fetchall()


# ============================================================================
# RAG FUNCTIONS (CONVERSATIONS + KNOWLEDGE BASE)
# ============================================================================

async def save_conversation_message(
    user_id: int,
    session_id: str,
    message: str,
    role: str,
    metadata: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
):
    """Salva mensagem de conversação para histórico"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversations (user_id, session_id, message, role, metadata, context)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id, session_id, message, role,
                    json.dumps(metadata or {}),
                    json.dumps(context or {})
                )
            )
            await conn.commit()


async def get_conversation_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Recupera histórico de conversação"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT * FROM conversations 
                WHERE session_id = %s 
                ORDER BY timestamp ASC 
                LIMIT %s
                """,
                (session_id, limit)
            )
            return await cur.fetchall()


async def add_knowledge(
    title: str,
    content: str,
    category: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """Adiciona documento à base de conhecimento"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO knowledgebase (title, content, category, source, tags, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    title, content, category, source,
                    tags or [],
                    json.dumps(metadata or {})
                )
            )
            row = await cur.fetchone()
            await conn.commit()
            return row['id']


async def search_knowledge(
    query: str,
    category: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Busca na base de conhecimento"""
    pool = await get_db_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if category:
                await cur.execute(
                    """
                    SELECT * FROM knowledgebase 
                    WHERE category = %s 
                    AND (title ILIKE %s OR content ILIKE %s)
                    ORDER BY updated_at DESC 
                    LIMIT %s
                    """,
                    (category, f"%{query}%", f"%{query}%", limit)
                )
            else:
                await cur.execute(
                    """
                    SELECT * FROM knowledgebase 
                    WHERE title ILIKE %s OR content ILIKE %s
                    ORDER BY updated_at DESC 
                    LIMIT %s
                    """,
                    (f"%{query}%", f"%{query}%", limit)
                )
            
            return await cur.fetchall()


# ============================================================================
# TEST SCRIPT
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_connection():
        """Testa conexão com PostgreSQL"""
        try:
            print("=" * 70)
            print("🧪 Testando conexão com PostgreSQL (psycopg3)...")
            print("=" * 70)
            
            pool = await get_db_pool()
            print("✅ Conexão estabelecida!")
            
            print("\n🔧 Criando tabelas (RAG-ready + Zones v2.2)...")
            await init_database(force_recreate=False)
            print("✅ Tabelas criadas!")
            
            print("\n✅ Database preparado para RAG + Smart Zones!")
            
            await close_db_pool()
            print("✅ Pool fechado com sucesso!")
            
            print("=" * 70)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(test_connection())
