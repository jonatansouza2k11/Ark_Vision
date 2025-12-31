"""
video_processor.py

Wrapper assíncrono para YOLOVisionSystem compatível com FastAPI.
Gerencia lifecycle, estado e comunicação thread-safe com o YOLO.
"""

import asyncio
import threading
import time
from typing import Optional, Dict, Any, List
from collections import defaultdict

# Import do seu yolo.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from yolo import YOLOVisionSystem, get_memory_usage_mb, _load_zones_rich_from_db
import config as app_config


class VideoProcessor:
    """
    Wrapper assíncrono thread-safe para YOLOVisionSystem.
    
    Features:
    - Thread-safe state management
    - Async status queries
    - Non-blocking control operations
    - Memory monitoring
    """
    
    def __init__(self):
        """Inicializa o processador de vídeo."""
        self.yolo: Optional[YOLOVisionSystem] = None
        self.lock = threading.Lock()
        self._initialized = False
        
        # Estado cache (atualizado periodicamente)
        self._status_cache: Dict[str, Any] = {}
        self._cache_timestamp = 0.0
        self._cache_ttl = 0.1  # 100ms cache
        
    async def initialize(self) -> bool:
        """
        Inicializa o sistema YOLO de forma assíncrona.
        
        Returns:
            bool: True se sucesso, False se erro
        """
        if self._initialized:
            return True
            
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._initialize_sync)
            self._initialized = True
            return True
        except Exception as e:
            print(f"❌ [VIDEO] Erro ao inicializar: {e}")
            return False
    
    def _initialize_sync(self):
        """Inicialização síncrona do YOLO (roda em thread pool)."""
        with self.lock:
            if self.yolo is None:
                source = app_config.VIDEO_SOURCE
                model_path = app_config.YOLO_MODEL_PATH
                self.yolo = YOLOVisionSystem(source=source, model_path=model_path)
                print(f"[VIDEO] ✅ YOLOVisionSystem inicializado")
    
    async def start_stream(self) -> Dict[str, Any]:
        """
        Inicia o stream de vídeo.
        
        Returns:
            dict: {"success": bool, "message": str, "system_status": str}
        """
        if not self._initialized:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._start_stream_sync)
        return result
    
    def _start_stream_sync(self) -> Dict[str, Any]:
        """Inicia stream (sync)."""
        with self.lock:
            if self.yolo is None:
                return {
                    "success": False,
                    "message": "Sistema não inicializado",
                    "system_status": "stopped"
                }
            
            success = self.yolo.start_live()
            
            if success:
                return {
                    "success": True,
                    "message": "Stream iniciado com sucesso",
                    "system_status": "running"
                }
            else:
                return {
                    "success": False,
                    "message": "Stream já estava rodando",
                    "system_status": "running"
                }
    
    async def stop_stream(self) -> Dict[str, Any]:
        """
        Para o stream de vídeo.
        
        Returns:
            dict: {"success": bool, "message": str, "system_status": str}
        """
        if not self._initialized:
            return {
                "success": False,
                "message": "Sistema não inicializado",
                "system_status": "stopped"
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._stop_stream_sync)
        return result
    
    def _stop_stream_sync(self) -> Dict[str, Any]:
        """Para stream (sync)."""
        with self.lock:
            if self.yolo is None:
                return {
                    "success": False,
                    "message": "Sistema não inicializado",
                    "system_status": "stopped"
                }
            
            success = self.yolo.stop_live()
            
            if success:
                return {
                    "success": True,
                    "message": "Stream parado com sucesso",
                    "system_status": "stopped"
                }
            else:
                return {
                    "success": False,
                    "message": "Stream já estava parado",
                    "system_status": "stopped"
                }
    
    async def toggle_pause(self) -> Dict[str, Any]:
        """
        Alterna pausa do stream.
        
        Returns:
            dict: {"success": bool, "message": str, "system_status": str}
        """
        if not self._initialized:
            return {
                "success": False,
                "message": "Sistema não inicializado",
                "system_status": "stopped"
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._toggle_pause_sync)
        return result
    
    def _toggle_pause_sync(self) -> Dict[str, Any]:
        """Toggle pause (sync)."""
        with self.lock:
            if self.yolo is None:
                return {
                    "success": False,
                    "message": "Sistema não inicializado",
                    "system_status": "stopped"
                }
            
            paused = self.yolo.toggle_pause()
            status = "paused" if paused else "running"
            message = "Stream pausado" if paused else "Stream retomado"
            
            return {
                "success": True,
                "message": message,
                "system_status": status
            }
    
    async def get_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Obtém status completo do sistema.
        
        Args:
            force_refresh: Força atualização do cache
            
        Returns:
            dict: Status completo (VideoStatusSchema compatible)
        """
        if not self._initialized:
            return self._get_stopped_status()
        
        # Cache check
        now = time.time()
        if not force_refresh and (now - self._cache_timestamp) < self._cache_ttl:
            return self._status_cache
        
        # Atualiza cache
        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, self._get_status_sync)
        
        self._status_cache = status
        self._cache_timestamp = now
        
        return status
    
    def _get_status_sync(self) -> Dict[str, Any]:
        """Obtém status (sync)."""
        with self.lock:
            if self.yolo is None:
                return self._get_stopped_status()
            
            # System status
            if not self.yolo.is_live():
                system_status = "stopped"
            elif self.yolo.is_paused():
                system_status = "paused"
            else:
                system_status = "running"
            
            # Count detections
            in_zone = 0
            out_zone = 0
            for tid, state in self.yolo.track_state.items():
                if state["status"] == "IN":
                    in_zone += 1
                else:
                    out_zone += 1
            
            detected_count = in_zone + out_zone
            
            # Zone stats
            zones_list = []
            for zone_idx, zs in self.yolo.zone_stats.items():
                now = time.time()
                
                empty_for = None
                full_for = None
                
                if zs.get("empty_since"):
                    empty_for = now - zs["empty_since"]
                
                if zs.get("full_since"):
                    full_for = now - zs["full_since"]
                
                zones_list.append({
                    "index": zone_idx,
                    "name": zs.get("name", f"Zona {zone_idx + 1}"),
                    "mode": zs.get("mode", "GENERIC"),
                    "count": zs.get("count", 0),
                    "empty_for": empty_for,
                    "full_for": full_for,
                    "state": zs.get("state", "OK")
                })
            
            # Memory
            memory_mb = get_memory_usage_mb()
            peak_memory_mb = self.yolo.peak_memory_mb if hasattr(self.yolo, 'peak_memory_mb') else 0.0
            
            return {
                "system_status": system_status,
                "stream_active": self.yolo.is_live(),
                "paused": self.yolo.is_paused(),
                "fps": round(self.yolo.current_fps, 2),
                "fps_inst": round(self.yolo.current_fps, 2),
                "fps_avg": round(self.yolo.avg_fps, 2),
                "in_zone": in_zone,
                "out_zone": out_zone,
                "detected_count": detected_count,
                "zones": zones_list,
                "memory_mb": round(memory_mb, 1) if memory_mb > 0 else None,
                "peak_memory_mb": round(peak_memory_mb, 1) if peak_memory_mb > 0 else None,
                "frame_count": self.yolo.frame_count if hasattr(self.yolo, 'frame_count') else 0,
                "preset": app_config.ACTIVE_PRESET
            }
    
    def _get_stopped_status(self) -> Dict[str, Any]:
        """Status quando sistema está parado."""
        return {
            "system_status": "stopped",
            "stream_active": False,
            "paused": False,
            "fps": 0.0,
            "fps_inst": 0.0,
            "fps_avg": 0.0,
            "in_zone": 0,
            "out_zone": 0,
            "detected_count": 0,
            "zones": [],
            "memory_mb": None,
            "peak_memory_mb": None,
            "frame_count": 0,
            "preset": app_config.ACTIVE_PRESET
        }
    
    async def get_detections(self) -> Dict[str, Any]:
        """
        Obtém lista de detecções ativas.
        
        Returns:
            dict: {"total": int, "detections": List[dict], "timestamp": str}
        """
        if not self._initialized:
            return {
                "total": 0,
                "detections": [],
                "timestamp": time.time()
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._get_detections_sync)
        return result
    
    def _get_detections_sync(self) -> Dict[str, Any]:
        """Obtém detecções (sync)."""
        with self.lock:
            if self.yolo is None:
                return {
                    "total": 0,
                    "detections": [],
                    "timestamp": time.time()
                }
            
            detections = []
            
            for tid, state in self.yolo.track_state.items():
                # Não temos bbox no track_state, apenas status
                # Vamos retornar apenas info de tracking
                detections.append({
                    "id": tid,
                    "bbox": [0, 0, 0, 0],  # Não disponível no track_state
                    "confidence": 0.0,  # Não disponível no track_state
                    "status": state["status"],
                    "out_time": round(state["out_time"], 2),
                    "zone_idx": state.get("zone_idx", -1),
                    "recording": state.get("recording", False),
                    "last_seen": state["last_seen"]
                })
            
            return {
                "total": len(detections),
                "detections": detections,
                "timestamp": time.time()
            }
    
    def get_frame_generator(self):
        """
        Retorna o generator de frames do YOLO.
        
        Returns:
            generator: Frame generator (MJPEG)
        """
        if not self._initialized or self.yolo is None:
            raise RuntimeError("Sistema não inicializado")
        
        return self.yolo.generate_frames()
    
    async def cleanup(self):
        """Limpa recursos do sistema."""
        if self._initialized and self.yolo:
            await self.stop_stream()
            
        self._initialized = False
        self.yolo = None
        print("[VIDEO] 🧹 Recursos limpos")


# =========================
# SINGLETON INSTANCE
# =========================
video_processor = VideoProcessor()
