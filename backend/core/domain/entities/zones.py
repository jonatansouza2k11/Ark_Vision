"""Entidades de zona v3.0 - Governança empresarial"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Set
from enum import Enum
from datetime import datetime

class ZoneMode(str, Enum):
    """Modos de operação de zona"""
    OCCUPANCY = "occupancy"
    COUNTING = "counting"
    CAPACITY = "capacity"
    ALERT = "alert"
    TRACKING = "tracking"
    QUEUE = "queue" 
    GENERIC = "GENERIC"
    EMPTY = "EMPTY"
    FULL = "FULL"
    
@dataclass(frozen=True)
class ZoneConfig:
    """
    Configuração imutável de zona (origem: DB).
    
    Versão: 3.0
    Compatibilidade: Backend API v1, Frontend v2
    """
    zone_id: int
    name: str
    polygon: List[Tuple[int, int]]
    mode: ZoneMode
    camera_id: int
    
    # Thresholds
    empty_threshold: int = 0
    full_threshold: int = 3
    
    # Timeouts (segundos)
    empty_timeout: float = 5.0
    full_timeout: float = 10.0
    email_cooldown: float = 600.0
    
    # Metadata (modo-específico)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Visual
    color: str = "#3B82F6"
    enabled: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ZoneConfig":
        """Constrói ZoneConfig de dict do DB/API"""
        return cls(
            zone_id=data["id"],
            name=data["name"],
            polygon=data.get("points", []),
            mode=ZoneMode(data.get("mode", "occupancy")),
            camera_id=data.get("camera_id", 0),
            empty_threshold=data.get("empty_threshold", 0),
            full_threshold=data.get("full_threshold", 3),
            empty_timeout=data.get("empty_timeout", 5.0),
            full_timeout=data.get("full_timeout", 10.0),
            email_cooldown=data.get("email_cooldown", 600.0),
            metadata=data.get("metadata", {}),
            color=data.get("color", "#3B82F6"),
            enabled=data.get("enabled", True),
        )

@dataclass
class ZoneRuntimeState:
    """
    Estado runtime mutável de zona.
    
    Vive em memória durante processamento.
    Pode ser serializado para Redis (multi-worker).
    """
    config: ZoneConfig
    
    # Contagem atual
    object_count: int = 0
    objects_inside: Set[int] = field(default_factory=set)
    
    # Status
    status: str = "IDLE"
    
    # Timers (epoch timestamp)
    last_alert_time: float = 0.0
    empty_since: float = 0.0
    full_since: float = 0.0
    
    # Counting mode (track positions)
    entry_times: Dict[int, float] = field(default_factory=dict)
    counted_entries: Set[int] = field(default_factory=set)
    object_positions: Dict[int, bool] = field(default_factory=dict)
    
    counting_last_inside: Set[int] = field(default_factory=set)
    counting_in: int = 0
    counting_out: int = 0
    counting_last_reset: float = 0.0

    def reset_timers(self) -> None:
        """Reset de todos os timers"""
        self.empty_since = 0.0
        self.full_since = 0.0
    
    def increment_count(self, delta: int) -> None:
        """Incrementa contador (regra de negócio)"""
        self.object_count = max(0, self.object_count + delta)
    
    def to_snapshot(self) -> Dict[str, Any]:
        """Serializa para Redis/cache"""
        return {
            "zone_id": self.config.zone_id,
            "object_count": self.object_count,
            "objects_inside": list(self.objects_inside),
            "status": self.status,
            "last_alert_time": self.last_alert_time,
            "empty_since": self.empty_since,
            "full_since": self.full_since,
        }

@dataclass(frozen=True)
class ZoneEvent:
    """
    Evento de zona (imutável, para persistência).
    
    Versão: 1.0
    """
    zone_id: int
    event_type: str  # "enter" | "exit" | "occupy" | "count" | "alert"
    track_id: int | None
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "zone_id": self.zone_id,
            "event_type": self.event_type,
            "track_id": self.track_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

@dataclass
class Zone:
    """
    Wrapper de conveniência (config + state).
    Usado por ZoneProcessor.
    """
    config: ZoneConfig
    state: ZoneRuntimeState
    
    @classmethod
    def from_config(cls, config: ZoneConfig) -> "Zone":
        """Cria zona com estado inicial"""
        return cls(
            config=config,
            state=ZoneRuntimeState(config=config)
        )
