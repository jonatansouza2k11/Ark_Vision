# reset_admin_password.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Configure database URL (mesmo do seu .env)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ark_yolo"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_admin_password():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        from sqlalchemy import text
        
        # Nova senha para admin
        new_password = "admin123"  # ⚠️ MUDE DEPOIS!
        hashed_password = pwd_context.hash(new_password)
        
        # Update no banco
        query = text("""
            UPDATE users 
            SET hashed_password = :hashed_password 
            WHERE username = 'admin'
        """)
        
        await session.execute(query, {"hashed_password": hashed_password})
        await session.commit()
        
        print(f"✅ Senha do admin resetada para: {new_password}")
        print("⚠️  LEMBRE-SE DE MUDAR A SENHA APÓS O LOGIN!")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
