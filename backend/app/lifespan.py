from contextlib import asynccontextmanager
import logging

from backend.adapters.storage.database import init_db_pool, close_db_pool
from backend.core.config.config import settings

logger = logging.getLogger("lifespan")


@asynccontextmanager
async def lifespan(app):
    logger.info("🚀 Starting FastAPI Application")

    await init_db_pool()
    logger.info("✅ PostgreSQL connected")

    logger.info(f"🌐 API: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"📚 Docs: /docs" if settings.DEBUG else "Docs disabled")

    yield

    logger.info("🛑 Shutting down application")
    await close_db_pool()
    logger.info("✅ Database pool closed")
