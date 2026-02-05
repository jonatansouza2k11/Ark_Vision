"""
Timer utilities for zone processing.
Handles cooldowns, timeouts, and auto-reset logic.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def should_send_alert(
    alert: bool,
    last_alert_time: Optional[datetime],
    email_cooldown: float,
    now: Optional[datetime] = None,
) -> bool:
    """
    Verifica se pode enviar alerta respeitando cooldown.
    
    Args:
        alert: Se alerta está ativo (condição de threshold atendida)
        last_alert_time: Timestamp do último alerta enviado
        email_cooldown: Tempo mínimo entre alertas (segundos)
        now: Timestamp atual (default: datetime.now())
    
    Returns:
        True se pode enviar alerta
    """
    if not alert:
        return False
    
    if last_alert_time is None:
        return True  # Primeiro alerta, sempre envia
    
    now = now or datetime.now()
    elapsed = (now - last_alert_time).total_seconds()
    
    return elapsed >= email_cooldown


def should_auto_reset(
    reset_interval: str,
    last_reset: Optional[str],
    now: Optional[datetime] = None,
) -> bool:
    """
    Verifica se deve resetar contadores automaticamente.
    Usado em counting mode.
    
    Args:
        reset_interval: 'none', 'hourly', 'daily', 'weekly', 'monthly'
        last_reset: ISO timestamp do último reset (ou None)
        now: Timestamp atual (default: datetime.now())
    
    Returns:
        True se deve resetar
    """
    if reset_interval == "none" or not last_reset:
        return False
    
    try:
        now = now or datetime.now()
        last_reset_dt = datetime.fromisoformat(last_reset)
        
        if reset_interval == "hourly":
            return (now - last_reset_dt).total_seconds() >= 3600
        
        elif reset_interval == "daily":
            return now.date() > last_reset_dt.date()
        
        elif reset_interval == "weekly":
            # Reset toda segunda-feira (weekday 0)
            return now.date() > last_reset_dt.date() and now.weekday() == 0
        
        elif reset_interval == "monthly":
            # Reset todo dia 1
            return now.date() > last_reset_dt.date() and now.day == 1
        
        return False
    
    except Exception as e:
        logger.warning(f"Error checking auto-reset: {e}")
        return False


def calculate_elapsed_time(
    start_time: Optional[datetime],
    end_time: Optional[datetime] = None,
    cap_at: Optional[float] = None,
) -> float:
    """
    Calcula tempo decorrido entre dois timestamps.
    
    Args:
        start_time: Timestamp inicial
        end_time: Timestamp final (default: datetime.now())
        cap_at: Limite máximo de tempo (segundos). Se elapsed > cap_at, retorna cap_at
    
    Returns:
        Tempo decorrido em segundos (ou 0.0 se start_time é None)
    """
    if start_time is None:
        return 0.0
    
    end_time = end_time or datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    if cap_at is not None:
        elapsed = min(elapsed, cap_at)
    
    return elapsed


def format_duration(seconds: float) -> str:
    """
    Formata duração em formato legível.
    
    Args:
        seconds: Duração em segundos
    
    Returns:
        String formatada (ex: "2h 15m", "45s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"
