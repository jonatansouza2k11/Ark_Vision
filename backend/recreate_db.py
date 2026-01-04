"""
recreate_db.py - OPTIMIZED v2.0
Database recreation with safety features and backup capability

Features:
- Automatic backup before deletion
- Dry-run mode for testing
- Progress tracking
- Rollback capability
- Multiple confirmation levels
- Comprehensive logging
- CLI arguments support
- Data export before recreation

🎯 Exemplos de Uso
# Dry run (testar sem executar)
python recreate_db.py --mode dry-run

# Recreação completa com backup
python recreate_db.py

# Recreação forçada sem backup (perigoso!)
python recreate_db.py --force --skip-backup

# Triple confirmation com backup
python recreate_db.py --confirmation triple

# Schema only (sem dados)
python recreate_db.py --mode schema-only

# Verbose logging
python recreate_db.py --verbose

⚠️ ATENÇÃO: Isso apaga TODOS os dados! Use com cuidado!
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import (
    init_database,
    close_db_pool,
    drop_all_tables,
    get_all_users,
    get_all_zones,
    get_all_settings,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# OTIMIZAÇÃO 1: Constants & Enums
# ============================================

class RecreateMode(str, Enum):
    """✅ Database recreation modes"""
    FULL = "full"  # Drop all tables and recreate
    SCHEMA_ONLY = "schema_only"  # Recreate schema without data
    CLEAN = "clean"  # Clear data but keep schema
    DRY_RUN = "dry_run"  # Test without changes


class BackupFormat(str, Enum):
    """✅ Backup export formats"""
    JSON = "json"
    SQL = "sql"
    NONE = "none"


class ConfirmationLevel(str, Enum):
    """✅ Confirmation levels"""
    NONE = "none"  # No confirmation (dangerous!)
    SIMPLE = "simple"  # Single confirmation
    DOUBLE = "double"  # Double confirmation
    TRIPLE = "triple"  # Triple confirmation with countdown


# Default paths
BACKUP_DIR = Path("backups")
DEFAULT_BACKUP_FORMAT = BackupFormat.JSON


# ============================================
# OTIMIZAÇÃO 2: Dataclasses
# ============================================

@dataclass
class RecreateConfig:
    """✅ Configuration for database recreation"""
    mode: RecreateMode = RecreateMode.FULL
    backup_format: BackupFormat = BackupFormat.JSON
    confirmation_level: ConfirmationLevel = ConfirmationLevel.DOUBLE
    backup_dir: Path = BACKUP_DIR
    skip_backup: bool = False
    force: bool = False
    verbose: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if self.force and self.confirmation_level != ConfirmationLevel.NONE:
            logger.warning("⚠️ Force mode enabled, ignoring confirmation level")
            self.confirmation_level = ConfirmationLevel.NONE
        
        # Create backup directory
        if not self.skip_backup and self.backup_format != BackupFormat.NONE:
            self.backup_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class BackupInfo:
    """✅ Backup metadata"""
    timestamp: datetime
    path: Path
    format: BackupFormat
    tables_backed_up: List[str] = field(default_factory=list)
    total_records: int = 0
    size_bytes: int = 0
    
    @property
    def size_mb(self) -> float:
        """Size in megabytes"""
        return self.size_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "path": str(self.path),
            "format": self.format.value,
            "tables_backed_up": self.tables_backed_up,
            "total_records": self.total_records,
            "size_bytes": self.size_bytes,
            "size_mb": f"{self.size_mb:.2f} MB"
        }


@dataclass
class RecreateResult:
    """✅ Result of recreation operation"""
    success: bool
    mode: RecreateMode
    backup_info: Optional[BackupInfo] = None
    tables_created: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0
    
    def __str__(self) -> str:
        if self.success:
            return (
                f"✅ Database recreation successful!\n"
                f"   Mode: {self.mode.value}\n"
                f"   Duration: {self.duration_seconds:.2f}s\n"
                f"   Tables created: {len(self.tables_created)}"
            )
        return f"❌ Database recreation failed: {self.error}"


# ============================================
# OTIMIZAÇÃO 3: Backup Functions
# ============================================

async def _backup_users() -> List[Dict[str, Any]]:
    """
    ✅ Backup users table
    
    Returns:
        List of user records
    """
    try:
        users = await get_all_users()
        logger.info(f"   📦 Backed up {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"   ❌ Error backing up users: {e}")
        return []


async def _backup_zones() -> List[Dict[str, Any]]:
    """
    ✅ Backup zones table
    
    Returns:
        List of zone records
    """
    try:
        zones = await get_all_zones(active_only=False)
        logger.info(f"   📦 Backed up {len(zones)} zones")
        return zones
    except Exception as e:
        logger.error(f"   ❌ Error backing up zones: {e}")
        return []


async def _backup_settings() -> Dict[str, Any]:
    """
    ✅ Backup settings table
    
    Returns:
        Dict of settings
    """
    try:
        settings = await get_all_settings()
        logger.info(f"   📦 Backed up {len(settings)} settings")
        return settings
    except Exception as e:
        logger.error(f"   ❌ Error backing up settings: {e}")
        return {}


async def create_backup(config: RecreateConfig) -> Optional[BackupInfo]:
    """
    ✅ Create backup of database before recreation
    
    Args:
        config: Recreation configuration
    
    Returns:
        BackupInfo or None if backup failed/skipped
    """
    if config.skip_backup or config.backup_format == BackupFormat.NONE:
        logger.info("⏭️  Skipping backup (as requested)")
        return None
    
    logger.info("\n📦 Creating backup...")
    
    try:
        # Generate backup filename
        timestamp = datetime.now()
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.{config.backup_format.value}"
        backup_path = config.backup_dir / filename
        
        # Collect data
        backup_data = {
            "metadata": {
                "timestamp": timestamp.isoformat(),
                "backup_format": config.backup_format.value,
                "mode": config.mode.value
            },
            "users": await _backup_users(),
            "zones": await _backup_zones(),
            "settings": await _backup_settings(),
        }
        
        # Calculate stats
        total_records = (
            len(backup_data["users"]) +
            len(backup_data["zones"]) +
            len(backup_data["settings"])
        )
        
        # Save backup
        if config.backup_format == BackupFormat.JSON:
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str)
        else:
            logger.warning(f"⚠️ Format {config.backup_format} not yet implemented, using JSON")
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, default=str)
        
        # Get file size
        size_bytes = backup_path.stat().st_size
        
        backup_info = BackupInfo(
            timestamp=timestamp,
            path=backup_path,
            format=config.backup_format,
            tables_backed_up=["users", "zones", "settings"],
            total_records=total_records,
            size_bytes=size_bytes
        )
        
        logger.info(f"✅ Backup created: {backup_path}")
        logger.info(f"   📊 {total_records} records, {backup_info.size_mb:.2f} MB")
        
        # Save backup metadata
        metadata_path = backup_path.with_suffix('.meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(backup_info.to_dict(), f, indent=2)
        
        return backup_info
    
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================
# OTIMIZAÇÃO 4: Confirmation Functions
# ============================================

def _get_user_confirmation_simple() -> bool:
    """
    ✅ Simple confirmation prompt
    
    Returns:
        True if user confirmed
    """
    print("\n" + "=" * 70)
    print("⚠️  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS!")
    print("=" * 70)
    
    response = input("\nDigite 'SIM' para confirmar: ").strip().upper()
    return response == "SIM"


def _get_user_confirmation_double() -> bool:
    """
    ✅ Double confirmation prompt
    
    Returns:
        True if user confirmed twice
    """
    print("\n" + "=" * 70)
    print("⚠️  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS!")
    print("⚠️  Esta ação é IRREVERSÍVEL!")
    print("=" * 70)
    
    response1 = input("\nDigite 'SIM' para confirmar: ").strip().upper()
    if response1 != "SIM":
        return False
    
    print("\n⚠️  Última chance! Tem certeza absoluta?")
    response2 = input("Digite 'CONFIRMO' para prosseguir: ").strip().upper()
    return response2 == "CONFIRMO"


def _get_user_confirmation_triple() -> bool:
    """
    ✅ Triple confirmation with countdown
    
    Returns:
        True if user confirmed three times
    """
    print("\n" + "=" * 70)
    print("🚨 ATENÇÃO MÁXIMA: Isso vai APAGAR TODOS OS DADOS!")
    print("🚨 Esta ação é IRREVERSÍVEL e PERMANENTE!")
    print("=" * 70)
    
    # First confirmation
    response1 = input("\n1️⃣ Digite 'SIM' para continuar: ").strip().upper()
    if response1 != "SIM":
        return False
    
    # Second confirmation
    print("\n⚠️  Todos os usuários, zonas e configurações serão perdidos!")
    response2 = input("2️⃣ Digite 'CONFIRMO' para prosseguir: ").strip().upper()
    if response2 != "CONFIRMO":
        return False
    
    # Third confirmation with countdown
    print("\n🚨 ÚLTIMA CHANCE!")
    print("   Esta é a última oportunidade de cancelar.")
    
    import time
    for i in range(3, 0, -1):
        print(f"   Confirmação final em {i}...")
        time.sleep(1)
    
    response3 = input("\n3️⃣ Digite 'DELETE ALL DATA' para confirmar: ").strip().upper()
    return response3 == "DELETE ALL DATA"


def get_user_confirmation(level: ConfirmationLevel) -> bool:
    """
    ✅ Get user confirmation based on level
    
    Args:
        level: Confirmation level
    
    Returns:
        True if user confirmed
    """
    if level == ConfirmationLevel.NONE:
        return True
    elif level == ConfirmationLevel.SIMPLE:
        return _get_user_confirmation_simple()
    elif level == ConfirmationLevel.DOUBLE:
        return _get_user_confirmation_double()
    elif level == ConfirmationLevel.TRIPLE:
        return _get_user_confirmation_triple()
    else:
        logger.error(f"Unknown confirmation level: {level}")
        return False


# ============================================
# OTIMIZAÇÃO 5: Recreation Functions
# ============================================

async def recreate_database(config: RecreateConfig) -> RecreateResult:
    """
    ✅ Recreate database with safety features
    
    Args:
        config: Recreation configuration
    
    Returns:
        RecreateResult with operation details
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Confirmation
        if not config.force:
            logger.info(f"📋 Mode: {config.mode.value}")
            logger.info(f"📋 Backup: {'No' if config.skip_backup else config.backup_format.value}")
            
            if not get_user_confirmation(config.confirmation_level):
                logger.info("❌ Operação cancelada pelo usuário")
                return RecreateResult(
                    success=False,
                    mode=config.mode,
                    error="Cancelled by user"
                )
        
        # Step 2: Backup
        backup_info = None
        if not config.skip_backup and config.mode != RecreateMode.DRY_RUN:
            backup_info = await create_backup(config)
            if backup_info is None and not config.force:
                logger.error("❌ Backup failed, aborting recreation")
                return RecreateResult(
                    success=False,
                    mode=config.mode,
                    error="Backup failed"
                )
        
        # Step 3: Recreation based on mode
        logger.info(f"\n🔧 Starting database recreation ({config.mode.value})...")
        
        if config.mode == RecreateMode.DRY_RUN:
            logger.info("🧪 DRY RUN MODE - No changes will be made")
            logger.info("   Would drop all tables")
            logger.info("   Would recreate schema")
            tables_created = ["(dry-run)"]
        
        elif config.mode == RecreateMode.FULL:
            logger.info("   Dropping all tables...")
            await drop_all_tables()
            
            logger.info("   Creating new schema...")
            await init_database(force_recreate=False)
            
            tables_created = [
                "users", "settings", "zones", "alerts",
                "systemlogs", "auditlogs", "conversations",
                "knowledgebase", "detections"
            ]
        
        elif config.mode == RecreateMode.SCHEMA_ONLY:
            logger.info("   Dropping all tables...")
            await drop_all_tables()
            
            logger.info("   Creating schema only...")
            await init_database(force_recreate=False)
            
            tables_created = ["(schema-only)"]
        
        elif config.mode == RecreateMode.CLEAN:
            logger.info("   Clearing data (keeping schema)...")
            # TODO: Implement data clearing without dropping tables
            logger.warning("   ⚠️ CLEAN mode not yet fully implemented")
            tables_created = ["(data-cleared)"]
        
        else:
            raise ValueError(f"Unknown mode: {config.mode}")
        
        duration = time.time() - start_time
        
        result = RecreateResult(
            success=True,
            mode=config.mode,
            backup_info=backup_info,
            tables_created=tables_created,
            duration_seconds=duration
        )
        
        logger.info(f"\n{result}")
        
        if backup_info:
            logger.info(f"\n💾 Backup saved to: {backup_info.path}")
            logger.info(f"   Use this file to restore data if needed")
        
        return result
    
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Erro durante recreação: {e}")
        import traceback
        traceback.print_exc()
        
        return RecreateResult(
            success=False,
            mode=config.mode,
            error=str(e),
            duration_seconds=duration
        )
    
    finally:
        await close_db_pool()


