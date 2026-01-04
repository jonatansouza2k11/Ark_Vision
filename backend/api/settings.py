"""
============================================================================
backend/api/settings.py - COMPLETE v3.0
System Settings Routes (Enhanced Unified + YOLO Config)
============================================================================
✨ Features v3.0:
- Settings CRUD genérico
- Configuração YOLO completa (compatível com Flask)
- Configuração de Email
- Configuração de API
- Reset para defaults
- Categories grouping
- Validation framework
- Export/Import (JSON/YAML)
- Settings comparison
- Bulk operations
- Audit logging

Endpoints v2.0 (12 endpoints):
- GET    /settings              - Lista todas configurações
- GET    /settings/list         - Lista detalhada
- GET    /settings/{key}        - Obtém configuração específica
- PUT    /settings              - Atualiza múltiplas
- PUT    /settings/{key}        - Atualiza específica
- GET    /settings/yolo/config  - Config YOLO completa
- PUT    /settings/yolo/config  - Atualiza config YOLO
- GET    /settings/email/config - Config de email
- PUT    /settings/email/config - Atualiza email
- GET    /settings/api/config   - Config de API
- PUT    /settings/api/config   - Atualiza API
- POST   /settings/reset        - Reset para defaults

NEW v3.0 (6 endpoints):
- GET    /settings/categories   - Lista por categorias
- POST   /settings/validate     - Valida configurações
- GET    /settings/compare      - Compara atual vs default
- GET    /settings/export       - Exporta settings
- POST   /settings/import       - Importa settings
- POST   /settings/bulk/update  - Update em lote

✅ v2.0 compatibility: 100%
============================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================

# ✅ FIX: Path para imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, Request, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import logging
import json
import io

from dependencies import get_current_admin_user, get_current_active_user
import database

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class SettingCategory(str, Enum):
    """Categories for settings organization"""
    YOLO = "yolo"
    EMAIL = "email"
    API = "api"
    SYSTEM = "system"
    CAMERA = "camera"
    ALERTS = "alerts"
    TRACKING = "tracking"
    OTHER = "other"


class ExportFormat(str, Enum):
    """Export formats"""
    JSON = "json"
    YAML = "yaml"


class ValidationLevel(str, Enum):
    """Validation levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Settings categories mapping
SETTINGS_CATEGORIES = {
    SettingCategory.YOLO: [
        "conf_thresh", "target_width", "frame_step", "model_path", "tracker"
    ],
    SettingCategory.CAMERA: [
        "source", "cam_width", "cam_height", "cam_fps", "buffer_seconds"
    ],
    SettingCategory.EMAIL: [
        "email_smtp_server", "email_smtp_port", "email_user", 
        "email_from", "email_password"
    ],
    SettingCategory.API: [
        "api_integration_enabled", "api_base_url", "api_username", "api_password"
    ],
    SettingCategory.ALERTS: [
        "max_out_time", "email_cooldown", "zone_empty_timeout", 
        "zone_full_timeout", "zone_full_threshold"
    ],
    SettingCategory.TRACKING: ["safe_zone"],
}


# ============================================================================
# PYDANTIC MODELS v2.0 (Compatible)
# ============================================================================

class SettingResponse(BaseModel):
    """Schema para resposta de setting único"""
    key: str
    value: Any
    description: Optional[str] = None


class SettingsListResponse(BaseModel):
    """Schema para lista de settings"""
    settings: List[SettingResponse]
    total: int


class SettingUpdate(BaseModel):
    """Schema para atualizar setting único"""
    value: Any = Field(..., description="Novo valor do setting")


class SettingsUpdate(BaseModel):
    """Model para atualizar múltiplas configurações"""
    settings: Dict[str, Any]


class YOLOConfigResponse(BaseModel):
    """Schema para configuração YOLO completa"""
    conf_thresh: float
    target_width: int
    frame_step: int
    max_out_time: float
    email_cooldown: float
    safe_zone: Any
    source: str
    cam_width: int
    cam_height: int
    cam_fps: int
    model_path: str
    tracker: str
    zone_empty_timeout: float
    zone_full_timeout: float
    zone_full_threshold: int
    buffer_seconds: float = 2.0


