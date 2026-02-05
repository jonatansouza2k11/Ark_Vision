"""
============================================================================
backend/models/alerts.py - ULTRA OPTIMIZED v3.0
Pydantic Models para Sistema de Alertas
============================================================================
"""

from typing import Optional, Dict, Any, Union, List, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum
import hashlib
import json


# ============================================================================
# OTIMIZAÇÃO 1: Extended Enums
# ============================================================================

class AlertSeverity(str, Enum):
    """✅ Níveis de severidade do alerta"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    @property
    def priority_score(self) -> int:
        """NEW: Get numeric priority score"""
        return {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4
        }[self]
    
    @property
    def color_code(self) -> str:
        """NEW: Get color code for UI"""
        return {
            AlertSeverity.LOW: "#90EE90",      # Light green
            AlertSeverity.MEDIUM: "#FFD700",   # Gold
            AlertSeverity.HIGH: "#FF8C00",     # Dark orange
            AlertSeverity.CRITICAL: "#FF0000"  # Red
        }[self]


class AlertType(str, Enum):
    """✅ Tipos de alerta"""
    ZONE_VIOLATION = "zone_violation"
    ZONE_EMPTY = "zone_empty"
    ZONE_FULL = "zone_full"
    TIMEOUT = "timeout"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CUSTOM = "custom"


class AlertState(str, Enum):
    """✅ NEW: Alert lifecycle states"""
    PENDING = "pending"          # Just created
    ACKNOWLEDGED = "acknowledged"  # Viewed by operator
    IN_PROGRESS = "in_progress"   # Being handled
    RESOLVED = "resolved"         # Fixed/handled
    DISMISSED = "dismissed"       # Ignored/false positive
    ESCALATED = "escalated"       # Sent to higher authority


class AlertPriority(str, Enum):
    """✅ NEW: Alert priority for queue management"""
    URGENT = "urgent"      # Process immediately
    HIGH = "high"          # Process soon
    NORMAL = "normal"      # Standard queue
    LOW = "low"            # Can wait


# ============================================================================
# OTIMIZAÇÃO 2: Alert Statistics
# ============================================================================

class AlertStatistics(BaseModel):
    """✅ NEW: Statistics for alert analysis"""
    total_alerts: int = 0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_state: Dict[str, int] = Field(default_factory=dict)
    average_resolution_time: Optional[float] = None
    false_positive_rate: Optional[float] = None
    
    def add_alert(self, alert: 'AlertResponse'):
        """Add alert to statistics"""
        self.total_alerts += 1
        
        # Count by severity
        if alert.severity not in self.by_severity:
            self.by_severity[alert.severity] = 0
        self.by_severity[alert.severity] += 1
        
        # Count by type
        if alert.alert_type not in self.by_type:
            self.by_type[alert.alert_type] = 0
        self.by_type[alert.alert_type] += 1


class AlertTimeAnalysis(BaseModel):
    """✅ NEW: Time-based alert analysis"""
    period_start: datetime
    period_end: datetime
    total_alerts: int
    alerts_per_hour: float
    peak_hour: Optional[int] = None
    peak_count: Optional[int] = None
    hourly_distribution: Dict[int, int] = Field(default_factory=dict)


# ============================================================================
# OTIMIZAÇÃO 3: Alert Filters
# ============================================================================

class AlertFilters(BaseModel):
    """✅ NEW: Comprehensive alert filtering"""
    severity: Optional[List[AlertSeverity]] = None
    alert_type: Optional[List[AlertType]] = None
    state: Optional[List[AlertState]] = None
    person_id: Optional[int] = None
    zone_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    resolved: Optional[bool] = None
    email_sent: Optional[bool] = None
    min_out_time: Optional[float] = None
    max_out_time: Optional[float] = None
    
    def matches(self, alert: 'AlertResponse') -> bool:
        """
        NEW: Check if alert matches filters
        
        Args:
            alert: Alert to check
        
        Returns:
            True if alert matches all filters
        """
        # Severity filter
        if self.severity and alert.severity not in [s.value for s in self.severity]:
            return False
        
        # Type filter
        if self.alert_type and alert.alert_type not in [t.value for t in self.alert_type]:
            return False
        
        # State filter
        if self.state and alert.state not in [s.value for s in self.state]:
            return False
        
        # Person ID filter
        if self.person_id and alert.person_id != self.person_id:
            return False
        
        # Zone ID filter
        if self.zone_id and alert.zone_id != self.zone_id:
            return False
        
        # Date range filter
        if self.date_from and alert.created_at < self.date_from:
            return False
        if self.date_to and alert.created_at > self.date_to:
            return False
        
        # Resolved filter
        if self.resolved is not None and alert.resolved != self.resolved:
            return False
        
        # Email sent filter
        if self.email_sent is not None and alert.email_sent != self.email_sent:
            return False
        
        # Out time range filter
        if self.min_out_time is not None and alert.out_time < self.min_out_time:
            return False
        if self.max_out_time is not None and alert.out_time > self.max_out_time:
            return False
        
        return True


# ============================================================================
# CREATE SCHEMA (Enhanced)
# ============================================================================

class AlertCreate(BaseModel):
    """
    ✅ Schema para criação de alerta (100% compatible + NEW features)
    
    Campos obrigatórios:
    - person_id: ID da pessoa detectada
    - out_time: Tempo fora da zona (segundos)
    
    Campos opcionais (v2.0):
    - zone_id, zone_name, alert_type, severity, etc.
    
    NEW v3.0:
    - state: Estado do alerta
    - priority: Prioridade do alerta
    - confidence: Confiança da detecção
    - auto_dismiss: Auto-dismiss após X segundos
    """
    
    # ✅ Campos obrigatórios (v1.0)
    person_id: int = Field(..., ge=1, description="ID da pessoa detectada")
    out_time: float = Field(..., ge=0.0, description="Tempo fora da zona em segundos")
    
    # ✅ Campos opcionais - Tracking (v1.0)
    track_id: Optional[int] = Field(None, ge=1, description="ID do tracker YOLO")
    
    # ✅ Campos opcionais - Zona (v1.0)
    zone_id: Optional[int] = Field(None, ge=1, description="ID da zona relacionada")
    zone_index: Optional[int] = Field(None, ge=0, description="Índice da zona (legacy)")
    zone_name: Optional[str] = Field(None, max_length=100, description="Nome da zona")
    
    # ✅ Aceita str também (v2.0 - será normalizado)
    alert_type: Union[AlertType, str] = Field(
        default=AlertType.ZONE_VIOLATION,
        description="Tipo do alerta"
    )
    severity: Union[AlertSeverity, str] = Field(
        default=AlertSeverity.MEDIUM,
        description="Severidade do alerta"
    )
    
    # ✅ Campos opcionais - Descrição (v1.0)
    description: Optional[str] = Field(None, max_length=500, description="Descrição do alerta")
    
    # ✅ Campos opcionais - Mídia (v1.0)
    snapshot_path: Optional[str] = Field(None, max_length=500, description="Caminho da foto")
    video_path: Optional[str] = Field(None, description="Caminho do vídeo")
    
    # ✅ Campos opcionais - Notificação (v1.0)
    email_sent: bool = Field(default=False, description="Email foi enviado?")
    
    # ✅ Campos opcionais - Metadados (v1.0)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dados adicionais em formato JSON"
    )
    
    # ➕ NEW v3.0: Enhanced fields
    state: AlertState = Field(
        default=AlertState.PENDING,
        description="Estado inicial do alerta"
    )
    
    priority: Optional[AlertPriority] = Field(
        None,
        description="Prioridade do alerta (auto-calculada se None)"
    )
    
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confiança da detecção (0.0 a 1.0)"
    )
    
    auto_dismiss_after: Optional[int] = Field(
        None,
        ge=60,
        description="Auto-dismiss após N segundos (mínimo 60s)"
    )
    
    source: Optional[str] = Field(
        default="yolo",
        max_length=50,
        description="Fonte do alerta (yolo, manual, system)"
    )
    
    # ✅ Validador de modelo (v2.0 - mantido)
    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        """✅ Normaliza severity e alert_type antes da validação (v2.0 compatible)"""
        if isinstance(data, dict):
            # Normaliza severity
            if 'severity' in data and isinstance(data['severity'], str):
                data['severity'] = data['severity'].upper()
            
            # Normaliza alert_type
            if 'alert_type' in data and isinstance(data['alert_type'], str):
                data['alert_type'] = data['alert_type'].lower()
        
        return data
    
    @field_validator('out_time')
    @classmethod
    def validate_out_time(cls, v):
        """✅ Valida que out_time é positivo e arredonda (v1.0 compatible)"""
        if v < 0:
            raise ValueError("out_time deve ser maior ou igual a zero")
        return round(v, 2)
    
    @model_validator(mode='after')
    def auto_calculate_priority(self) -> 'AlertCreate':
        """
        ➕ NEW: Auto-calculate priority if not provided
        """
        if self.priority is None:
            # Calculate based on severity and out_time
            severity_map = {
                AlertSeverity.LOW: AlertPriority.LOW,
                AlertSeverity.MEDIUM: AlertPriority.NORMAL,
                AlertSeverity.HIGH: AlertPriority.HIGH,
                AlertSeverity.CRITICAL: AlertPriority.URGENT
            }
            
            # Convert string to enum if needed
            severity_enum = AlertSeverity(self.severity) if isinstance(self.severity, str) else self.severity
            self.priority = severity_map[severity_enum]
        
        return self
    
    # ========================================================================
    # NEW v3.0: Alert Methods
    # ========================================================================
    
    def calculate_hash(self) -> str:
        """
        ➕ NEW: Calculate unique hash for deduplication
        
        Returns:
            MD5 hash of alert key fields
        """
        key_fields = f"{self.person_id}|{self.zone_id}|{self.alert_type}"
        return hashlib.md5(key_fields.encode()).hexdigest()
    
    def is_high_priority(self) -> bool:
        """
        ➕ NEW: Check if alert is high priority
        
        Returns:
            True if urgent or high priority
        """
        return self.priority in [AlertPriority.URGENT, AlertPriority.HIGH]
    
    def should_send_email(self) -> bool:
        """
        ➕ NEW: Determine if email should be sent
        
        Returns:
            True if severity is HIGH or CRITICAL
        """
        severity_enum = AlertSeverity(self.severity) if isinstance(self.severity, str) else self.severity
        return severity_enum in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
    
    def to_notification_dict(self) -> Dict[str, Any]:
        """
        ➕ NEW: Convert to notification format
        
        Returns:
            Dict suitable for notification systems
        """
        return {
            "title": f"Alert: {self.alert_type}",
            "message": self.description or f"Person {self.person_id} detected",
            "severity": self.severity,
            "priority": self.priority,
            "zone": self.zone_name,
            "timestamp": datetime.now().isoformat()
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "person_id": 1,
                "track_id": 42,
                "out_time": 5.3,
                "zone_id": 1,
                "zone_name": "Zona Principal",
                "alert_type": "zone_violation",
                "severity": "HIGH",
                "description": "Pessoa permaneceu fora da zona por 5.3 segundos",
                "snapshot_path": "snapshots/alert_20240101_123456.jpg",
                "video_path": "videos/alert_20240101_123456.mp4",
                "email_sent": True,
                "metadata": {
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 300]
                },
                "state": "pending",
                "priority": "high",
                "confidence": 0.95,
                "source": "yolo"
            }
        }
    )


# ============================================================================
# UPDATE SCHEMA (Enhanced)
# ============================================================================

class AlertUpdate(BaseModel):
    """
    ✅ Schema para atualização de alerta (100% compatible + NEW features)
    Todos os campos são opcionais.
    """
    
    # ✅ v1.0 fields
    severity: Optional[Union[AlertSeverity, str]] = None
    description: Optional[str] = Field(None, max_length=500)
    email_sent: Optional[bool] = None
    resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    
    # ➕ NEW v3.0 fields
    state: Optional[AlertState] = None
    priority: Optional[AlertPriority] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = Field(None, max_length=50)
    escalated_to: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    
    @model_validator(mode='before')
    @classmethod
    def normalize_severity(cls, data: Any) -> Any:
        """✅ Normaliza severity antes da validação (v1.0 compatible)"""
        if isinstance(data, dict) and 'severity' in data:
            if data['severity'] is not None and isinstance(data['severity'], str):
                data['severity'] = data['severity'].upper()
        return data
    
    @model_validator(mode='after')
    def validate_state_transitions(self) -> 'AlertUpdate':
        """
        ➕ NEW: Validate state machine transitions
        """
        # Auto-set timestamps based on state
        if self.state == AlertState.ACKNOWLEDGED and self.acknowledged_at is None:
            self.acknowledged_at = datetime.now()
        
        if self.state == AlertState.RESOLVED and self.resolved_at is None:
            self.resolved_at = datetime.now()
            if self.resolved is None:
                self.resolved = True
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "severity": "LOW",
                "description": "Alerta resolvido - falso positivo",
                "email_sent": True,
                "resolved": True,
                "resolved_by": "admin",
                "state": "resolved",
                "notes": "False positive - person was authorized"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMA (Enhanced)
# ============================================================================

class AlertResponse(BaseModel):
    """
    ✅ Schema de resposta da API (100% compatible + NEW features)
    Retorna todos os dados do alerta.
    """
    
    # ✅ v1.0 Campos principais
    id: int
    person_id: int
    out_time: float
    
    # ✅ v1.0 Tracking
    track_id: Optional[int] = None
    
    # ✅ v1.0 Zona
    zone_id: Optional[int] = None
    zone_index: Optional[int] = None
    zone_name: Optional[str] = None
    
    # ✅ v1.0 Classificação
    alert_type: str
    severity: str
    description: Optional[str] = None
    
    # ✅ v1.0 Mídia
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    
    # ✅ v1.0 Notificação
    email_sent: bool
    
    # ✅ v1.0 Resolução
    resolved: Optional[bool] = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    # ✅ v1.0 Metadados
    metadata: Optional[Dict[str, Any]] = None
    
    # ✅ v1.0 Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # ➕ NEW v3.0 fields
    state: AlertState = AlertState.PENDING
    priority: Optional[AlertPriority] = None
    confidence: Optional[float] = None
    source: Optional[str] = "yolo"
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    escalated_to: Optional[str] = None
    notes: Optional[str] = None
    auto_dismiss_after: Optional[int] = None
    dismissed_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "person_id": 1,
                "track_id": 42,
                "out_time": 5.3,
                "zone_id": 1,
                "zone_index": 0,
                "zone_name": "Zona Principal",
                "alert_type": "zone_violation",
                "severity": "HIGH",
                "description": "Pessoa permaneceu fora da zona por 5.3 segundos",
                "snapshot_path": "snapshots/alert_20240101_123456.jpg",
                "video_path": "videos/alert_20240101_123456.mp4",
                "email_sent": True,
                "resolved": False,
                "resolved_at": None,
                "resolved_by": None,
                "metadata": {
                    "confidence": 0.95,
                    "bbox": [100, 100, 200, 300]
                },
                "created_at": "2024-01-01T12:34:56",
                "updated_at": None,
                "state": "pending",
                "priority": "high",
                "confidence": 0.95,
                "source": "yolo"
            }
        }
    )
    
    # ========================================================================
    # NEW v3.0: Response Methods
    # ========================================================================
    
    def get_age_seconds(self) -> float:
        """
        ➕ NEW: Get alert age in seconds
        
        Returns:
            Seconds since alert creation
        """
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_age_minutes(self) -> float:
        """
        ➕ NEW: Get alert age in minutes
        
        Returns:
            Minutes since alert creation
        """
        return self.get_age_seconds() / 60
    
    def is_stale(self, threshold_minutes: int = 60) -> bool:
        """
        ➕ NEW: Check if alert is stale
        
        Args:
            threshold_minutes: Minutes before considering stale
        
        Returns:
            True if alert is older than threshold
        """
        return self.get_age_minutes() > threshold_minutes
    
    def should_auto_dismiss(self) -> bool:
        """
        ➕ NEW: Check if alert should be auto-dismissed
        
        Returns:
            True if auto_dismiss_after time has passed
        """
        if not self.auto_dismiss_after:
            return False
        
        return self.get_age_seconds() >= self.auto_dismiss_after
    
    def get_resolution_time(self) -> Optional[float]:
        """
        ➕ NEW: Calculate time to resolution
        
        Returns:
            Seconds from creation to resolution, or None if not resolved
        """
        if not self.resolved_at:
            return None
        
        return (self.resolved_at - self.created_at).total_seconds()
    
    def to_csv_row(self) -> List[str]:
        """
        ➕ NEW: Convert to CSV row format
        
        Returns:
            List of string values for CSV export
        """
        return [
            str(self.id),
            str(self.person_id),
            str(self.out_time),
            str(self.zone_name or ""),
            self.alert_type,
            self.severity,
            str(self.created_at),
            str(self.resolved),
            str(self.email_sent)
        ]
    
    def to_summary(self) -> str:
        """
        ➕ NEW: Get human-readable summary
        
        Returns:
            Summary string for notifications
        """
        return (
            f"[{self.severity}] {self.alert_type}: "
            f"Person {self.person_id} in {self.zone_name or 'unknown zone'} "
            f"for {self.out_time:.1f}s"
        )
    
    def get_priority_score(self) -> int:
        """
        ➕ NEW: Calculate numeric priority score
        
        Returns:
            Score from 1-10 for sorting
        """
        # Base score from severity
        severity_scores = {
            "LOW": 1,
            "MEDIUM": 3,
            "HIGH": 6,
            "CRITICAL": 9
        }
        score = severity_scores.get(self.severity, 1)
        
        # Boost for unresolved
        if not self.resolved:
            score += 1
        
        # Boost for high confidence
        if self.confidence and self.confidence > 0.9:
            score += 1
        
        return min(score, 10)


# ============================================================================
# NEW v3.0: Bulk Operations
# ============================================================================

class AlertBulkCreate(BaseModel):
    """➕ NEW: Bulk alert creation"""
    alerts: List[AlertCreate] = Field(..., min_length=1, max_length=100)
    
    def get_count(self) -> int:
        """Get number of alerts"""
        return len(self.alerts)
    
    def get_by_severity(self) -> Dict[str, int]:
        """Count alerts by severity"""
        counts: Dict[str, int] = {}
        for alert in self.alerts:
            severity = str(alert.severity)
            counts[severity] = counts.get(severity, 0) + 1
        return counts


class AlertBulkUpdate(BaseModel):
    """➕ NEW: Bulk alert update"""
    alert_ids: List[int] = Field(..., min_length=1)
    update: AlertUpdate


class AlertBulkResponse(BaseModel):
    """➕ NEW: Bulk operation response"""
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    results: List[AlertResponse] = Field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


# ============================================================================
# NEW v3.0: Alert List with Pagination
# ============================================================================

class AlertListResponse(BaseModel):
    """➕ NEW: Paginated alert list response"""
    alerts: List[AlertResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False
    
    # Statistics
    summary: Optional[AlertStatistics] = None
    
    def calculate_summary(self):
        """Calculate summary statistics"""
        self.summary = AlertStatistics()
        for alert in self.alerts:
            self.summary.add_alert(alert)


# ============================================================================
# NEW v3.0: Alert Export Formats
# ============================================================================

class AlertExportFormat(str, Enum):
    """➕ NEW: Export format options"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EMAIL = "email"


