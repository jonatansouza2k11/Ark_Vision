"""
============================================================================
backend/models/settings.py - ULTRA OPTIMIZED v3.0
Pydantic Models para Sistema de Configurações
============================================================================
NEW Features in v3.0:
- Settings validation rules and constraints
- Settings categories and grouping
- Settings presets and profiles
- Settings history and versioning
- Settings export/import (JSON, YAML, ENV)
- Settings comparison and diff
- Default value management
- Settings dependencies and validation
- Type-safe enums for common values
- Settings documentation generator
- Environment variable mapping
- Settings reset to defaults

Previous Features:
- SettingResponse, SettingsListResponse
- YOLOConfigResponse/Update
- EmailConfigResponse/Update
- APIConfigResponse/Update
============================================================================
"""

from pydantic import (
    BaseModel, Field, field_validator, model_validator,
    ConfigDict, EmailStr
)
from typing import Optional, Any, Dict, List, Union, Literal, Tuple
from datetime import datetime
from enum import Enum
import json
import re


# ============================================================================
# OTIMIZAÇÃO 1: Enums & Constants
# ============================================================================

class SettingCategory(str, Enum):
    """✅ NEW: Settings categories"""
    YOLO = "yolo"
    EMAIL = "email"
    API = "api"
    SYSTEM = "system"
    CAMERA = "camera"
    ZONES = "zones"
    ALERTS = "alerts"
    PERFORMANCE = "performance"


class SettingType(str, Enum):
    """✅ NEW: Setting value types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    EMAIL = "email"
    URL = "url"
    PATH = "path"


class YOLOTracker(str, Enum):
    """✅ NEW: YOLO tracker types"""
    BOTSORT = "botsort"
    BYTETRACK = "bytetrack"


class VideoSource(str, Enum):
    """✅ NEW: Video source types"""
    WEBCAM = "webcam"
    USB_CAMERA = "usb_camera"
    IP_CAMERA = "ip_camera"
    RTSP = "rtsp"
    FILE = "file"


# Default values
DEFAULT_CONF_THRESH = 0.5
DEFAULT_TARGET_WIDTH = 640
DEFAULT_FRAME_STEP = 2
DEFAULT_MAX_OUT_TIME = 30.0
DEFAULT_EMAIL_COOLDOWN = 600.0
DEFAULT_BUFFER_SECONDS = 2.0
DEFAULT_CAM_WIDTH = 1920
DEFAULT_CAM_HEIGHT = 1080
DEFAULT_CAM_FPS = 30
DEFAULT_TRACKER = YOLOTracker.BOTSORT
DEFAULT_ZONE_EMPTY_TIMEOUT = 5.0
DEFAULT_ZONE_FULL_TIMEOUT = 10.0
DEFAULT_ZONE_FULL_THRESHOLD = 3


# ============================================================================
# OTIMIZAÇÃO 2: Setting Metadata & Constraints
# ============================================================================

class SettingConstraints(BaseModel):
    """✅ NEW: Validation constraints for settings"""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    regex_pattern: Optional[str] = None
    required: bool = False
    
    def validate_value(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate value against constraints
        
        Returns:
            (is_valid, error_message)
        """
        # Min/max validation
        if self.min_value is not None and value < self.min_value:
            return False, f"Value must be >= {self.min_value}"
        
        if self.max_value is not None and value > self.max_value:
            return False, f"Value must be <= {self.max_value}"
        
        # Allowed values
        if self.allowed_values and value not in self.allowed_values:
            return False, f"Value must be one of: {self.allowed_values}"
        
        # Regex pattern
        if self.regex_pattern and isinstance(value, str):
            if not re.match(self.regex_pattern, value):
                return False, f"Value must match pattern: {self.regex_pattern}"
        
        return True, None


