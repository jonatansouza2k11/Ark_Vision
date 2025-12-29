"""
schedule_backup.py

Agendador de backups automáticos integrado ao Flask.
Roda em background thread.
"""

import threading
import time
from datetime import datetime, time as dt_time
from backup_logs import LogBackupManager
import logging

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Agendador de backups automáticos."""
    
    def __init__(self, backup_time="02:00"):
        """
        Args:
            backup_time: Hora do backup diário (formato "HH:MM")
        """
        self.backup_time = backup_time
        self.manager = LogBackupManager()
        self.running = False
        self.thread = None
        
        hour, minute = map(int, backup_time.split(':'))
        self.target_time = dt_time(hour, minute)
        
        logger.info(f"📅 BackupScheduler initialized: daily backup at {backup_time}")
    
    def _backup_loop(self):
        """Loop que executa backup diário."""
        logger.info("🔄 Backup scheduler thread started")
        last_backup_day = None
        
        while self.running:
            now = datetime.now()
            current_time = now.time()
            current_day = now.date()
            
            # Verifica se chegou a hora do backup E não foi feito hoje
            if (current_time.hour == self.target_time.hour and 
                current_time.minute == self.target_time.minute and
                current_day != last_backup_day):
                
                logger.info(f"⏰ Scheduled backup triggered at {now.strftime('%Y-%m-%d %H:%M')}")
                
                try:
                    backups = self.manager.backup_all_logs()
                    logger.info(f"✅ Scheduled backup completed: {len(backups)} files backed up")
                    last_backup_day = current_day
                    
                    # Limpeza automática no primeiro dia do mês
                    if now.day == 1:
                        logger.info("🗑️ Monthly cleanup starting...")
                        removed = self.manager.cleanup_old_backups(dry_run=False)
                        logger.info(f"✅ Cleanup completed: {len(removed)} old files removed")
                    
                except Exception as e:
                    logger.error(f"❌ Scheduled backup failed: {e}", exc_info=True)
            
            # Aguarda 60 segundos antes de checar novamente
            time.sleep(60)
        
        logger.info("🛑 Backup scheduler thread stopped")
    
    def start(self):
        """Inicia o scheduler em background thread."""
        if self.running:
            logger.warning("⚠️ Backup scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._backup_loop,
            daemon=True,
            name="BackupScheduler"
        )
        self.thread.start()
        logger.info(f"✅ Backup scheduler started (backup at {self.backup_time})")
    
    def stop(self):
        """Para o scheduler."""
        if not self.running:
            logger.warning("⚠️ Backup scheduler not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✅ Backup scheduler stopped")
    
    def get_status(self):
        """Retorna status do scheduler."""
        return {
            'running': self.running,
            'backup_time': self.backup_time,
            'thread_alive': self.thread.is_alive() if self.thread else False
        }


# Instância global (será usada no app.py)
backup_scheduler = None


def init_scheduler(app, backup_time="02:00"):
    """
    Inicializa o scheduler de backup.
    
    Chamada no app.py após criar o Flask app.
    
    Args:
        app: Instância do Flask
        backup_time: Hora do backup (formato "HH:MM")
    """
    global backup_scheduler
    
    backup_scheduler = BackupScheduler(backup_time=backup_time)
    backup_scheduler.start()
    
    app.logger.info(f"✅ Backup scheduler initialized and started")
    
    return backup_scheduler


if __name__ == "__main__":
    # Teste standalone
    print("🧪 Testing BackupScheduler...")
    
    scheduler = BackupScheduler(backup_time="02:00")
    status = scheduler.get_status()
    
    print(f"Status: {status}")
    print(f"Running: {status['running']}")
    print(f"Backup time: {status['backup_time']}")
    
    # Teste de backup manual
    print("\nExecutando backup de teste...")
    scheduler.manager.backup_all_logs()
    
    print("\n✅ Teste concluído")