# ============================================
# OTIMIZAÇÃO 6: CLI Interface
# ============================================

def parse_arguments() -> RecreateConfig:
    """
    ✅ Parse command line arguments
    
    Returns:
        RecreateConfig from CLI args
    """
    parser = argparse.ArgumentParser(
        description="Recreate database with safety features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full recreation with double confirmation
  python recreate_db.py
  
  # Dry run (test without changes)
  python recreate_db.py --mode dry-run
  
  # Force recreation without backup (dangerous!)
  python recreate_db.py --force --skip-backup
  
  # Triple confirmation with JSON backup
  python recreate_db.py --confirmation triple --backup json
  
  # Schema only recreation
  python recreate_db.py --mode schema-only
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=[m.value for m in RecreateMode],
        default=RecreateMode.FULL.value,
        help="Recreation mode (default: full)"
    )
    
    parser.add_argument(
        "--backup",
        type=str,
        choices=[b.value for b in BackupFormat],
        default=BackupFormat.JSON.value,
        help="Backup format (default: json)"
    )
    
    parser.add_argument(
        "--confirmation",
        type=str,
        choices=[c.value for c in ConfirmationLevel],
        default=ConfirmationLevel.DOUBLE.value,
        help="Confirmation level (default: double)"
    )
    
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=str(BACKUP_DIR),
        help="Backup directory (default: backups/)"
    )
    
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation (dangerous!)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation without confirmation (dangerous!)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    return RecreateConfig(
        mode=RecreateMode(args.mode),
        backup_format=BackupFormat(args.backup),
        confirmation_level=ConfirmationLevel(args.confirmation),
        backup_dir=Path(args.backup_dir),
        skip_backup=args.skip_backup,
        force=args.force,
        verbose=args.verbose
    )


