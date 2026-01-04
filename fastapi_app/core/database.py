"""
Database configuration and session management
SQLAlchemy setup para FastAPI
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

from fastapi_app.core.config import settings


# ============================================
# DATABASE ENGINE
# ============================================

# Configuração otimizada para PostgreSQL ou SQLite
if settings.DATABASE_URL.startswith('postgresql'):
    # PostgreSQL: Pool de conexões
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,          # Conexões no pool
        max_overflow=20,       # Conexões extras sob demanda
        pool_pre_ping=True,    # Testa conexão antes de usar
        echo=settings.DEBUG,
        connect_args={"client_encoding": "utf8"}  # Fix UTF-8 encoding
    )
else:
    # SQLite: check_same_thread necessário
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )


# ============================================
# ENABLE FOREIGN KEYS (SQLite only)
# ============================================

# Foreign keys: Apenas para SQLite (PostgreSQL já tem por padrão)
if not settings.DATABASE_URL.startswith('postgresql'):
    def _enable_foreign_keys(dbapi_conn, connection_record):
        """Habilita foreign keys no SQLite"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    event.listen(engine, "connect", _enable_foreign_keys)


# ============================================
# SESSION FACTORY
# ============================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================
# BASE CLASS para Models
# ============================================

Base = declarative_base()


# ============================================
# DEPENDENCY INJECTION
# ============================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obter sessão do banco
    
    Uso em endpoints FastAPI:
    
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        users = db.query(User).all()
        return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_db():
    """
    Cria todas as tabelas no banco
    Chamado no startup do FastAPI
    """
    # Import models DENTRO da função para evitar circular import
    from fastapi_app.models.user import User
    from fastapi_app.models.alert import Alert
    from fastapi_app.models.setting import Setting
    from fastapi_app.models.system_log import SystemLog
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def drop_db():
    """
    CUIDADO: Deleta todas as tabelas
    Apenas para desenvolvimento/testes
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  Database dropped")


def reset_db():
    """
    CUIDADO: Reseta o banco (drop + create)
    Apenas para desenvolvimento/testes
    """
    drop_db()
    init_db()
    print("✅ Database reset complete")


# ============================================
# DATABASE INFO
# ============================================

def get_db_info():
    """Retorna informações sobre o banco"""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Detectar nome do banco baseado na URL
    if settings.DATABASE_URL.startswith('postgresql'):
        db_name = settings.DATABASE_URL.split('/')[-1]
    else:
        db_name = settings.DATABASE_PATH
    
    info = {
        "database_url": str(settings.DATABASE_URL),
        "database_name": db_name,
        "tables_count": len(tables),
        "tables": tables
    }
    
    return info


if __name__ == "__main__":
    # Teste de conexão
    print("="*70)
    print("🗄️  Database Connection Test")
    print("="*70)
    
    try:
        # Tentar conectar
        with engine.connect() as conn:
            print("✅ Conexão bem-sucedida!")
            
            # Mostrar info
            info = get_db_info()
            print(f"   Database: {info['database_name']}")
            print(f"   Tabelas existentes: {info['tables_count']}")
            if info['tables']:
                for table in info['tables']:
                    print(f"     - {table}")
            else:
                print("     (nenhuma tabela ainda)")
    
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*70)
