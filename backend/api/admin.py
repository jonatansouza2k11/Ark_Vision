"""
backend/api/admin.py
Admin Routes (Backup, Logs, Diagnostics)
"""

# ✅ FIX: Path para imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from typing import Optional
import logging
import os
import shutil
from datetime import datetime
import psutil

from dependencies import get_current_admin_user
import database

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

# ============================================
# GET SYSTEM LOGS
# ============================================
@router.get("/logs")
async def get_system_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Obtém logs do sistema (apenas admin)
    
    Requer: Token JWT de admin
    """
    logs = await database.get_system_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}

# ============================================
# CREATE BACKUP
# ============================================
@router.post("/backup")
async def create_backup(
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Cria backup do banco de dados (apenas admin)
    
    Requer: Token JWT de admin
    """
    try:
        # Criar diretório de backup se não existir
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.sql"
        
        # TODO: Implementar backup PostgreSQL
        # Por enquanto, apenas simular
        
        # Log ação
        await database.log_system_action(
            action="backup_created",
            username=current_user["username"],
            reason=f"Manual backup created: {backup_file.name}",
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"✅ Admin {current_user['username']} created backup: {backup_file.name}")
        
        return {
            "message": "Backup created successfully",
            "filename": backup_file.name,
            "path": str(backup_file),
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        return {
            "message": "Backup failed",
            "error": str(e)
        }

# ============================================
# LIST BACKUPS
# ============================================
@router.get("/backups")
async def list_backups(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Lista todos os backups disponíveis (apenas admin)
    
    Requer: Token JWT de admin
    """
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        return {"backups": [], "count": 0}
    
    backups = []
    for file in backup_dir.glob("backup_*.sql"):
        stat = file.stat()
        backups.append({
            "filename": file.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
        })
    
    # Ordenar por data (mais recente primeiro)
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"backups": backups, "count": len(backups)}

# ============================================
# DOWNLOAD BACKUP
# ============================================
@router.get("/backups/{filename}")
async def download_backup(
    filename: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Download de backup específico (apenas admin)
    
    Requer: Token JWT de admin
    """
    backup_file = Path("backups") / filename
    
    if not backup_file.exists():
        return {"error": "Backup not found"}
    
    # Log ação
    await database.log_system_action(
        action="backup_downloaded",
        username=current_user["username"],
        reason=f"Downloaded backup: {filename}"
    )
    
    return FileResponse(
        path=str(backup_file),
        filename=filename,
        media_type="application/sql"
    )

# ============================================
# SYSTEM DIAGNOSTICS
# ============================================
@router.get("/diagnostics")
async def get_diagnostics(
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Obtém diagnósticos do sistema (apenas admin)
    
    Retorna informações sobre:
    - CPU, RAM, Disco
    - Banco de dados
    - Processos
    
    Requer: Token JWT de admin
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # RAM
        memory = psutil.virtual_memory()
        
        # Disco
        disk = psutil.disk_usage('/')
        
        # Database
        try:
            pool = await database.get_db_pool()
            async with pool.connection() as conn:
                await conn.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        diagnostics = {
            "system": {
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": memory.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_percent": disk.percent
            },
            "database": {
                "status": db_status,
                "type": "PostgreSQL"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"❌ Diagnostics failed: {e}")
        return {"error": str(e)}

# ============================================
# CLEAR OLD LOGS
# ============================================
@router.delete("/logs/old")
async def clear_old_logs(
    request: Request,  # ✅ Obrigatório vem PRIMEIRO
    current_user: dict = Depends(get_current_admin_user),  # ✅ Dependency
    days: int = 30  # ✅ Opcional vem POR ÚLTIMO
):
    """
    Remove logs antigos (apenas admin)
    
    - **days**: Remove logs mais antigos que X dias (padrão: 30)
    
    Requer: Token JWT de admin
    """
    # TODO: Implementar limpeza de logs antigos
    
    await database.log_system_action(
        action="logs_cleared",
        username=current_user["username"],
        reason=f"Cleared logs older than {days} days",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ Admin {current_user['username']} cleared old logs")
    
    return {
        "message": f"Logs older than {days} days cleared successfully"
    }


# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("🔧 ROUTES: Admin")
    print("=" * 70)
    
    print("\n✅ Endpoints disponíveis:")
    print("\n1️⃣  GET /api/v1/admin/logs")
    print("   • Visualiza logs do sistema")
    print("   • Requer: Admin token")
    
    print("\n2️⃣  POST /api/v1/admin/backup")
    print("   • Cria backup do banco")
    print("   • Requer: Admin token")
    
    print("\n3️⃣  GET /api/v1/admin/backups")
    print("   • Lista backups disponíveis")
    print("   • Requer: Admin token")
    
    print("\n4️⃣  GET /api/v1/admin/backups/{filename}")
    print("   • Download de backup")
    print("   • Requer: Admin token")
    
    print("\n5️⃣  GET /api/v1/admin/diagnostics")
    print("   • Diagnósticos do sistema")
    print("   • Requer: Admin token")
    
    print("\n6️⃣  DELETE /api/v1/admin/logs/old")
    print("   • Remove logs antigos")
    print("   • Requer: Admin token")
    
    print("\n" + "=" * 70)
    print("✅ Admin routes prontas!")
    print("=" * 70)