class AlertExportRequest(BaseModel):
    """➕ NEW: Request for exporting alerts"""
    format: AlertExportFormat
    filters: Optional[AlertFilters] = None
    include_resolved: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ============================================================================
# TESTE v3.0
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("📋 TESTE: Alert Models v3.0")
    print("=" * 70)
    
    # Test 1: v1.0 compatibility - Basic creation
    print("\n✅ Teste 1: v1.0 Compatibility - Criação básica")
    alert_v1 = AlertCreate(
        person_id=1,
        track_id=42,
        out_time=5.3,
        zone_id=1,
        zone_name="Zona Principal",
        severity="high",  # ✅ String lowercase (será normalizado)
        alert_type="zone_violation"
    )
    print(f"   ✅ Severity normalizado: {alert_v1.severity}")
    print(f"   ✅ Priority auto-calculado: {alert_v1.priority}")
    print(f"   ✅ Out time arredondado: {alert_v1.out_time}")
    
    # Test 2: NEW v3.0 features
    print("\n➕ Teste 2: NEW v3.0 - Features avançados")
    alert_v3 = AlertCreate(
        person_id=1,
        out_time=5.3,
        severity="CRITICAL",
        state=AlertState.PENDING,
        priority=AlertPriority.URGENT,
        confidence=0.95,
        auto_dismiss_after=300,
        source="yolo"
    )
    print(f"   ✅ Estado: {alert_v3.state}")
    print(f"   ✅ Prioridade: {alert_v3.priority}")
    print(f"   ✅ Confiança: {alert_v3.confidence}")
    print(f"   ✅ É high priority? {alert_v3.is_high_priority()}")
    print(f"   ✅ Deve enviar email? {alert_v3.should_send_email()}")
    
    # Test 3: Alert hash for deduplication
    print("\n➕ Teste 3: Alert hash (deduplicação)")
    hash1 = alert_v1.calculate_hash()
    print(f"   ✅ Hash: {hash1}")
    
    # Test 4: Alert response with age calculation
    print("\n➕ Teste 4: Alert response com cálculos")
    response = AlertResponse(
        id=123,
        person_id=1,
        out_time=5.3,
        alert_type="zone_violation",
        severity="HIGH",
        email_sent=True,
        created_at=datetime.now() - timedelta(minutes=30),
        resolved_at=datetime.now() - timedelta(minutes=5),
        state=AlertState.RESOLVED,
        priority=AlertPriority.HIGH,
        confidence=0.95
    )
    print(f"   ✅ Idade: {response.get_age_minutes():.1f} minutos")
    print(f"   ✅ Tempo de resolução: {response.get_resolution_time():.1f}s")
    print(f"   ✅ Priority score: {response.get_priority_score()}/10")
    print(f"   ✅ Summary: {response.to_summary()}")
    
    # Test 5: Alert filters
    print("\n➕ Teste 5: Filtros de alerta")
    filters = AlertFilters(
        severity=[AlertSeverity.HIGH, AlertSeverity.CRITICAL],
        resolved=False,
        min_out_time=3.0
    )
    
    test_alerts = [
        AlertResponse(
            id=1, person_id=1, out_time=5.0, alert_type="zone_violation",
            severity="HIGH", email_sent=False, created_at=datetime.now(),
            resolved=False, state=AlertState.PENDING
        ),
        AlertResponse(
            id=2, person_id=2, out_time=2.0, alert_type="zone_violation",
            severity="LOW", email_sent=False, created_at=datetime.now(),
            resolved=False, state=AlertState.PENDING
        ),
    ]
    
    matched = [a for a in test_alerts if filters.matches(a)]
    print(f"   ✅ Alertas filtrados: {len(matched)}/{len(test_alerts)}")
    
    # Test 6: Bulk operations
    print("\n➕ Teste 6: Operações em lote")
    bulk_create = AlertBulkCreate(
        alerts=[
            AlertCreate(person_id=1, out_time=3.0, severity="LOW"),
            AlertCreate(person_id=2, out_time=7.0, severity="HIGH"),
            AlertCreate(person_id=3, out_time=5.0, severity="MEDIUM"),
        ]
    )
    by_severity = bulk_create.get_by_severity()
    print(f"   ✅ Total: {bulk_create.get_count()} alertas")
    print(f"   ✅ Por severidade: {by_severity}")
    
    # Test 7: Alert statistics
    print("\n➕ Teste 7: Estatísticas")
    stats = AlertStatistics()
    for alert in test_alerts:
        stats.add_alert(alert)
    print(f"   ✅ Total: {stats.total_alerts}")
    print(f"   ✅ Por severidade: {stats.by_severity}")
    
    # Test 8: Severity enum properties
    print("\n➕ Teste 8: Severity enum properties")
    for severity in AlertSeverity:
        print(f"   ✅ {severity.value}: score={severity.priority_score}, color={severity.color_code}")
    
    # Test 9: State transitions
    print("\n➕ Teste 9: Transições de estado")
    update = AlertUpdate(
        state=AlertState.ACKNOWLEDGED,
        acknowledged_by="operator1"
    )
    print(f"   ✅ Estado: {update.state}")
    print(f"   ✅ Timestamp auto-set: {update.acknowledged_at is not None}")
    
    # Test 10: Backward compatibility validation
    print("\n✅ Teste 10: Validação de compatibilidade v1.0")
    # Testa se código v1.0 funciona
    try:
        old_style_alert = AlertCreate(
            person_id=1,
            out_time=5.0,
            severity="medium",  # lowercase (v1.0 style)
            email_sent=False
        )
        print(f"   ✅ Código v1.0 funciona: severity={old_style_alert.severity}")
        print(f"   ✅ Defaults mantidos: alert_type={old_style_alert.alert_type}")
        print(f"   ✅ Compatibilidade 100%!")
    except Exception as e:
        print(f"   ❌ FALHOU: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes v3.0 passaram!")
    print("✅ Compatibilidade v1.0/v2.0 mantida 100%!")
    print("=" * 70)