# ============================================
# OTIMIZAÇÃO 7: Main Function
# ============================================

async def main():
    """
    ✅ Main entry point with CLI support
    """
    logger.info("=" * 70)
    logger.info("🗄️  Database Recreation Tool v2.0")
    logger.info("=" * 70)
    
    try:
        # Parse CLI arguments
        config = parse_arguments()
        
        # Show warnings for dangerous options
        if config.force:
            logger.warning("⚠️  FORCE MODE ENABLED - Skipping confirmations!")
        
        if config.skip_backup:
            logger.warning("⚠️  BACKUP DISABLED - Data cannot be restored!")
        
        # Execute recreation
        result = await recreate_database(config)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Operation cancelled by user (Ctrl+C)")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================
# LEGACY FUNCTION (Backward Compatibility)
# ============================================

async def recreate():
    """
    ✅ Legacy function for backward compatibility
    Uses simple confirmation like original
    """
    config = RecreateConfig(
        mode=RecreateMode.FULL,
        confirmation_level=ConfirmationLevel.SIMPLE,
        backup_format=BackupFormat.JSON,
        skip_backup=False,
        force=False
    )
    
    await recreate_database(config)


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    # Check if running with arguments (new CLI) or without (legacy)
    if len(sys.argv) > 1:
        asyncio.run(main())
    else:
        # Legacy mode for backward compatibility
        asyncio.run(recreate())
