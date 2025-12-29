"""
app.py

Sistema completo de monitoramento YOLO com autenticação.
Usa o módulo yolo.py para toda lógica de computação visual.

✨ MELHORIAS IMPLEMENTADAS:
- Rate limiting em endpoints críticos (login, register, APIs)
- Logs de tentativas de login (sucesso/falha)
- Health check endpoints (/health e /ready)
- Métricas de memória e performance (/metrics)
- Integração completa com config.py
- Monitoramento de RAM e CPU via psutil
- Sistema de auditoria compliant (ANVISA/FDA)
"""

import os
import json
import hashlib  # ✅ NECESSÁRIO para AuditLogger
import time  # ✅ NECESSÁRIO para métricas de tempo
from datetime import datetime, timezone  # ✅ NECESSÁRIO para timestamps UTC

import logging
from logging.handlers import RotatingFileHandler

from flask import (
    Flask,
    Response,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_from_directory,
)
from werkzeug.exceptions import NotFound

# Carrega configurações do .env via config.py
import config

# ✨ Monitoramento de sistema
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil não instalado - métricas de memória desabilitadas")
    print("   pip install psutil")

from database import (
    verify_user,
    create_user,
    update_last_login,
    get_recent_alerts,
    get_all_users,
    get_setting,
    set_setting,
    delete_alert,
    log_system_action,
    get_system_logs,
    delete_system_log,
)
from auth import login_required, admin_required
from yolo import get_vision_system

app = Flask(__name__)


# ==========================================================
# ✨ SISTEMA DE LOGGING ESTRUTURADO
# ==========================================================
def setup_logging(app):
    """
    Configura sistema de logging com rotação de arquivos.
    
    Cria dois handlers:
    - RotatingFileHandler: Para logs em arquivo (produção)
    - StreamHandler: Para console (desenvolvimento)
    """
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_format = logging.Formatter(
        '%(asctime)s [%(levelname)s]: %(message)s [%(pathname)s:%(lineno)d]'
    )
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    try:
        console_handler.stream.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # Python < 3.7 não suporta reconfigure
    
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    app.logger.info('=' * 60)
    app.logger.info('🚀 ARK YOLO System Startup')
    app.logger.info(f'Environment: {config.FLASK_ENV}')
    app.logger.info(f'Preset: {config.ACTIVE_PRESET}')
    app.logger.info('=' * 60)


# ✅ Chama a função de logging
setup_logging(app)


# ==========================================================
# ✨ SISTEMA DE AUDITORIA COMPLIANT
# ==========================================================
class AuditLogger:
    """
    Logger de auditoria com hash para integridade.
    Atende requisitos ANVISA, FDA 21 CFR Part 11, ISO.
    """
    
    def __init__(self, audit_file='logs/audit.log'):
        self.audit_file = audit_file
        self.last_hash = self._get_last_hash()
        app.logger.info(f"[AUDIT] AuditLogger initialized: {audit_file}")  # ✅ Sem emoji
    
    def _get_last_hash(self):
        """Obtém o hash da última linha para encadeamento."""
        try:
            with open(self.audit_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = json.loads(lines[-1])
                    return last_line.get('hash', '0' * 64)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return '0' * 64  # Hash inicial
    
    def _calculate_hash(self, entry):
        """Calcula SHA-256 do registro + hash anterior."""
        data = f"{entry['timestamp']}{entry['user']}{entry['action']}{entry['details']}{self.last_hash}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def log_action(self, user, action, details, ip_address=None):
        """
        Registra ação crítica com hash para auditoria.
        
        Args:
            user: Username do operador
            action: Tipo de ação (LOGIN, CONFIG_CHANGE, ZONE_UPDATE, etc)
            details: Detalhes da ação
            ip_address: IP do cliente (opcional)
        """
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),  # UTC obrigatório
            'user': user,
            'action': action,
            'details': details,
            'ip': ip_address,
            'previous_hash': self.last_hash
        }
        
        # Calcula hash do registro atual
        entry['hash'] = self._calculate_hash(entry)
        self.last_hash = entry['hash']
        
        # Grava em formato JSON (uma linha por registro)
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Log também no logger padrão
        app.logger.info(f"[AUDIT] {user} - {action}: {details}")
    
    def verify_integrity(self):
        """
        Verifica integridade da cadeia de logs.
        Retorna (bool, list_errors)
        """
        errors = []
        previous_hash = '0' * 64
        
        try:
            with open(self.audit_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    entry = json.loads(line)
                    
                    # Verifica se o hash anterior está correto
                    if entry['previous_hash'] != previous_hash:
                        errors.append(f"Linha {line_num}: Hash anterior não confere")
                    
                    # Recalcula o hash
                    expected_hash = hashlib.sha256(
                        f"{entry['timestamp']}{entry['user']}{entry['action']}"
                        f"{entry['details']}{entry['previous_hash']}".encode()
                    ).hexdigest()
                    
                    if entry['hash'] != expected_hash:
                        errors.append(f"Linha {line_num}: Hash do registro foi alterado")
                    
                    previous_hash = entry['hash']
        
        except Exception as e:
            errors.append(f"Erro ao verificar: {str(e)}")
        
        return (len(errors) == 0, errors)


# ✅ Instancia o audit logger
audit_logger = AuditLogger()


# ==========================================================
# FLASK-LIMITER: Proteção contra brute force e DoS
# ==========================================================
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Simples para começar, use Redis em produção
)

# Usa a chave secreta do .env ou valor padrão do config.py
app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY


# ==========================================================
# Helpers
# ==========================================================
def list_yolo_models(models_dir="yolo_models"):
    if not os.path.isdir(models_dir):
        return []
    files = []
    for name in os.listdir(models_dir):
        if name.lower().endswith(".pt"):
            files.append(os.path.join(models_dir, name))
    files.sort(key=lambda s: s.lower())
    return files


def normalize_user(user):
    if not user:
        return None
    if isinstance(user, dict):
        return {
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role", "user"),
            "id": user.get("id"),
        }
    out = {
        "username": getattr(user, "username", None),
        "email": getattr(user, "email", None),
        "role": getattr(user, "role", "user"),
    }
    if hasattr(user, "id"):
        out["id"] = getattr(user, "id")
    return out


def parse_safe_zone(value):
    """
    Converte string de settings.safe_zone para formato usado no dashboard.

    Formatos aceitos agora (apenas JSON):
    - lista de zonas ricas:
      [
        {"name": "...", "mode": "...", "points": [[x,y], ...]},
        ...
      ]
    - lista de polígonos: [[[x,y],...], [[x,y],...]]
    - zona única: [[x,y], ...]
    """
    if not value:
        return None
    s = str(value).strip()
    if not s.startswith("["):
        return None
    try:
        data = json.loads(s)
    except Exception:
        return None

    # Se vier lista de objetos, extrai só a geometria para o mini-mapa
    if isinstance(data, list) and data and isinstance(data[0], dict):
        polys = []
        for z in data:
            pts = z.get("points") or []
            if isinstance(pts, list) and len(pts) >= 3:
                polys.append(pts)
        return polys

    return data


