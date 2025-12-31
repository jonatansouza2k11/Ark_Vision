"""
backend/create_admin.py
Cria usuário admin inicial
"""

import asyncio
import sys
from pathlib import Path

# Adiciona backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from database import create_user, get_user_by_username, init_database
from passlib.context import CryptContext

# Configuração de hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user():
    """Cria usuário admin se não existir"""
    
    print("=" * 70)
    print("🔐 ARK YOLO - Criação de Usuário Admin")
    print("=" * 70)
    
    # Inicializa database (garante que tabelas existem)
    await init_database()
    
    # Verifica se admin já existe
    admin = await get_user_by_username("admin")
    
    if admin:
        print("⚠️  Usuário 'admin' já existe!")
        print(f"   Email: {admin['email']}")
        print(f"   Criado em: {admin['created_at']}")
        print()
        
        response = input("Deseja criar outro admin? (s/n): ").lower()
        if response != 's':
            print("❌ Operação cancelada.")
            return
    
    # Solicita dados do novo admin
    print()
    print("📝 Criando novo usuário admin...")
    print()
    
    username = input("Username [admin]: ").strip() or "admin"
    email = input("Email [admin@example.com]: ").strip() or "jonatandj2k14@gmail.com"
    password = input("Password [admin123]: ").strip() or "admin123"
    
    # Hash da senha
    password_hash = pwd_context.hash(password)
    
    # Cria usuário
    success = await create_user(
        username=username,
        email=email,
        password_hash=password_hash,
        role="admin"
    )
    
    if success:
        print()
        print("=" * 70)
        print("✅ Usuário admin criado com sucesso!")
        print("=" * 70)
        print(f"👤 Username: {username}")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"🛡️  Role: admin")
        print("=" * 70)
        print()
        print("🚀 Agora você pode fazer login no sistema!")
        print(f"   Frontend: http://localhost:5173")
        print(f"   API: http://localhost:8000/docs")
        print("=" * 70)
    else:
        print()
        print("❌ Erro ao criar usuário!")
        print("   Verifique se o username/email já existe.")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
