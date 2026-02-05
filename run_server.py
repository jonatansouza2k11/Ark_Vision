import sys
import asyncio


def main():
    """Inicia o servidor FastAPI com event loop correto para Windows."""
    
    # ======================================================================
    # 🔥 CRITICAL: Aplica policy ANTES de importar uvicorn/FastAPI
    # ======================================================================
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("✔ Windows Event Loop Policy applied")
    
    # Agora importa (após policy aplicada)
    import uvicorn
    from backend.core.config.config import settings

    print("=" * 70)
    print("ARK YOLO FastAPI - Windows Bootstrap")
    print("=" * 70)
    print(f"✔ Host: {settings.HOST}:{settings.PORT}")
    print("=" * 70)

    # ======================================================================
    # 🔥 FIX: Força uvicorn a usar o loop correto
    # ======================================================================
    if sys.platform.startswith("win"):
        # Cria loop explícito com a policy correta
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Usa uvicorn.Config + uvicorn.Server para controle total
        config = uvicorn.Config(
            "backend.app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower(),
            loop="asyncio",  # Força uso do asyncio (não auto)
        )
        server = uvicorn.Server(config)
        
        # Roda no loop que criamos
        loop.run_until_complete(server.serve())
    else:
        # Linux/Mac: usa uvicorn.run normal
        uvicorn.run(
            "backend.app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            log_level=settings.LOG_LEVEL.lower(),
        )


# ======================================================================
# 🔒 OBRIGATÓRIO NO WINDOWS
# ======================================================================
if __name__ == "__main__":
    main()
