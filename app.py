"""
app.py

Sistema completo de monitoramento YOLO com autenticação.
Usa o módulo yolo.py para toda lógica de computação visual.
"""

import os
import json
from flask import (
    Flask, Response, render_template, request, redirect,
    url_for, session, flash, jsonify, send_from_directory
)
from werkzeug.exceptions import NotFound

# Carrega configurações do .env via config.py
import config

from database import (
    verify_user, create_user, update_last_login,
    get_recent_alerts, get_all_users, get_setting, set_setting,
    delete_alert, log_system_action, get_system_logs, delete_system_log
)
from auth import login_required, admin_required
from yolo import get_vision_system

app = Flask(__name__)

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
    Converte string de settings.safe_zone para formato usado pelo dashboard/API.

    Aceita:
    - string JSON múltiplas zonas: "[[[x,y],...], [[x,y],...]]"
    - string JSON zona única: "[[x_norm,y_norm], ...]"
    - string tuple antiga: "(x1, y1, x2, y2)"
    """
    if not value:
        return None
    value = str(value).strip()

    # novo formato: JSON
    if value.startswith("["):
        try:
            pts = json.loads(value)
            return pts
        except Exception:
            return None

    # formato antigo retângulo
    try:
        cleaned = value.strip().strip("()")
        parts = [p.strip() for p in cleaned.split(",")]
        if len(parts) != 4:
            return None
        x1, y1, x2, y2 = map(int, parts)
        return [x1, y1, x2, y2]
    except Exception:
        return None


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


# ==========================================================
# Template context
# ==========================================================
@app.context_processor
def inject_user():
    return {"user": session.get("user")}


# ==========================================================
# Routes
# ==========================================================
@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", type=str)
        password = request.form.get("password", type=str)
        user = verify_user(username, password)
        if user:
            session["user"] = normalize_user(user)
            update_last_login(username)
            flash(f"Bem-vindo, {username}!", "success")
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha incorretos.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", type=str)
        email = request.form.get("email", type=str)
        password = request.form.get("password", type=str)
        if create_user(username, email, password):
            flash("Usuário criado com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        flash("Usuário ou e-mail já existe.", "danger")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    vs = get_vision_system()
    config = vs.get_config()
    model_path = config.get("model_path") or get_setting("model_path") or "yolo_models\\yolov8n.pt"
    source = config.get("source") or get_setting("source") or "0"
    system_info = {
        "model_name": os.path.basename(str(model_path)),
        "video_source_label": get_video_source_label(source),
    }
    return render_template("dashboard.html", active="dashboard", system_info=system_info)


@app.route("/video_feed")
@login_required
def video_feed():
    vs = get_vision_system()
    return Response(vs.generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/start_stream", methods=["POST"])
@login_required
def start_stream():
    vs = get_vision_system()

    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")

    started = vs.start_live()

    if started:
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
def toggle_camera():
    vs = get_vision_system()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "").strip()

    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")

    paused = vs.toggle_pause()

    if paused:
        # PAUSAR
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
def stop_stream():
    vs = get_vision_system()
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "").strip()

    user_info = session.get("user") or {}
    username = user_info.get("username", "desconhecido")

    stopped = vs.stop_live()

    if stopped:
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
        return send_from_directory(alerts_dir, filename, mimetype="video/mp4", as_attachment=False)
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
        # Detecção / performance
        conf_thresh = request.form.get("conf_thresh", default="0.78", type=str)
        target_width = request.form.get("target_width", default="1280", type=str)
        frame_step = request.form.get("frame_step", default="2", type=str)
        set_setting("conf_thresh", conf_thresh)
        set_setting("target_width", target_width)
        set_setting("frame_step", frame_step)

        # Alertas / buffer
        max_out_time = request.form.get("max_out_time", default="5.0", type=str)
        email_cooldown = request.form.get("email_cooldown", default="10.0", type=str)
        buffer_seconds = request.form.get("buffer_seconds", default="2.0", type=str)
        set_setting("max_out_time", max_out_time)
        set_setting("email_cooldown", email_cooldown)
        set_setting("buffer_seconds", buffer_seconds)

        # Parâmetros de zona (novos)
        zone_empty_timeout = request.form.get("zone_empty_timeout", default="10.0", type=str)
        zone_full_timeout = request.form.get("zone_full_timeout", default="20.0", type=str)
        zone_full_threshold = request.form.get("zone_full_threshold", default="5", type=str)
        set_setting("zone_empty_timeout", zone_empty_timeout)
        set_setting("zone_full_timeout", zone_full_timeout)
        set_setting("zone_full_threshold", zone_full_threshold)

        # Modelo / fonte
        model_path = request.form.get("model_path", default=r"yolo_models\yolo11n.pt", type=str)
        set_setting("model_path", model_path)

        source = request.form.get("source", default="0", type=str).strip()
        if source == "":
            source = "0"
        set_setting("source", source)

        # Câmera
        cam_width = request.form.get("cam_width", default=1280, type=int)
        cam_height = request.form.get("cam_height", default=720, type=int)
        cam_fps = request.form.get("cam_fps", default=30, type=int)
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

        set_setting("email_smtp_server", email_smtp_server or "")
        set_setting("email_smtp_port", email_smtp_port or "587")
        set_setting("email_from", email_from or "")
        set_setting("email_user", email_user or "")
        set_setting("email_password", email_password or "")

        set_setting("email_use_tls", "1" if email_use_tls else "0")
        set_setting("email_use_ssl", "1" if email_use_ssl else "0")

        # Reinicia o stream automaticamente ao salvar configs
        vs = get_vision_system()
        vs.stop_live()
        vs.start_live()

        flash("Configurações salvas. Stream reiniciado e redirecionado para o dashboard.", "success")
        return redirect(url_for("dashboard"))

    vs = get_vision_system()
    config = vs.get_config()
    available_models = list_yolo_models("yolo_models")

    return render_template(
        "settings.html",
        config=config,
        active="settings",
        available_models=available_models
    )


@app.route("/api/stats")
@login_required
def api_stats():
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
    config = vs.get_config()
    model_path = config.get("model_path") or get_setting("model_path") or "yolo_models\\yolov8n.pt"
    source = config.get("source") or get_setting("source") or "0"
    stats["model_name"] = os.path.basename(str(model_path))
    stats["video_source_label"] = get_video_source_label(source)

    # safe_zone para o mini-mapa
    safe_zone_str = config.get("safe_zone") or get_setting("safe_zone")
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
            if ',' in video_path:
                video_file = video_path.split(',')[0].strip()
            else:
                video_file = video_path

        recent_compact.append({
            "type": "alert",
            "person_id": person_id,
            "timestamp": created_at,
            "status": status_text,
            "email_sent": bool(email_sent),
            "video_file": video_file,
        })

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
        else:
            msg = f'Ação {action} por "{username}"'

        if reason:
            msg += f' (motivo: {reason})'

        system_compact.append({
            "type": "system",
            "action": action,
            "username": username,
            "reason": reason,
            "timestamp": ts,
            "email_sent": bool(email_sent),
            "message": msg,
        })

    stats["system_logs"] = system_compact

    return jsonify(stats)


@app.route("/api/safe_zone", methods=["POST"])
@admin_required
def api_safe_zone():
    """
    Recebe JSON:
    - {"zones": [[[x,y],...], [[x,y],...], ...]} para múltiplas zonas
    - {"points": [[x,y],...]} para zona única (compatibilidade)

    Salva em settings.safe_zone como JSON e reinicia o stream em qualquer alteração.
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"success": False, "error": "JSON inválido"}), 400

    vs = get_vision_system()

    # novo formato: múltiplas zonas
    if "zones" in payload:
        zones = payload.get("zones")

        # permitir limpar todas as zonas
        if isinstance(zones, list) and len(zones) == 0:
            set_setting("safe_zone", json.dumps([]))
            vs.stop_live()
            vs.start_live()
            return jsonify({"success": True, "zones": []})

        if not isinstance(zones, list) or len(zones) == 0:
            return jsonify({"success": False, "error": "É necessário ao menos uma zona"}), 400

        validated_zones = []
        for zone in zones:
            if not isinstance(zone, list) or len(zone) < 3:
                continue
            validated_points = []
            for p in zone:
                if not (isinstance(p, (list, tuple)) and len(p) == 2):
                    continue
                try:
                    x, y = float(p[0]), float(p[1])
                    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                        continue
                    validated_points.append([x, y])
                except Exception:
                    continue
            if len(validated_points) >= 3:
                validated_zones.append(validated_points)

        if len(validated_zones) == 0:
            return jsonify({"success": False, "error": "Nenhuma zona válida fornecida"}), 400

        set_setting("safe_zone", json.dumps(validated_zones))

        vs.stop_live()
        vs.start_live()

        return jsonify({"success": True, "zones": validated_zones})

    # formato antigo: zona única
    if "points" in payload:
        points = payload.get("points")

        if isinstance(points, list) and len(points) == 0:
            set_setting("safe_zone", json.dumps([]))
            vs.stop_live()
            vs.start_live()
            return jsonify({"success": True, "points": []})

        if not isinstance(points, list) or len(points) < 3:
            return jsonify({"success": False, "error": "É necessário ao menos 3 pontos"}), 400

        norm_points = []
        for p in points:
            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                return jsonify({"success": False, "error": "Formato de ponto inválido"}), 400
            try:
                x, y = float(p[0]), float(p[1])
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    return jsonify({"success": False, "error": "Pontos devem estar entre 0 e 1"}), 400
                norm_points.append([x, y])
            except Exception:
                return jsonify({"success": False, "error": "Erro ao processar pontos"}), 400

        set_setting("safe_zone", json.dumps(norm_points))

        vs.stop_live()
        vs.start_live()

        return jsonify({"success": True, "points": norm_points})

    return jsonify({"success": False, "error": "Formato inválido: use 'zones' ou 'points'"}), 400

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
            "missing": []
        }
        
        # 1. TABELAS
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        required_tables = {
            'users': 'Usuários e autenticação',
            'alerts': 'Alertas de zona segura',
            'settings': 'Configurações do sistema',
            'system_logs': 'Logs de ações do sistema'
        }
        
        for table, description in required_tables.items():
            if table in tables:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                results["tables"][table] = {"exists": True, "count": count, "desc": description}
            else:
                results["tables"][table] = {"exists": False, "count": 0, "desc": description}
                results["missing"].append(f"Tabela '{table}' não existe")
        
        # 2. YOLO
        yolo_keys = {
            'conf_thresh': 'Threshold de confiança',
            'model_path': 'Caminho do modelo',
            'target_width': 'Largura do frame',
            'frame_step': 'Pular frames',
            'tracker': 'Algoritmo de tracking'
        }
        
        for key, desc in yolo_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                results["yolo"][key] = {"value": result[0], "desc": desc, "exists": True}
            else:
                results["yolo"][key] = {"value": None, "desc": desc, "exists": False}
                results["missing"].append(f"Config YOLO '{key}' não existe")
        
        # 3. ZONA
        zone_keys = {
            'safe_zone': 'Coordenadas da zona',
            'max_out_time': 'Tempo máximo fora',
            'email_cooldown': 'Cooldown e-mail',
            'buffer_seconds': 'Buffer pré-gravação',
            'zone_empty_timeout': 'Timeout vazia',
            'zone_full_timeout': 'Timeout cheia',
            'zone_full_threshold': 'Limite pessoas'
        }
        
        for key, desc in zone_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                if key == 'safe_zone' and len(value) > 60:
                    value = value[:57] + "..."
                results["zone"][key] = {"value": value, "desc": desc, "exists": True}
            else:
                results["zone"][key] = {"value": None, "desc": desc, "exists": False}
                results["missing"].append(f"Config ZONA '{key}' não existe")
        
        # 4. CÂMERA
        camera_keys = {
            'source': 'Fonte de vídeo',
            'cam_width': 'Largura',
            'cam_height': 'Altura',
            'cam_fps': 'FPS'
        }
        
        for key, desc in camera_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                results["camera"][key] = {"value": result[0], "desc": desc, "exists": True}
            else:
                results["camera"][key] = {"value": None, "desc": desc, "exists": False}
                results["missing"].append(f"Config CÂMERA '{key}' não existe")
        
        # 5. E-MAIL
        email_keys = {
            'email_smtp_server': 'Servidor SMTP',
            'email_smtp_port': 'Porta',
            'email_use_tls': 'TLS',
            'email_use_ssl': 'SSL',
            'email_from': 'Remetente',
            'email_user': 'Usuário',
            'email_password': 'Senha'
        }
        
        for key, desc in email_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                if key == 'email_password' and value:
                    value = "***" + value[-4:] if len(value) > 4 else "****"
                elif key == 'email_password':
                    value = "[vazio]"
                results["email"][key] = {"value": value, "desc": desc, "exists": True}
            else:
                results["email"][key] = {"value": None, "desc": desc, "exists": False}
                results["missing"].append(f"Config E-MAIL '{key}' não existe")
        
        # 6. DADOS
        c.execute("SELECT COUNT(*) FROM users")
        results["data"]["users"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM alerts")
        results["data"]["alerts"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM system_logs")
        results["data"]["logs"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM settings")
        results["data"]["settings"] = c.fetchone()[0]
        
        # 7. ADMIN
        c.execute("SELECT username, email, role FROM users WHERE role = 'admin'")
        admins = c.fetchall()
        results["admin"] = [{"username": a[0], "email": a[1], "role": a[2]} for a in admins]
        
        if not admins:
            results["missing"].append("Nenhum usuário admin encontrado")
        
        conn.close()
        
        if results["missing"]:
            results["status"] = "warning"
        
        return render_template("diagnostics.html", results=results, active="settings")
        
    except Exception as e:
        return render_template("diagnostics.html", 
                             results={"status": "error", "error": str(e)}, 
                             active="settings")

if __name__ == "__main__":
    print("[Flask] Iniciando servidor...")
        # Valida configurações antes de iniciar
    errors, warnings = config.validate_config()
    
    if errors:
        print("\n❌ ERROS DE CONFIGURAÇÃO - não é possível iniciar:")
        for error in errors:
            print(f"  {error}")
        exit(1)
    
    if warnings:
        print("\n⚠️  AVISOS DE CONFIGURAÇÃO:")
        for warning in warnings:
            print(f"  {warning}")
    
    # Exibe resumo de configuração
    config.print_config_summary()
    
    # Inicia servidor Flask
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
        threaded=True
    )
    
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)