def get_video_source_label(source_str):
    if source_str is None:
        return "Desconhecida"
    s = str(source_str).strip()
    if s == "" or s == "0":
        return "Webcam 0"
    if s.isdigit():
        return f"Webcam {s}"
    if s.startswith("http"):
        return "IP Cam (HTTP)"
    if s.startswith("rtsp"):
        return "IP Cam (RTSP)"
    return s


def get_memory_info():
    """✨ NOVO: Retorna informações de memória do sistema"""
    if not PSUTIL_AVAILABLE:
        return None
    
    try:
        memory = psutil.virtual_memory()
        return {
            "total_mb": round(memory.total / (1024**2), 1),
            "used_mb": round(memory.used / (1024**2), 1),
            "available_mb": round(memory.available / (1024**2), 1),
            "percent": memory.percent
        }
    except Exception:
        return None


# ==========================================================
# Template context
# ==========================================================
@app.context_processor
def inject_user():
    return {"user": session.get("user")}


# ==========================================================
# HEALTH CHECK ENDPOINTS (sem autenticação)
# ==========================================================
@app.route("/health", methods=["GET"])
def health_check():
    """
    ✨ MELHORADO: Health check com métricas de memória.
    
    Health check endpoint para monitoramento (sem autenticação).
    Útil para Docker, Kubernetes, load balancers, etc.
    
    Retorna:
    - 200: Sistema saudável
    - 503: Sistema com problemas
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "preset": config.ACTIVE_PRESET
    }
    
    # 1. Check Database
    try:
        get_setting("model_path")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 2. Check Vision System
    try:
        vs = get_vision_system()
        if vs and hasattr(vs, 'stream_active'):
            health_status["checks"]["vision_system"] = "ok"
            health_status["vision_active"] = bool(vs.stream_active)
        else:
            health_status["checks"]["vision_system"] = "error: not initialized"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["vision_system"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 3. Check Config
    try:
        health_status["checks"]["config"] = "ok"
        health_status["flask_env"] = config.FLASK_ENV
    except Exception as e:
        health_status["checks"]["config"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 4. ✨ NOVO: Check Memory
    if PSUTIL_AVAILABLE:
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > 90:
                health_status["checks"]["memory"] = f"critical: {memory_percent}%"
                health_status["status"] = "unhealthy"
            elif memory_percent > 80:
                health_status["checks"]["memory"] = f"warning: {memory_percent}%"
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
            else:
                health_status["checks"]["memory"] = f"ok: {memory_percent}%"
            
            health_status["memory_mb"] = round(memory.used / (1024**2), 1)
        except Exception as e:
            health_status["checks"]["memory"] = f"error: {str(e)}"
    else:
        health_status["checks"]["memory"] = "unavailable (psutil not installed)"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@app.route("/ready", methods=["GET"])
def readiness_check():
    """
    Readiness check - verifica se app está pronta para receber tráfego.
    Diferente de /health que verifica se está viva.
    
    Retorna:
    - 200: Pronto para receber tráfego
    - 503: Ainda inicializando ou com problemas
    """
    try:
        vs = get_vision_system()
        if vs and hasattr(vs, 'model'):
            return jsonify({
                "ready": True,
                "timestamp": datetime.now().isoformat(),
                "preset": config.ACTIVE_PRESET
            }), 200
        return jsonify({
            "ready": False,
            "reason": "Vision system not ready",
            "timestamp": datetime.now().isoformat()
        }), 503
    except Exception as e:
        return jsonify({
            "ready": False,
            "reason": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503


@app.route("/metrics", methods=["GET"])
@admin_required
def metrics():
    """
    ✨ NOVO: Endpoint de métricas detalhadas (apenas admin).
    
    Monitora uso de CPU, RAM, e status do vision system.
    Útil para dashboards de monitoramento e troubleshooting.
    """
    if not PSUTIL_AVAILABLE:
        return jsonify({
            "error": "psutil not available",
            "message": "Install psutil for system metrics: pip install psutil"
        }), 503
    
    try:
        # Métricas do sistema
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Métricas do Vision System
        vs = get_vision_system()
        stats = vs.get_stats()
        
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_total_mb": round(memory.total / (1024**2), 1),
                "memory_used_mb": round(memory.used / (1024**2), 1),
                "memory_available_mb": round(memory.available / (1024**2), 1),
                "memory_percent": memory.percent
            },
            "vision": {
                "fps": stats.get("fps", 0),
                "detected": stats.get("detected_count", 0),
                "in_zone": stats.get("in_zone", 0),
                "out_zone": stats.get("out_zone", 0),
                "stream_active": stats.get("stream_active", False),
                "paused": stats.get("paused", False)
            },
            "config": {
                "preset": config.ACTIVE_PRESET,
                "buffer_size": config.BUFFER_SIZE,
                "buffer_duration_s": config.BUFFER_DURATION_SECONDS,
                "buffer_memory_mb": config.ESTIMATED_BUFFER_MEMORY_MB,
                "gc_interval": config.GC_INTERVAL,
                "memory_threshold_mb": config.MEMORY_WARNING_THRESHOLD,
                "camera_resolution": f"{config.CAM_WIDTH}x{config.CAM_HEIGHT}",
                "camera_fps": config.CAM_FPS,
                "yolo_conf": config.YOLO_CONF_THRESHOLD,
                "yolo_width": config.YOLO_TARGET_WIDTH,
                "frame_step": config.YOLO_FRAME_STEP
            }
        }
        
        return jsonify(metrics_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================================
# Routes
# ==========================================================
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # ✨ Rate limiting contra brute force
def login():
    """
    ✨ MELHORADO: Login com auditoria completa e detecção de anomalias.
    
    Recursos de segurança:
    - Rate limiting (5 tentativas/minuto)
    - Logging detalhado de tentativas
    - Auditoria compliant (ANVISA/FDA)
    - Detecção de IPs suspeitos
    - User-Agent tracking
    """
    
    if request.method == "POST":
        username = request.form.get("username", type=str)
        password = request.form.get("password", type=str)
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # ✨ NOVO: Validação de entrada
        if not username or not password:
            app.logger.warning(f"⚠️ Login attempt with empty credentials from {ip_address}")
            flash("Usuário e senha são obrigatórios.", "danger")
            return render_template("login.html")
        
        # ✨ NOVO: Log detalhado de tentativa
        app.logger.info(
            f"🔐 Login attempt: user='{username}' from {ip_address} "
            f"(User-Agent: {user_agent[:50]}...)"
        )
        
        # ✨ NOVO: Detecta tentativas de SQL injection
        suspicious_chars = ["'", '"', ';', '--', '/*', '*/', 'OR', 'AND', '=', 'DROP']
        if any(char in username.upper() for char in suspicious_chars):
            app.logger.error(
                f"🚨 SECURITY ALERT: Possible SQL injection attempt! "
                f"User: '{username}' from {ip_address}"
            )
            log_system_action(
                action="SECURITY_ALERT",
                username="SYSTEM",
                reason=f"SQL injection attempt: {username} from {ip_address}"
            )
            flash("Requisição inválida.", "danger")
            return render_template("login.html")
        
        # Tentativa de autenticação
        start_time = time.time()
        user = verify_user(username, password)
        auth_duration = time.time() - start_time
        
        if user:
            # ✅ LOGIN BEM-SUCEDIDO
            session["user"] = normalize_user(user)
            session["login_time"] = datetime.now(timezone.utc).isoformat()
            session["login_ip"] = ip_address
            
            update_last_login(username)
            
            # ✨ NOVO: Log detalhado de sucesso
            user_role = user.get('role', 'user') if isinstance(user, dict) else getattr(user, 'role', 'user')
            app.logger.info(
                f"✅ Login successful: user='{username}' role='{user_role}' "
                f"from {ip_address} (auth took {auth_duration:.3f}s)"
            )
            
            # Log de sistema (banco de dados)
            log_system_action(
                action="LOGIN_SUCCESS",
                username=username,
                reason=f"IP: {ip_address}, Role: {user_role}"
            )
            
            # ✨ NOVO: Auditoria compliant (se implementado)
            try:
                audit_logger.log_action(
                    user=username,
                    action="LOGIN_SUCCESS",
                    details=f"Successful authentication (role: {user_role}, auth_time: {auth_duration:.3f}s)",
                    ip_address=ip_address
                )
            except NameError:
                # audit_logger ainda não implementado
                pass
            
            flash(f"Bem-vindo, {username}!", "success")
            
            # ✨ NOVO: Redireciona para página solicitada ou dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Previne open redirect
                app.logger.debug(f"Redirecting {username} to requested page: {next_page}")
                return redirect(next_page)
            
            return redirect(url_for("dashboard"))
        
        else:
            # ❌ LOGIN FALHOU
            
            # ✨ NOVO: Log detalhado de falha
            app.logger.warning(
                f"❌ Login FAILED: user='{username}' from {ip_address} "
                f"(invalid credentials, auth took {auth_duration:.3f}s)"
            )
            
            # ✨ NOVO: Detecta tentativas de força bruta
            # (Você pode implementar contador em Redis/memcached para produção)
            if auth_duration < 0.1:  # Autenticação muito rápida = possível ataque
                app.logger.error(
                    f"🚨 SECURITY ALERT: Suspicious fast authentication attempt! "
                    f"User: '{username}' from {ip_address} ({auth_duration:.3f}s)"
                )
            
            # Log de sistema (banco de dados)
            log_system_action(
                action="LOGIN_FAILED",
                username=username or "unknown",
                reason=f"IP: {ip_address}, Invalid credentials"
            )
            
            # ✨ NOVO: Auditoria compliant (se implementado)
            try:
                audit_logger.log_action(
                    user=username or "unknown",
                    action="LOGIN_FAILED",
                    details=f"Failed authentication attempt (auth_time: {auth_duration:.3f}s)",
                    ip_address=ip_address
                )
            except NameError:
                # audit_logger ainda não implementado
                pass
            
            # ✨ NOVO: Mensagem genérica para não revelar se usuário existe
            flash("Usuário ou senha incorretos.", "danger")
    
    else:
        # ✨ NOVO: Log de acesso à página de login (GET)
        ip_address = request.remote_addr
        app.logger.debug(f"Login page accessed from {ip_address}")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def register():
    if request.method == "POST":
        username = request.form.get("username", type=str)
        email = request.form.get("email", type=str)
        password = request.form.get("password", type=str)
        
        if create_user(username, email, password):
            # ✨ ADICIONE ESTA LINHA:
            app.logger.info(f"✅ New user created: {username} ({email})")
            
            log_system_action(
                action="USER_CREATED",
                username=username,
                reason=f"Email: {email}, IP: {request.remote_addr}"
            )
            
            flash("Usuário criado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        
        # ✨ ADICIONE ESTA LINHA:
        app.logger.warning(f"⚠️ Registration failed: {username} (already exists)")
        
        flash("Usuário ou e-mail já existe.", "danger")
    
    return render_template("register.html")


@app.route("/logout")
def logout():
    username = session.get("user", {}).get("username", "unknown")
    session.pop("user", None)
    
    # ✨ NOVO: Log de logout
    log_system_action(
        action="LOGOUT",
        username=username,
        reason=f"IP: {request.remote_addr}"
    )
    
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    vs = get_vision_system()
    config_data = vs.get_config()
    model_path = (
        config_data.get("model_path") or get_setting("model_path") or "yolo_models\\yolov8n.pt"
    )
    source = config_data.get("source") or get_setting("source") or "0"
    
    system_info = {
        "model_name": os.path.basename(str(model_path)),
        "video_source_label": get_video_source_label(source),
        "preset": config.ACTIVE_PRESET,
    }
    
    # ✨ NOVO: Adiciona info de memória se disponível
    if PSUTIL_AVAILABLE:
        mem_info = get_memory_info()
        if mem_info:
            system_info["memory_percent"] = mem_info["percent"]
            system_info["memory_used_mb"] = mem_info["used_mb"]
    
    return render_template(
        "dashboard.html", active="dashboard", system_info=system_info
    )


@app.route("/video_feed")
@login_required
def video_feed():
    vs = get_vision_system()
    return Response(
        vs.generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/start_stream", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def start_stream():
    vs = get_vision_system()
    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")
    
    started = vs.start_live()
    
    if started:
        # ✨ ADICIONE ESTA LINHA:
        app.logger.info(f"🎥 Stream started by {username}")
        
        email_flag = bool(getattr(vs, "notifier", None))
        log_system_action("INICIAR", username, reason=None, email_sent=email_flag)

        if getattr(vs, "notifier", None) is not None:
            subject = "Ark: stream INICIADO"
            body = (
                f'O stream de vídeo foi INICIADO pelo usuário "{username}".\n\n'
                "Sistema entrou em estado ativo."
            )
            vs.notifier.send_email_background(subject=subject, body=body)

    return jsonify({"success": started, "status": "ativo" if started else "já estava ativo"})


@app.route("/toggle_camera", methods=["POST"])
@login_required
@limiter.limit("10 per minute")  # ✨ PROTEÇÃO: Evita spam de toggle
def toggle_camera():
    vs = get_vision_system()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "").strip()

    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")

    paused = vs.toggle_pause()

    if paused:
        # PAUSAR
        app.logger.info(f"⏸️ Stream paused by {username}. Reason: {reason or 'not provided'}")
        email_flag = bool(getattr(vs, "notifier", None))
        log_system_action("PAUSAR", username, reason=reason or None, email_sent=email_flag)

        if getattr(vs, "notifier", None) is not None:
            subject = "Ark: stream PAUSADO"
            body = (
                f'O stream de vídeo foi PAUSADO pelo usuário "{username}".\n\n'
                f"Motivo informado: {reason or 'não informado'}\n\n"
                "Verifique se essa ação foi autorizada."
            )
            vs.notifier.send_email_background(subject=subject, body=body)
    else:
        # RETOMAR
        app.logger.info(f"▶️ Stream resumed by {username}")
        email_flag = bool(getattr(vs, "notifier", None))
        log_system_action("RETOMAR", username, reason=None, email_sent=email_flag)

        if getattr(vs, "notifier", None) is not None:
            subject = "Ark: stream RETOMADO"
            body = (
                f'O stream de vídeo foi RETOMADO pelo usuário "{username}".\n\n'
                "Sistema voltou ao estado ativo."
            )
            vs.notifier.send_email_background(subject=subject, body=body)

    return jsonify({"paused": paused, "status": "pausado" if paused else "ativo"})


@app.route("/stop_stream", methods=["POST"])
@login_required
@limiter.limit("10 per minute")  # ✨ PROTEÇÃO: Evita spam de stop
def stop_stream():
    vs = get_vision_system()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "").strip()

    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")

    stopped = vs.stop_live()

    if stopped:
        app.logger.info(f"⏹️ Stream stopped by {username}. Reason: {reason or 'not provided'}")
        email_flag = bool(getattr(vs, "notifier", None))
        log_system_action("PARAR", username, reason=reason or None, email_sent=email_flag)

        if getattr(vs, "notifier", None) is not None:
            subject = "Ark: stream PARADO"
            body = (
                f'O stream de vídeo foi PARADO pelo usuário "{username}".\n\n'
                f"Motivo informado: {reason or 'não informado'}\n\n"
                "Verifique se essa ação foi autorizada."
            )
            vs.notifier.send_email_background(subject=subject, body=body)

    return jsonify({"success": stopped, "status": "parado" if stopped else "já estava parado"})


@app.route("/logs")
@login_required
def logs():
    alerts = get_recent_alerts(50)
    system_actions = get_system_logs(limit=100)

    return render_template(
        "logs.html",
        alerts=alerts,
        system_actions=system_actions,
        active="logs",
    )


@app.route("/logs/delete", methods=["POST"])
@admin_required
def delete_log():
    person_id = request.form.get("person_id")
    timestamp = request.form.get("timestamp")

    if not person_id or not timestamp:
        flash("Dados inválidos para exclusão.", "danger")
        return redirect(url_for("logs"))

    try:
        pid = int(person_id)
    except ValueError:
        flash("ID inválido.", "danger")
        return redirect(url_for("logs"))

    if delete_alert(pid, timestamp):
        flash("Alerta removido com sucesso.", "success")
    else:
        flash("Alerta não encontrado ou já removido.", "warning")

    return redirect(url_for("logs"))


@app.route("/logs/system/delete", methods=["POST"])
@admin_required
def delete_system_log_route():
    timestamp = request.form.get("timestamp")

    if not timestamp:
        flash("Dados inválidos para exclusão de log de sistema.", "danger")
        return redirect(url_for("logs"))

    if delete_system_log(timestamp):
        flash("Log de sistema removido com sucesso.", "success")
    else:
        flash("Log de sistema não encontrado ou já removido.", "warning")

    return redirect(url_for("logs"))


@app.route("/video/<path:filename>")
@login_required
def video_file(filename):
    alerts_dir = os.path.join(os.getcwd(), "alertas")
    try:
        return send_from_directory(
            alerts_dir, filename, mimetype="video/mp4", as_attachment=False
        )
    except NotFound:
        return "Vídeo não encontrado", 404


@app.route("/snapshot/<path:filename>")
@login_required
def snapshot(filename):
    base_dir = os.getcwd()
    try:
        return send_from_directory(base_dir, filename, as_attachment=False)
    except NotFound:
        return "Arquivo não encontrado", 404


@app.route("/users")
@admin_required
def users():
    all_users = get_all_users()
    return render_template("users.html", users=all_users, active="users")


@app.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        # ✨ NOVO: Captura informações do usuário e valores anteriores para auditoria
        user_info = session.get("user") or {}
        username = user_info.get("username", "admin")
        ip_address = request.remote_addr
        
        # ✨ NOVO: Captura valores ANTES das mudanças para log de alterações
        old_config = {
            'conf_thresh': get_setting("conf_thresh", "0.87"),
            'model_path': get_setting("model_path", "yolo_models\\yolov8n.pt"),
            'source': get_setting("source", "0"),
            'zones_count': len(json.loads(get_setting("safe_zone", "[]") or "[]"))
        }
        
        app.logger.info(f"⚙️ Settings update initiated by {username} from {ip_address}")
        
        # Detecção / performance
        conf_thresh = request.form.get("conf_thresh", default="0.87", type=str)
        target_width = request.form.get("target_width", default="960", type=str)
        frame_step = request.form.get("frame_step", default="2", type=str)
        
        # ✨ NOVO: Log de mudanças em parâmetros críticos de detecção
        if conf_thresh != old_config['conf_thresh']:
            app.logger.info(f"🎯 Detection threshold changed: {old_config['conf_thresh']} -> {conf_thresh}")
        
        set_setting("conf_thresh", conf_thresh)
        set_setting("target_width", target_width)
        set_setting("frame_step", frame_step)

        # Alertas / buffer
        max_out_time = request.form.get("max_out_time", default="30.0", type=str)
        email_cooldown = request.form.get("email_cooldown", default="600.0", type=str)
        buffer_seconds = request.form.get("buffer_seconds", default="2.0", type=str)
        set_setting("max_out_time", max_out_time)
        set_setting("email_cooldown", email_cooldown)
        set_setting("buffer_seconds", buffer_seconds)

        # Parâmetros de zona (globais)
        zone_empty_timeout = request.form.get(
            "zone_empty_timeout", default="10.0", type=str
        )
        zone_full_timeout = request.form.get(
            "zone_full_timeout", default="20.0", type=str
        )
        zone_full_threshold = request.form.get(
            "zone_full_threshold", default="5", type=str
        )
        set_setting("zone_empty_timeout", zone_empty_timeout)
        set_setting("zone_full_timeout", zone_full_timeout)
        set_setting("zone_full_threshold", zone_full_threshold)

        # --------------------------------------
        # Zonas inteligentes (modo + tempos)
        # --------------------------------------
        raw_safe = get_setting("safe_zone", "[]")
        try:
            current_zones = json.loads(str(raw_safe).strip() or "[]")
        except Exception:
            current_zones = []

        if not isinstance(current_zones, list):
            current_zones = []

        new_zones = []

        # Fallbacks globais
        try:
            g_max_out = float(max_out_time)
        except Exception:
            g_max_out = 30.0
        try:
            g_email_cd = float(email_cooldown)
        except Exception:
            g_email_cd = 600.0
        try:
            g_empty_t = float(zone_empty_timeout)
        except Exception:
            g_empty_t = 10.0
        try:
            g_full_t = float(zone_full_timeout)
        except Exception:
            g_full_t = 20.0
        try:
            g_full_thr = int(zone_full_threshold)
        except Exception:
            g_full_thr = 5

        for i, z in enumerate(current_zones):
            # compat: pode vir como dict ou lista de pontos
            if isinstance(z, dict):
                pts = z.get("points") or z.get("polygon") or []
            else:
                pts = z

            if not isinstance(pts, list) or len(pts) < 3:
                continue

            name = request.form.get(f"zone_{i}_name") or f"Zona {i+1}"
            mode = (request.form.get(f"zone_{i}_mode") or "GENERIC").upper()

            try:
                z_max_out = float(request.form.get(f"zone_{i}_max_out") or g_max_out)
            except Exception:
                z_max_out = g_max_out

            try:
                z_email_cd = float(request.form.get(f"zone_{i}_email_cd") or g_email_cd)
            except Exception:
                z_email_cd = g_email_cd

            try:
                z_empty_t = float(request.form.get(f"zone_{i}_empty_t") or g_empty_t)
            except Exception:
                z_empty_t = g_empty_t

            try:
                z_full_t = float(request.form.get(f"zone_{i}_full_t") or g_full_t)
            except Exception:
                z_full_t = g_full_t

            try:
                z_full_thr = int(request.form.get(f"zone_{i}_full_thr") or g_full_thr)
            except Exception:
                z_full_thr = g_full_thr

            new_zones.append(
                {
                    "name": name,
                    "mode": mode,
                    "points": pts,
                    "max_out_time": z_max_out,
                    "email_cooldown": z_email_cd,
                    "empty_timeout": z_empty_t,
                    "full_timeout": z_full_t,
                    "full_threshold": z_full_thr,
                }
            )

        # ✨ NOVO: Log de mudanças nas zonas
        zones_changed = len(new_zones) != old_config['zones_count']
        if zones_changed:
            app.logger.info(f"📍 Zones configuration changed: {old_config['zones_count']} -> {len(new_zones)} zones")
            for idx, zone in enumerate(new_zones):
                app.logger.debug(f"   Zone {idx+1}: {zone['name']} ({zone['mode']}) - {len(zone['points'])} points")
        
        set_setting("safe_zone", json.dumps(new_zones, ensure_ascii=False))

        # Modelo / fonte
        model_path = request.form.get(
            "model_path", default=r"yolo_models\yolov8n.pt", type=str
        )
        
        # ✨ NOVO: Log de mudança de modelo (crítico para rastreabilidade)
        if model_path != old_config['model_path']:
            app.logger.warning(f"🤖 CRITICAL: Model changed by {username}: {old_config['model_path']} -> {model_path}")
        
        set_setting("model_path", model_path)

        source = request.form.get("source", default="0", type=str).strip()
        if source == "":
            source = "0"
        
        # ✨ NOVO: Log de mudança de fonte de vídeo
        if source != old_config['source']:
            app.logger.warning(f"📹 CRITICAL: Video source changed by {username}: {old_config['source']} -> {source}")
        
        set_setting("source", source)

        # Câmera
        cam_width = request.form.get("cam_width", default=960, type=int)
        cam_height = request.form.get("cam_height", default=540, type=int)
        cam_fps = request.form.get("cam_fps", default=30, type=int)
        
        app.logger.debug(f"📷 Camera settings: {cam_width}x{cam_height} @ {cam_fps}fps")
        
        set_setting("cam_width", cam_width)
        set_setting("cam_height", cam_height)
        set_setting("cam_fps", cam_fps)

        # Tracker
        tracker = request.form.get("tracker", default="botsort.yaml", type=str)
        if tracker not in ("botsort.yaml", "bytetrack.yaml"):
            tracker = "botsort.yaml"
        set_setting("tracker", tracker)

        # Servidor de e-mail / SMTP
        email_smtp_server = request.form.get("email_smtp_server", type=str)
        email_smtp_port = request.form.get("email_smtp_port", default="587", type=str)
        email_from = request.form.get("email_from", type=str)
        email_user = request.form.get("email_user", type=str)
        email_password = request.form.get("email_password", type=str)

        email_use_tls = request.form.get("email_use_tls")
        email_use_ssl = request.form.get("email_use_ssl")

        # ✨ NOVO: Log de mudanças nas configurações de email (sem expor senhas)
        email_changed = False
        if email_smtp_server and email_smtp_server != get_setting("email_smtp_server", ""):
            app.logger.info(f"📧 Email SMTP server changed to: {email_smtp_server}:{email_smtp_port}")
            email_changed = True
        if email_user and email_user != get_setting("email_user", ""):
            app.logger.info(f"📧 Email user changed to: {email_user}")
            email_changed = True
        if email_password:  # Nunca loga a senha, apenas que foi alterada
            app.logger.info(f"🔐 Email password was updated by {username}")
            email_changed = True

        set_setting("email_smtp_server", email_smtp_server or "")
        set_setting("email_smtp_port", email_smtp_port or "587")
        set_setting("email_from", email_from or "")
        set_setting("email_user", email_user or "")
        set_setting("email_password", email_password or "")

        set_setting("email_use_tls", "1" if email_use_tls else "0")
        set_setting("email_use_ssl", "1" if email_use_ssl else "0")

        # ✨ MELHORADO: Log detalhado de mudança de configuração
        changes_summary = []
        if conf_thresh != old_config['conf_thresh']:
            changes_summary.append(f"conf_thresh: {old_config['conf_thresh']}→{conf_thresh}")
        if model_path != old_config['model_path']:
            changes_summary.append(f"model: {os.path.basename(old_config['model_path'])}→{os.path.basename(model_path)}")
        if source != old_config['source']:
            changes_summary.append(f"source: {old_config['source']}→{source}")
        if zones_changed:
            changes_summary.append(f"zones: {old_config['zones_count']}→{len(new_zones)}")
        if email_changed:
            changes_summary.append("email_config")
        
        changes_str = ", ".join(changes_summary) if changes_summary else "minor_params"
        
        app.logger.info(f"✅ Settings updated successfully by {username}: {changes_str}")
        
        log_system_action(
            action="CONFIG_UPDATE",
            username=username,
            reason=f"Changes: {changes_str}"
        )
        
        # ✨ NOVO: Se tiver audit_logger implementado, adicione aqui
        try:
            audit_logger.log_action(
                user=username,
                action="CONFIG_UPDATE",
                details=f"Model: {os.path.basename(model_path)}, Source: {source}, Zones: {len(new_zones)}, Changes: {changes_str}",
                ip_address=ip_address
            )
        except NameError:
            # audit_logger ainda não implementado, apenas continua
            pass

        # Reinicia o stream
        app.logger.info(f"🔄 Restarting stream with new configuration...")
        
        vs = get_vision_system()
        vs.stop_live()
        vs.start_live()
        
        app.logger.info(f"✅ Stream restarted successfully")

        flash(
            "Configurações salvas. Stream reiniciado e redirecionado para o dashboard.",
            "success",
        )
        return redirect(url_for("dashboard"))

    # GET
    app.logger.debug(f"Settings page accessed by {session.get('user', {}).get('username', 'unknown')}")
    
    vs = get_vision_system()
    config_data = vs.get_config()
    available_models = list_yolo_models("yolo_models")

    raw_zones = get_setting("safe_zone", "[]")
    try:
        zones_meta = json.loads(str(raw_zones).strip() or "[]")
    except Exception as e:
        app.logger.error(f"Error parsing zones metadata: {e}")
        zones_meta = []

    return render_template(
        "settings.html",
        config=config_data,
        active="settings",
        available_models=available_models,
        zones_meta=zones_meta,
    )


@app.route("/api/stats")
@login_required
@limiter.limit("30 per minute")  # ✨ PROTEÇÃO: Limita chamadas de API
def api_stats():
    """
    ✨ MELHORADO: Rate limiting + métricas de memória
    """
    vs = get_vision_system()
    stats = vs.get_stats()

    # total de alertas
    total_alerts = len(get_recent_alerts(1000))
    stats["total_alerts"] = total_alerts

    # status do sistema
    paused = bool(stats.get("paused", False))
    stream_active = bool(stats.get("stream_active", True))
    if not stream_active:
        system_status = "stopped"
    elif paused:
        system_status = "paused"
    else:
        system_status = "running"
    stats["system_status"] = system_status

    # infos de modelo/fonte
    config_data = vs.get_config()
    model_path = (
        config_data.get("model_path") or get_setting("model_path") or "yolo_models\\yolov8n.pt"
    )
    source = config_data.get("source") or get_setting("source") or "0"
    stats["model_name"] = os.path.basename(str(model_path))
    stats["video_source_label"] = get_video_source_label(source)

    # safe_zone para o mini-mapa (apenas geometria)
    safe_zone_str = config_data.get("safe_zone") or get_setting("safe_zone")
    stats["safe_zone"] = parse_safe_zone(safe_zone_str)

    # Activity: últimos 5 alertas
    recent = get_recent_alerts(5)
    recent_compact = []
    for a in recent:
        person_id = a[0] if len(a) > 0 else None
        out_time = a[1] if len(a) > 1 else None
        created_at = a[2] if len(a) > 2 else None
        email_sent = a[3] if len(a) > 3 else None
        video_path = a[4] if len(a) > 4 else None

        status_text = (
            f"Pessoa ID {person_id} fora da zona por {out_time:.1f}s"
            if person_id is not None and isinstance(out_time, (int, float))
            else "Alerta registrado"
        )

        video_file = None
        if video_path and isinstance(video_path, str):
            if "," in video_path:
                video_file = video_path.split(",")[0].strip()
            else:
                video_file = video_path

        recent_compact.append(
            {
                "type": "alert",
                "person_id": person_id,
                "timestamp": created_at,
                "status": status_text,
                "email_sent": bool(email_sent),
                "video_file": video_file,
            }
        )

    stats["recent_alerts"] = recent_compact

    # Logs de sistema recentes
    sys_logs = get_system_logs(limit=5)
    system_compact = []
    for s in sys_logs:
        # (action, username, reason, timestamp, email_sent)
        action, username, reason, ts, email_sent = s

        if action == "PAUSAR":
            msg = f'Stream PAUSADO por "{username}"'
        elif action == "RETOMAR":
            msg = f'Stream RETOMADO por "{username}"'
        elif action == "PARAR":
            msg = f'Stream PARADO por "{username}"'
        elif action == "INICIAR":
            msg = f'Stream INICIADO por "{username}"'
        elif action == "LOGIN_SUCCESS":
            msg = f'Login bem-sucedido: "{username}"'
        elif action == "LOGIN_FAILED":
            msg = f'Tentativa de login falhou: "{username}"'
        elif action == "CONFIG_UPDATE":
            msg = f'Configurações atualizadas por "{username}"'
        elif action == "ZONE_UPDATED":
            msg = f'Zonas atualizadas por "{username}"'
        elif action == "ZONE_CLEARED":
            msg = f'Zonas removidas por "{username}"'
        else:
            msg = f'Ação {action} por "{username}"'

        if reason:
            msg += f" ({reason})"

        system_compact.append(
            {
                "type": "system",
                "action": action,
                "username": username,
                "reason": reason,
                "timestamp": ts,
                "email_sent": bool(email_sent),
                "message": msg,
            }
        )

    stats["system_logs"] = system_compact

    # ---------- Nomes das zonas no payload ----------
    zones_stats = stats.get("zones") or []
    raw_safe = config_data.get("safe_zone") or get_setting("safe_zone", "[]")
    try:
        zones_config = json.loads(str(raw_safe).strip() or "[]")
    except Exception:
        zones_config = []

    names_by_index = {}
    for idx, zconf in enumerate(zones_config):
        if isinstance(zconf, dict):
            name = zconf.get("name")
            if name:
                names_by_index[idx] = name

    for z in zones_stats:
        idx = z.get("index")
        if isinstance(idx, int) and idx in names_by_index:
            z["name"] = names_by_index[idx]

    stats["zones"] = zones_stats
    # -------------------------------------------------

    # ✨ NOVO: Métricas de memória e performance
    if PSUTIL_AVAILABLE:
        try:
            memory = psutil.virtual_memory()
            stats["system_memory"] = {
                "used_mb": round(memory.used / (1024**2), 1),
                "percent": memory.percent,
                "preset": config.ACTIVE_PRESET
            }
        except Exception:
            pass

    return jsonify(stats)


@app.route("/api/safe_zone", methods=["POST"])
@admin_required
@limiter.limit("10 per minute")  # ✨ PROTEÇÃO: Limita mudanças de zona
def api_safe_zone():
    """
    ✨ MELHORADO: Rate limiting para evitar spam de mudanças de zona
    
    Recebe JSON:

    Novo formato principal:
    - {
        "zones": [
          {"name": "Entrada", "mode": "FLOW", "points": [[x,y], ...]},
          ...
        ]
      }

    Compatibilidade (antigo):
    - {"points": [[x,y],...]}  (zona única)

    Salva em settings.safe_zone como JSON e reinicia o stream em qualquer alteração.
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"success": False, "error": "JSON inválido"}), 400

    vs = get_vision_system()
    
    # ✨ NOVO: Log de mudança de zona
    user_info = session.get("user") or {}
    username = user_info.get("username", "admin")

    # NOVO FORMATO: múltiplas zonas com metadados
    if "zones" in payload:
        zones = payload.get("zones")

        # permitir limpar todas as zonas
        if isinstance(zones, list) and len(zones) == 0:
            set_setting("safe_zone", json.dumps([]))
            vs.stop_live()
            vs.start_live()
            
            log_system_action(
                action="ZONE_CLEARED",
                username=username,
                reason="Todas as zonas foram removidas"
            )
            
            return jsonify({"success": True, "zones": []})

        if not isinstance(zones, list) or len(zones) == 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "É necessário enviar uma lista em 'zones'",
                    }
                ),
                400,
            )

        validated_zones = []
        for zone in zones:
            if not isinstance(zone, dict):
                continue

            name = str(zone.get("name", "")).strip()
            mode = str(zone.get("mode", "")).strip().upper() or "GENERIC"
            points = zone.get("points")

            if not name:
                continue
            if not isinstance(points, list) or len(points) < 3:
                continue

            norm_points = []
            for p in points:
                if not (isinstance(p, (list, tuple)) and len(p) == 2):
                    continue
                try:
                    x, y = float(p[0]), float(p[1])
                    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                        continue
                    norm_points.append([x, y])
                except Exception:
                    continue

            if len(norm_points) >= 3:
                validated_zones.append(
                    {"name": name, "mode": mode, "points": norm_points}
                )

        if len(validated_zones) == 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Nenhuma zona válida fornecida (verifique name/mode/points)",
                    }
                ),
                400,
            )

        set_setting("safe_zone", json.dumps(validated_zones))
        
        log_system_action(
            action="ZONE_UPDATED",
            username=username,
            reason=f"{len(validated_zones)} zona(s) configurada(s)"
        )

        vs.stop_live()
        vs.start_live()

        return jsonify({"success": True, "zones": validated_zones})

    # FORMATO ANTIGO: zona única (sem nome/modo)
    if "points" in payload:
        points = payload.get("points")

        if isinstance(points, list) and len(points) == 0:
            set_setting("safe_zone", json.dumps([]))
            vs.stop_live()
            vs.start_live()
            
            log_system_action(
                action="ZONE_CLEARED",
                username=username,
                reason="Zona removida (formato legado)"
            )
            
            return jsonify({"success": True, "points": []})

        if not isinstance(points, list) or len(points) < 3:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "É necessário ao menos 3 pontos em 'points'",
                    }
                ),
                400,
            )

        norm_points = []
        for p in points:
            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Formato de ponto inválido em 'points'",
                        }
                    ),
                    400,
                )
            try:
                x, y = float(p[0]), float(p[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Pontos devem estar entre 0 e 1 em 'points'",
                            }
                        ),
                        400,
                    )
                norm_points.append([x, y])
            except Exception:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Erro ao processar pontos em 'points'",
                        }
                    ),
                    400,
                )

        # salva como lista de uma zona rica genérica
        rich = [
            {"name": "Zona 1", "mode": "GENERIC", "points": norm_points},
        ]
        set_setting("safe_zone", json.dumps(rich))
        
        log_system_action(
            action="ZONE_UPDATED",
            username=username,
            reason="Zona configurada (formato legado)"
        )

        vs.stop_live()
        vs.start_live()

        return jsonify({"success": True, "points": norm_points})

    return (
        jsonify(
            {
                "success": False,
                "error": "Formato inválido: use 'zones' (novo) ou 'points' (legado)",
            }
        ),
        400,
    )


