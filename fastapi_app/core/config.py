"""
FastAPI Configuration
Migrado do Flask mantendo compatibilidade com .env existente
Usa Pydantic Settings para validação automática
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Union
from pathlib import Path
import os
import json

# ============================================
# FORÇAR CARREGAMENTO DO .env.fastapi
# ============================================
from dotenv import load_dotenv

# Carregar .env.fastapi ANTES de criar a classe Settings
env_path = Path(__file__).parent.parent.parent / ".env.fastapi"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ .env.fastapi carregado de: {env_path}")
else:
    print(f"⚠️  .env.fastapi NÃO encontrado em: {env_path}")


class Settings(BaseSettings):
    """
    Configurações FastAPI
    Lê do .env.fastapi (ou .env como fallback)
    Mantém compatibilidade com variáveis do Flask original
    """
    
    # ============================================
    # FASTAPI APPLICATION
    # ============================================
    ENVIRONMENT: str = Field(default='development')
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default='0.0.0.0')
    PORT: int = Field(default=8000)
    
    # SECRET_KEY
    SECRET_KEY: str = Field(
        default='dev-secret-key-not-for-production-change-in-production'
    )
    ALGORITHM: str = Field(default='HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)
    
    # ============================================
    # DATABASE
    # ============================================
    DATABASE_URL: str = Field(
        default='postgresql://postgres:postgres@localhost:5432/ark_yolo'
    )
    
    # Manter DATABASE_PATH para fallback SQLite se necessário
    DATABASE_PATH: str = Field(default='cv_system_fastapi.db')
    
    # ============================================
    # YOLO CONFIGURATION
    # ============================================
    YOLO_MODEL_PATH: str = Field(default='yolo_models/yolov8n.pt')
    VIDEO_SOURCE: Union[int, str] = Field(default='0')
    YOLO_CONF_THRESHOLD: float = Field(default=0.87)
    YOLO_TARGET_WIDTH: int = Field(default=960)
    YOLO_FRAME_STEP: int = Field(default=2)
    
    @field_validator('VIDEO_SOURCE', mode='before')
    @classmethod
    def parse_video_source(cls, v):
        """Converte para int se número, senão string (RTSP/HTTP)"""
        try:
            return int(v)
        except (ValueError, TypeError):
            return str(v)
    
    # ============================================
    # TRACKER
    # ============================================
    TRACKER: str = Field(default='botsort.yaml')
    
    @field_validator('TRACKER')
    @classmethod
    def validate_tracker(cls, v):
        if v not in ('botsort.yaml', 'bytetrack.yaml'):
            print(f"⚠️  TRACKER inválido '{v}', usando 'botsort.yaml'")
            return 'botsort.yaml'
        return v
    
    # ============================================
    # CAMERA
    # ============================================
    CAM_WIDTH: int = Field(default=960)
    CAM_HEIGHT: int = Field(default=540)
    CAM_FPS: int = Field(default=30)
    
    # ============================================
    # MEMORY MANAGEMENT
    # ============================================
    BUFFER_SIZE: int = Field(default=40, ge=10, le=120)
    GC_INTERVAL: int = Field(default=50, ge=10, le=200)
    MEMORY_WARNING_THRESHOLD: int = Field(default=1024, ge=256, le=4096)
    
    # ============================================
    # ZONE CONFIGURATION
    # ============================================
    SAFE_ZONE: str = Field(default='[]')
    MAX_OUT_TIME: float = Field(default=30.0)
    EMAIL_COOLDOWN: float = Field(default=600.0)
    BUFFER_SECONDS: float = Field(default=2.0)
    ZONE_EMPTY_TIMEOUT: float = Field(default=10.0)
    ZONE_FULL_TIMEOUT: float = Field(default=20.0)
    ZONE_FULL_THRESHOLD: int = Field(default=5)
    
    @field_validator('SAFE_ZONE', mode='before')
    @classmethod
    def parse_safe_zone(cls, v):
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        try:
            json.loads(v)
            return v
        except:
            try:
                return json.dumps(eval(v))
            except:
                return '[]'
    
    @property
    def SAFE_ZONE_LIST(self) -> list:
        try:
            return json.loads(self.SAFE_ZONE)
        except:
            return []
    
    # ============================================
    # EMAIL
    # ============================================
    EMAIL_SENDER: str = Field(default='')
    EMAIL_APP_PASSWORD: str = Field(default='')
    SMTP_SERVER: str = Field(default='smtp.gmail.com')
    SMTP_PORT: int = Field(default=587)
    SMTP_USE_TLS: bool = Field(default=True)
    SMTP_USE_SSL: bool = Field(default=False)
    EMAIL_RECIPIENTS: str = Field(default='')
    
    @property
    def EMAIL_RECIPIENTS_LIST(self) -> List[str]:
        if not self.EMAIL_RECIPIENTS:
            return []
        return [email.strip() for email in self.EMAIL_RECIPIENTS.split(',')]
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = Field(default='INFO')
    LOG_FILE: str = Field(default='logs/ark_yolo_fastapi.log')
    
    # ============================================
    # SECURITY
    # ============================================
    PASSWORD_HASH_ROUNDS: int = Field(default=10)
    SESSION_TIMEOUT: int = Field(default=1440)
    
    # ============================================
    # PERFORMANCE
    # ============================================
    USE_GPU: bool = Field(default=True)
    WORKER_THREADS: int = Field(default=4)
    MAX_CONCURRENT_FRAMES: int = Field(default=2)
    
    # ============================================
    # DEVELOPMENT
    # ============================================
    DEBUG_MODE: bool = Field(default=False)
    VERBOSE_ERRORS: bool = Field(default=False)
    TEST_MODE: bool = Field(default=False)
    
    # ============================================
    # IP CAMERA CREDENTIALS
    # ============================================
    CAMERA_USERNAME: str = Field(default='')
    CAMERA_PASSWORD: str = Field(default='')
    
    # ============================================
    # CORS (FastAPI specific)
    # ============================================
    CORS_ORIGINS: str = Field(
        default='http://localhost:3000,http://localhost:5173,http://localhost:5000'
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
    
    # ============================================
    # DERIVED PROPERTIES (calculadas automaticamente)
    # ============================================
    
    @property
    def BUFFER_DURATION_SECONDS(self) -> float:
        """Duração do buffer em segundos"""
        if self.CAM_FPS > 0:
            return round(self.BUFFER_SIZE / self.CAM_FPS, 2)
        return 0.0
    
    @property
    def ESTIMATED_BUFFER_MEMORY_MB(self) -> float:
        """Memória estimada do buffer em MB"""
        bytes_per_frame = self.CAM_WIDTH * self.CAM_HEIGHT * 3
        total_bytes = bytes_per_frame * self.BUFFER_SIZE
        return round(total_bytes / (1024 * 1024), 1)
    
    @property
    def ACTIVE_PRESET(self) -> str:
        """Detecta preset ativo"""
        if self.CAM_WIDTH == 640 and self.CAM_HEIGHT == 480 and self.GC_INTERVAL == 30:
            return "LOW-END"
        elif self.CAM_WIDTH == 960 and self.CAM_HEIGHT == 540 and self.GC_INTERVAL == 50:
            return "BALANCED"
        elif self.CAM_WIDTH == 1280 and self.CAM_HEIGHT == 720 and self.GC_INTERVAL == 75:
            return "HIGH-END"
        elif self.CAM_WIDTH == 1920 and self.CAM_HEIGHT == 1080 and self.GC_INTERVAL == 100:
            return "ULTRA"
        else:
            return "CUSTOM"
    
    class Config:
        env_file = ".env.fastapi"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"
        validate_assignment = True


# ============================================
# SINGLETON
# ============================================
settings = Settings()

# Criar diretório de logs
Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)


# ============================================
# VALIDATION
# ============================================

def validate_settings():
    """Valida configurações críticas"""
    errors = []
    warnings = []
    
    # Erros críticos
    if settings.ENVIRONMENT == 'production' and 'dev-secret-key' in settings.SECRET_KEY:
        errors.append("❌ Em produção: defina SECRET_KEY segura")
    
    if settings.ENVIRONMENT == 'production' and not settings.EMAIL_APP_PASSWORD:
        warnings.append("⚠️  EMAIL_APP_PASSWORD não configurado")
    
    if not os.path.exists(settings.YOLO_MODEL_PATH):
        warnings.append(f"⚠️  Modelo YOLO não encontrado: {settings.YOLO_MODEL_PATH}")
    
    if settings.YOLO_CONF_THRESHOLD < 0.5 or settings.YOLO_CONF_THRESHOLD > 1.0:
        errors.append("❌ YOLO_CONF_THRESHOLD deve estar entre 0.5 e 1.0")
    
    # Avisos de segurança
    if settings.DEBUG and settings.ENVIRONMENT == 'production':
        warnings.append("⚠️  DEBUG=true em produção")
    
    # Avisos de memória
    if settings.ESTIMATED_BUFFER_MEMORY_MB > 200:
        warnings.append(f"⚠️  Buffer alto: {settings.ESTIMATED_BUFFER_MEMORY_MB} MB")
    
    # Avisos de câmera
    if settings.CAM_WIDTH < 320 or settings.CAM_HEIGHT < 240:
        warnings.append(f"⚠️  Resolução baixa ({settings.CAM_WIDTH}x{settings.CAM_HEIGHT})")
    
    if settings.CAM_WIDTH > 1920:
        warnings.append(f"⚠️  Resolução alta ({settings.CAM_WIDTH}x{settings.CAM_HEIGHT})")
    
    if settings.CAM_FPS > 60:
        warnings.append(f"⚠️  FPS alto ({settings.CAM_FPS})")
    
    # Avisos YOLO
    if settings.YOLO_TARGET_WIDTH > settings.CAM_WIDTH:
        warnings.append("⚠️  YOLO_TARGET_WIDTH > CAM_WIDTH")
    
    if settings.YOLO_FRAME_STEP > 5:
        warnings.append(f"⚠️  YOLO_FRAME_STEP alto ({settings.YOLO_FRAME_STEP})")
    
    return errors, warnings


def print_settings():
    """Exibe resumo das configurações"""
    print("="*70)
    print("⚙️  ARK YOLO FastAPI - Configuration")
    print("="*70)
    print(f"Environment      : {settings.ENVIRONMENT.upper()}")
    print(f"Debug            : {settings.DEBUG}")
    print(f"Host:Port        : {settings.HOST}:{settings.PORT}")
    
    # Detectar tipo de banco
    if settings.DATABASE_URL.startswith('postgresql'):
        db_name = settings.DATABASE_URL.split('/')[-1]
        print(f"Database         : PostgreSQL - {db_name}")
    else:
        print(f"Database         : SQLite - {settings.DATABASE_PATH}")
    
    print("-" * 70)
    print(f"YOLO Model       : {os.path.basename(settings.YOLO_MODEL_PATH)}")
    print(f"Video Source     : {settings.VIDEO_SOURCE}")
    print(f"Confidence       : {settings.YOLO_CONF_THRESHOLD}")
    print(f"Target Width     : {settings.YOLO_TARGET_WIDTH}px")
    print(f"Frame Step       : 1/{settings.YOLO_FRAME_STEP}")
    print(f"Tracker          : {settings.TRACKER}")
    print("-" * 70)
    print(f"Resolution       : {settings.CAM_WIDTH}x{settings.CAM_HEIGHT} @ {settings.CAM_FPS}fps")
    print(f"Preset           : {settings.ACTIVE_PRESET}")
    print("-" * 70)
    print(f"Buffer           : {settings.BUFFER_SIZE} frames (~{settings.BUFFER_DURATION_SECONDS}s)")
    print(f"Buffer Memory    : ~{settings.ESTIMATED_BUFFER_MEMORY_MB} MB")
    print(f"GC Interval      : {settings.GC_INTERVAL} frames")
    print(f"Memory Threshold : {settings.MEMORY_WARNING_THRESHOLD} MB")
    print("-" * 70)
    print(f"Max Out Time     : {settings.MAX_OUT_TIME}s")
    print(f"Email Cooldown   : {settings.EMAIL_COOLDOWN}s")
    print(f"Email Active     : {'✅' if settings.EMAIL_APP_PASSWORD else '❌'}")
    print(f"Recipients       : {len(settings.EMAIL_RECIPIENTS_LIST)}")
    print(f"GPU Enabled      : {settings.USE_GPU}")
    print("="*70)


if __name__ == '__main__':
    errors, warnings = validate_settings()
    
    if errors:
        print("\n❌ ERROS:")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  AVISOS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors:
        print("\n✅ Configuração válida!")
        print_settings()
    else:
        print("\n❌ Corrija os erros acima.")
        exit(1)
