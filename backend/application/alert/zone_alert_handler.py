"""
Zone Alert Handler v1.0

Responsabilidade:
- Receber eventos de zona (ZoneMetrics em forma de dict) vindo do ZoneProcessorV3.
- Decidir se é um "novo alerta" (mudança de status + flag alert=True).
- Opcionalmente acionar gravação de clipe de vídeo e anexar o videopath.
- Opcionalmente despachar o evento para algum sink (fila, serviço de Alert, etc).

Camada: application (sem FastAPI, sem DB direto).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Assinaturas de callbacks de infra que serão injetados
ZoneClipRecorder = Callable[[int, int, Dict[str, Any], float], Optional[str]]
ZoneAlertSink = Callable[[Dict[str, Any]], None]


@dataclass
class ZoneAlertHandler:
    """
    Orquestra criação de eventos de alerta de zona.

    - NÃO sabe sobre FastAPI, DB ou models Pydantic.
    - Trabalha apenas com dicts compatíveis com ZoneMetrics.to_dict().
    - Usa callbacks injetados para gravar clipes e persistir/encaminhar alertas.
    """

    clip_recorder: Optional[ZoneClipRecorder] = None
    alert_sink: Optional[ZoneAlertSink] = None

    def handle_zone_metrics(
        self,
        camera_id: int,
        zone_id: int,
        metrics: Dict[str, Any],
        previous_status: Optional[str],
        event_time: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Processa métricas de uma zona e, se for um NOVO alerta, emite um evento.

        Args:
            camera_id: ID da câmera que gerou o frame.
            zone_id: ID da zona.
            metrics: Dict retornado de ZoneMetrics.to_dict().
            previous_status: status anterior da zona (state.status antes do frame).
            event_time: timestamp epoch usado no cálculo (current_time do processor).

        Returns:
            Dict com evento de alerta enriquecido (ex.: videopath) ou None se:
            - não é alerta, ou
            - status não mudou (evita spam de frames).
        """
        is_alert = bool(metrics.get("alert", False))
        current_status = metrics.get("status")

        # Sem alerta ativo → nada a fazer
        if not is_alert:
            return None

        # Se status não mudou, não dispara de novo (governança básica de evento)
        if previous_status is not None and current_status == previous_status:
            return None

        zone_name = metrics.get("zonename") or metrics.get("zone_name")
        mode = metrics.get("mode")
        count = metrics.get("count")
        event_dt = datetime.fromtimestamp(event_time)

        alert_event: Dict[str, Any] = {
            "camera_id": camera_id,
            "zone_id": zone_id,
            "zone_name": zone_name,
            "mode": mode,
            "status": current_status,
            "previous_status": previous_status,
            "count": count,
            "alert": True,
            "alert_message": metrics.get("alert_message"),
            "event_time": event_time,
            "event_time_iso": event_dt.isoformat(),
            "metadata": metrics.get("metadata") or {},
            "activetrackids": metrics.get("activetrackids"),
            "activeglobalids": metrics.get("activeglobalids"),
        }

        # 1) Opcional: gravar clipe de vídeo e anexar videopath
        if self.clip_recorder is not None:
            try:
                videopath = self.clip_recorder(
                    camera_id=camera_id,
                    zone_id=zone_id,
                    metrics=metrics,
                    event_time=event_time,
                )
                if videopath:
                    alert_event["videopath"] = videopath
            except Exception:
                logger.exception(
                    "ZoneAlertHandler: erro ao gravar clipe de alerta "
                    "(camera_id=%s, zone_id=%s)",
                    camera_id,
                    zone_id,
                )

        # 2) Opcional: despachar evento para um sink (fila, serviço de alertas, etc.)
        if self.alert_sink is not None:
            try:
                self.alert_sink(alert_event)
            except Exception:
                logger.exception(
                    "ZoneAlertHandler: erro ao enviar evento de alerta para sink "
                    "(camera_id=%s, zone_id=%s)",
                    camera_id,
                    zone_id,
                )

        return alert_event
