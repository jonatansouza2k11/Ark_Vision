"""
Zone state management for runtime processing.
Maintains per-zone state across frames (timers, counters, status).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, Dict


@dataclass
class ZoneState:
    """
    Estado runtime de uma zona (mantido entre frames).
    
    Attributes:
        zone_id: ID da zona
        object_count: Quantidade de objetos detectados na zona
        objects_inside: Set de track_ids dentro da zona (frame atual)
        status: Status atual (EMPTY, OCCUPIED, FULL, ALERT, etc)
        
        # Timers
        empty_since: Timestamp de quando ficou vazia (para timeout)
        full_since: Timestamp de quando ficou cheia (para timeout)
        last_alert_time: Timestamp do último alerta enviado (para cooldown)
        
        # Counting mode
        entry_times: Dict[track_id, datetime] - quando cada objeto entrou
        counted_entries: Set de track_ids já contados (evita duplicação)
        object_positions: Dict[track_id, bool] - presença prévia (para detectar saídas)
    """
    
    zone_id: int
    object_count: int = 0
    objects_inside: Set[int] = field(default_factory=set)
    status: str = "IDLE"
    
    # Timers
    empty_since: Optional[datetime] = None
    full_since: Optional[datetime] = None
    last_alert_time: Optional[datetime] = None
    
    # Counting mode
    entry_times: Dict[int, datetime] = field(default_factory=dict)
    counted_entries: Set[int] = field(default_factory=set)
    object_positions: Dict[int, bool] = field(default_factory=dict)
    
    def reset_timers(self):
        """Reseta todos os timers da zona."""
        self.empty_since = None
        self.full_since = None
        self.last_alert_time = None
    
    def reset_counting_state(self):
        """Reseta estado específico de counting mode."""
        self.entry_times.clear()
        self.counted_entries.clear()
        self.object_positions.clear()
    
    def update_object_count(self):
        """Atualiza object_count baseado em objects_inside."""
        self.object_count = len(self.objects_inside)