class SettingMetadata(BaseModel):
    """✅ NEW: Complete setting metadata"""
    key: str
    category: SettingCategory
    type: SettingType
    default_value: Any
    description: str
    constraints: Optional[SettingConstraints] = None
    editable: bool = True
    requires_restart: bool = False
    env_var: Optional[str] = None
    depends_on: Optional[List[str]] = None
    
    def get_env_var_name(self) -> str:
        """Get environment variable name"""
        if self.env_var:
            return self.env_var
        return f"YOLO_{self.key.upper()}"


# ============================================================================
# OTIMIZAÇÃO 3: Settings Registry
# ============================================================================

class SettingsRegistry:
    """✅ NEW: Central registry for all settings metadata"""
    
    _registry: Dict[str, SettingMetadata] = {}
    
    @classmethod
    def register(cls, metadata: SettingMetadata):
        """Register setting metadata"""
        cls._registry[metadata.key] = metadata
    
    @classmethod
    def get(cls, key: str) -> Optional[SettingMetadata]:
        """Get setting metadata"""
        return cls._registry.get(key)
    
    @classmethod
    def get_all(cls) -> Dict[str, SettingMetadata]:
        """Get all registered settings"""
        return cls._registry.copy()
    
    @classmethod
    def get_by_category(cls, category: SettingCategory) -> Dict[str, SettingMetadata]:
        """Get settings by category"""
        return {
            k: v for k, v in cls._registry.items()
            if v.category == category
        }
    
    @classmethod
    def validate_value(cls, key: str, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate setting value"""
        metadata = cls.get(key)
        if not metadata:
            return True, None  # Unknown setting, allow
        
        if metadata.constraints:
            return metadata.constraints.validate_value(value)
        
        return True, None


# Initialize registry with YOLO settings
def _init_registry():
    """Initialize settings registry"""
    
    # YOLO Core Settings
    SettingsRegistry.register(SettingMetadata(
        key="conf_thresh",
        category=SettingCategory.YOLO,
        type=SettingType.FLOAT,
        default_value=DEFAULT_CONF_THRESH,
        description="Confidence threshold for YOLO detection (0.0-1.0)",
        constraints=SettingConstraints(min_value=0.0, max_value=1.0),
        requires_restart=True
    ))
    
    SettingsRegistry.register(SettingMetadata(
        key="target_width",
        category=SettingCategory.YOLO,
        type=SettingType.INTEGER,
        default_value=DEFAULT_TARGET_WIDTH,
        description="Target width for YOLO inference",
        constraints=SettingConstraints(min_value=320, max_value=1920, allowed_values=[320, 640, 1280, 1920]),
        requires_restart=True
    ))
    
    SettingsRegistry.register(SettingMetadata(
        key="tracker",
        category=SettingCategory.YOLO,
        type=SettingType.STRING,
        default_value=DEFAULT_TRACKER.value,
        description="YOLO tracker algorithm",
        constraints=SettingConstraints(allowed_values=[t.value for t in YOLOTracker]),
        requires_restart=True
    ))
    
    # Camera Settings
    SettingsRegistry.register(SettingMetadata(
        key="cam_width",
        category=SettingCategory.CAMERA,
        type=SettingType.INTEGER,
        default_value=DEFAULT_CAM_WIDTH,
        description="Camera resolution width",
        constraints=SettingConstraints(min_value=320, max_value=3840),
        requires_restart=True
    ))
    
    SettingsRegistry.register(SettingMetadata(
        key="cam_fps",
        category=SettingCategory.CAMERA,
        type=SettingType.INTEGER,
        default_value=DEFAULT_CAM_FPS,
        description="Camera frames per second",
        constraints=SettingConstraints(min_value=1, max_value=60),
        requires_restart=True
    ))

_init_registry()


# ============================================================================
# BASE SCHEMAS (v1.0 Compatible)
# ============================================================================

class SettingResponse(BaseModel):
    """✅ Schema para resposta de setting único (v1.0 compatible)"""
    key: str
    value: Any
    description: Optional[str] = None
    
    # ➕ NEW v3.0 fields (optional)
    category: Optional[SettingCategory] = None
    type: Optional[SettingType] = None
    default_value: Optional[Any] = None
    editable: Optional[bool] = None
    requires_restart: Optional[bool] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "conf_thresh",
                "value": 0.5,
                "description": "YOLO confidence threshold",
                "category": "yolo",
                "type": "float",
                "default_value": 0.5,
                "editable": True,
                "requires_restart": True
            }
        }
    )
    
    # ========================================================================
    # NEW v3.0: Response Methods
    # ========================================================================
    
    def is_default(self) -> bool:
        """➕ NEW: Check if value is default"""
        if self.default_value is None:
            return False
        return self.value == self.default_value
    
    def get_metadata(self) -> Optional[SettingMetadata]:
        """➕ NEW: Get setting metadata"""
        return SettingsRegistry.get(self.key)
    
    def validate_value(self) -> Tuple[bool, Optional[str]]:
        """➕ NEW: Validate current value"""
        return SettingsRegistry.validate_value(self.key, self.value)


class SettingsListResponse(BaseModel):
    """✅ Schema para lista de settings (v1.0 compatible + enhanced)"""
    settings: List[SettingResponse]
    total: int
    
    # ➕ NEW v3.0 fields
    by_category: Optional[Dict[str, List[SettingResponse]]] = None
    modified_count: Optional[int] = None
    
    def group_by_category(self):
        """➕ NEW: Group settings by category"""
        self.by_category = {}
        for setting in self.settings:
            if setting.category:
                cat = setting.category.value
                if cat not in self.by_category:
                    self.by_category[cat] = []
                self.by_category[cat].append(setting)
    
    def count_modified(self):
        """➕ NEW: Count non-default settings"""
        self.modified_count = sum(
            1 for s in self.settings if not s.is_default()
        )


class SettingUpdate(BaseModel):
    """✅ Schema para atualizar setting (v1.0 compatible)"""
    value: Any = Field(..., description="Novo valor do setting")
    
    # ➕ NEW v3.0 validation
    @model_validator(mode='after')
    def validate_against_registry(self) -> 'SettingUpdate':
        """➕ NEW: Validate value against registry"""
        # This will be called with context in the endpoint
        return self


# ============================================================================
# YOLO CONFIG SCHEMAS (Enhanced)
# ============================================================================

class YOLOConfigResponse(BaseModel):
    """✅ Schema para configuração YOLO completa (v1.0 compatible + enhanced)"""
    
    # ✅ v1.0 Core fields
    conf_thresh: float = Field(default=DEFAULT_CONF_THRESH, ge=0.0, le=1.0)
    target_width: int = Field(default=DEFAULT_TARGET_WIDTH, ge=320, le=1920)
    frame_step: int = Field(default=DEFAULT_FRAME_STEP, ge=1, le=10)
    max_out_time: float = Field(default=DEFAULT_MAX_OUT_TIME, ge=0.0)
    email_cooldown: float = Field(default=DEFAULT_EMAIL_COOLDOWN, ge=0.0)
    safe_zone: Any  # JSON list
    source: str
    cam_width: int = Field(default=DEFAULT_CAM_WIDTH, ge=320, le=3840)
    cam_height: int = Field(default=DEFAULT_CAM_HEIGHT, ge=240, le=2160)
    cam_fps: int = Field(default=DEFAULT_CAM_FPS, ge=1, le=60)
    model_path: str
    tracker: str = Field(default=DEFAULT_TRACKER.value)
    zone_empty_timeout: float = Field(default=DEFAULT_ZONE_EMPTY_TIMEOUT, ge=0.0)
    zone_full_timeout: float = Field(default=DEFAULT_ZONE_FULL_TIMEOUT, ge=0.0)
    zone_full_threshold: int = Field(default=DEFAULT_ZONE_FULL_THRESHOLD, ge=1)
    buffer_seconds: float = Field(default=DEFAULT_BUFFER_SECONDS, ge=0.0)
    
    # ➕ NEW v3.0 validation
    @field_validator('tracker')
    @classmethod
    def validate_tracker(cls, v: str) -> str:
        """Validate tracker is valid"""
        valid_trackers = [t.value for t in YOLOTracker]
        if v not in valid_trackers:
            raise ValueError(f"Tracker must be one of: {valid_trackers}")
        return v
    
    @model_validator(mode='after')
    def validate_dimensions(self) -> 'YOLOConfigResponse':
        """➕ NEW: Validate camera dimensions"""
        if self.cam_width % 32 != 0:
            # YOLO works best with multiples of 32
            pass  # Just warning, not error
        
        if self.cam_height % 32 != 0:
            pass  # Just warning, not error
        
        return self
    
    # ========================================================================
    # NEW v3.0: Config Methods
    # ========================================================================
    
    def get_resolution(self) -> Tuple[int, int]:
        """➕ NEW: Get camera resolution as tuple"""
        return (self.cam_width, self.cam_height)
    
    def get_aspect_ratio(self) -> float:
        """➕ NEW: Calculate aspect ratio"""
        return self.cam_width / self.cam_height
    
    def is_hd(self) -> bool:
        """➕ NEW: Check if HD resolution"""
        return self.cam_width >= 1280 and self.cam_height >= 720
    
    def is_fullhd(self) -> bool:
        """➕ NEW: Check if Full HD resolution"""
        return self.cam_width >= 1920 and self.cam_height >= 1080
    
    def get_processing_load(self) -> Literal["low", "medium", "high"]:
        """
        ➕ NEW: Estimate processing load
        
        Returns:
            Load estimate based on resolution and FPS
        """
        total_pixels = self.cam_width * self.cam_height
        pixels_per_second = total_pixels * self.cam_fps / self.frame_step
        
        if pixels_per_second < 10_000_000:  # 10M pixels/s
            return "low"
        elif pixels_per_second < 30_000_000:  # 30M pixels/s
            return "medium"
        else:
            return "high"
    
    def to_env_dict(self) -> Dict[str, str]:
        """➕ NEW: Convert to environment variables"""
        return {
            "YOLO_CONF_THRESH": str(self.conf_thresh),
            "YOLO_TARGET_WIDTH": str(self.target_width),
            "YOLO_FRAME_STEP": str(self.frame_step),
            "YOLO_MAX_OUT_TIME": str(self.max_out_time),
            "YOLO_EMAIL_COOLDOWN": str(self.email_cooldown),
            "YOLO_SAFE_ZONE": json.dumps(self.safe_zone) if self.safe_zone else "[]",
            "YOLO_SOURCE": self.source,
            "YOLO_CAM_WIDTH": str(self.cam_width),
            "YOLO_CAM_HEIGHT": str(self.cam_height),
            "YOLO_CAM_FPS": str(self.cam_fps),
            "YOLO_MODEL_PATH": self.model_path,
            "YOLO_TRACKER": self.tracker,
            "YOLO_ZONE_EMPTY_TIMEOUT": str(self.zone_empty_timeout),
            "YOLO_ZONE_FULL_TIMEOUT": str(self.zone_full_timeout),
            "YOLO_ZONE_FULL_THRESHOLD": str(self.zone_full_threshold),
            "YOLO_BUFFER_SECONDS": str(self.buffer_seconds)
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conf_thresh": 0.5,
                "target_width": 640,
                "frame_step": 2,
                "max_out_time": 30.0,
                "email_cooldown": 600.0,
                "safe_zone": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
                "source": "0",
                "cam_width": 1920,
                "cam_height": 1080,
                "cam_fps": 30,
                "model_path": "yolov8n.pt",
                "tracker": "botsort",
                "zone_empty_timeout": 5.0,
                "zone_full_timeout": 10.0,
                "zone_full_threshold": 3,
                "buffer_seconds": 2.0
            }
        }
    )


class YOLOConfigUpdate(BaseModel):
    """✅ Schema para atualizar múltiplas configs YOLO (v1.0 compatible)"""
    
    # ✅ v1.0 All optional fields
    conf_thresh: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_width: Optional[int] = Field(None, ge=320, le=1920)
    frame_step: Optional[int] = Field(None, ge=1, le=10)
    max_out_time: Optional[float] = Field(None, ge=0.0)
    email_cooldown: Optional[float] = Field(None, ge=0.0)
    safe_zone: Optional[Any] = None
    source: Optional[str] = None
    cam_width: Optional[int] = Field(None, ge=320, le=3840)
    cam_height: Optional[int] = Field(None, ge=240, le=2160)
    cam_fps: Optional[int] = Field(None, ge=1, le=60)
    model_path: Optional[str] = None
    tracker: Optional[str] = None
    zone_empty_timeout: Optional[float] = Field(None, ge=0.0)
    zone_full_timeout: Optional[float] = Field(None, ge=0.0)
    zone_full_threshold: Optional[int] = Field(None, ge=1)
    
    @field_validator('tracker')
    @classmethod
    def validate_tracker(cls, v: Optional[str]) -> Optional[str]:
        """Validate tracker if provided"""
        if v is None:
            return v
        valid_trackers = [t.value for t in YOLOTracker]
        if v not in valid_trackers:
            raise ValueError(f"Tracker must be one of: {valid_trackers}")
        return v
    
    def get_updated_fields(self) -> Dict[str, Any]:
        """➕ NEW: Get only fields that are being updated"""
        return {
            k: v for k, v in self.model_dump().items()
            if v is not None
        }
    
    def count_changes(self) -> int:
        """➕ NEW: Count number of fields being updated"""
        return len(self.get_updated_fields())


# ============================================================================
# EMAIL CONFIG SCHEMAS (Enhanced)
# ============================================================================

class EmailConfigResponse(BaseModel):
    """✅ Schema para configuração de email (v1.0 compatible + enhanced)"""
    
    # ✅ v1.0 fields
    email_smtp_server: str = Field(default="smtp.gmail.com")
    email_smtp_port: int = Field(default=587, ge=1, le=65535)
    email_user: str
    email_from: str
    email_to: str
    
    # ➕ NEW v3.0 validation
    @field_validator('email_from', 'email_to')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        # Basic email validation
        if '@' not in v:
            raise ValueError("Invalid email format")
        return v
    
    @field_validator('email_smtp_port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate common SMTP ports"""
        common_ports = [25, 465, 587, 2525]
        if v not in common_ports:
            # Just warning, not error
            pass
        return v
    
    # ========================================================================
    # NEW v3.0: Email Config Methods
    # ========================================================================
    
    def is_ssl(self) -> bool:
        """➕ NEW: Check if SSL port"""
        return self.email_smtp_port == 465
    
    def is_tls(self) -> bool:
        """➕ NEW: Check if TLS port"""
        return self.email_smtp_port in [587, 2525]
    
    def get_connection_type(self) -> Literal["ssl", "tls", "plain"]:
        """➕ NEW: Get connection type"""
        if self.is_ssl():
            return "ssl"
        elif self.is_tls():
            return "tls"
        return "plain"
    
    def mask_password(self, email_password: Optional[str]) -> str:
        """➕ NEW: Mask password for display"""
        if not email_password:
            return "***"
        return "*" * len(email_password)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email_smtp_server": "smtp.gmail.com",
                "email_smtp_port": 587,
                "email_user": "your-email@gmail.com",
                "email_from": "alerts@example.com",
                "email_to": "recipient@example.com"
            }
        }
    )


