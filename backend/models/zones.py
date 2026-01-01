"""
backend/models/zones.py
Pydantic Models para Smart Zones (Zonas Inteligentes)
✨ v2.1: Adicionado empty_threshold e enabled
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


# ============================================
# ZONE MODELS
# ============================================

class ZoneBase(BaseModel):
    """Base model para zona"""
    name: str = Field(..., min_length=1, max_length=255, description="Nome da zona")
    mode: str = Field(default="GENERIC", description="Modo da zona: GENERIC, EMPTY, FULL")
    points: List[List[float]] = Field(..., min_length=3, description="Pontos do polígono (mínimo 3)")
    
    # Configs opcionais (None = usa valores globais de settings)
    max_out_time: Optional[float] = Field(None, ge=0, description="Tempo máximo fora da zona (segundos)")
    email_cooldown: Optional[float] = Field(None, ge=0, description="Cooldown entre emails (segundos)")
    empty_timeout: Optional[float] = Field(default=5.0, ge=0, description="Timeout para zona vazia (segundos)")
    full_timeout: Optional[float] = Field(default=10.0, ge=0, description="Timeout para zona cheia (segundos)")
    
    # ✨ NOVOS CAMPOS v2.1
    empty_threshold: Optional[int] = Field(default=0, ge=0, description="Threshold de pessoas para zona vazia")
    full_threshold: Optional[int] = Field(default=3, ge=1, description="Threshold de pessoas para zona cheia")
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Valida se o modo é válido"""
        allowed = ['GENERIC', 'EMPTY', 'FULL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Mode deve ser um de: {', '.join(allowed)}")
        return v_upper
    
    @field_validator('points')
    @classmethod
    def validate_points(cls, v: List[List[float]]) -> List[List[float]]:
        """
        Valida se os pontos formam um polígono válido.
        Aceita tanto coordenadas normalizadas (0-1) quanto pixels absolutos (>1).
        """
        if len(v) < 3:
            raise ValueError("Polígono deve ter no mínimo 3 pontos")
        
        for i, point in enumerate(v):
            if len(point) != 2:
                raise ValueError(f"Ponto {i} deve ter exatamente 2 coordenadas [x, y]")
            
            x, y = point
            
            # ✅ Aceita valores negativos também (pode ser útil)
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError(f"Coordenadas do ponto {i} devem ser números")
        
        return v


class ZoneCreate(ZoneBase):
    """Model para criação de zona"""
    enabled: bool = Field(default=True, description="Se a zona está habilitada")
    active: bool = Field(default=True, description="Se a zona está ativa (deprecated, use enabled)")
    
    # ✨ SCHEMA EXAMPLE PARA SWAGGER
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Zona Principal",
                "mode": "GENERIC",
                "points": [
                    [100.0, 100.0],
                    [500.0, 100.0],
                    [500.0, 400.0],
                    [100.0, 400.0]
                ],
                "max_out_time": 30.0,
                "email_cooldown": 60.0,
                "empty_timeout": 5.0,
                "full_timeout": 10.0,
                "empty_threshold": 0,
                "full_threshold": 3,
                "enabled": True,
                "active": True
            }
        }
    )


class ZoneUpdate(BaseModel):
    """Model para atualização de zona (todos campos opcionais)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    mode: Optional[str] = None
    points: Optional[List[List[float]]] = Field(None, min_length=3)
    max_out_time: Optional[float] = Field(None, ge=0)
    email_cooldown: Optional[float] = Field(None, ge=0)
    empty_timeout: Optional[float] = Field(None, ge=0)
    full_timeout: Optional[float] = Field(None, ge=0)
    
    # ✨ NOVOS CAMPOS v2.1
    empty_threshold: Optional[int] = Field(None, ge=0)
    full_threshold: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    active: Optional[bool] = None
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        """Valida modo se fornecido"""
        if v is None:
            return v
        allowed = ['GENERIC', 'EMPTY', 'FULL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Mode deve ser um de: {', '.join(allowed)}")
        return v_upper
    
    @field_validator('points')
    @classmethod
    def validate_points(cls, v: Optional[List[List[float]]]) -> Optional[List[List[float]]]:
        """Valida pontos se fornecidos"""
        if v is None:
            return v
        
        if len(v) < 3:
            raise ValueError("Polígono deve ter no mínimo 3 pontos")
        
        for i, point in enumerate(v):
            if len(point) != 2:
                raise ValueError(f"Ponto {i} deve ter exatamente 2 coordenadas [x, y]")
            
            x, y = point
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError(f"Coordenadas do ponto {i} devem ser números")
        
        return v


class ZoneResponse(ZoneBase):
    """Model para resposta de zona"""
    id: int
    enabled: bool
    active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ZoneListResponse(BaseModel):
    """Model para lista de zonas"""
    zones: List[ZoneResponse]
    total: int


# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("📋 TESTE: Zone Models v2.1")
    print("=" * 70)
    
    # 1. Test ZoneCreate - Coordenadas normalizadas (0-1)
    print("\n1️⃣ Testando ZoneCreate (coordenadas normalizadas)...")
    zone1 = ZoneCreate(
        name="Zona Normalizada",
        mode="GENERIC",
        points=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
        max_out_time=30.0,
        email_cooldown=600.0,
        empty_threshold=0,
        full_threshold=5,
        enabled=True
    )
    print(f"   ✅ Zona com coordenadas 0-1: {zone1.name}")
    
    # 2. Test ZoneCreate - Coordenadas absolutas (pixels)
    print("\n2️⃣ Testando ZoneCreate (coordenadas absolutas)...")
    zone2 = ZoneCreate(
        name="Zona Absoluta",
        mode="EMPTY",
        points=[[100, 100], [500, 100], [500, 400], [100, 400]],
        empty_timeout=5.0,
        full_timeout=10.0,
        empty_threshold=0,
        full_threshold=3
    )
    print(f"   ✅ Zona com pixels absolutos: {zone2.name}")
    print(f"   ✅ Pontos: {zone2.points}")
    
    # 3. Test JSON dump do example
    print("\n3️⃣ Testando JSON example do Swagger...")
    import json
    example = ZoneCreate.model_config.get('json_schema_extra', {}).get('example', {})
    print(f"   ✅ Example points: {example.get('points')}")
    
    # 4. Test validation - modo inválido
    print("\n4️⃣ Testando validação de modo...")
    try:
        invalid = ZoneCreate(
            name="Zona Inválida",
            mode="INVALID_MODE",
            points=[[0.1, 0.1], [0.5, 0.1], [0.3, 0.5]]
        )
    except ValueError as e:
        print(f"   ✅ Validação funcionando: {e}")
    
    # 5. Test validation - menos de 3 pontos
    print("\n5️⃣ Testando validação de pontos...")
    try:
        invalid2 = ZoneCreate(
            name="Zona Inválida 2",
            mode="GENERIC",
            points=[[0.1, 0.1], [0.9, 0.1]]  # Apenas 2 pontos
        )
    except ValueError as e:
        print(f"   ✅ Validação funcionando: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes passaram!")
    print("=" * 70)