class YOLOConfigUpdate(BaseModel):
    """Schema para atualizar configs YOLO"""
    conf_thresh: Optional[float] = None
    target_width: Optional[int] = None
    frame_step: Optional[int] = None
    max_out_time: Optional[float] = None
    email_cooldown: Optional[float] = None
    safe_zone: Optional[Any] = None
    source: Optional[str] = None
    cam_width: Optional[int] = None
    cam_height: Optional[int] = None
    cam_fps: Optional[int] = None
    model_path: Optional[str] = None
    tracker: Optional[str] = None
    zone_empty_timeout: Optional[float] = None
    zone_full_timeout: Optional[float] = None
    zone_full_threshold: Optional[int] = None


class EmailConfigResponse(BaseModel):
    """Schema para configuração de email"""
    email_smtp_server: str
    email_smtp_port: int
    email_user: str
    email_from: str


class EmailConfigUpdate(BaseModel):
    """Schema para atualizar email"""
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = None
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None


class APIConfigResponse(BaseModel):
    """Schema para configuração da API"""
    api_integration_enabled: bool
    api_base_url: str
    api_username: str


class APIConfigUpdate(BaseModel):
    """Schema para atualizar API"""
    api_integration_enabled: Optional[bool] = None
    api_base_url: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None


# ============================================================================
# PYDANTIC MODELS v3.0 (NEW)
# ============================================================================

class SettingValidation(BaseModel):
    """Validation result"""
    key: str
    valid: bool
    level: ValidationLevel
    message: str


class SettingsValidationResponse(BaseModel):
    """Validation response"""
    valid: bool
    errors: List[SettingValidation]
    warnings: List[SettingValidation]
    infos: List[SettingValidation]


class SettingComparison(BaseModel):
    """Setting comparison"""
    key: str
    current_value: Any
    default_value: Any
    is_modified: bool
    category: Optional[str] = None


class SettingsComparisonResponse(BaseModel):
    """Settings comparison response"""
    modified_count: int
    total_count: int
    comparisons: List[SettingComparison]


class SettingsCategoryResponse(BaseModel):
    """Settings grouped by category"""
    category: str
    settings: List[SettingResponse]
    count: int


class BulkUpdateOperation(BaseModel):
    """Bulk update operation"""
    key: str
    value: Any
    category: Optional[str] = None


class BulkUpdateRequest(BaseModel):
    """Bulk update request"""
    operations: List[BulkUpdateOperation]
    validate_first: bool = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def categorize_setting(key: str) -> SettingCategory:
    """Determine category for a setting key"""
    for category, keys in SETTINGS_CATEGORIES.items():
        if key in keys:
            return category
    return SettingCategory.OTHER


async def validate_setting_value(key: str, value: Any) -> List[SettingValidation]:
    """
    Validate a setting value
    Returns list of validation issues (errors, warnings, infos)
    """
    validations = []
    
    # YOLO validations
    if key == "conf_thresh":
        try:
            val = float(value)
            if not (0.0 <= val <= 1.0):
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.ERROR,
                    message="Confidence threshold must be between 0.0 and 1.0"
                ))
        except ValueError:
            validations.append(SettingValidation(
                key=key, valid=False, level=ValidationLevel.ERROR,
                message="Must be a valid number"
            ))
    
    elif key in ["target_width", "cam_width", "cam_height"]:
        try:
            val = int(value)
            if val <= 0:
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.ERROR,
                    message=f"{key} must be positive"
                ))
            elif val > 4096:
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.WARNING,
                    message=f"{key} is very large, may cause performance issues"
                ))
        except ValueError:
            validations.append(SettingValidation(
                key=key, valid=False, level=ValidationLevel.ERROR,
                message="Must be a valid integer"
            ))
    
    elif key == "email_smtp_port":
        try:
            val = int(value)
            if not (1 <= val <= 65535):
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.ERROR,
                    message="SMTP port must be between 1 and 65535"
                ))
        except ValueError:
            validations.append(SettingValidation(
                key=key, valid=False, level=ValidationLevel.ERROR,
                message="Must be a valid port number"
            ))
    
    elif key == "cam_fps":
        try:
            val = int(value)
            if val < 1:
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.ERROR,
                    message="FPS must be at least 1"
                ))
            elif val > 60:
                validations.append(SettingValidation(
                    key=key, valid=False, level=ValidationLevel.WARNING,
                    message="FPS > 60 may cause performance issues"
                ))
        except ValueError:
            validations.append(SettingValidation(
                key=key, valid=False, level=ValidationLevel.ERROR,
                message="Must be a valid integer"
            ))
    
    # If no validations, it's valid
    if not validations:
        validations.append(SettingValidation(
            key=key, valid=True, level=ValidationLevel.INFO,
            message="Valid"
        ))
    
    return validations


