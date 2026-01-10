"""
backend/config.py - v4.7 (COCO INTEGRATED)

Configuracoes FastAPI + YOLO + RAG
Carrega .env automaticamente via Pydantic Settings

v4.7 (2026-01-09):
- ADICIONADO: Integração com coco_classes.py
- ADICIONADO: field_validator para parsear YOLO_CLASSES do .env
- ADICIONADO: yolo_classes_names property para debug
- CORRIGIDO: Type hints e suporte a configuração via .env

v4.6 (2026-01-06):
- ADICIONADO: GC_INTERVAL, MEMORY_PERCENT_THRESHOLD, MEMORY_MIN_AVAILABLE_MB
- ADICIONADO: MAX_CONCURRENT_STREAMS, DEFAULT_STREAM_QUALITY
- ADICIONADO: PERSON_CLASS_ID, MAX_RECONNECTION_ATTEMPTS, RECONNECTION_DELAY
- ADICIONADO: FRAME_POOL_SIZE para pre-alocacao de frames
"""

import os
from pathlib import Path
from typing import Optional, List, Union
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

# ✅ Importar constantes do COCO
try:
    from backend.coco_classes import (
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
    # Fallback se coco_classes.py não existir
    PERSON_CLASS_ID = 0
    VEHICLE_CLASS_IDS = {1, 2, 3, 5, 7}
    ANIMAL_CLASS_IDS = {16, 17, 18}
    FURNITURE_CLASS_IDS = {15, 56, 57, 58, 59, 61, 62, 63, 67, 73}
    ALL_RELEVANT_CLASS_IDS = {PERSON_CLASS_ID} | VEHICLE_CLASS_IDS | ANIMAL_CLASS_IDS | FURNITURE_CLASS_IDS
    COCO_CLASSES = {0: "person"}
    COCO_AVAILABLE = False
    
    def get_class_name(class_id):
        return COCO_CLASSES.get(class_id, f"class_{class_id}")


# ============================================
# CONFIGURACAO DE CLASSE SETTINGS
# ============================================
class Settings(BaseSettings):
    """Configuracoes validadas com Pydantic"""
    
    # ============================================
    # APP CONFIG
    # ============================================
    APP_NAME: str = "ARK Vision"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ============================================
    # SECURITY & AUTH
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 dias
    
    # ============================================
    # DATABASE - POSTGRESQL
    # ============================================
    DATABASE_URL: str
    DB_ECHO: bool = False
    ENABLE_PGVECTOR: bool = False
    
    # ============================================
    # OPENAI (RAG)
    # ============================================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7
    
    # ============================================
    # OLLAMA (Alternative Local LLM)
    # ============================================
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # ============================================
    # RAG SETTINGS
    # ============================================
    RAG_ENABLED: bool = False
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    
    # ============================================
    # VECTOR STORE
    # ============================================
    VECTOR_STORE_TYPE: str = "pgvector"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    
    # ============================================
    # v4.7: YOLO MODEL & COCO CLASSES CONFIG
    # ============================================
    YOLO_MODEL_PATH: str = "yolo_models/yolo11n.engine"
    YOLO_CONF_THRESHOLD: float = 0.87
    YOLO_TARGET_WIDTH: int = 960
    YOLO_FRAME_STEP: int = 1
    TRACKER: str = "botsort.yaml"
    JPEG_QUALITY: int = 70
    
    # ✅ v4.7: YOLO Classes com parsing automático do .env
    YOLO_CLASSES: Optional[List[int]] = [PERSON_CLASS_ID]  # Default: apenas pessoa
    
    @field_validator('YOLO_CLASSES', mode='before')
    @classmethod
    def parse_yolo_classes(cls, v):
        """
        Parseia YOLO_CLASSES do .env:
        - None ou "None" -> None (todas as classes)
        - "[0,2,3]" -> [0, 2, 3]
        - "0,2,3" -> [0, 2, 3]
        - [0, 2, 3] -> [0, 2, 3] (já é lista)
        """
        if v is None or (isinstance(v, str) and v.upper() == "NONE"):
            return None
        
        if isinstance(v, str):
            # Remove espaços e brackets
            v = v.strip().replace('[', '').replace(']', '').replace(' ', '')
            if not v:
                return [PERSON_CLASS_ID]  # Fallback
            # Split por vírgula e converte para int
            try:
                return [int(x) for x in v.split(',') if x]
            except ValueError:
                return [PERSON_CLASS_ID]  # Fallback em caso de erro
        
        if isinstance(v, list):
            return v
        
        # Fallback final
        return [PERSON_CLASS_ID]
    
    # ============================================
    # v4.9: TRACKING CONFIGURATION (IoU-based)
    # ============================================
    TRACKING_IOU_THRESHOLD: float = 0.3  # 30% overlap = mesmo objeto
    TRACKING_TTL_SECONDS: float = 10.0 # 10 segundos (tempo para voltar)
    
    # ============================================
    # VIDEO SOURCE CONFIG (Fallback do .env)
    # ============================================
    VIDEO_SOURCE: str = "0"
    
    # ============================================
    # CAMERA SETTINGS (Resolucao)
    # ============================================
    CAM_WIDTH: int = 960
    CAM_HEIGHT: int = 540
    CAM_FPS: int = 30
    
    # Camera authentication
    CAMERA_USERNAME: str = "admin"
    CAMERA_PASSWORD: str = "camera-password"
    
    # ============================================
    # v4.6: MEMORY MANAGEMENT (OPTIMIZED)
    # ============================================
    BUFFER_SIZE: int = 40
    GC_INTERVAL: int = 100
    MEMORY_WARNING_THRESHOLD: int = 512
    
    MEMORY_PERCENT_THRESHOLD: int = 85
    MEMORY_MIN_AVAILABLE_MB: int = 200
    
    # ============================================
    # v4.6: STREAM CONFIG (OPTIMIZED)
    # ============================================
    MAX_CONCURRENT_STREAMS: int = 3
    DEFAULT_STREAM_QUALITY: str = "MEDIUM"
    
    # ============================================
    # ZONE DETECTION CONFIG
    # ============================================
    MAX_OUT_TIME: float = 20.0
    EMAIL_COOLDOWN: float = 120.0
    BUFFER_DURATION_SECONDS: float = 2.0
    ZONE_EMPTY_TIMEOUT: float = 5.0
    ZONE_FULL_TIMEOUT: float = 10.0
    ZONE_FULL_THRESHOLD: int = 3
    
    # ============================================
    # v4.6: YOLO DETECTION CONFIG
    # ============================================
    MAX_RECONNECTION_ATTEMPTS: int = 5
    RECONNECTION_DELAY: float = 0.5
    FRAME_POOL_SIZE: int = 10
    
    # ============================================
    # EMAIL NOTIFICATIONS
    # ============================================
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_SENDER: str
    EMAIL_APP_PASSWORD: str
    SMTP_USE_TLS: bool = True
    
    # ============================================
    # API INTEGRATION (YOLO -> FastAPI)
    # ============================================
    API_INTEGRATION_ENABLED: bool = True
    API_BASE_URL: str = "http://localhost:8000"
    API_USERNAME: str = "admin"
    API_PASSWORD: str = "admin123"
    
    # ============================================
    # CORS (Frontend origins)
    # ============================================
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/ark_yolo.log"
    RAG_LOG_QUERIES: bool = True
    RAG_LOG_RESPONSES: bool = False
    
    # ============================================
    # GPU CONFIG
    # ============================================
    USE_GPU: bool = True
    CUDA_VISIBLE_DEVICES: str = "0"
    RAG_USE_GPU: bool = False
    RAG_GPU_DEVICE: str = "cuda:0"
    
    # ============================================
    # CONVERSATION & MEMORY
    # ============================================
    CONVERSATION_MAX_HISTORY: int = 50
    CONVERSATION_TIMEOUT_MINUTES: int = 30
    MEMORY_TYPE: str = "buffer"
    MEMORY_MAX_TOKENS: int = 2000
    
    # ============================================
    # ADVANCED RAG SETTINGS
    # ============================================
    RERANK_ENABLED: bool = False
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    HYBRID_SEARCH_ENABLED: bool = False
    HYBRID_SEARCH_ALPHA: float = 0.5
    MULTI_QUERY_ENABLED: bool = False
    MULTI_QUERY_COUNT: int = 3
    
    # ============================================
    # PYDANTIC CONFIG (Carrega .env automaticamente)
    # ============================================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    ENV_FILE: Path = BASE_DIR / ".env"
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================
    # v4.7: COMPUTED PROPERTIES - YOLO CLASSES
    # ============================================
    
    @property
    def yolo_classes_names(self) -> List[str]:
        """
        Retorna nomes das classes configuradas
        
        Returns:
            List[str]: Lista de nomes (ex: ['person', 'car'])
        """
        if self.YOLO_CLASSES is None:
            return ["ALL 80 COCO CLASSES"]
        
        return [get_class_name(cid) for cid in self.YOLO_CLASSES]
    
    # ============================================
    # COMPUTED PROPERTIES (Helper methods)
    # ============================================
    
    @property
    def active_preset(self) -> str:
        """Retorna preset ativo (usado para compatibilidade)"""
        return self.DEFAULT_STREAM_QUALITY
    
    @property
    def video_source_parsed(self) -> str | int:
        """Converte VIDEO_SOURCE para int (webcam) ou mantém como str (URL/RTSP)"""
        try:
            return int(self.VIDEO_SOURCE)
        except (ValueError, TypeError):
            return str(self.VIDEO_SOURCE).strip()
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Converte CORS_ORIGINS (string) para lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def database_url_sync(self) -> str:
        """Converte DATABASE_URL para versão síncrona (psycopg2)"""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    
    def __str__(self) -> str:
        """String representation amigável"""
        return f"<Settings app={self.APP_NAME} env={self.ENVIRONMENT}>"
    
    def __repr__(self) -> str:
        """Representação detalhada (para debugging)"""
        return (
            f"Settings("
            f"APP_NAME='{self.APP_NAME}', "
            f"ENVIRONMENT='{self.ENVIRONMENT}', "
            f"YOLO_CLASSES={self.YOLO_CLASSES}, "
            f"VIDEO_SOURCE='{self.VIDEO_SOURCE}')"
        )


# ============================================
# INSTANCIA GLOBAL (Singleton)
# ============================================
settings = Settings()


# ============================================
# DEBUG OUTPUT (Apenas em desenvolvimento)
# ============================================
if settings.DEBUG and settings.ENVIRONMENT == "development":
    print("=" * 70)
    print("ARK YOLO FastAPI v4.7 - Configuration Loaded")
    print("=" * 70)
    print(f"App Name: {settings.APP_NAME}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Host: {settings.HOST}:{settings.PORT}")
    print("-" * 70)
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print(f"YOLO Model: {settings.YOLO_MODEL_PATH}")
    print(f"YOLO Confidence: {settings.YOLO_CONF_THRESHOLD}")
    print(f"YOLO Target Width: {settings.YOLO_TARGET_WIDTH}px")
    print("-" * 70)
    print(f"✅ YOLO Classes (v4.7):")
    print(f"  Class IDs: {settings.YOLO_CLASSES}")
    print(f"  Class Names: {', '.join(settings.yolo_classes_names)}")
    print("-" * 70)
    print(f"Video Source (Fallback): {settings.VIDEO_SOURCE}")
    print(f"Camera Resolution: {settings.CAM_WIDTH}x{settings.CAM_HEIGHT}")
    print(f"Camera FPS: {settings.CAM_FPS}")
    print("-" * 70)
    print(f"v4.6 Optimizations:")
    print(f"  GC Interval: {settings.GC_INTERVAL} frames")
    print(f"  Memory Percent Threshold: {settings.MEMORY_PERCENT_THRESHOLD}%")
    print(f"  Memory Min Available: {settings.MEMORY_MIN_AVAILABLE_MB}MB")
    print(f"  Max Concurrent Streams: {settings.MAX_CONCURRENT_STREAMS}")
    print(f"  Max Reconnection Attempts: {settings.MAX_RECONNECTION_ATTEMPTS}")
    print(f"  Frame Pool Size: {settings.FRAME_POOL_SIZE}")
    print("-" * 70)
    print(f"GPU Enabled: {settings.USE_GPU}")
    print(f"Email Configured: {bool(settings.EMAIL_SENDER and settings.EMAIL_APP_PASSWORD)}")
    print(f"API Integration: {settings.API_INTEGRATION_ENABLED}")
    print(f"RAG Enabled: {settings.RAG_ENABLED}")
    print("=" * 70)
    print()


# ============================================
# VALIDACOES (Executadas na importacao)
# ============================================
def validate_settings():
    """Valida configuracoes criticas"""
    errors = []
    
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY deve ter pelo menos 32 caracteres")
    
    if not settings.DATABASE_URL or not settings.DATABASE_URL.startswith("postgresql"):
        errors.append("DATABASE_URL deve ser uma conexao PostgreSQL valida")
    
    if settings.EMAIL_SENDER and not settings.EMAIL_APP_PASSWORD:
        errors.append("EMAIL_APP_PASSWORD e obrigatorio quando EMAIL_SENDER esta configurado")
    
    model_path = Path(settings.YOLO_MODEL_PATH)
    if not model_path.exists() and not model_path.is_absolute():
        model_path = settings.BASE_DIR / settings.YOLO_MODEL_PATH
        if not model_path.exists():
            errors.append(f"YOLO_MODEL_PATH nao encontrado: {settings.YOLO_MODEL_PATH}")
    
    if settings.RAG_ENABLED and not settings.OLLAMA_ENABLED and not settings.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY e obrigatorio quando RAG_ENABLED=true")
    
    if errors:
        print("\nERROS DE CONFIGURACAO:")
        for error in errors:
            print(f"   - {error}")
        print()
    
    return len(errors) == 0


# Executar validacao
if settings.ENVIRONMENT == "production":
    if not validate_settings():
        raise RuntimeError("Configuracao invalida! Corrija os erros acima antes de continuar.")
