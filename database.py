"""
database.py

Gerencia usuários, logs de alertas, logs de sistema e configurações no SQLite.
"""

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "cv_system.db"


def init_db():
    """Cria as tabelas se não existirem e insere configurações padrão."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            out_time REAL NOT NULL,
            snapshot_path TEXT,
            email_sent INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Tabela para logs de sistema (PAUSAR, PARAR, RETOMAR, INICIAR)
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            username TEXT NOT NULL,
            reason TEXT,
            email_sent INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Configurações padrão
    default_settings = {
        # YOLO
        "conf_thresh": "0.87",
        "model_path": r"yolo_models\yolov8n.pt",

        ## performance / resize
        "target_width": "960",
        "frame_step": "1",

        # zona / alertas
        # Agora apenas zonas inteligentes poligonais (JSON), sem retângulo fixo
        "safe_zone": "[]",
        "max_out_time": "5.0",
        "email_cooldown": "10.0",
        "buffer_seconds": "2.0",

        # fonte de vídeo
        "source": "0",
        
        # parâmetros da câmera
        "cam_width": "960",
        "cam_height": "640",
        "cam_fps": "20",

        # tracker
        "tracker": "botsort.yaml",

        # parâmetros de zona (novos)
        "zone_empty_timeout": "15.0",
        "zone_full_timeout": "20.0",
        "zone_full_threshold": "5",

        # E-mail / SMTP
        "email_smtp_server": "smtp.gmail.com",
        "email_smtp_port": "587",
        "email_use_tls": "1",
        "email_use_ssl": "0",
        "email_from": "jonatandj2k14@gmail.com",
        "email_user": "jonatandj2k14@gmail.com",
        "email_password": "isozasiyvtxvmpcb",
    }

    for key, value in default_settings.items():
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        if not c.fetchone():
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    conn.commit()
    conn.close()


def create_user(username, email, password, role="user"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()

    if result and check_password_hash(result[0], password):
        return {"username": username, "role": result[1]}
    return None


def update_last_login(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET last_login = ? WHERE username = ?",
        (datetime.now(), username)
    )
    conn.commit()
    conn.close()


def log_alert(person_id, out_time, snapshot_path, email_sent=True):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO alerts (person_id, out_time, snapshot_path, email_sent) VALUES (?, ?, ?, ?)",
        (person_id, out_time, snapshot_path, 1 if email_sent else 0)
    )
    conn.commit()
    conn.close()


def get_recent_alerts(limit=20):
    """Retorna alertas recentes COM snapshot_path."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT person_id, out_time, timestamp, email_sent, snapshot_path "
        "FROM alerts ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    results = c.fetchall()
    conn.close()
    return results


def delete_alert(person_id, timestamp):
    """
    Remove um alerta específico com base em person_id + timestamp exato.
    Usado na página de logs e no card Activity.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "DELETE FROM alerts WHERE person_id = ? AND timestamp = ?",
        (person_id, timestamp)
    )
    conn.commit()
    rows = c.rowcount
    conn.close()
    return rows > 0


def log_system_action(action, username, reason=None, email_sent=False):
    """
    Registra ações do sistema (PAUSAR, RETOMAR, PARAR, INICIAR).

    Args:
        action: string com a ação (PAUSAR, RETOMAR, PARAR, INICIAR)
        username: usuário que executou a ação
        reason: motivo informado (opcional)
        email_sent: bool indicando se e-mail foi disparado
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO system_logs (action, username, reason, email_sent) VALUES (?, ?, ?, ?)",
        (action, username, reason, 1 if email_sent else 0)
    )
    conn.commit()
    conn.close()


def get_system_logs(limit=100):
    """
    Retorna logs de ações do sistema.

    Returns:
        Lista de tuplas: (action, username, reason, timestamp, email_sent)
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT action, username, reason, timestamp, email_sent "
        "FROM system_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    results = c.fetchall()
    conn.close()
    return results



def delete_system_log(timestamp):
    """
    Remove um log de sistema específico com base no timestamp exato.
    Usado na página de logs (Logs de Sistema).
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "DELETE FROM system_logs WHERE timestamp = ?",
        (timestamp,)
    )
    conn.commit()
    rows = c.rowcount
    conn.close()
    return rows > 0


def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, username, email, role, created_at, last_login FROM users")
    results = c.fetchall()
    conn.close()
    return results


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default


def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


# Inicializar banco de dados
init_db()

# Criar usuário admin padrão
if not verify_user("admin", "admin123"):
    create_user("admin", "admin@example.com", "admin123", role="admin")