async def get_default_settings() -> Dict[str, Any]:
    """Get default settings from config"""
    from config import settings as app_config
    
    return {
        # YOLO
        "conf_thresh": str(app_config.YOLO_CONF_THRESHOLD),
        "target_width": str(app_config.YOLO_TARGET_WIDTH),
        "frame_step": str(app_config.YOLO_FRAME_STEP),
        "max_out_time": str(app_config.MAX_OUT_TIME),
        "email_cooldown": str(app_config.EMAIL_COOLDOWN),
        "source": str(app_config.VIDEO_SOURCE),
        "cam_width": str(app_config.CAM_WIDTH),
        "cam_height": str(app_config.CAM_HEIGHT),
        "cam_fps": str(app_config.CAM_FPS),
        "model_path": app_config.YOLO_MODEL_PATH,
        "tracker": app_config.TRACKER,
        "zone_empty_timeout": str(app_config.ZONE_EMPTY_TIMEOUT),
        "zone_full_timeout": str(app_config.ZONE_FULL_TIMEOUT),
        "zone_full_threshold": str(app_config.ZONE_FULL_THRESHOLD),
        "buffer_seconds": str(app_config.BUFFER_DURATION_SECONDS),
        "safe_zone": "[]",
        
        # Email
        "email_smtp_server": app_config.SMTP_SERVER,
        "email_smtp_port": str(app_config.SMTP_PORT),
        "email_user": app_config.EMAIL_SENDER,
        "email_from": app_config.EMAIL_SENDER,
        
        # API
        "api_integration_enabled": str(app_config.API_INTEGRATION_ENABLED).lower(),
        "api_base_url": app_config.API_BASE_URL,
        "api_username": app_config.API_USERNAME,
    }


# ============================================================================
# v2.0 ENDPOINTS - SETTINGS CRUD (Compatible)
# ============================================================================

