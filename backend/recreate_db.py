"""
Recria banco de dados com schema atualizado
⚠️ ATENÇÃO: Isso apaga TODOS os dados!
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import init_database, close_db_pool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def recreate():
    """Recria banco de dados"""
    logger.warning("=" * 70)
    logger.warning("⚠️  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS!")
    logger.warning("=" * 70)
    
    response = input("\nDigite 'SIM' para confirmar: ")
    
    if response.strip().upper() != "SIM":
        logger.info("❌ Operação cancelada")
        return
    
    try:
        logger.info("\n🔧 Recriando banco de dados...")
        await init_database(force_recreate=True)
        logger.info("✅ Banco de dados recriado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db_pool()


if __name__ == "__main__":
    asyncio.run(recreate())