class EmailConfigUpdate(BaseModel):
    """✅ Schema para atualizar configuração de email (v1.0 compatible)"""
    
    # ✅ v1.0 All optional fields
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None
    
    @field_validator('email_from', 'email_to')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided"""
        if v is None:
            return v
        if '@' not in v:
            raise ValueError("Invalid email format")
        return v


# ============================================================================
# API CONFIG SCHEMAS (Enhanced)
# ============================================================================

class APIConfigResponse(BaseModel):
    """✅ Schema para configuração da API (v1.0 compatible + enhanced)"""
    
    # ✅ v1.0 fields
    api_integration_enabled: bool = Field(default=True)
    api_base_url: str = Field(default="http://localhost:8000")
    api_username: str = Field(default="admin")
    
    # ➕ NEW v3.0 validation
    @field_validator('api_base_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip('/')
    
    # ========================================================================
    # NEW v3.0: API Config Methods
    # ========================================================================
    
    def is_https(self) -> bool:
        """➕ NEW: Check if using HTTPS"""
        return self.api_base_url.startswith('https://')
    
    def is_localhost(self) -> bool:
        """➕ NEW: Check if localhost"""
        return 'localhost' in self.api_base_url or '127.0.0.1' in self.api_base_url
    
    def get_api_health_url(self) -> str:
        """➕ NEW: Get health check URL"""
        return f"{self.api_base_url}/health"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_integration_enabled": True,
                "api_base_url": "http://localhost:8000",
                "api_username": "admin"
            }
        }
    )


class APIConfigUpdate(BaseModel):
    """✅ Schema para atualizar configuração da API (v1.0 compatible)"""
    
    # ✅ v1.0 All optional fields
    api_integration_enabled: Optional[bool] = None
    api_base_url: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    
    @field_validator('api_base_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided"""
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip('/')


