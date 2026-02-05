"""
backend/config.py - v3.2 (COMPLETE)

Configuracoes ARK Vision - FastAPI + YOLO + RAG
Carrega .env automaticamente via Pydantic Settings

Changelog:
v3.2 (2026-01-14):
- ADICIONADO: MEMORY_PERCENT_THRESHOLD, MEMORY_MIN_AVAILABLE_MB configuráveis
- ADICIONADO: SNAPSHOT_PATH configurável
- ADICIONADO: ZONE_RETENTION_DAYS (CFR21 Part 11)
- ADICIONADO: STREAM_TARGET_FPS configurável

v4.7 (2026-01-09):
- ADICIONADO: Integração com coco_classes.py
- ADICIONADO: field_validator para YOLO_CLASSES
- ADICIONADO: yolo_classes_names property

v4.6 (2026-01-06):
- ADICIONADO: GC_INTERVAL, MAX_CONCURRENT_STREAMS
- ADICIONADO: PERSON_CLASS_ID, MAX_RECONNECTION_ATTEMPTS
- ADICIONADO: FRAME_POOL_SIZE
"""

import os
from pathlib import Path
from typing import Optional, List, Union
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================================
# COCO CLASSES (Importacao condicional)
# ============================================================================
try:
    from backend.adapters.vision.coco_classes import (
        PERSON_CLASS_ID,
        VEHICLE_CLASS_IDS,
        ANIMAL_CLASS_IDS,
        FURNITURE_CLASS_IDS,
        ALL_RELEVANT_CLASS_IDS,
        COCO_CLASSES,
        get_class_name
    )
    COCO_AVAILABLE = True
except ImportError:
    PERSON_CLASS_ID = 0
    VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7}
    ANIMAL_CLASS_IDS = {16, 17, 18}
    FURNITURE_CLASS_IDS = {15, 56, 57, 58, 59, 61, 62, 63, 67, 73}
    ALL_RELEVANT_CLASS_IDS = {PERSON_CLASS_ID} | VEHICLE_CLASS_IDS | ANIMAL_CLASS_IDS | FURNITURE_CLASS_IDS
    COCO_CLASSES = {0: "person"}
    COCO_AVAILABLE = False
    
    def get_class_name(class_id):
        return COCO_CLASSES.get(class_id, f"class_{class_id}")


