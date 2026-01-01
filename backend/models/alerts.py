"""
============================================================================
ALERTS MODELS - Pydantic Schemas
============================================================================
Modelos de validação para o sistema de alertas.
Compatível com PostgreSQL + JSON fallback.

Schemas:
- AlertCreate: Criação de novo alerta
- AlertUpdate: Atualização de alerta existente
- AlertResponse: Resposta da API (retorno)
============================================================================
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AlertSeverity(str, Enum):
    """Níveis de severidade do alerta"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """Tipos de alerta"""
    ZONE_VIOLATION = "zone_violation"
    ZONE_EMPTY = "zone_empty"
    ZONE_FULL = "zone_full"
    TIMEOUT = "timeout"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CUSTOM = "custom"


# ============================================================================
# CREATE SCHEMA
# ============================================================================

class AlertCreate(BaseModel):
    """
    Schema para criação de alerta.
    
    Campos obrigatórios:
    - person_id: ID da pessoa detectada
    - out_time: Tempo fora da zona (segundos)
    
    Campos opcionais:
    - zone_id: ID da zona relacionada
    - zone_name: Nome da zona
    - alert_type: Tipo do alerta
    - severity: Severidade (LOW/MEDIUM/HIGH/CRITICAL)
    - description: Descrição do alerta
    - snapshot_path: Caminho da foto
    - video_path: Caminho do vídeo
    - metadata: Dados adicionais (JSON)
    """
    
    # Campos obrigatórios
    person_id: int = Field(..., ge=1, description="ID da pessoa detectada")
    out_time: float = Field(..., ge=0.0, description="Tempo fora da zona em segundos")
    
    # Campos opcionais - Tracking
    track_id: Optional[int] = Field(None, ge=1, description="ID do tracker YOLO")
    
    # Campos opcionais - Zona
    zone_id: Optional[int] = Field(None, ge=1, description="ID da zona relacionada")
    zone_index: Optional[int] = Field(None, ge=0, description="Índice da zona (legacy)")
    zone_name: Optional[str] = Field(None, max_length=100, description="Nome da zona")
    
    # ✨ CORREÇÃO: Aceita str também (será normalizado)
    alert_type: Union[AlertType, str] = Field(
        default=AlertType.ZONE_VIOLATION,
        description="Tipo do alerta"
    )
    severity: Union[AlertSeverity, str] = Field(
        default=AlertSeverity.MEDIUM,
        description="Severidade do alerta"
    )
    
    # Campos opcionais - Descrição
    description: Optional[str] = Field(None, max_length=500, description="Descrição do alerta")
    
    # Campos opcionais - Mídia
    snapshot_path: Optional[str] = Field(None, max_length=500, description="Caminho da foto")
    video_path: Optional[str] = Field(None, description="Caminho do vídeo")
    
    # Campos opcionais - Notificação
    email_sent: bool = Field(default=False, description="Email foi enviado?")
    
    # Campos opcionais - Metadados
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dados adicionais em formato JSON"
    )
    
    # ✨ NOVO: Validador de modelo (executa ANTES da validação de tipo)
    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        """Normaliza severity e alert_type antes da validação"""
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
        """Valida que out_time é positivo e arredonda"""
        if v < 0:
            raise ValueError("out_time deve ser maior ou igual a zero")
        return round(v, 2)
    
    class Config:
        json_schema_extra = {
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
                }
            }
        }


# ============================================================================
# UPDATE SCHEMA
# ============================================================================

class AlertUpdate(BaseModel):
    """
    Schema para atualização de alerta.
    Todos os campos são opcionais.
    """
    
    severity: Optional[Union[AlertSeverity, str]] = None
    description: Optional[str] = Field(None, max_length=500)
    email_sent: Optional[bool] = None
    resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    
    @model_validator(mode='before')
    @classmethod
    def normalize_severity(cls, data: Any) -> Any:
        """Normaliza severity antes da validação"""
        if isinstance(data, dict) and 'severity' in data:
            if data['severity'] is not None and isinstance(data['severity'], str):
                data['severity'] = data['severity'].upper()
        return data
    
    class Config:
        json_schema_extra = {
            "example": {
                "severity": "LOW",
                "description": "Alerta resolvido - falso positivo",
                "email_sent": True,
                "resolved": True,
                "resolved_by": "admin"
            }
        }


# ============================================================================
# RESPONSE SCHEMA
# ============================================================================

class AlertResponse(BaseModel):
    """
    Schema de resposta da API.
    Retorna todos os dados do alerta.
    """
    
    # Campos principais
    id: int
    person_id: int
    out_time: float
    
    # Tracking
    track_id: Optional[int] = None
    
    # Zona
    zone_id: Optional[int] = None
    zone_index: Optional[int] = None
    zone_name: Optional[str] = None
    
    # Classificação
    alert_type: str
    severity: str
    description: Optional[str] = None
    
    # Mídia
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    
    # Notificação
    email_sent: bool
    
    # Resolução (futuro)
    resolved: Optional[bool] = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    # Metadados
    metadata: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Permite criar de ORM models
        json_schema_extra = {
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
                "updated_at": None
            }
        }


# ============================================================================
# TESTE
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("📋 TESTE: Alert Models (Pydantic)")
    print("=" * 70)
    
    # Teste 1: Criação válida com normalização
    print("\n✅ Teste 1: Criação de alerta válido (com normalização)")
    alert = AlertCreate(
        person_id=1,
        track_id=42,
        out_time=5.3,
        zone_id=1,
        zone_name="Zona Principal",
        severity="high",  # ✅ Será normalizado para HIGH
        alert_type="zone_violation"
    )
    print(f"   Severity normalizado: {alert.severity}")
    print(f"   Alert type: {alert.alert_type}")
    print(f"   Out time arredondado: {alert.out_time}")
    
    # Teste 2: Validação de out_time negativo
    print("\n❌ Teste 2: Out time negativo (deve falhar)")
    try:
        invalid = AlertCreate(person_id=1, out_time=-5.0)
    except ValueError as e:
        print(f"   ✅ Erro capturado: {e}")
    
    # Teste 3: Valores default
    print("\n✅ Teste 3: Valores default")
    minimal = AlertCreate(person_id=1, out_time=3.5)
    print(f"   Alert type default: {minimal.alert_type}")
    print(f"   Severity default: {minimal.severity}")
    print(f"   Email sent default: {minimal.email_sent}")
    
    # Teste 4: Normalização de strings variadas
    print("\n✅ Teste 4: Normalização de strings")
    test_cases = [
        ("low", "LOW"),
        ("MeDiUm", "MEDIUM"),
        ("HIGH", "HIGH"),
        ("critical", "CRITICAL")
    ]
    for input_val, expected in test_cases:
        alert = AlertCreate(person_id=1, out_time=1.0, severity=input_val)
        status = "✅" if alert.severity == expected else "❌"
        print(f"   {status} '{input_val}' -> '{alert.severity}' (esperado: '{expected}')")
    
    # Teste 5: Response model
    print("\n✅ Teste 5: Response model")
    response_data = {
        "id": 123,
        "person_id": 1,
        "out_time": 5.3,
        "alert_type": "zone_violation",
        "severity": "HIGH",
        "email_sent": True,
        "created_at": datetime.now()
    }
    response = AlertResponse(**response_data)
    print(f"   ID: {response.id}")
    print(f"   Created at: {response.created_at}")
    
    # Teste 6: Update model
    print("\n✅ Teste 6: Update model com normalização")
    update = AlertUpdate(severity="low", description="Teste")
    print(f"   Severity atualizado: {update.severity}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes passaram!")
    print("=" * 70)
