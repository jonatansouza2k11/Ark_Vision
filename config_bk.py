"""
Configuration loader for ARK YOLO System
Carrega variáveis de ambiente do arquivo .env
Usa valores padrão se .env não existir (compatibilidade com desenvolvimento)

✨ v2.0: Adicionado suporte a memory management e configurações otimizadas
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

YOLO_CONF_THRESHOLD = float(os.getenv('YOLO_CONF_THRESHOLD', '0.87'))
YOLO_TARGET_WIDTH = int(os.getenv('YOLO_TARGET_WIDTH', '960'))
YOLO_FRAME_STEP = int(os.getenv('YOLO_FRAME_STEP', '2'))


# ============================================
# TRACKER CONFIGURATION
# ============================================

TRACKER = os.getenv('TRACKER', 'botsort.yaml')

# Valida tracker
if TRACKER not in ('botsort.yaml', 'bytetrack.yaml'):
    print(f"⚠️  TRACKER inválido '{TRACKER}', usando 'botsort.yaml'")
    TRACKER = 'botsort.yaml'


# ============================================
# CAMERA CONFIGURATION
# ============================================

CAM_WIDTH = int(os.getenv('CAM_WIDTH', '960'))
CAM_HEIGHT = int(os.getenv('CAM_HEIGHT', '540'))
CAM_FPS = int(os.getenv('CAM_FPS', '30'))


# ============================================
# MEMORY MANAGEMENT CONFIGURATION
# ============================================
# ✨ NOVO: Configurações de gerenciamento de memória

BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', '40'))
GC_INTERVAL = int(os.getenv('GC_INTERVAL', '50'))
MEMORY_WARNING_THRESHOLD = int(os.getenv('MEMORY_WARNING_THRESHOLD', '1024'))

# Validação de limites
if BUFFER_SIZE < 10:
    print(f"⚠️  BUFFER_SIZE muito baixo ({BUFFER_SIZE}), usando mínimo de 10")
    BUFFER_SIZE = 10
elif BUFFER_SIZE > 120:
    print(f"⚠️  BUFFER_SIZE muito alto ({BUFFER_SIZE}), usando máximo de 120")
    BUFFER_SIZE = 120

if GC_INTERVAL < 10:
    print(f"⚠️  GC_INTERVAL muito baixo ({GC_INTERVAL}), usando mínimo de 10")
    GC_INTERVAL = 10
elif GC_INTERVAL > 200:
    print(f"⚠️  GC_INTERVAL muito alto ({GC_INTERVAL}), usando máximo de 200")
    GC_INTERVAL = 200

if MEMORY_WARNING_THRESHOLD < 256:
    print(f"⚠️  MEMORY_WARNING_THRESHOLD muito baixo ({MEMORY_WARNING_THRESHOLD}), usando mínimo de 256 MB")
    MEMORY_WARNING_THRESHOLD = 256
elif MEMORY_WARNING_THRESHOLD > 4096:
    print(f"⚠️  MEMORY_WARNING_THRESHOLD muito alto ({MEMORY_WARNING_THRESHOLD}), usando máximo de 4096 MB")
    MEMORY_WARNING_THRESHOLD = 4096


# ============================================
# ZONE CONFIGURATION
# ============================================

SAFE_ZONE_STR = os.getenv('SAFE_ZONE', '[]')
try:
    # Tenta carregar como JSON primeiro (novo formato)
    import json
    SAFE_ZONE = json.loads(SAFE_ZONE_STR)
except Exception:
    # Fallback para formato antigo (tuple)
    try:
        SAFE_ZONE = eval(SAFE_ZONE_STR)
    except Exception:
        SAFE_ZONE = []  # Lista vazia se falhar

MAX_OUT_TIME = float(os.getenv('MAX_OUT_TIME', '30'))
EMAIL_COOLDOWN = float(os.getenv('EMAIL_COOLDOWN', '600'))
BUFFER_SECONDS = float(os.getenv('BUFFER_SECONDS', '2.0'))

# ✨ NOVO: Parâmetros de zona inteligente
ZONE_EMPTY_TIMEOUT = float(os.getenv('ZONE_EMPTY_TIMEOUT', '10.0'))
ZONE_FULL_TIMEOUT = float(os.getenv('ZONE_FULL_TIMEOUT', '20.0'))
ZONE_FULL_THRESHOLD = int(os.getenv('ZONE_FULL_THRESHOLD', '5'))


# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD', '')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'

EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS', '')
# Converte string separada por vírgula em lista
if EMAIL_RECIPIENTS:
    EMAIL_RECIPIENTS_LIST = [email.strip() for email in EMAIL_RECIPIENTS.split(',')]
else:
    EMAIL_RECIPIENTS_LIST = []


# ============================================
# LOGGING CONFIGURATION
# ============================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/ark_yolo.log')

# Cria diretório de logs se não existir
log_dir = Path(LOG_FILE).parent
log_dir.mkdir(parents=True, exist_ok=True)


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
# DERIVED SETTINGS
# ============================================
# ✨ NOVO: Configurações derivadas calculadas automaticamente

# Calcula buffer em segundos baseado em BUFFER_SIZE e CAM_FPS
BUFFER_DURATION_SECONDS = round(BUFFER_SIZE / CAM_FPS, 2) if CAM_FPS > 0 else 0

# Estima uso de memória esperado (rough estimate)
# Frame size: width * height * 3 (RGB) * buffer_size
ESTIMATED_BUFFER_MEMORY_MB = round((CAM_WIDTH * CAM_HEIGHT * 3 * BUFFER_SIZE) / (1024 * 1024), 1)

# Detecta preset baseado nas configurações
def detect_preset():
    """Detecta qual preset está sendo usado baseado nas configurações"""
    if CAM_WIDTH == 640 and CAM_HEIGHT == 480 and GC_INTERVAL == 30:
        return "LOW-END"
    elif CAM_WIDTH == 960 and CAM_HEIGHT == 540 and GC_INTERVAL == 50:
        return "BALANCED"
    elif CAM_WIDTH == 1280 and CAM_HEIGHT == 720 and GC_INTERVAL == 75:
        return "HIGH-END"
    elif CAM_WIDTH == 1920 and CAM_HEIGHT == 1080 and GC_INTERVAL == 100:
        return "ULTRA"
    else:
        return "CUSTOM"

ACTIVE_PRESET = detect_preset()


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
    
    # ✨ NOVO: Validações de memory management
    if ESTIMATED_BUFFER_MEMORY_MB > 200:
        warnings.append(f"⚠️  Buffer de memória estimado alto: {ESTIMATED_BUFFER_MEMORY_MB} MB - considere reduzir BUFFER_SIZE ou resolução")
    
    if MEMORY_WARNING_THRESHOLD < ESTIMATED_BUFFER_MEMORY_MB * 3:
        warnings.append(f"⚠️  MEMORY_WARNING_THRESHOLD ({MEMORY_WARNING_THRESHOLD} MB) pode ser muito baixo para buffer ({ESTIMATED_BUFFER_MEMORY_MB} MB)")
    
    # Validações de câmera
    if CAM_WIDTH < 320 or CAM_HEIGHT < 240:
        warnings.append(f"⚠️  Resolução muito baixa ({CAM_WIDTH}x{CAM_HEIGHT}) - qualidade de detecção pode ser afetada")
    
    if CAM_WIDTH > 1920 or CAM_HEIGHT > 1080:
        warnings.append(f"⚠️  Resolução muito alta ({CAM_WIDTH}x{CAM_HEIGHT}) - alto uso de memória e CPU")
    
    if CAM_FPS > 60:
        warnings.append(f"⚠️  FPS muito alto ({CAM_FPS}) - geralmente 30 fps é suficiente para vigilância")
    
    # Validação de YOLO
    if YOLO_TARGET_WIDTH > CAM_WIDTH:
        warnings.append(f"⚠️  YOLO_TARGET_WIDTH ({YOLO_TARGET_WIDTH}) maior que CAM_WIDTH ({CAM_WIDTH}) - processamento desnecessário")
    
    if YOLO_FRAME_STEP > 5:
        warnings.append(f"⚠️  YOLO_FRAME_STEP ({YOLO_FRAME_STEP}) muito alto - pode perder movimentos rápidos")
    
    return errors, warnings


def print_config_summary():
    """Exibe resumo da configuração no startup"""
    print("\n" + "="*70)
    print("🔧 ARK YOLO Configuration Summary")
    print("="*70)
    print(f"Environment      : {FLASK_ENV.upper()}")
    print(f"Debug Mode       : {FLASK_DEBUG}")
    print(f"Flask Port       : {FLASK_PORT}")
    print(f"Database         : {DATABASE_PATH}")
    print("-" * 70)
    print(f"YOLO Model       : {os.path.basename(YOLO_MODEL_PATH)}")
    print(f"Video Source     : {VIDEO_SOURCE}")
    print(f"Confidence       : {YOLO_CONF_THRESHOLD}")
    print(f"Target Width     : {YOLO_TARGET_WIDTH}px")
    print(f"Frame Step       : 1/{YOLO_FRAME_STEP} frames")
    print(f"Tracker          : {TRACKER}")
    print("-" * 70)
    print(f"Camera Resolution: {CAM_WIDTH}x{CAM_HEIGHT} @{CAM_FPS}fps")
    print(f"Active Preset    : {ACTIVE_PRESET}")
    print("-" * 70)
    print(f"Buffer Size      : {BUFFER_SIZE} frames (~{BUFFER_DURATION_SECONDS}s)")
    print(f"Buffer Memory    : ~{ESTIMATED_BUFFER_MEMORY_MB} MB")
    print(f"GC Interval      : Every {GC_INTERVAL} frames")
    print(f"Memory Warning   : {MEMORY_WARNING_THRESHOLD} MB")
    print("-" * 70)
    print(f"Max Out Time     : {MAX_OUT_TIME}s")
    print(f"Email Cooldown   : {EMAIL_COOLDOWN}s")
    print(f"Zone Empty Time  : {ZONE_EMPTY_TIMEOUT}s")
    print(f"Zone Full Time   : {ZONE_FULL_TIMEOUT}s")
    print(f"Zone Full Thresh : {ZONE_FULL_THRESHOLD} people")
    print("-" * 70)
    print(f"Email Configured : {'✅' if EMAIL_APP_PASSWORD else '❌'}")
    print(f"Email Recipients : {len(EMAIL_RECIPIENTS_LIST)} recipient(s)")
    print(f"Use GPU          : {USE_GPU}")
    print(f"Worker Threads   : {WORKER_THREADS}")
    print("="*70 + "\n")


def print_memory_recommendations():
    """✨ NOVO: Imprime recomendações de memória baseado na config"""
    print("\n" + "💡 Memory Usage Recommendations")
    print("="*70)
    
    # Estimativa total de RAM
    model_memory = 150  # MB (yolov8n)
    opencv_memory = 150  # MB
    flask_memory = 80   # MB
    tracking_memory = 40  # MB
    
    total_base = model_memory + opencv_memory + flask_memory + tracking_memory
    total_with_buffer = total_base + ESTIMATED_BUFFER_MEMORY_MB
    peak_memory = total_with_buffer * 1.5  # Estimativa de pico
    
    print(f"Estimated RAM Usage:")
    print(f"  Base (YOLO + OpenCV + Flask): ~{total_base} MB")
    print(f"  + Buffer ({BUFFER_SIZE} frames): +{ESTIMATED_BUFFER_MEMORY_MB} MB")
    print(f"  = Normal Operation: ~{total_with_buffer} MB")
    print(f"  Peak (with alerts): ~{int(peak_memory)} MB")
    print("-" * 70)
    
    if peak_memory < 512:
        print("✅ Configuração LEVE - adequada para sistemas com 2GB+ RAM")
    elif peak_memory < 1024:
        print("✅ Configuração BALANCEADA - adequada para sistemas com 4GB+ RAM")
    elif peak_memory < 1536:
        print("⚠️  Configuração ALTA - recomendado 8GB+ RAM")
    else:
        print("⚠️  Configuração MUITO ALTA - recomendado 16GB+ RAM")
    
    print("="*70 + "\n")


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
        print_memory_recommendations()
    else:
        print("\n❌ Por favor, corrija os erros acima antes de iniciar a aplicação.")
        exit(1)
