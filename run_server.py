import sys
import asyncio

# ======================================================================
# 🔥 FIX DEFINITIVO: psycopg3 + Windows + asyncio
# ======================================================================
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


def main():
    import uvicorn
    from backend.config import settings

    print("=" * 70)
    print("ARK YOLO FastAPI - Windows Bootstrap")
    print("=" * 70)
    print("✔ Event loop policy: WindowsSelectorEventLoopPolicy")
    print("=" * 70)

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,          # ok em dev
        log_level="info",
    )


# ======================================================================
# 🔒 OBRIGATÓRIO NO WINDOWS
# ======================================================================
if __name__ == "__main__":
    main()
