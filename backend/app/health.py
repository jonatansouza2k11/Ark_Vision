from fastapi import FastAPI
from backend.database import get_pool


def register_healthcheck(app: FastAPI) -> None:

    @app.get("/health")
    async def health():
        try:
            pool = await get_pool()
            async with pool.connection() as conn:
                await conn.execute("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}