# ============================================================================
# SETTINGS CLASS
# ============================================================================
class Settings(BaseSettings):
    """Configuracoes validadas com Pydantic"""
    
    # ========================================================================
    # 1. APPLICATION CORE
    # ========================================================================
    APP_NAME: str = "ARK Vision"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ========================================================================
    # 2. SECURITY & AUTHENTICATION
    # ========================================================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 dias
    
    # ========================================================================
    # 3. DATABASE - POSTGRESQL
    # ========================================================================
    DATABASE_URL: str
    DB_ECHO: bool = False
    ENABLE_PGVECTOR: bool = False
    
    # ========================================================================
    # 4. YOLO MODEL & COMPUTER VISION
    # ========================================================================
    YOLO_MODEL_PATH: str = "yolo_models/yolo11s.engine"

    # ReID / appearance models (multi-profile)
    REID_PROFILE_DEFAULT: str = "default"
    REID_MODEL_PATH_EDGE: str | None = None
    REID_MODEL_PATH_DEFAULT: str | None = None
    REID_MODEL_PATH_HIGH: str | None = None

    # Profile padrão de ReID para câmeras que não especificarem
    REID_PROFILE_DEFAULT: str = "default"


    USE_ZONE_PROCESSOR_V3: bool = True
    USE_SAM3: bool = False
    SAM3_MODEL_PATH: str = "sam3_models/sam3.pt"
    SAM3_CONFIDENCE: float = 0.25
    SAM3_IMAGE_SIZE: int = 640

    YOLO_TARGET_WIDTH: int = 960
    YOLO_FRAME_STEP: int = 1
    TRACKER: str = "botsort.yaml"

    # YOLO Classes com parsing automático
    YOLO_CLASSES: Optional[List[int]] = [PERSON_CLASS_ID]

    @field_validator('YOLO_CLASSES', mode='before')
    @classmethod
    def parse_yolo_classes(cls, v):
        """
        Parseia YOLO_CLASSES do .env (DETECÇÃO GLOBAL):
        - None ou "None" -> None (todas as classes)
        - "[0,2,3]" -> [0, 2, 3]
        - "0,2,3" -> [0, 2, 3]
        - [0, 2, 3] -> [0, 2, 3] (já é lista)
        
        IMPORTANTE: YOLO_CLASSES define quais classes o YOLO detecta GLOBALMENTE.
        Cada zona pode filtrar classes específicas via metadata.detection_classes.
        """
        if v is None or (isinstance(v, str) and v.upper() == "NONE"):
            return None
        
        if isinstance(v, str):
            v = v.strip().replace('[', '').replace(']', '').replace(' ', '')
            if not v:
                return [PERSON_CLASS_ID]
            try:
                return [int(x) for x in v.split(',') if x]
            except ValueError:
                return [PERSON_CLASS_ID]
        
        if isinstance(v, list):
            return v
        
        return [PERSON_CLASS_ID]

    # Classes padrão para novas zonas
    DEFAULT_ZONE_CLASSES: List[int] = Field(
        default=[PERSON_CLASS_ID],
        description="Classes padrão ao criar nova zona (pode ser sobrescrito por zona)"
    )

    @field_validator('DEFAULT_ZONE_CLASSES', mode='before')
    @classmethod
    def parse_default_zone_classes(cls, v):
        """Parseia DEFAULT_ZONE_CLASSES do .env (mesmo formato que YOLO_CLASSES)"""
        if v is None or (isinstance(v, str) and v.upper() == "NONE"):
            return [PERSON_CLASS_ID]
        
        if isinstance(v, str):
            v = v.strip().replace('[', '').replace(']', '').replace(' ', '')
            if not v:
                return [PERSON_CLASS_ID]
            try:
                return [int(x) for x in v.split(',') if x]
            except ValueError:
                return [PERSON_CLASS_ID]
        
        if isinstance(v, list):
            return v
        
        return [PERSON_CLASS_ID]
    
    # ========================================================================
    # 6. INFERENCE & DETECTION
    # ========================================================================
    YOLO_CONF_THRESHOLD: float = 0.25   # Balanceado (padrão)

    # ADICIONAR (se não existir): IOU threshold para NMS
    YOLO_IOU_THRESHOLD: float = 0.45    # Padrão

    # ADICIONAR (se não existir): Tamanho de inferência
    YOLO_IMG_SIZE: int = 640            # Resolução para inferência (640, 1280)

    # ADICIONAR (se não existir): Classes máximas
    YOLO_MAX_DETECTIONS: int = 10       # Máximo de objetos por frame
    
    # ========================================================================
    # 7. TRACKING & DETECTION
    # ========================================================================
    TRACKING_IOU_THRESHOLD: float = 0.3
    TRACKING_TTL_SECONDS: float = 1.0

    
    MAX_RECONNECTION_ATTEMPTS: int = 5
    RECONNECTION_DELAY: float = 0.5
    FRAME_POOL_SIZE: int = 10
    
    # ========================================================================
    # 8. CAMERA & VIDEO SOURCE
    # ========================================================================
    VIDEO_SOURCE: str = "0"
    
    CAM_WIDTH: int = 960
    CAM_HEIGHT: int = 540
    CAM_FPS: int = 60
    
    CAMERA_USERNAME: str = "admin"
    CAMERA_PASSWORD: str = "camera-password"
    
    # ========================================================================
    # 9. STREAM CONFIGURATION
    # ========================================================================
    STREAM_TARGET_FPS: int = Field(
        default=60,
        ge=1,
        le=60,
        description="FPS alvo do streaming"
    )
    
    MAX_CONCURRENT_STREAMS: int = 3
    DEFAULT_STREAM_QUALITY: str = "MEDIUM"
    

    # ============================================================================
    # VIDEO SETTINGS
    # ============================================================================
    JPEG_QUALITY: int = 85
    FLIP_HORIZONTAL: bool = True  # Espelha vídeo horizontalmente


    # ========================================================================
    # 10. MEMORY & PERFORMANCE
    # ========================================================================
    BUFFER_SIZE: int = 40
    GC_INTERVAL: int = 50
    MEMORY_WARNING_THRESHOLD: int = 1024
    
    MEMORY_PERCENT_THRESHOLD: int = Field(
        default=95,
        ge=50,
        le=99,
        description="Bloqueio de stream se uso de RAM > X%"
    )
    
    MEMORY_MIN_AVAILABLE_MB: int = Field(
        default=100,
        ge=50,
        le=2000,
        description="Bloqueio de stream se RAM disponível < X MB"
    )
    # ========================================================================
    # 9. ZONE DETECTION & ALERTS
    # ========================================================================
    MAX_OUT_TIME: float = 20.0
    EMAIL_COOLDOWN: float = 120.0
    ZONE_EMPTY_TIMEOUT: float = 5.0
    ZONE_FULL_TIMEOUT: float = 10.0
    ZONE_FULL_THRESHOLD: int = 3
    
    # ========================================================================
    # 10. STORAGE & DATA RETENTION
    # ========================================================================
    SNAPSHOT_PATH: str = Field(
        default="data/zone_snapshots",
        description="Diretório para snapshots de zonas"
    )


    ALERT_CLIP_PRE_SECONDS: float = 5.0     # Segundos de vídeo ANTES do evento de alerta
    ALERT_CLIP_POST_SECONDS: float = 10.0   # Segundos de vídeo DEPOIS do evento de alerta
    ALERT_CLIP_FPS: int = 15                # FPS do clipe salvo (menor = arquivo menor)
    BUFFER_DURATION_SECONDS: float = 20.0   # Duração mínima do buffer circular (fallback)
    MAX_FRAMES_PER_CAMERA: float = 200.0    # Limite hard: ~300 MiB @ 1.5MiB/frame
    # Diretório onde salvar clipes de alerta
    ALERT_VIDEO_PATH: str = Field(
        default="data/alertas",
        description="Diretório para vídeos de ocorrência de alertas"
    )

    ZONE_RETENTION_DAYS: int = Field(
        default=1825,
        ge=365,
        le=3650,
        description="Retenção de zonas deletadas (CFR21: 5 anos)"
    )
    
    # ========================================================================
    # 11. EMAIL NOTIFICATIONS
    # ========================================================================
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    EMAIL_SENDER: str
    EMAIL_APP_PASSWORD: str
    
    # ========================================================================
    # 12. API INTEGRATION
    # ========================================================================
    API_INTEGRATION_ENABLED: bool = True
    API_BASE_URL: str = "http://localhost:8000"
    API_USERNAME: str = "admin"
    API_PASSWORD: str = "admin123"
    
    # ========================================================================
    # 13. CORS (FRONTEND ORIGINS)
    # ========================================================================
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # ========================================================================
    # 14. LLM & RAG (OPTIONAL)
    # ========================================================================
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7
    
    # Ollama
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # RAG
    RAG_ENABLED: bool = False
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    
    # Vector Store
    VECTOR_STORE_TYPE: str = "pgvector"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    
    # Advanced RAG
    RERANK_ENABLED: bool = False
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    HYBRID_SEARCH_ENABLED: bool = False
    HYBRID_SEARCH_ALPHA: float = 0.5
    MULTI_QUERY_ENABLED: bool = False
    MULTI_QUERY_COUNT: int = 3
    
    # Conversation Memory
    CONVERSATION_MAX_HISTORY: int = 50
    CONVERSATION_TIMEOUT_MINUTES: int = 30
    MEMORY_TYPE: str = "buffer"
    MEMORY_MAX_TOKENS: int = 2000
    
    # ========================================================================
    # 15. GPU & ACCELERATION
    # ========================================================================
    USE_GPU: bool = True
    CUDA_VISIBLE_DEVICES: str = "0"
    RAG_USE_GPU: bool = False
    RAG_GPU_DEVICE: str = "cuda:0"
    
    # ========================================================================
    # 16. LOGGING & OBSERVABILITY
    # ========================================================================
    LOG_LEVEL: str = "INFO"
    RELOAD_APP: bool = False
    LOG_FILE: str = "logs/ark_yolo.log"
    RAG_LOG_QUERIES: bool = True
    RAG_LOG_RESPONSES: bool = False
    
    # ========================================================================
    # PYDANTIC CONFIG
    # ========================================================================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    ENV_FILE: Path = BASE_DIR / ".env"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================
    
    @property
    def yolo_classes_names(self) -> List[str]:
        """Retorna nomes das classes YOLO configuradas"""
        if self.YOLO_CLASSES is None:
            return ["ALL 80 COCO CLASSES"]
        return [get_class_name(cid) for cid in self.YOLO_CLASSES]
    
    @property
    def default_zone_classes_names(self) -> List[str]:
        """Retorna nomes das classes padrão para novas zonas"""
        return [get_class_name(cid) for cid in self.DEFAULT_ZONE_CLASSES]

    @property
    def active_preset(self) -> str:
        """Preset ativo (compatibilidade)"""
        return self.DEFAULT_STREAM_QUALITY
    
    @property
    def video_source_parsed(self) -> str | int:
        """Converte VIDEO_SOURCE para int ou str"""
        try:
            return int(self.VIDEO_SOURCE)
        except (ValueError, TypeError):
            return str(self.VIDEO_SOURCE).strip()
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Converte CORS_ORIGINS para lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def database_url_sync(self) -> str:
        """Converte DATABASE_URL para versão síncrona"""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    
    def __str__(self) -> str:
        return f"<Settings app={self.APP_NAME} env={self.ENVIRONMENT}>"
    
    def __repr__(self) -> str:
        return (
            f"Settings("
            f"APP_NAME='{self.APP_NAME}', "
            f"ENVIRONMENT='{self.ENVIRONMENT}', "
            f"YOLO_CLASSES={self.YOLO_CLASSES})"
        )


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
settings = Settings()


