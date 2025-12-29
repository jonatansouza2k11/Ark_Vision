"""
Política de Retenção de Logs para Compliance
Atende ANVISA RDC 301/2019 e FDA 21 CFR Part 11
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

class AuditRetentionPolicy:
    """
    Gerencia retenção de logs conforme regulamentações.
    
    ANVISA/FDA exigem:
    - Mínimo 5 anos de retenção
    - Backup em local separado
    - Impossibilidade de alteração
    """
    
    RETENTION_YEARS = 5
    BACKUP_DIR = 'logs/archive'
    
    @classmethod
    def archive_old_logs(cls):
        """
        Move logs antigos para diretório de arquivo.
        Deve ser executado mensalmente.
        """
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
        
        cutoff_date = datetime.now() - timedelta(days=90)  # Arquiva logs > 90 dias
        
        for log_file in Path('logs').glob('*.log.*'):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                archive_path = Path(cls.BACKUP_DIR) / f"{log_file.stem}_{datetime.now().strftime('%Y%m')}.log"
                shutil.copy2(log_file, archive_path)
                
                # Torna arquivo read-only (imutável)
                os.chmod(archive_path, 0o444)
                
                print(f"✅ Archived: {log_file} -> {archive_path}")
    
    @classmethod
    def check_retention_compliance(cls):
        """
        Verifica se há logs disponíveis para os últimos 5 anos.
        """
        required_date = datetime.now() - timedelta(days=365 * cls.RETENTION_YEARS)
        
        all_logs = list(Path('logs').glob('*.log*')) + list(Path(cls.BACKUP_DIR).glob('*.log'))
        
        oldest_log = min((Path(f).stat().st_mtime for f in all_logs), default=datetime.now().timestamp())
        oldest_date = datetime.fromtimestamp(oldest_log)
        
        is_compliant = oldest_date <= required_date
        
        return {
            'compliant': is_compliant,
            'oldest_log_date': oldest_date.isoformat(),
            'required_date': required_date.isoformat(),
            'total_logs': len(all_logs)
        }