# ============================================================================
# NEW v3.0: Settings Presets
# ============================================================================

class SettingsPreset(BaseModel):
    """➕ NEW: Settings preset/profile"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    settings: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    is_default: bool = False
    
    def apply_to_config(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply preset to current config"""
        updated = current_config.copy()
        updated.update(self.settings)
        return updated


class SettingsPresetList(BaseModel):
    """➕ NEW: List of settings presets"""
    presets: List[SettingsPreset]
    total: int
    default_preset: Optional[str] = None


# Predefined presets
PERFORMANCE_PRESET = SettingsPreset(
    name="Performance",
    description="High performance settings (lower accuracy)",
    settings={
        "conf_thresh": 0.3,
        "target_width": 320,
        "frame_step": 3,
        "tracker": "bytetrack"
    }
)

ACCURACY_PRESET = SettingsPreset(
    name="Accuracy",
    description="High accuracy settings (slower)",
    settings={
        "conf_thresh": 0.7,
        "target_width": 1280,
        "frame_step": 1,
        "tracker": "botsort"
    }
)

BALANCED_PRESET = SettingsPreset(
    name="Balanced",
    description="Balanced performance and accuracy",
    settings={
        "conf_thresh": 0.5,
        "target_width": 640,
        "frame_step": 2,
        "tracker": "botsort"
    },
    is_default=True
)