# ============================================================================
# DEBUG OUTPUT
# ============================================================================
if settings.DEBUG and settings.ENVIRONMENT == "development":
    print("=" * 70)
    print("ARK VISION v3.2 - Configuration Loaded")
    print("=" * 70)
    print(f"App: {settings.APP_NAME}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Host: {settings.HOST}:{settings.PORT}")
    print("-" * 70)
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print(f"YOLO Model: {settings.YOLO_MODEL_PATH}")
    print(f"YOLO Confidence: {settings.YOLO_CONF_THRESHOLD}")
    print(f"Target Width: {settings.YOLO_TARGET_WIDTH}px")
    print("-" * 70)
    print(f"YOLO Classes (Global): {settings.YOLO_CLASSES}")
    print(f"  └─ Detecting: {', '.join(settings.yolo_classes_names)}")
    print(f"Default Zone Classes: {settings.DEFAULT_ZONE_CLASSES}")
    print(f"  └─ New zones default to: {', '.join(settings.default_zone_classes_names)}")
    print("-" * 70)
    print(f"Video Source: {settings.VIDEO_SOURCE}")
    print(f"Camera: {settings.CAM_WIDTH}x{settings.CAM_HEIGHT} @ {settings.CAM_FPS} FPS")
    print(f"Stream Target: {settings.STREAM_TARGET_FPS} FPS")
    print("-" * 70)
    print(f"Memory Threshold: {settings.MEMORY_PERCENT_THRESHOLD}%")
    print(f"Memory Min: {settings.MEMORY_MIN_AVAILABLE_MB}MB")
    print(f"Max Streams: {settings.MAX_CONCURRENT_STREAMS}")
    print("-" * 70)
    print(f"Snapshot Path: {settings.SNAPSHOT_PATH}")
    print(f"Zone Retention: {settings.ZONE_RETENTION_DAYS} days")
    print("-" * 70)
    print(f"GPU: {settings.USE_GPU}")
    print(f"Email: {bool(settings.EMAIL_SENDER and settings.EMAIL_APP_PASSWORD)}")
    print(f"RAG: {settings.RAG_ENABLED}")
    print("=" * 70)
    print()


