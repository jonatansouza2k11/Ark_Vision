"""
backend/api/settings.py
System Settings Routes
"""

# ✅ FIX: Path para imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from dependencies import get_current_admin_user, get_current_active_user
import database

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

# ============================================
# MODELS
# ============================================
class SettingsUpdate(BaseModel):
    """Model para atualizar múltiplas configurações"""
    settings: Dict[str, Any]

class SingleSetting(BaseModel):
    """Model para uma configuração"""
    key: str
    value: Any

# ============================================
# GET ALL SETTINGS (user precisa estar logado)
# ============================================
@router.get("")
async def get_all_settings(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtém todas as configurações do sistema
    
    Requer: Token JWT válido
    """
    # Lista de configurações comuns
    settings_keys = [
        "model_path",
        "confidence_threshold",
        "iou_threshold",
        "tracker_type",
        "max_age",
        "n_init",
        "video_source",
        "enable_email",
        "email_recipients",
        "smtp_server",
        "smtp_port",
        "smtp_username"
    ]
    
    settings = {}
    for key in settings_keys:
        value = await database.get_setting(key)
        if value is not None:
            settings[key] = value
    
    return settings

# ============================================
# GET SINGLE SETTING
# ============================================
@router.get("/{key}")
async def get_setting(
    key: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtém uma configuração específica
    
    Requer: Token JWT válido
    """
    value = await database.get_setting(key)
    
    if value is None:
        return {"key": key, "value": None, "exists": False}
    
    return {"key": key, "value": value, "exists": True}

# ============================================
# UPDATE SETTINGS (admin only)
# ============================================
@router.put("")
async def update_settings(
    settings_data: SettingsUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Atualiza múltiplas configurações (apenas admin)
    
    Requer: Token JWT de admin
    """
    updated_count = 0
    
    for key, value in settings_data.settings.items():
        await database.set_setting(
            key=key,
            value=value,
            updated_by=current_user["username"]
        )
        updated_count += 1
    
    # Log ação
    await database.log_system_action(
        action="settings_updated",
        username=current_user["username"],
        reason=f"Updated {updated_count} settings",
        ip_address=request.client.host if request.client else None,
        context={"updated_keys": list(settings_data.settings.keys())}
    )
    
    logger.info(f"✅ Admin {current_user['username']} updated {updated_count} settings")
    
    return {
        "message": "Settings updated successfully",
        "updated_count": updated_count
    }

# ============================================
# UPDATE SINGLE SETTING (admin only)
# ============================================
@router.put("/{key}")
async def update_single_setting(
    key: str,
    value: Any,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Atualiza uma configuração específica (apenas admin)
    
    Requer: Token JWT de admin
    """
    await database.set_setting(
        key=key,
        value=value,
        updated_by=current_user["username"]
    )
    
    # Log ação
    await database.log_system_action(
        action="setting_updated",
        username=current_user["username"],
        reason=f"Updated setting: {key}",
        ip_address=request.client.host if request.client else None,
        context={"key": key, "value": str(value)}
    )
    
    logger.info(f"✅ Admin {current_user['username']} updated setting: {key}")
    
    return {
        "message": "Setting updated successfully",
        "key": key,
        "value": value
    }

# ============================================
# RESET SETTINGS TO DEFAULT (admin only)
# ============================================
@router.post("/reset")
async def reset_settings(
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Restaura configurações para valores padrão (apenas admin)
    
    Requer: Token JWT de admin
    """
    # Configurações padrão
    default_settings = {
        "model_path": "yolov8n.pt",
        "confidence_threshold": "0.5",
        "iou_threshold": "0.5",
        "tracker_type": "botsort",
        "max_age": "30",
        "n_init": "3",
        "video_source": "0",
        "enable_email": "false",
        "smtp_port": "587"
    }
    
    for key, value in default_settings.items():
        await database.set_setting(
            key=key,
            value=value,
            updated_by=current_user["username"]
        )
    
    # Log ação
    await database.log_system_action(
        action="settings_reset",
        username=current_user["username"],
        reason="Reset all settings to default",
        ip_address=request.client.host if request.client else None
    )
    
    logger.info(f"✅ Admin {current_user['username']} reset settings to default")
    
    return {
        "message": "Settings reset to default successfully",
        "default_settings": default_settings
    }

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("⚙️  ROUTES: Settings")
    print("=" * 70)
    
    print("\n✅ Endpoints disponíveis:")
    print("\n1️⃣  GET /api/v1/settings")
    print("   • Lista todas configurações")
    print("   • Requer: User token")
    
    print("\n2️⃣  GET /api/v1/settings/{key}")
    print("   • Obtém configuração específica")
    print("   • Requer: User token")
    
    print("\n3️⃣  PUT /api/v1/settings")
    print("   • Atualiza múltiplas configurações")
    print("   • Requer: Admin token")
    
    print("\n4️⃣  PUT /api/v1/settings/{key}")
    print("   • Atualiza configuração específica")
    print("   • Requer: Admin token")
    
    print("\n5️⃣  POST /api/v1/settings/reset")
    print("   • Restaura valores padrão")
    print("   • Requer: Admin token")
    
    print("\n" + "=" * 70)
    print("✅ Settings routes prontas!")
    print("=" * 70)