@router.get("", summary="📋 Lista todas configurações")
async def get_all_settings(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Lista todas as configurações do sistema
    
    **Requer:** Token JWT válido
    """
    try:
        settings_keys = [
            # YOLO
            "conf_thresh", "target_width", "frame_step", "max_out_time",
            "email_cooldown", "safe_zone", "source", "cam_width", "cam_height",
            "cam_fps", "model_path", "tracker", "zone_empty_timeout",
            "zone_full_timeout", "zone_full_threshold", "buffer_seconds",
            
            # Email
            "email_smtp_server", "email_smtp_port", "email_user",
            "email_password", "email_from",
            
            # API
            "api_integration_enabled", "api_base_url", "api_username",
            "api_password",
        ]
        
        settings = {}
        for key in settings_keys:
            value = await database.get_setting(key)
            if value is not None:
                settings[key] = value
        
        logger.info(f"📋 Listando {len(settings)} settings para {current_user.get('username')}")
        
        return settings
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar settings: {str(e)}"
        )


@router.get("/list", response_model=SettingsListResponse, summary="📋 Lista detalhada")
async def list_all_settings_detailed(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Lista todos os settings com formato detalhado
    
    **Requer:** Token JWT válido
    """
    try:
        all_settings_dict = await database.get_all_settings()
        
        settings_list = [
            SettingResponse(key=key, value=value, description=None)
            for key, value in all_settings_dict.items()
        ]
        
        logger.info(f"📋 Listando {len(settings_list)} settings (detalhado)")
        
        return SettingsListResponse(
            settings=settings_list,
            total=len(settings_list)
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar settings: {str(e)}"
        )


@router.get("/{key}", summary="🔍 Obtém configuração específica")
async def get_setting(
    key: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Obtém uma configuração específica
    
    **Requer:** Token JWT válido
    """
    try:
        value = await database.get_setting(key)
        
        if value is None:
            return {"key": key, "value": None, "exists": False}
        
        logger.info(f"🔍 Setting '{key}' obtido")
        
        return {"key": key, "value": value, "exists": True}
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter setting '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter setting: {str(e)}"
        )


@router.put("", summary="✏️ Atualiza múltiplas configurações")
async def update_settings(
    settings_data: SettingsUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Atualiza múltiplas configurações (apenas admin)
    
    **Requer:** Token JWT de admin
    """
    try:
        updated_count = 0
        
        for key, value in settings_data.settings.items():
            await database.set_setting(
                key=key,
                value=value,
                updated_by=current_user["username"]
            )
            updated_count += 1
        
        await database.log_system_action(
            action="settings_updated",
            username=current_user["username"],
            reason=f"Updated {updated_count} settings",
            ip_address=request.client.host if request.client else None,
            context={"updated_keys": list(settings_data.settings.keys())}
        )
        
        logger.info(f"✅ Admin updated {updated_count} settings")
        
        return {
            "message": "Settings updated successfully",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar settings: {str(e)}"
        )


@router.put("/{key}", summary="✏️ Atualiza configuração específica")
async def update_single_setting(
    key: str,
    setting_update: SettingUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Atualiza uma configuração específica (apenas admin)
    
    **Requer:** Token JWT de admin
    """
    try:
        if isinstance(setting_update.value, (dict, list)):
            value_str = json.dumps(setting_update.value)
        else:
            value_str = str(setting_update.value)
        
        await database.set_setting(
            key=key,
            value=value_str,
            updated_by=current_user["username"]
        )
        
        await database.log_system_action(
            action="setting_updated",
            username=current_user["username"],
            reason=f"Updated setting: {key}",
            ip_address=request.client.host if request.client else None,
            context={"key": key, "value": str(setting_update.value)}
        )
        
        logger.info(f"✅ Admin updated setting: {key}")
        
        return {
            "message": "Setting updated successfully",
            "key": key,
            "value": setting_update.value
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar setting '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar setting: {str(e)}"
        )


# ============================================================================
# v2.0 ENDPOINTS - YOLO CONFIG (Compatible)
# ============================================================================

@router.get("/yolo/config", response_model=YOLOConfigResponse, summary="🎯 Config YOLO")
async def get_yolo_config(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Obtém configuração completa do YOLO
    
    **Compatível com Flask settings.html**
    **Requer:** Token JWT válido
    """
    try:
        from config import settings as app_config
        
        config = {
            "conf_thresh": float(await database.get_setting("conf_thresh", str(app_config.YOLO_CONF_THRESHOLD))),
            "target_width": int(await database.get_setting("target_width", str(app_config.YOLO_TARGET_WIDTH))),
            "frame_step": int(await database.get_setting("frame_step", str(app_config.YOLO_FRAME_STEP))),
            "max_out_time": float(await database.get_setting("max_out_time", str(app_config.MAX_OUT_TIME))),
            "email_cooldown": float(await database.get_setting("email_cooldown", str(app_config.EMAIL_COOLDOWN))),
            "source": await database.get_setting("source", str(app_config.VIDEO_SOURCE)),
            "cam_width": int(await database.get_setting("cam_width", str(app_config.CAM_WIDTH))),
            "cam_height": int(await database.get_setting("cam_height", str(app_config.CAM_HEIGHT))),
            "cam_fps": int(await database.get_setting("cam_fps", str(app_config.CAM_FPS))),
            "model_path": await database.get_setting("model_path", app_config.YOLO_MODEL_PATH),
            "tracker": await database.get_setting("tracker", app_config.TRACKER),
            "zone_empty_timeout": float(await database.get_setting("zone_empty_timeout", str(app_config.ZONE_EMPTY_TIMEOUT))),
            "zone_full_timeout": float(await database.get_setting("zone_full_timeout", str(app_config.ZONE_FULL_TIMEOUT))),
            "zone_full_threshold": int(await database.get_setting("zone_full_threshold", str(app_config.ZONE_FULL_THRESHOLD))),
            "buffer_seconds": float(await database.get_setting("buffer_seconds", "2.0")),
        }
        
        # Safe zone (JSON)
        raw_safe_zone = await database.get_setting("safe_zone", "[]")
        try:
            config["safe_zone"] = json.loads(raw_safe_zone) if isinstance(raw_safe_zone, str) else raw_safe_zone
        except:
            config["safe_zone"] = []
        
        logger.info(f"🎯 Config YOLO obtida")
        
        return YOLOConfigResponse(**config)
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter config YOLO: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter configuração YOLO: {str(e)}"
        )


@router.put("/yolo/config", response_model=YOLOConfigResponse, summary="✏️ Atualiza YOLO")
async def update_yolo_config(
    update: YOLOConfigUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Atualiza configuração do YOLO
    
    **Compatível com Flask settings.html**
    **Requer:** Token JWT de admin
    """
    try:
        updated_fields = []
        
        field_mapping = {
            "conf_thresh": ("conf_thresh", str),
            "target_width": ("target_width", str),
            "frame_step": ("frame_step", str),
            "max_out_time": ("max_out_time", str),
            "email_cooldown": ("email_cooldown", str),
            "source": ("source", str),
            "cam_width": ("cam_width", str),
            "cam_height": ("cam_height", str),
            "cam_fps": ("cam_fps", str),
            "model_path": ("model_path", str),
            "tracker": ("tracker", str),
            "zone_empty_timeout": ("zone_empty_timeout", str),
            "zone_full_timeout": ("zone_full_timeout", str),
            "zone_full_threshold": ("zone_full_threshold", str),
        }
        
        for field, (setting_key, converter) in field_mapping.items():
            value = getattr(update, field, None)
            if value is not None:
                await database.set_setting(setting_key, converter(value), updated_by=current_user["username"])
                updated_fields.append(setting_key)
        
        # Safe zone (JSON)
        if update.safe_zone is not None:
            safe_zone_json = json.dumps(update.safe_zone) if isinstance(update.safe_zone, (list, dict)) else str(update.safe_zone)
            await database.set_setting("safe_zone", safe_zone_json, updated_by=current_user["username"])
            updated_fields.append("safe_zone")
        
        await database.log_system_action(
            action="yolo_config_updated",
            username=current_user["username"],
            reason=f"Updated YOLO config: {', '.join(updated_fields)}",
            ip_address=request.client.host if request.client else None,
            context={"updated_fields": updated_fields}
        )
        
        logger.info(f"✏️ Config YOLO atualizada: {', '.join(updated_fields)}")
        
        return await get_yolo_config(current_user)
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar config YOLO: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configuração YOLO: {str(e)}"
        )


# ============================================================================
# v2.0 ENDPOINTS - EMAIL CONFIG (Compatible)
# ============================================================================

@router.get("/email/config", response_model=EmailConfigResponse, summary="📧 Config Email")
async def get_email_config(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Obtém configuração de email
    
    **Requer:** Token JWT válido
    """
    try:
        from config import settings as app_config
        
        config = EmailConfigResponse(
            email_smtp_server=await database.get_setting("email_smtp_server", app_config.SMTP_SERVER),
            email_smtp_port=int(await database.get_setting("email_smtp_port", str(app_config.SMTP_PORT))),
            email_user=await database.get_setting("email_user", app_config.EMAIL_SENDER),
            email_from=await database.get_setting("email_from", app_config.EMAIL_SENDER),
        )
        
        logger.info(f"📧 Config de email obtida")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter config de email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter configuração de email: {str(e)}"
        )


@router.put("/email/config", response_model=EmailConfigResponse, summary="✏️ Atualiza Email")
async def update_email_config(
    update: EmailConfigUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Atualiza configuração de email
    
    **Requer:** Token JWT de admin
    """
    try:
        updated_fields = []
        
        if update.email_smtp_server is not None:
            await database.set_setting("email_smtp_server", update.email_smtp_server, updated_by=current_user["username"])
            updated_fields.append("smtp_server")
        
        if update.email_smtp_port is not None:
            await database.set_setting("email_smtp_port", str(update.email_smtp_port), updated_by=current_user["username"])
            updated_fields.append("smtp_port")
        
        if update.email_user is not None:
            await database.set_setting("email_user", update.email_user, updated_by=current_user["username"])
            updated_fields.append("email_user")
        
        if update.email_password is not None:
            await database.set_setting("email_password", update.email_password, updated_by=current_user["username"])
            updated_fields.append("email_password")
        
        if update.email_from is not None:
            await database.set_setting("email_from", update.email_from, updated_by=current_user["username"])
            updated_fields.append("email_from")
        
        await database.log_system_action(
            action="email_config_updated",
            username=current_user["username"],
            reason=f"Updated email config: {', '.join(updated_fields)}",
            ip_address=request.client.host if request.client else None,
            context={"updated_fields": updated_fields}
        )
        
        logger.info(f"✏️ Config de email atualizada: {', '.join(updated_fields)}")
        
        return await get_email_config(current_user)
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar config de email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configuração de email: {str(e)}"
        )


# ============================================================================
# v2.0 ENDPOINTS - API CONFIG (Compatible)
# ============================================================================

@router.get("/api/config", response_model=APIConfigResponse, summary="🔌 Config API")
async def get_api_config(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ✅ v2.0: Obtém configuração da integração API
    
    **Requer:** Token JWT válido
    """
    try:
        config = APIConfigResponse(
            api_integration_enabled=(await database.get_setting("api_integration_enabled", "true")).lower() == "true",
            api_base_url=await database.get_setting("api_base_url", "http://localhost:8000"),
            api_username=await database.get_setting("api_username", "admin"),
        )
        
        logger.info(f"🔌 Config de API obtida")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter config de API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter configuração de API: {str(e)}"
        )


@router.put("/api/config", response_model=APIConfigResponse, summary="✏️ Atualiza API")
async def update_api_config(
    update: APIConfigUpdate,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Atualiza configuração da integração API
    
    **Requer:** Token JWT de admin
    """
    try:
        updated_fields = []
        
        if update.api_integration_enabled is not None:
            await database.set_setting("api_integration_enabled", "true" if update.api_integration_enabled else "false", updated_by=current_user["username"])
            updated_fields.append("enabled")
        
        if update.api_base_url is not None:
            await database.set_setting("api_base_url", update.api_base_url, updated_by=current_user["username"])
            updated_fields.append("base_url")
        
        if update.api_username is not None:
            await database.set_setting("api_username", update.api_username, updated_by=current_user["username"])
            updated_fields.append("username")
        
        if update.api_password is not None:
            await database.set_setting("api_password", update.api_password, updated_by=current_user["username"])
            updated_fields.append("password")
        
        await database.log_system_action(
            action="api_config_updated",
            username=current_user["username"],
            reason=f"Updated API config: {', '.join(updated_fields)}",
            ip_address=request.client.host if request.client else None,
            context={"updated_fields": updated_fields}
        )
        
        logger.info(f"✏️ Config de API atualizada: {', '.join(updated_fields)}")
        
        return await get_api_config(current_user)
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar config de API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configuração de API: {str(e)}"
        )


# ============================================================================
# v2.0 ENDPOINTS - RESET (Compatible)
# ============================================================================

@router.post("/reset", summary="🔄 Reset para defaults")
async def reset_settings(
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ✅ v2.0: Restaura configurações para valores padrão
    
    **Requer:** Token JWT de admin
    """
    try:
        default_settings = await get_default_settings()
        
        for key, value in default_settings.items():
            await database.set_setting(
                key=key,
                value=value,
                updated_by=current_user["username"]
            )
        
        await database.log_system_action(
            action="settings_reset",
            username=current_user["username"],
            reason="Reset all settings to default",
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"✅ Admin reset settings to default")
        
        return {
            "message": "Settings reset to default successfully",
            "reset_count": len(default_settings)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao resetar settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao resetar settings: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - CATEGORIES (NEW)
# ============================================================================

@router.get("/categories", summary="📂 Lista por categorias")
async def get_settings_by_category(
    category: Optional[SettingCategory] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    ➕ NEW v3.0: Lista settings agrupados por categoria
    """
    try:
        all_settings = await database.get_all_settings()
        
        if category:
            # Filter by specific category
            category_keys = SETTINGS_CATEGORIES.get(category, [])
            settings_list = [
                SettingResponse(key=k, value=v)
                for k, v in all_settings.items()
                if k in category_keys
            ]
            
            return SettingsCategoryResponse(
                category=category.value,
                settings=settings_list,
                count=len(settings_list)
            )
        
        else:
            # Group all by categories
            result = {}
            for cat, keys in SETTINGS_CATEGORIES.items():
                category_settings = [
                    SettingResponse(key=k, value=all_settings.get(k))
                    for k in keys
                    if k in all_settings
                ]
                
                result[cat.value] = SettingsCategoryResponse(
                    category=cat.value,
                    settings=category_settings,
                    count=len(category_settings)
                )
            
            return result
    
    except Exception as e:
        logger.error(f"❌ Error getting settings by category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter settings por categoria: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - VALIDATION (NEW)
# ============================================================================

@router.post("/validate", response_model=SettingsValidationResponse, summary="✔️ Valida configurações")
async def validate_settings(
    settings_data: Dict[str, Any],
    current_user: dict = Depends(get_current_active_user)
):
    """
    ➕ NEW v3.0: Valida múltiplas configurações antes de salvar
    """
    try:
        errors = []
        warnings = []
        infos = []
        
        for key, value in settings_data.items():
            validations = await validate_setting_value(key, value)
            
            for validation in validations:
                if validation.level == ValidationLevel.ERROR:
                    errors.append(validation)
                elif validation.level == ValidationLevel.WARNING:
                    warnings.append(validation)
                else:
                    infos.append(validation)
        
        is_valid = len(errors) == 0
        
        return SettingsValidationResponse(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            infos=infos
        )
    
    except Exception as e:
        logger.error(f"❌ Error validating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao validar settings: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - COMPARISON (NEW)
# ============================================================================

@router.get("/compare", response_model=SettingsComparisonResponse, summary="🔍 Compara atual vs default")
async def compare_settings(
    current_user: dict = Depends(get_current_active_user)
):
    """
    ➕ NEW v3.0: Compara settings atuais com defaults
    """
    try:
        current_settings = await database.get_all_settings()
        default_settings = await get_default_settings()
        
        comparisons = []
        modified_count = 0
        
        for key, default_value in default_settings.items():
            current_value = current_settings.get(key, default_value)
            is_modified = str(current_value) != str(default_value)
            
            if is_modified:
                modified_count += 1
            
            comparisons.append(SettingComparison(
                key=key,
                current_value=current_value,
                default_value=default_value,
                is_modified=is_modified,
                category=categorize_setting(key).value
            ))
        
        return SettingsComparisonResponse(
            modified_count=modified_count,
            total_count=len(comparisons),
            comparisons=comparisons
        )
    
    except Exception as e:
        logger.error(f"❌ Error comparing settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao comparar settings: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - EXPORT (NEW)
# ============================================================================

@router.get("/export", summary="📤 Exporta settings")
async def export_settings(
    format: ExportFormat = Query(default=ExportFormat.JSON),
    category: Optional[SettingCategory] = Query(None),
    current_user: dict = Depends(get_current_active_user)
):
    """
    ➕ NEW v3.0: Exporta settings em JSON ou YAML
    """
    try:
        all_settings = await database.get_all_settings()
        
        # Filter by category if specified
        if category:
            category_keys = SETTINGS_CATEGORIES.get(category, [])
            all_settings = {k: v for k, v in all_settings.items() if k in category_keys}
        
        # Add metadata
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "exported_by": current_user.get("username"),
            "format_version": "3.0",
            "category": category.value if category else "all",
            "settings": all_settings
        }
        
        if format == ExportFormat.JSON:
            return JSONResponse(content=export_data)
        
        else:  # YAML
            try:
                import yaml
                yaml_str = yaml.dump(export_data, default_flow_style=False, allow_unicode=True)
            except ImportError:
                # Fallback to JSON if yaml not available
                logger.warning("YAML library not available, returning JSON")
                return JSONResponse(content=export_data)
            
            return StreamingResponse(
                iter([yaml_str]),
                media_type="text/yaml",
                headers={
                    "Content-Disposition": f"attachment; filename=settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
                }
            )
    
    except Exception as e:
        logger.error(f"❌ Error exporting settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao exportar settings: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - IMPORT (NEW)
# ============================================================================

@router.post("/import", summary="📥 Importa settings")
async def import_settings(
    file: UploadFile = File(...),
    validate_first: bool = Query(default=True),
    request: Request = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ➕ NEW v3.0: Importa settings de arquivo JSON ou YAML
    """
    try:
        content = await file.read()
        
        # Parse based on file extension
        if file.filename.endswith('.json'):
            data = json.loads(content)
        elif file.filename.endswith(('.yaml', '.yml')):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="YAML library not installed. Use JSON format."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de arquivo não suportado. Use .json ou .yaml"
            )
        
        settings_to_import = data.get('settings', data)
        
        # Validate if requested
        if validate_first:
            validation = await validate_settings(settings_to_import, current_user)
            if not validation.valid:
                return {
                    "imported": False,
                    "validation": validation,
                    "message": "Validation failed. Settings not imported."
                }
        
        # Import settings
        imported_count = 0
        for key, value in settings_to_import.items():
            await database.set_setting(key, str(value), updated_by=current_user["username"])
            imported_count += 1
        
        # Log
        await database.log_system_action(
            action="settings_imported",
            username=current_user["username"],
            reason=f"Imported {imported_count} settings from {file.filename}",
            ip_address=request.client.host if request else None
        )
        
        logger.info(f"✅ Imported {imported_count} settings from {file.filename}")
        
        return {
            "imported": True,
            "imported_count": imported_count,
            "filename": file.filename
        }
    
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    except Exception as e:
        logger.error(f"❌ Error importing settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao importar settings: {str(e)}"
        )


# ============================================================================
# v3.0 ENDPOINTS - BULK UPDATE (NEW)
# ============================================================================

@router.post("/bulk/update", summary="🔄 Update em lote")
async def bulk_update_settings(
    bulk_request: BulkUpdateRequest,
    request: Request,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    ➕ NEW v3.0: Atualiza múltiplos settings com validação
    """
    try:
        # Validate first if requested
        if bulk_request.validate_first:
            settings_dict = {op.key: op.value for op in bulk_request.operations}
            validation = await validate_settings(settings_dict, current_user)
            
            if not validation.valid:
                return {
                    "updated": False,
                    "validation": validation,
                    "message": "Validation failed. Settings not updated."
                }
        
        # Update all
        updated_count = 0
        for operation in bulk_request.operations:
            value_str = json.dumps(operation.value) if isinstance(operation.value, (dict, list)) else str(operation.value)
            await database.set_setting(operation.key, value_str, updated_by=current_user["username"])
            updated_count += 1
        
        # Log
        await database.log_system_action(
            action="settings_bulk_updated",
            username=current_user["username"],
            reason=f"Bulk updated {updated_count} settings",
            ip_address=request.client.host if request else None
        )
        
        logger.info(f"✅ Bulk updated {updated_count} settings")
        
        return {
            "updated": True,
            "updated_count": updated_count
        }
    
    except Exception as e:
        logger.error(f"❌ Error bulk updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar settings em lote: {str(e)}"
        )


# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("⚙️  SETTINGS API ROUTER v3.0 - COMPLETE")
    print("=" * 80)
    
    print("\n✅ v2.0 ENDPOINTS (12 endpoints - 100% Compatible):")
    print("\n📋 CRUD Genérico:")
    print("   1. GET    /api/v1/settings              - Lista todas")
    print("   2. GET    /api/v1/settings/list         - Lista detalhada")
    print("   3. GET    /api/v1/settings/{key}        - Obtém específica")
    print("   4. PUT    /api/v1/settings              - Atualiza múltiplas (admin)")
    print("   5. PUT    /api/v1/settings/{key}        - Atualiza específica (admin)")
    
    print("\n🎯 YOLO Config:")
    print("   6. GET    /api/v1/settings/yolo/config  - Config YOLO completa")
    print("   7. PUT    /api/v1/settings/yolo/config  - Atualiza YOLO (admin)")
    
    print("\n📧 Email Config:")
    print("   8. GET    /api/v1/settings/email/config - Config email")
    print("   9. PUT    /api/v1/settings/email/config - Atualiza email (admin)")
    
    print("\n🔌 API Config:")
    print("   10. GET   /api/v1/settings/api/config   - Config API")
    print("   11. PUT   /api/v1/settings/api/config   - Atualiza API (admin)")
    
    print("\n🔄 Utilidades:")
    print("   12. POST  /api/v1/settings/reset        - Reset defaults (admin)")
    
    print("\n➕ NEW v3.0 ENDPOINTS (6 endpoints):")
    print("   13. GET   /api/v1/settings/categories   - Lista por categorias")
    print("   14. POST  /api/v1/settings/validate     - Valida settings")
    print("   15. GET   /api/v1/settings/compare      - Compara atual vs default")
    print("   16. GET   /api/v1/settings/export       - Exporta (JSON/YAML)")
    print("   17. POST  /api/v1/settings/import       - Importa arquivo")
    print("   18. POST  /api/v1/settings/bulk/update  - Update em lote")
    
    print("\n🚀 v3.0 FEATURES:")
    print("   • Settings categories grouping (YOLO, Email, API, Camera, etc)")
    print("   • Validation framework (errors, warnings, infos)")
    print("   • Export/Import (JSON/YAML)")
    print("   • Comparison (current vs default)")
    print("   • Bulk operations with validation")
    print("   • Enhanced audit logging")
    print("   • Flask compatibility maintained")
    
    print("\n" + "=" * 80)
    print("✅ Settings API v3.0 COMPLETE and READY!")
    print("✅ Total endpoints: 18 (12 v2.0 + 6 v3.0)")
    print("✅ v2.0 compatibility: 100%")
    print("✅ Flask settings.html: Compatible")
    print("=" * 80)