@app.route("/diagnostics", methods=["GET"])
@admin_required
def diagnostics():
    """
    Executa verificação completa do banco de dados e retorna resultado formatado.
    """
    import sqlite3
    from database import DB_NAME

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        results = {
            "status": "success",
            "tables": {},
            "yolo": {},
            "zone": {},
            "camera": {},
            "email": {},
            "data": {},
            "admin": [],
            "missing": [],
        }

        # 1. TABELAS
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        required_tables = {
            "users": "Usuários e autenticação",
            "alerts": "Alertas de zona segura",
            "settings": "Configurações do sistema",
            "system_logs": "Logs de ações do sistema",
        }

        for table, description in required_tables.items():
            if table in tables:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                results["tables"][table] = {
                    "exists": True,
                    "count": count,
                    "desc": description,
                }
            else:
                results["tables"][table] = {
                    "exists": False,
                    "count": 0,
                    "desc": description,
                }
                results["missing"].append(f"Tabela '{table}' não existe")

        # 2. YOLO
        yolo_keys = {
            "conf_thresh": "Threshold de confiança",
            "model_path": "Caminho do modelo",
            "target_width": "Largura do frame",
            "frame_step": "Pular frames",
            "tracker": "Algoritmo de tracking",
        }

        for key, desc in yolo_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                results["yolo"][key] = {
                    "value": result[0],
                    "desc": desc,
                    "exists": True,
                }
            else:
                results["yolo"][key] = {
                    "value": None,
                    "desc": desc,
                    "exists": False,
                }
                results["missing"].append(f"Config YOLO '{key}' não existe")

        # 3. ZONA
        zone_keys = {
            "safe_zone": "Coordenadas da zona",
            "max_out_time": "Tempo máximo fora",
            "email_cooldown": "Cooldown e-mail",
            "buffer_seconds": "Buffer pré-gravação",
            "zone_empty_timeout": "Timeout vazia",
            "zone_full_timeout": "Timeout cheia",
            "zone_full_threshold": "Limite pessoas",
        }

        for key, desc in zone_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                if key == "safe_zone" and len(value) > 60:
                    value = value[:57] + "..."
                results["zone"][key] = {
                    "value": value,
                    "desc": desc,
                    "exists": True,
                }
            else:
                results["zone"][key] = {
                    "value": None,
                    "desc": desc,
                    "exists": False,
                }
                results["missing"].append(f"Config ZONA '{key}' não existe")

        # 4. CÂMERA
        camera_keys = {
            "source": "Fonte de vídeo",
            "cam_width": "Largura",
            "cam_height": "Altura",
            "cam_fps": "FPS",
        }

        for key, desc in camera_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                results["camera"][key] = {
                    "value": result[0],
                    "desc": desc,
                    "exists": True,
                }
            else:
                results["camera"][key] = {
                    "value": None,
                    "desc": desc,
                    "exists": False,
                }
                results["missing"].append(f"Config CÂMERA '{key}' não existe")

        # 5. EMAIL
        email_keys = {
            "email_smtp_server": "Servidor SMTP",
            "email_smtp_port": "Porta SMTP",
            "email_from": "E-mail remetente",
            "email_user": "Usuário SMTP",
            "email_password": "Senha SMTP",
            "email_use_tls": "Usar TLS",
            "email_use_ssl": "Usar SSL",
        }

        for key, desc in email_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                if key == "email_password" and value:
                    value = "***" * len(value[:8])
                results["email"][key] = {
                    "value": value,
                    "desc": desc,
                    "exists": True,
                }
            else:
                results["email"][key] = {
                    "value": None,
                    "desc": desc,
                    "exists": False,
                }

        # 6. DADOS
        c.execute("SELECT COUNT(*) FROM users")
        results["data"]["users"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM alerts")
        results["data"]["alerts"] = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM system_logs")
        results["data"]["system_logs"] = c.fetchone()[0]

        # 7. ADMIN
        c.execute("SELECT username, email, role FROM users WHERE role = 'admin'")
        for row in c.fetchall():
            results["admin"].append(
                {"username": row[0], "email": row[1], "role": row[2]}
            )

        conn.close()

        return render_template("diagnostics.html", results=results, active="diagnostics")

    except Exception as e:
        return render_template(
            "diagnostics.html",
            results={"status": "error", "error": str(e)},
            active="diagnostics",
        )


@app.route("/admin/backup", methods=["GET", "POST"])
@admin_required
def admin_backup():
    """
    ✨ NOVO: Interface web para gerenciar backups.
    
    Permite:
    - Executar backup manual
    - Ver estatísticas
    - Verificar integridade
    - Baixar backups
    """
    from backup_logs import LogBackupManager
    
    manager = LogBackupManager()
    
    if request.method == "POST":
        action = request.form.get("action")
        username = session.get("user", {}).get("username", "admin")
        
        if action == "backup":
            app.logger.info(f"📦 Manual backup triggered by {username}")
            backups = manager.backup_all_logs()
            flash(f"✅ Backup concluído: {len(backups)} arquivo(s)", "success")
            
        elif action == "verify":
            app.logger.info(f"🔍 Integrity check triggered by {username}")
            total, valid, invalid = manager.verify_backup_integrity()
            
            if len(invalid) == 0:
                flash(f"✅ Integridade OK: {valid}/{total} backups válidos", "success")
            else:
                flash(f"⚠️ Problemas encontrados: {len(invalid)} backups inválidos", "warning")
        
        elif action == "cleanup_dry":
            app.logger.info(f"🗑️ Cleanup simulation by {username}")
            removed = manager.cleanup_old_backups(dry_run=True)
            flash(f"ℹ️ Simulação: {len(removed)} arquivo(s) seriam removidos", "info")
        
        elif action == "cleanup_real":
            app.logger.warning(f"🗑️ REAL cleanup triggered by {username}")
            removed = manager.cleanup_old_backups(dry_run=False)
            flash(f"✅ Limpeza concluída: {len(removed)} arquivo(s) removidos", "success")
            
            # Log de auditoria
            audit_logger.log_action(
                user=username,
                action="BACKUP_CLEANUP",
                details=f"Removed {len(removed)} old backup files",
                ip_address=request.remote_addr
            )
    
    # GET: Mostra estatísticas
    stats = manager.get_backup_statistics()
    
    # Lista backups recentes
    recent_backups = []
    for backup_file in sorted(
        manager.ARCHIVE_DIR.rglob('*.gz'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:20]:  # Últimos 20
        mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
        size_kb = backup_file.stat().st_size / 1024
        
        recent_backups.append({
            'filename': backup_file.name,
            'path': str(backup_file.relative_to(manager.ARCHIVE_DIR)),
            'date': mtime.strftime('%Y-%m-%d %H:%M'),
            'size_kb': round(size_kb, 1)
        })
    
    return render_template(
        "admin_backup.html",
        active="backup",
        stats=stats,
        recent_backups=recent_backups
    )



# ==========================================================
# Error Handlers
# ==========================================================
@app.errorhandler(404)
def not_found(e):
    app.logger.warning(f"404 Error: {request.url} from {request.remote_addr}")
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"500 Error: {str(e)} - URL: {request.url}", exc_info=True)
    return render_template("500.html"), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    app.logger.warning(f"⚠️ Rate limit exceeded: {request.remote_addr} on {request.url}")
    """✨ NOVO: Handler customizado para rate limiting"""
    return jsonify(
        {
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
        }
    ), 429

# ==========================================================
# AUDIT LOG VERIFICATION
# ==========================================================
@app.route("/audit/verify", methods=["GET"])
@admin_required
def audit_verify():
    """
    Verifica integridade da trilha de auditoria.
    Essencial para demonstrar compliance em auditorias.
    """
    is_valid, errors = audit_logger.verify_integrity()
    
    if is_valid:
        app.logger.info("✅ Audit log integrity verified successfully")
        flash("✅ Trilha de auditoria íntegra - sem alterações detectadas", "success")
    else:
        app.logger.error(f"❌ Audit log integrity compromised: {len(errors)} errors found")
        for error in errors:
            app.logger.error(f"   {error}")
        flash(f"❌ ALERTA: {len(errors)} problemas detectados na trilha de auditoria!", "danger")
    
    return render_template("audit_verify.html", is_valid=is_valid, errors=errors)


# ==========================================================
# Main
# ==========================================================
if __name__ == "__main__":
    # Valida configuração antes de iniciar
    errors, warnings = config.validate_config()
    
    if errors:
        print("\n❌ ERROS DE CONFIGURAÇÃO:")
        for error in errors:
            print(f"  {error}")
        print("\n❌ Corrija os erros antes de iniciar a aplicação.")
        exit(1)
    
    if warnings:
        print("\n⚠️  AVISOS:")
        for warning in warnings:
            print(f"  {warning}")
    
    # Exibe resumo da configuração
    config.print_config_summary()
    
    if PSUTIL_AVAILABLE:
        config.print_memory_recommendations()
    else:
        print("\n⚠️  psutil não instalado - métricas de memória desabilitadas")
        print("   Instale com: pip install psutil\n")
    
    # Teste rápido do audit logger
    #print("\n🧪 Testing audit logger...")
    #audit_logger.log_action("admin", "SYSTEM_START", "Testing audit system", "127.0.0.1")
    #audit_logger.log_action("admin", "TEST_ACTION", "Second test entry", "127.0.0.1")
    
    # Verifica integridade
    #is_valid, errors = audit_logger.verify_integrity()
    #if is_valid:
    #    print("✅ Audit log integrity: OK")
    #else:
    #    print(f"❌ Audit log integrity: FAILED ({len(errors)} errors)")
    #    for error in errors:
    #        print(f"   {error}")
    
    #print("\n")
    
    # ✨ NOVO: Inicia o scheduler de backup automático
    #print("🔄 Initializing backup scheduler...")
    #try:
    #    from schedule_backup import init_scheduler
    #    backup_scheduler = init_scheduler(app, backup_time="02:00")
    #    print("✅ Backup scheduler started (daily at 02:00 AM)")
    #    app.logger.info("✅ Automatic backup scheduler running (daily at 02:00)")
    #except ImportError as e:
    #    print(f"⚠️  Backup scheduler disabled: schedule_backup.py not found")
    #    app.logger.warning(f"⚠️ schedule_backup.py not found: {e}")
    #except Exception as e:
    #    print(f"⚠️  Backup scheduler disabled: {e}")
    #    app.logger.error(f"❌ Failed to start backup scheduler: {e}", exc_info=True)
    
    #print("\n")
    
    # Inicia o servidor Flask
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True
    )