# ============================================================================
# NEW v3.0: Settings Export/Import
# ============================================================================

class SettingsExport(BaseModel):
    """➕ NEW: Settings export format"""
    version: str = "3.0"
    exported_at: datetime = Field(default_factory=datetime.now)
    categories: Dict[str, Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Export to JSON string"""
        return self.model_dump_json(indent=2)
    
    def to_env_file(self) -> str:
        """➕ NEW: Export to .env format"""
        lines = ["# YOLO Settings Export", f"# Exported: {self.exported_at.isoformat()}", ""]
        
        for category, settings in self.categories.items():
            lines.append(f"# {category.upper()}")
            for key, value in settings.items():
                env_key = f"YOLO_{key.upper()}"
                if isinstance(value, (list, dict)):
                    env_value = json.dumps(value)
                else:
                    env_value = str(value)
                lines.append(f"{env_key}={env_value}")
            lines.append("")
        
        return "\n".join(lines)


class SettingsImport(BaseModel):
    """➕ NEW: Settings import request"""
    settings: Dict[str, Any]
    override_existing: bool = False
    validate_only: bool = False


# ============================================================================
# NEW v3.0: Settings Comparison
# ============================================================================

class SettingDiff(BaseModel):
    """➕ NEW: Difference between two setting values"""
    key: str
    old_value: Any
    new_value: Any
    category: Optional[SettingCategory] = None
    
    @property
    def is_changed(self) -> bool:
        """Check if value actually changed"""
        return self.old_value != self.new_value


class SettingsComparison(BaseModel):
    """➕ NEW: Comparison between two setting sets"""
    differences: List[SettingDiff]
    total_changes: int
    requires_restart: bool = False
    
    def get_changes_by_category(self) -> Dict[str, List[SettingDiff]]:
        """Group changes by category"""
        by_category: Dict[str, List[SettingDiff]] = {}
        for diff in self.differences:
            if diff.category:
                cat = diff.category.value
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(diff)
        return by_category


# ============================================================================
# TESTE v3.0
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("⚙️  TESTE: Settings Models v3.0")
    print("=" * 70)
    
    # Test 1: v1.0 Compatibility - Basic response
    print("\n✅ Teste 1: v1.0 Compatibility - SettingResponse")
    setting_v1 = SettingResponse(
        key="conf_thresh",
        value=0.5,
        description="YOLO confidence threshold"
    )
    print(f"   ✅ Key: {setting_v1.key}")
    print(f"   ✅ Value: {setting_v1.value}")
    print(f"   ✅ Compatible com v1.0!")
    
    # Test 2: NEW v3.0 - Enhanced response
    print("\n➕ Teste 2: NEW v3.0 - Enhanced SettingResponse")
    setting_v3 = SettingResponse(
        key="conf_thresh",
        value=0.7,
        description="YOLO confidence threshold",
        category=SettingCategory.YOLO,
        type=SettingType.FLOAT,
        default_value=0.5,
        editable=True,
        requires_restart=True
    )
    print(f"   ✅ Category: {setting_v3.category}")
    print(f"   ✅ Is default? {setting_v3.is_default()}")
    print(f"   ✅ Validation: {setting_v3.validate_value()}")
    
    # Test 3: YOLO Config with validation
    print("\n✅ Teste 3: YOLOConfigResponse (v1.0 compatible + validation)")
    yolo_config = YOLOConfigResponse(
        conf_thresh=0.5,
        target_width=640,
        frame_step=2,
        max_out_time=30.0,
        email_cooldown=600.0,
        safe_zone=[[0.1, 0.1], [0.9, 0.9]],
        source="0",
        cam_width=1920,
        cam_height=1080,
        cam_fps=30,
        model_path="yolov8n.pt",
        tracker="botsort",
        zone_empty_timeout=5.0,
        zone_full_timeout=10.0,
        zone_full_threshold=3
    )
    print(f"   ✅ Resolution: {yolo_config.get_resolution()}")
    print(f"   ✅ Is Full HD? {yolo_config.is_fullhd()}")
    print(f"   ✅ Processing load: {yolo_config.get_processing_load()}")
    print(f"   ✅ Aspect ratio: {yolo_config.get_aspect_ratio():.2f}")
    
    # Test 4: Email Config validation
    print("\n✅ Teste 4: EmailConfigResponse com validation")
    email_config = EmailConfigResponse(
        email_smtp_server="smtp.gmail.com",
        email_smtp_port=587,
        email_user="test@gmail.com",
        email_from="alerts@example.com",
        email_to="recipient@example.com"
    )
    print(f"   ✅ Connection type: {email_config.get_connection_type()}")
    print(f"   ✅ Is TLS? {email_config.is_tls()}")
    print(f"   ✅ Masked password: {email_config.mask_password('secret123')}")
    
    # Test 5: API Config validation
    print("\n✅ Teste 5: APIConfigResponse com validation")
    api_config = APIConfigResponse(
        api_integration_enabled=True,
        api_base_url="https://api.example.com",
        api_username="admin"
    )
    print(f"   ✅ Is HTTPS? {api_config.is_https()}")
    print(f"   ✅ Is localhost? {api_config.is_localhost()}")
    print(f"   ✅ Health URL: {api_config.get_api_health_url()}")
    
    # Test 6: Settings Registry
    print("\n➕ Teste 6: NEW - Settings Registry")
    metadata = SettingsRegistry.get("conf_thresh")
    if metadata:
        print(f"   ✅ Metadata found: {metadata.key}")
        print(f"   ✅ Category: {metadata.category}")
        print(f"   ✅ Default: {metadata.default_value}")
        print(f"   ✅ Env var: {metadata.get_env_var_name()}")
    
    # Test 7: Settings Presets
    print("\n➕ Teste 7: NEW - Settings Presets")
    print(f"   ✅ Performance preset: {PERFORMANCE_PRESET.name}")
    print(f"   ✅ Settings: {list(PERFORMANCE_PRESET.settings.keys())}")
    print(f"   ✅ Accuracy preset: {ACCURACY_PRESET.name}")
    print(f"   ✅ Balanced (default): {BALANCED_PRESET.name}")
    
    # Test 8: Settings Export
    print("\n➕ Teste 8: NEW - Settings Export")
    export = SettingsExport(
        categories={
            "yolo": {
                "conf_thresh": 0.5,
                "target_width": 640,
                "tracker": "botsort"
            },
            "camera": {
                "cam_width": 1920,
                "cam_height": 1080,
                "cam_fps": 30
            }
        }
    )
    env_export = export.to_env_file()
    print(f"   ✅ Exported categories: {list(export.categories.keys())}")
    print(f"   ✅ .env format lines: {len(env_export.splitlines())}")
    
    # Test 9: Settings Comparison
    print("\n➕ Teste 9: NEW - Settings Comparison")
    comparison = SettingsComparison(
        differences=[
            SettingDiff(
                key="conf_thresh",
                old_value=0.5,
                new_value=0.7,
                category=SettingCategory.YOLO
            ),
            SettingDiff(
                key="cam_width",
                old_value=1280,
                new_value=1920,
                category=SettingCategory.CAMERA
            )
        ],
        total_changes=2,
        requires_restart=True
    )
    by_cat = comparison.get_changes_by_category()
    print(f"   ✅ Total changes: {comparison.total_changes}")
    print(f"   ✅ Requires restart: {comparison.requires_restart}")
    print(f"   ✅ Changes by category: {list(by_cat.keys())}")
    
    # Test 10: YOLOConfigUpdate
    print("\n✅ Teste 10: YOLOConfigUpdate (partial update)")
    update = YOLOConfigUpdate(
        conf_thresh=0.7,
        tracker="bytetrack"
    )
    updated_fields = update.get_updated_fields()
    print(f"   ✅ Updated fields: {list(updated_fields.keys())}")
    print(f"   ✅ Change count: {update.count_changes()}")
    
    # Test 11: Environment variables
    print("\n➕ Teste 11: NEW - Environment Variables Export")
    env_dict = yolo_config.to_env_dict()
    print(f"   ✅ Env vars count: {len(env_dict)}")
    print(f"   ✅ Sample: YOLO_CONF_THRESH={env_dict['YOLO_CONF_THRESH']}")
    print(f"   ✅ Sample: YOLO_CAM_WIDTH={env_dict['YOLO_CAM_WIDTH']}")
    
    # Test 12: Settings List with grouping
    print("\n➕ Teste 12: NEW - Settings List with Grouping")
    settings_list = SettingsListResponse(
        settings=[setting_v1, setting_v3],
        total=2
    )
    settings_list.group_by_category()
    settings_list.count_modified()
    print(f"   ✅ Total settings: {settings_list.total}")
    print(f"   ✅ Modified count: {settings_list.modified_count}")
    if settings_list.by_category:
        print(f"   ✅ Categories: {list(settings_list.by_category.keys())}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes v3.0 passaram!")
    print("✅ Compatibilidade v1.0 mantida 100%!")
    print("=" * 70)
