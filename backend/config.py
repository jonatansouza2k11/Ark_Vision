"""
backend/config.py
Configurações FastAPI + RAG
Carrega .env automaticamente
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================
# 🐛 DEBUG: Verificar caminho do .env
# ============================================
#from pathlib import Path
#_BASE_DIR = Path(__file__).resolve().parent.parent
#_ENV_FILE = _BASE_DIR / ".env"
#print(f"🔍 DEBUG: Procurando .env em: {_ENV_FILE}")
#print(f"🔍 DEBUG: Arquivo existe? {_ENV_FILE.exists()}")
#if _ENV_FILE.exists():
#    print(f"🔍 DEBUG: Primeiras 5 linhas do .env:")
#    with open(_ENV_FILE, 'r', encoding='utf-8') as f:
#        for i, line in enumerate(f):
#            if i >= 5:
#                break
#            print(f"   {line.rstrip()}")
#print("=" * 70)

class Settings(BaseSettings):
    """Configurações validadas com Pydantic"""
    
    # ============================================
    # APP CONFIG
    # ============================================
    APP_NAME: str = "ARK YOLO FastAPI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ============================================
    # SECURITY & AUTH
    # ============================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # ============================================
    # DATABASE - POSTGRESQL
    # ============================================
    DATABASE_URL: str
    DB_ECHO: bool = False
    ENABLE_PGVECTOR: bool = False
    
    # ============================================
    # 🤖 RAG CONFIGURATION
    # ============================================
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7
    
    # Ollama (alternative)
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # RAG Settings
    RAG_ENABLED: bool = False
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.7
    
    # Vector Store
    VECTOR_STORE_TYPE: str = "pgvector"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    
    # ============================================
    # YOLO MODEL CONFIG
    # ============================================
    YOLO_MODEL_PATH: str = "yolo_models/yolov8n.pt"
    YOLO_CONF_THRESHOLD: float = 0.87
    YOLO_TARGET_WIDTH: int = 960
    YOLO_FRAME_STEP: int = 1
    TRACKER: str = "botsort.yaml"
    
    # ============================================
    # VIDEO SOURCE CONFIG
    # ============================================
    VIDEO_SOURCE: str = "0"
    
    # ============================================
    # CAMERA SETTINGS
    # ============================================
    CAM_WIDTH: int = 960
    CAM_HEIGHT: int = 540
    CAM_FPS: int = 30
    
    # ============================================
    # MEMORY MANAGEMENT
    # ============================================
    BUFFER_SIZE: int = 40
    GC_INTERVAL: int = 50
    MEMORY_WARNING_THRESHOLD: int = 1024
    
    # ============================================
    # ZONE DETECTION CONFIG
    # ============================================
    MAX_OUT_TIME: float = 5.0
    EMAIL_COOLDOWN: float = 10.0
    BUFFER_SECONDS: float = 2.0
    ZONE_EMPTY_TIMEOUT: float = 15.0
    ZONE_FULL_TIMEOUT: float = 20.0
    ZONE_FULL_THRESHOLD: int = 5
    
    # ============================================
    # EMAIL NOTIFICATIONS
    # ============================================
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_SENDER: str = ""
    EMAIL_APP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    
    # ============================================
    # CORS
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
    # 🤖 CONVERSATION & MEMORY
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
    # PYDANTIC CONFIG
    # ============================================
    _BASE_DIR = Path(__file__).resolve().parent.parent
    _ENV_FILE = _BASE_DIR / ".env"
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================
    # COMPUTED PROPERTIES
    # ============================================
    @property
    def cors_origins_list(self) -> list[str]:
        """Converte CORS_ORIGINS string para lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def video_source_parsed(self):
        """Converte VIDEO_SOURCE para int se for número"""
        try:
            return int(self.VIDEO_SOURCE)
        except ValueError:
            return self.VIDEO_SOURCE
    
    @property
    def buffer_duration_seconds(self) -> float:
        """Calcula duração do buffer em segundos"""
        return round(self.BUFFER_SIZE / self.CAM_FPS, 2) if self.CAM_FPS > 0 else 0
    
    @property
    def estimated_buffer_memory_mb(self) -> float:
        """Estima uso de memória do buffer"""
        return round(
            (self.CAM_WIDTH * self.CAM_HEIGHT * 3 * self.BUFFER_SIZE) / (1024 * 1024),
            1
        )
    
    @property
    def active_preset(self) -> str:
        """Detecta preset baseado na resolução"""
        if self.CAM_WIDTH == 640 and self.CAM_HEIGHT == 480:
            return "LOW-END"
        elif self.CAM_WIDTH == 960 and self.CAM_HEIGHT == 540:
            return "BALANCED"
        elif self.CAM_WIDTH == 1280 and self.CAM_HEIGHT == 720:
            return "HIGH-END"
        elif self.CAM_WIDTH == 1920 and self.CAM_HEIGHT == 1080:
            return "ULTRA"
        return "CUSTOM"
    
    @property
    def is_rag_ready(self) -> bool:
        """Verifica se RAG está configurado"""
        if self.OLLAMA_ENABLED:
            return True
        return bool(self.OPENAI_API_KEY)

