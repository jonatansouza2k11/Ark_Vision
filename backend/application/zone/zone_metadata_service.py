"""
zone_metadata_service.py - v1.0

Serviço de normalização de metadata por modo de zona.

Responsabilidade:
- Definir defaults de metadata por modo (counting, capacity, queue, etc.).
- Normalizar metadata preservando valores existentes e aplicando apenas defaults para campos ausentes/None.
- Ser reutilizado por API (create/update de zonas) e por ZoneProcessorV3 (runtime).

Camada: application / domain service (sem FastAPI, sem DB).
"""

from typing import Dict, Any, Optional, Union

from backend.core.domain.entities.zones import ZoneMode

# ============================================================================
# DEFAULTS DE METADATA POR MODO (migrado de backend/api/zones.py)
# ============================================================================

MODE_METADATA_DEFAULTS: Dict[str, Dict[str, Any]] = {
    # v3.0 modes - sem metadata específico
    "occupancy": {},
    "alert": {},
    "tracking": {},

    # Counting - direção, reset e alertas
    "counting": {
        "count_in": 0,
        "count_out": 0,
        # Campos de configuração adicionais NÃO são obrigatórios aqui;
        # são aplicados apenas se não existirem no metadata.
        # Ex.: "count_direction", "reset_interval", "alert_enabled", etc.
    },

    # Capacity: lotação máxima
    "capacity": {
        "max_capacity": 50,
        "alert_percentage": 90,
    },

    # Queue: inicialmente sem campos obrigatórios
    "queue": {
        # Quando a lógica de fila estiver estável, podemos adicionar:
        # "max_wait_seconds": 300,
        # "min_people": 1,
    },

    # v2.0 legacy - sem metadata específico
    "GENERIC": {},
    "EMPTY": {},
    "FULL": {},
}


def normalize_metadata_for_mode(mode: str, metadata: dict | None) -> dict:
    """
    ✅ v3.9: Normaliza metadata baseado no modo da zona
    
    PRESERVA valores existentes - só aplica defaults para campos None/ausentes.
    
    Comportamento:
    - COUNTING: Preserva TODOS os campos (ex: detection_classes) + adiciona defaults
    - CAPACITY: Preserva TODOS os campos + garante max_capacity e alert_percentage
    - OUTROS: Preserva TODOS os campos + adiciona defaults do MODE_METADATA_DEFAULTS
    
    Args:
        mode: Modo da zona (ex: 'capacity', 'tracking', 'counting')
        metadata: Metadata atual ou None
    
    Returns:
        Dict normalizado preservando campos existentes
    """
    # Começa com metadata existente ou vazio
    base = dict(metadata or {})
    
    # Pega defaults do modo (ou {} se modo não tem metadata)
    defaults = MODE_METADATA_DEFAULTS.get(mode, {})
    

    # ========================================================================
    # ✅ MODO COUNTING: Preserva TUDO que veio + adiciona defaults
    # ========================================================================
    if mode == ZoneMode.COUNTING:
        # Inicia com todos os campos que vieram do frontend/banco
        cleaned = dict(base)
        
        # Garante campos obrigatórios com defaults se não existirem
        if "count_in" not in cleaned:
            cleaned["count_in"] = 0
        if "count_out" not in cleaned:
            cleaned["count_out"] = 0
        if "count_direction" not in cleaned:
            cleaned["count_direction"] = "both"
        if "reset_interval" not in cleaned:
            cleaned["reset_interval"] = "never"
        if "alert_enabled" not in cleaned:
            cleaned["alert_enabled"] = False
         # Interseção para zonas de contagem
        if ("intersection_threshold" not in cleaned or cleaned["intersection_threshold"] is None):
            cleaned["intersection_threshold"] = 0.7

        return cleaned
    

    # ========================================================================
    # ✅ MODO CAPACITY: Garante estrutura + preserva outros campos
    # ========================================================================
    if mode == ZoneMode.CAPACITY:
        cleaned = dict(base)  # Preserva tudo que veio
        
        # Garante campos obrigatórios
        if "max_capacity" not in cleaned or cleaned["max_capacity"] is None:
            cleaned["max_capacity"] = 50
        if "alert_percentage" not in cleaned or cleaned["alert_percentage"] is None:
            cleaned["alert_percentage"] = 90
        
        return cleaned
    

    # ========================================================================
    # ✅ OUTROS MODOS: Comportamento padrão (preserva + adiciona defaults)
    # ========================================================================
    cleaned = dict(base)  # Preserva tudo
    
    # Adiciona defaults apenas para campos faltantes
    for key, default_value in defaults.items():
        if key not in cleaned or cleaned[key] is None:
            cleaned[key] = default_value

    return cleaned
