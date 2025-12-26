"""
Configuration loader for ARK YOLO System
Carrega variáveis de ambiente do arquivo .env
Usa valores padrão se .env não existir (compatibilidade com desenvolvimento)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env file se existir
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Se não houver .env, tenta .env.example para desenvolvimento
    example_path = Path(__file__).parent / '.env.example'
    if example_path.exists():
        print("⚠️  Arquivo .env não encontrado. Use .env.example como template.")
        print("   cp .env.example .env  # e configure com seus valores")

# ============================================
# FLASK CONFIGURATION
# ============================================

FLASK_SECRET_KEY = os.getenv(
    'FLASK_SECRET_KEY',
    'dev-secret-key-not-for-production-change-in-production'
)
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

# ============================================
# DATABASE CONFIGURATION
# ============================================

DATABASE_PATH = os.getenv('DATABASE_PATH', 'cv_system.db')

# ============================================
# YOLO CONFIGURATION
# ============================================

YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'yolo_models/yolov8n.pt')
VIDEO_SOURCE = os.getenv('VIDEO_SOURCE', '0')

# Tenta converter para int se for número, senão usa como string (RTSP/HTTP URL)
try:
    VIDEO_SOURCE = int(VIDEO_SOURCE)
except ValueError:
    pass

YOLO_CONF_THRESHOLD = float(os.getenv('YOLO_CONF_THRESHOLD', '0.78'))
YOLO_TARGET_WIDTH = int(os.getenv('YOLO_TARGET_WIDTH', '960'))
YOLO_FRAME_STEP = int(os.getenv('YOLO_FRAME_STEP', '2'))

# ============================================
# ZONE CONFIGURATION
# ============================================

SAFE_ZONE_STR = os.getenv('SAFE_ZONE', '(400,100,700,600)')
try:
    SAFE_ZONE = eval(SAFE_ZONE_STR)  # Convert "(400,100,700,600)" to tuple
except Exception:
    SAFE_ZONE = (400, 100, 700, 600)  # Fallback

MAX_OUT_TIME = int(os.getenv('MAX_OUT_TIME', '30'))

# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD', '')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS', 'admin@example.com')
# Converte string separada por vírgula em lista
EMAIL_RECIPIENTS_LIST = [email.strip() for email in EMAIL_RECIPIENTS.split(',')]

EMAIL_COOLDOWN = int(os.getenv('EMAIL_COOLDOWN', '300'))

# ============================================
# LOGGING CONFIGURATION
# ============================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/ark_yolo.log')

# ============================================
# SECURITY CONFIGURATION
# ============================================

PASSWORD_HASH_ROUNDS = int(os.getenv('PASSWORD_HASH_ROUNDS', '10'))
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '1440'))  # minutes
CORS_ENABLED = os.getenv('CORS_ENABLED', 'false').lower() == 'true'

# ============================================
# PERFORMANCE CONFIGURATION
# ============================================

USE_GPU = os.getenv('USE_GPU', 'true').lower() == 'true'
WORKER_THREADS = int(os.getenv('WORKER_THREADS', '4'))
MAX_CONCURRENT_FRAMES = int(os.getenv('MAX_CONCURRENT_FRAMES', '2'))

# ============================================
# DEVELOPMENT CONFIGURATION
# ============================================

DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
VERBOSE_ERRORS = os.getenv('VERBOSE_ERRORS', 'false').lower() == 'true'
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'

# ============================================
# OPTIONAL: IP CAMERA CONFIGURATION
# ============================================

CAMERA_USERNAME = os.getenv('CAMERA_USERNAME', '')
CAMERA_PASSWORD = os.getenv('CAMERA_PASSWORD', '')

# ============================================
# VALIDATION & WARNINGS
# ============================================

def validate_config():
    """Valida configurações críticas e emite avisos"""
    errors = []
    warnings = []
    
    # Erros críticos (bloqueiam inicialização)
    if FLASK_ENV == 'production' and FLASK_SECRET_KEY == 'dev-secret-key-not-for-production-change-in-production':
        errors.append("❌ Em produção: defina FLASK_SECRET_KEY segura em .env")
    
    if FLASK_ENV == 'production' and not EMAIL_APP_PASSWORD:
        warnings.append("⚠️  EMAIL_APP_PASSWORD não configurado - alertas por email desabilitados")
    
    if not os.path.exists(YOLO_MODEL_PATH):
        errors.append(f"❌ Modelo YOLO não encontrado: {YOLO_MODEL_PATH}")
    
    if YOLO_CONF_THRESHOLD < 0.5 or YOLO_CONF_THRESHOLD > 1.0:
        errors.append("❌ YOLO_CONF_THRESHOLD deve estar entre 0.5 e 1.0")
    
    # Avisos
    if FLASK_DEBUG and FLASK_ENV == 'production':
        warnings.append("⚠️  FLASK_DEBUG=true em produção - desabilite para segurança")
    
    if DEBUG_MODE and FLASK_ENV == 'production':
        warnings.append("⚠️  DEBUG_MODE=true em produção - desabilite para segurança")
    
    if VERBOSE_ERRORS and FLASK_ENV == 'production':
        warnings.append("⚠️  VERBOSE_ERRORS=true em produção - pode expor informações sensíveis")
    
    return errors, warnings


def print_config_summary():
    """Exibe resumo da configuração no startup"""
    print("\n" + "="*60)
    print("🔧 ARK YOLO Configuration Summary")
    print("="*60)
    print(f"Environment: {FLASK_ENV.upper()}")
    print(f"Debug: {FLASK_DEBUG}")
    print(f"Flask Port: {FLASK_PORT}")
    print(f"Database: {DATABASE_PATH}")
    print(f"YOLO Model: {YOLO_MODEL_PATH}")
    print(f"Confidence Threshold: {YOLO_CONF_THRESHOLD}")
    print(f"Target Width: {YOLO_TARGET_WIDTH}px")
    print(f"Frame Step: {YOLO_FRAME_STEP}")
    print(f"Safe Zone: {SAFE_ZONE}")
    print(f"Max Out Time: {MAX_OUT_TIME}s")
    print(f"Email Configured: {'✅' if EMAIL_APP_PASSWORD else '❌'}")
    print(f"Use GPU: {USE_GPU}")
    print("="*60 + "\n")


if __name__ == '__main__':
    # Teste as configurações
    errors, warnings = validate_config()
    
    if errors:
        print("\n❌ ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️  AVISOS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors:
        print("✅ Configuração válida!")
        print_config_summary()
    else:
        print("\n❌ Por favor, corrija os erros acima antes de iniciar a aplicação.")
        exit(1)
