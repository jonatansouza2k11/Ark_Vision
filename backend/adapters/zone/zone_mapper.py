"""
Mapper: Dict ↔ ZoneConfig

Responsabilidade: Conversão bidirecional entre DB/API e Domain
"""

from typing import Dict, List
import logging

from backend.core.domain.entities import Zone, ZoneConfig, ZoneMode

logger = logging.getLogger(__name__)


class ZoneMapper:
    """
    Adapter para conversão entre dicts (DB/API) e entities (Domain).
    Responsabilidade: Governança de schema, versionamento.
    """

    @staticmethod
    def _normalize_mode(data: Dict) -> Dict:
        """
        Normaliza campo 'mode' para um valor aceito por ZoneMode.

        - Aceita minúsculo ('queue', 'occupancy', etc.).
        - Tenta converter maiúsculo/legado ('QUEUE', 'GENERIC', etc.).
        - Em caso de valor totalmente inválido, faz fallback para 'occupancy'.
        """
        raw_mode = data.get("mode")
        if raw_mode is None:
            data["mode"] = "occupancy"
            return data

        # Se já é um valor válido em ZoneMode, mantém
        try:
            ZoneMode(raw_mode)
            return data
        except ValueError:
            pass

        # Tenta normalizar lower-case (ex: "QUEUE" -> "queue")
        lower = str(raw_mode).lower()
        for m in ZoneMode:
            if m.value == lower:
                data["mode"] = m.value
                return data

        # Fallback seguro
        logger.warning(
            f"⚠️ Modo de zona desconhecido '{raw_mode}', usando 'occupancy' como fallback"
        )
        data["mode"] = "occupancy"
        return data

    @staticmethod
    def dict_to_config(data: Dict) -> ZoneConfig:
        """
        Converte dict (DB/API) → ZoneConfig (Domain).

        Args:
            data: Dict do banco ou API

        Returns:
            ZoneConfig validado

        Raises:
            ValueError: Se campos obrigatórios faltarem ou forem inválidos
        """
        try:
            # Garante que 'mode' sempre seja algo aceitável por ZoneMode,
            # incluindo o novo modo 'queue'.
            normalized = ZoneMapper._normalize_mode(dict(data))
            return ZoneConfig.from_dict(normalized)
        except Exception as e:
            logger.error(f"❌ Erro ao converter dict → ZoneConfig: {e}")
            raise ValueError(f"Invalid zone data: {e}")

    @staticmethod
    def config_to_dict(config: ZoneConfig) -> Dict:
        """
        Converte ZoneConfig (Domain) → dict (DB/API).

        Args:
            config: ZoneConfig entity

        Returns:
            Dict para serialização
        """
        return {
            "id": config.zone_id,
            "name": config.name,
            "points": config.polygon,
            "mode": config.mode.value,
            "camera_id": config.camera_id,
            "empty_threshold": config.empty_threshold,
            "full_threshold": config.full_threshold,
            "empty_timeout": config.empty_timeout,
            "full_timeout": config.full_timeout,
            "email_cooldown": config.email_cooldown,
            "metadata": config.metadata,
            "color": config.color,
            "enabled": config.enabled,
        }

    @staticmethod
    def dicts_to_zones(data_list: List[Dict]) -> List[Zone]:
        """
        Converte lista de dicts → lista de Zone entities.

        Args:
            data_list: Lista de dicts do DB

        Returns:
            Lista de Zone (config + state runtime)
        """
        zones: List[Zone] = []

        for data in data_list:
            try:
                config = ZoneMapper.dict_to_config(data)
                zone = Zone.from_config(config)
                zones.append(zone)
            except Exception as e:
                zone_id = data.get("id", "unknown")
                logger.error(f"❌ Skipping invalid zone {zone_id}: {e}")
                # Continua sem quebrar (graceful degradation)

        return zones

    @staticmethod
    def zones_to_dicts(zones: List[Zone]) -> List[Dict]:
        """
        Converte lista de Zone entities → lista de dicts.

        Args:
            zones: Lista de Zone entities

        Returns:
            Lista de dicts para API/DB
        """
        return [ZoneMapper.config_to_dict(zone.config) for zone in zones]