# ============================================================================
# VALIDATIONS
# ============================================================================
def validate_settings():
    """Valida configuracoes criticas"""
    errors = []
    
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY deve ter pelo menos 32 caracteres")
    
    if not settings.DATABASE_URL or not settings.DATABASE_URL.startswith("postgresql"):
        errors.append("DATABASE_URL deve ser PostgreSQL valido")
    
    if settings.EMAIL_SENDER and not settings.EMAIL_APP_PASSWORD:
        errors.append("EMAIL_APP_PASSWORD obrigatorio quando EMAIL_SENDER configurado")
    
    model_path = Path(settings.YOLO_MODEL_PATH)
    if not model_path.exists() and not model_path.is_absolute():
        model_path = settings.BASE_DIR / settings.YOLO_MODEL_PATH
        if not model_path.exists():
            errors.append(f"YOLO_MODEL_PATH nao encontrado: {settings.YOLO_MODEL_PATH}")
    
    # (Opcional) Validar REID models se configurados
    for label, path in [
        ("REID_MODEL_PATH_DEFAULT", settings.REID_MODEL_PATH_DEFAULT),
        ("REID_MODEL_PATH_HIGH", settings.REID_MODEL_PATH_HIGH),
        ("REID_MODEL_PATH_EDGE", settings.REID_MODEL_PATH_EDGE),
    ]:
        if not path:
            continue
        p = Path(path)
        if not p.exists() and not p.is_absolute():
            p = settings.BASE_DIR / path
        if not p.exists():
            errors.append(f"{label} nao encontrado: {path}")

    if settings.RAG_ENABLED and not settings.OLLAMA_ENABLED and not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY obrigatorio quando RAG_ENABLED=true")
    
    # Validar DEFAULT_ZONE_CLASSES
    if settings.DEFAULT_ZONE_CLASSES:
        invalid_classes = [
            cid for cid in settings.DEFAULT_ZONE_CLASSES 
            if cid not in range(80)
        ]
        if invalid_classes:
            errors.append(
                f"DEFAULT_ZONE_CLASSES contém IDs inválidos: {invalid_classes} "
                f"(deve ser 0-79)"
            )
    
    # Avisar se YOLO_CLASSES não inclui DEFAULT_ZONE_CLASSES
    if (settings.YOLO_CLASSES is not None and 
        settings.DEFAULT_ZONE_CLASSES):
        missing = set(settings.DEFAULT_ZONE_CLASSES) - set(settings.YOLO_CLASSES)
        if missing:
            print(f"\n⚠️  AVISO: DEFAULT_ZONE_CLASSES inclui classes não detectadas "
                  f"pelo YOLO: {missing}")
            print(f"   Considere adicionar estas classes ao YOLO_CLASSES")

    if errors:
        print("\nERROS DE CONFIGURACAO:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    return len(errors) == 0


# Executar validacao em producao
if settings.ENVIRONMENT == "production":
    if not validate_settings():
        raise RuntimeError("Configuracao invalida!")