# ============================================
# INSTÂNCIA GLOBAL
# ============================================
settings = Settings()

# ============================================
# BACKWARDS COMPATIBILITY (para yolo.py)
# ============================================
FLASK_SECRET_KEY = settings.SECRET_KEY
FLASK_ENV = settings.ENVIRONMENT
FLASK_DEBUG = settings.DEBUG
FLASK_HOST = settings.HOST
FLASK_PORT = settings.PORT

VIDEO_SOURCE = settings.video_source_parsed
YOLO_MODEL_PATH = settings.YOLO_MODEL_PATH
YOLO_CONF_THRESHOLD = settings.YOLO_CONF_THRESHOLD
YOLO_TARGET_WIDTH = settings.YOLO_TARGET_WIDTH
YOLO_FRAME_STEP = settings.YOLO_FRAME_STEP
TRACKER = settings.TRACKER

CAM_WIDTH = settings.CAM_WIDTH
CAM_HEIGHT = settings.CAM_HEIGHT
CAM_FPS = settings.CAM_FPS

BUFFER_SIZE = settings.BUFFER_SIZE
GC_INTERVAL = settings.GC_INTERVAL
MEMORY_WARNING_THRESHOLD = settings.MEMORY_WARNING_THRESHOLD

MAX_OUT_TIME = settings.MAX_OUT_TIME
EMAIL_COOLDOWN = settings.EMAIL_COOLDOWN
ZONE_EMPTY_TIMEOUT = settings.ZONE_EMPTY_TIMEOUT
ZONE_FULL_TIMEOUT = settings.ZONE_FULL_TIMEOUT
ZONE_FULL_THRESHOLD = settings.ZONE_FULL_THRESHOLD

SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
EMAIL_SENDER = settings.EMAIL_SENDER
EMAIL_APP_PASSWORD = settings.EMAIL_APP_PASSWORD

BUFFER_DURATION_SECONDS = settings.buffer_duration_seconds
ESTIMATED_BUFFER_MEMORY_MB = settings.estimated_buffer_memory_mb
ACTIVE_PRESET = settings.active_preset
CORS_ENABLED = settings.ENVIRONMENT != "production"

# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print(f"✅ Config loaded: {settings.active_preset} preset")
    print(f"📹 Camera: {settings.CAM_WIDTH}x{settings.CAM_HEIGHT}@{settings.CAM_FPS}fps")
    print(f"💾 Buffer: {settings.BUFFER_SIZE} frames (~{settings.buffer_duration_seconds}s)")
    print(f"🧠 Memory: ~{settings.estimated_buffer_memory_mb} MB")
    print(f"🔐 Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    print(f"📧 Email: {settings.EMAIL_SENDER or 'not configured'}")
    print(f"🌐 CORS: {len(settings.cors_origins_list)} origins")
    print("-" * 70)
    print(f"🤖 RAG Enabled: {settings.RAG_ENABLED}")
    print(f"🤖 RAG Ready: {settings.is_rag_ready}")
    print(f"🤖 Vector Store: {settings.VECTOR_STORE_TYPE}")
    if settings.OPENAI_API_KEY:
        print(f"🤖 OpenAI: {settings.OPENAI_MODEL}")
    if settings.OLLAMA_ENABLED:
        print(f"🤖 Ollama: {settings.OLLAMA_MODEL}")
    print("=" * 70)
