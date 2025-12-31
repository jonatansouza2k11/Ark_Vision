"""
Seed database with default data
Popula PostgreSQL com dados iniciais
"""

from sqlalchemy.orm import Session
from fastapi_app.core.database import SessionLocal
from fastapi_app.models.setting import Setting
from fastapi_app.models.user import User
from werkzeug.security import generate_password_hash


def seed_default_settings(db: Session):
    """Insere configurações padrão do sistema"""
    
    default_settings = {
        # YOLO
        "conf_thresh": "0.87",
        "model_path": r"yolo_models\yolov8n.pt",
        "target_width": "960",
        "frame_step": "1",
        
        # Zona / alertas
        "safe_zone": "[]",
        "max_out_time": "5.0",
        "email_cooldown": "10.0",
        "buffer_seconds": "2.0",
        
        # Fonte de vídeo
        "source": "0",
        
        # Câmera
        "cam_width": "960",
        "cam_height": "640",
        "cam_fps": "20",
        
        # Tracker
        "tracker": "botsort.yaml",
        
        # Zona
        "zone_empty_timeout": "15.0",
        "zone_full_timeout": "20.0",
        "zone_full_threshold": "5",
        
        # Email
        "email_smtp_server": "smtp.gmail.com",
        "email_smtp_port": "587",
        "email_use_tls": "1",
        "email_use_ssl": "0",
        "email_from": "jonatandj2k14@gmail.com",
        "email_user": "jonatandj2k14@gmail.com",
        "email_password": "isozasiyvtxvmpcb",
    }
    
    count = 0
    for key, value in default_settings.items():
        existing = db.query(Setting).filter(Setting.key == key).first()
        if not existing:
            setting = Setting(key=key, value=value)
            db.add(setting)
            count += 1
    
    db.commit()
    print(f"✅ {count} configurações inseridas")


def seed_admin_user(db: Session):
    """Cria usuário admin padrão"""
    
    existing = db.query(User).filter(User.username == "admin").first()
    if not existing:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()
        print("✅ Admin user criado (username: admin, password: admin123)")
    else:
        print("ℹ️  Admin user já existe")


def seed_all():
    """Popula banco com dados iniciais"""
    db = SessionLocal()
    try:
        print("\n" + "="*70)
        print("🌱 Populando PostgreSQL com dados iniciais...")
        print("="*70)
        
        seed_default_settings(db)
        seed_admin_user(db)
        
        print("="*70)
        print("✅ Banco de dados populado com sucesso!")
        print("="*70 + "\n")
    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
