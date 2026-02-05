"""
Counting Mode Handler
Contagem de entradas/saídas com confirmação temporal e auto-reset.
"""

import logging
from datetime import datetime
from typing import Dict, Set

from application.zone.modes.base import BaseModeHandler
from application.zone.modes.common.state import ZoneState
from application.zone.modes.common.timers import should_send_alert, should_auto_reset

logger = logging.getLogger(__name__)


class CountingModeHandler(BaseModeHandler):
    """
    Counting mode: Contagem de entradas/saídas com tempo de confirmação.
    
    Lógica:
    - confirmation_time: Tempo mínimo dentro da zona antes de contar entrada
    - count_direction: 'in', 'out', ou 'both'
    - reset_interval: 'none', 'hourly', 'daily', 'weekly', 'monthly'
    - alert_threshold: Contador >= X dispara alerta
    
    Estados:
    - COUNTING: Objetos presentes na zona
    - IDLE: Zona vazia
    """
    
    def process(
        self,
        zone: Dict,
        state: ZoneState,
        track_state: Dict,
        current_time: float
    ) -> Dict:
        """
        Processa zona em modo counting.
        
        Args:
            zone: Configuração da zona
            state: Estado runtime
            track_state: Estado de tracking
            current_time: Timestamp atual (Unix)
        
        Returns:
            Dict com métricas + metadata atualizado
        """
        metadata = zone.get("metadata", {}) or {}
        
        count_direction = metadata.get("count_direction", "both")
        reset_interval = metadata.get("reset_interval", "daily")
        alert_enabled = metadata.get("alert_enabled", False)
        alert_threshold = metadata.get("alert_threshold", 100)
        email_cooldown = zone.get("email_cooldown", 600.0)
        confirmation_time = float(metadata.get("confirmation_time", 0))
        
        count_in = int(metadata.get("count_in", 0))
        count_out = int(metadata.get("count_out", 0))
        last_reset_str = metadata.get("last_reset")
        
        now = datetime.fromtimestamp(current_time)
      
        # 1. AUTO-RESET
        if should_auto_reset(reset_interval, last_reset_str, now):
            logger.info(
                f"Zone '{zone['name']}': reset automático ({reset_interval}) "
                f"(antes in={count_in}, out={count_out})"
            )
            count_in = 0
            count_out = 0
            metadata["count_in"] = 0
            metadata["count_out"] = 0
            metadata["last_reset"] = now.isoformat()
        elif reset_interval != "none" and not last_reset_str:
            metadata["last_reset"] = now.isoformat()
        
        # 2. OBJETOS ATUAIS
        current_objects: Set[int] = set(state.objects_inside)
        
        # 3. RASTREAMENTO DE TEMPO DE PERMANÊNCIA
        if not state.entry_times:
            state.entry_times = {}
        if not state.counted_entries:
            state.counted_entries = set()
        
        # Limpar objetos que saíram
        for obj_id in list(state.entry_times.keys()):
            if obj_id not in current_objects:
                del state.entry_times[obj_id]
                state.counted_entries.discard(obj_id)
        
        # Registrar entrada de novos objetos
        for obj_id in current_objects:
            if obj_id not in state.entry_times:
                state.entry_times[obj_id] = now
        
        # 4. DETECTAR ENTRADAS/SAÍDAS
        if not state.object_positions:
            state.object_positions = {}
        
        previous_objects = set(state.object_positions.keys())
        raw_leaving = previous_objects - current_objects
        
        # Entradas confirmadas (após confirmation_time)
        entering: Set[int] = set()
        for obj_id in current_objects:
            first_seen = state.entry_times.get(obj_id)
            if not first_seen:
                continue
            
            elapsed = (now - first_seen).total_seconds()
            
            if elapsed >= confirmation_time and obj_id not in state.counted_entries:
                entering.add(obj_id)
                state.counted_entries.add(obj_id)
        
        leaving = raw_leaving
        
        # 5. ATUALIZAR CONTADORES
        new_entries = 0
        new_exits = 0
        
        if count_direction in ["in", "both"]:
            new_entries = len(entering)
            if new_entries > 0:
                count_in += new_entries
                metadata["count_in"] = count_in
        
        if count_direction in ["out", "both"]:
            new_exits = len(leaving)
            if new_exits > 0:
                count_out += new_exits
                metadata["count_out"] = count_out
        
        # Atualizar posições
        state.object_positions = {obj_id: True for obj_id in current_objects}
        
        # 6. STATUS
        current_occupancy = len(current_objects)
        new_status = "COUNTING" if current_occupancy > 0 else "IDLE"
        
        # 7. ALERTAS
        alert = False
        alert_message = None
        
        if alert_enabled:
            if count_direction == "in":
                check_count = count_in
            elif count_direction == "out":
                check_count = count_out
            else:
                check_count = max(count_in, count_out)
            
            if check_count >= alert_threshold:
                alert = True
                alert_message = (
                    f"Limite atingido: {check_count} eventos (limite: {alert_threshold})"
                )
        
        can_notify = should_send_alert(alert, state.last_alert_time, email_cooldown, now)
        
        if alert and can_notify:
            state.last_alert_time = now
            logger.warning(f"Zone '{zone['name']}': {alert_message}")
        
        # Log mudanças de status
        if new_status != state.status:
            logger.info(
                f"Zone '{zone['name']}': {state.status} → {new_status} "
                f"(IN: {count_in}, OUT: {count_out}, ocupação: {current_occupancy})"
            )
        
        state.status = new_status
        
        return {
            "zone_id": state.zone_id,
            "zone_name": zone["name"],
            "mode": "counting",
            "count": current_occupancy,
            "count_in": count_in,
            "count_out": count_out,
            "count_direction": count_direction,
            "reset_interval": reset_interval,
            "last_reset": metadata.get("last_reset"),
            "status": new_status,
            "alert": alert,
            "alert_message": alert_message,
            "metadata_updated": metadata,
        }
