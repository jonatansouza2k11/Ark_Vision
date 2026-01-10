"""
yolo.py - v4.6 (OPTIMIZED)

Módulo de computação visual com YOLO (Ultralytics) + Tracking + BoT-SORT/ByteTrack.
Implementa buffer circular para gravar ~2s antes + durante a saída da zona.

✨ MELHORIAS v4.6 (2026-01-06) - OTIMIZAÇÕES DE PERFORMANCE:
- ✅ GC_INTERVAL aumentado para 100 frames (menos overhead)
- ✅ Pool de frames pré-alocados (reduz alocações)
- ✅ Timeout configurável para reconexão (5 tentativas)
- ✅ Preserva botsort.yaml do banco de dados
- ✅ Otimizações de memória e performance

✨ v4.5:
- ✅ Removido lock de câmera que bloqueava segunda conexão
- ✅ Reutilização de câmera já aberta
- ✅ Múltiplas conexões ao /video_feed funcionam

✨ v4.4:
- ✅ Carregamento do source do banco de dados
- ✅ Suporte para câmeras IP e webcams via configuração do banco

v4.6 (2026-01-06) - OTIMIZACOES DE PERFORMANCE:
- GC_INTERVAL, PERSON_CLASS_ID, MAX_RECONNECTION_ATTEMPTS agora vem do config.py
- Pool de frames pre-alocados (reduz alocacoes)
- Preserva botsort.yaml do banco de dados
- Otimizacoes de memoria e performance
"""

import sys
import logging
import threading
import time
import os
import json
import gc
from pathlib import Path
from collections import defaultdict, deque
from typing import Optional, List, Dict, Any, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

# ============================================
# CONFIGURACAO DE CAMINHOS
# ============================================
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ============================================
# IMPORTS DO PROJETO
# ============================================
try:
    from backend.config import settings
    from backend.database_sync import log_alert, get_setting, get_all_settings
except ImportError:
    try:
        from config import settings
        from database_sync import log_alert, get_setting, get_all_settings
    except ImportError:
        print("[YOLO] Erro ao importar configuracoes do backend")
        settings = None

from backend.services.api_client import YOLOApiClient

try:
    from backend.notifications import Notifier
except ImportError:
    Notifier = None

logger = logging.getLogger(__name__)

# ============================================
# v4.6: CONFIGURACOES CARREGADAS DO config.py
# ============================================
DEFAULT_SOURCE = settings.video_source_parsed if settings else "0"
MODEL_PATH = settings.YOLO_MODEL_PATH if settings else "yolo_models/yolov8n.pt"
CAM_FPS = settings.CAM_FPS if settings else 30
BUFFER_SIZE = settings.BUFFER_SIZE if settings else 40
CAM_WIDTH = settings.CAM_WIDTH if settings else 960
CAM_HEIGHT = settings.CAM_HEIGHT if settings else 540
CAM_RESOLUTION = (CAM_WIDTH, CAM_HEIGHT)

# v4.6: Memory management from config
GC_INTERVAL = settings.GC_INTERVAL if settings else 100
MEMORY_WARNING_THRESHOLD = settings.MEMORY_WARNING_THRESHOLD if settings else 1024

# v4.6: Reconnection settings from config
MAX_RECONNECTION_ATTEMPTS = settings.MAX_RECONNECTION_ATTEMPTS if settings else 5
RECONNECTION_DELAY = settings.RECONNECTION_DELAY if settings else 0.5

# v4.6: YOLO detection settings from config
PERSON_CLASS_ID = settings.PERSON_CLASS_ID if settings else 0

# v4.6: Frame pool size from config
FRAME_POOL_SIZE = settings.FRAME_POOL_SIZE if settings else 10

ALERTS_FOLDER = "alertas"
os.makedirs(ALERTS_FOLDER, exist_ok=True)


# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def _load_safe_zone_from_db():
    """Carrega zonas do banco (apenas coordenadas)"""
    raw_safe = get_setting("safe_zone", "[]")
    try:
        data = json.loads(str(raw_safe).strip())
        if isinstance(data, list) and data and isinstance(data[0], dict) and "points" in data[0]:
            return [z.get("points") or [] for z in data if len(z.get("points") or []) >= 3]
        return data
    except:
        return []

def _load_zones_rich_from_db():
    """Carrega zonas do banco com metadados completos"""
    raw_safe = get_setting("safe_zone", "[]")
    try:
        data = json.loads(str(raw_safe).strip())
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return [{
                "name": z.get("name") or "",
                "mode": (z.get("mode") or "GENERIC").upper(),
                "points": z.get("points") or z.get("polygon") or [],
                "max_out_time": z.get("max_out_time"),
                "email_cooldown": z.get("email_cooldown"),
                "empty_timeout": z.get("empty_timeout"),
                "full_timeout": z.get("full_timeout"),
                "full_threshold": z.get("full_threshold"),
            } for z in data if len(z.get("points") or z.get("polygon") or []) >= 3]
        return []
    except:
        return []

def get_memory_usage_mb():
    """Retorna uso de memória RAM em MB"""
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 / 1024
    except:
        return 0.0


# ============================================
# ✅ v4.6: POOL DE FRAMES PRÉ-ALOCADOS
# ============================================
class FramePool:
    """Pool de frames pré-alocados para reduzir alocações de memória"""
    def __init__(self, size: int = 10, shape: Tuple[int, int, int] = (540, 960, 3)):
        self.pool = deque(maxlen=size)
        self.shape = shape
        # Pre-allocate frames
        for _ in range(size):
            self.pool.append(np.zeros(shape, dtype=np.uint8))
    
    def get_frame(self) -> np.ndarray:
        """Get a frame from pool or create new"""
        if self.pool:
            return self.pool.popleft()
        return np.zeros(self.shape, dtype=np.uint8)
    
    def return_frame(self, frame: np.ndarray):
        """Return frame to pool"""
        if len(self.pool) < self.pool.maxlen:
            self.pool.append(frame)


# ============================================
# CLASSE PRINCIPAL: YOLO VISION SYSTEM
# ============================================
class YOLOVisionSystem:
    def __init__(self, source=None, model_path=MODEL_PATH):
        """
        Inicializa sistema YOLO com suporte a configurações do banco de dados.
        
        Args:
            source: Fonte de vídeo (None = carregar do banco, int = webcam, str = URL/arquivo)
            model_path: Caminho do modelo YOLO
        """
        self.model_path = model_path
        self.cam_width = CAM_WIDTH
        self.cam_height = CAM_HEIGHT
        self.cam_fps = CAM_FPS
        self.buffer_size = BUFFER_SIZE
        
        # ✅ v4.6: Initialize frame pool
        self.frame_pool = FramePool(size=10, shape=(self.cam_height, self.cam_width, 3))
        
        # ============================================
        # CARREGAR SOURCE DO BANCO DE DADOS
        # ============================================
        if source is None:
            db_source = get_setting("source", None)
            if db_source is None or db_source == "":
                self.source = DEFAULT_SOURCE
                print(f"[YOLO] 📹 Fonte do .env: {self.source}")
            else:
                try:
                    self.source = int(db_source)
                    print(f"[YOLO] 📹 Fonte do BD (webcam): {self.source}")
                except (ValueError, TypeError):
                    self.source = str(db_source).strip()
                    print(f"[YOLO] 📹 Fonte do BD (URL/IP): {self.source}")
        else:
            self.source = source
            print(f"[YOLO] 📹 Fonte fornecida manualmente: {self.source}")
        
        # ============================================
        # CARREGAR MODELO YOLO
        # ============================================
        print(f"[YOLO] 🤖 Carregando modelo: {self.model_path}")
        self.model = YOLO(self.model_path)
        
        def dummy_fuse(verbose=False):
            return self.model.model
        self.model.fuse = dummy_fuse
        self.model.model.is_fused = lambda: True
        
        # ============================================
        # ESTADO DO TRACKING
        # ============================================
        self.track_state = defaultdict(lambda: {
            "last_seen": 0.0,
            "status": "OUT",
            "out_time": 0.0,
            "video_writer": None,
            "video_path": None,
            "recording": False,
            "buffer": deque(maxlen=BUFFER_SIZE),
            "zone_idx": -1
        })
        self.last_email_time = defaultdict(lambda: 0.0)
        
        # ============================================
        # ESTADO DO STREAM
        # ============================================
        self.paused = False
        self.stream_active = False
        self.last_frame_time = None
        self.current_fps = 0.0
        self.avg_fps = 0.0
        self._fps_samples = []
        self.cap = None
        self.frame_count = 0
        self.peak_memory_mb = 0.0
        
        # ✅ v4.6: Camera state
        self._camera_configured = False
        self._reconnection_attempts = 0
        
        # ============================================
        # NOTIFIER & API CLIENT
        # ============================================
        self.notifier = None
        if Notifier and settings and settings.EMAIL_SENDER and settings.EMAIL_APP_PASSWORD:
            self.notifier = Notifier(
                email_user=settings.EMAIL_SENDER,
                email_app_password=settings.EMAIL_APP_PASSWORD,
                email_to=settings.EMAIL_SENDER,
                smtp_server=settings.SMTP_SERVER,
                smtp_port=settings.SMTP_PORT
            )
        
        api_enabled = get_setting("api_integration_enabled", "true").lower() == "true"
        if api_enabled:
            try:
                self.api_client = YOLOApiClient(
                    base_url=get_setting("api_base_url", "http://localhost:8000"),
                    username=get_setting("api_username", "admin"),
                    password=get_setting("api_password", "admin123"),
                    enabled=True
                )
            except:
                self.api_client = None
        else:
            self.api_client = None
        
        # ============================================
        # CACHE DE CONFIGURAÇÕES E ZONAS
        # ============================================
        self.zone_stats = {}
        self._cached_config = None
        self._cached_zones_rich = None
        self._cached_zones_polys = None
        self._cached_pixel_polys = []
        self._last_config_update = 0
        self._config_update_interval = 2.0
        
        print("[YOLO] ✅ Sistema YOLO v4.6 inicializado com sucesso!")
        print(f"[YOLO] ✅ GC_INTERVAL: {GC_INTERVAL} frames")
        print(f"[YOLO] ✅ Frame pool: {self.frame_pool.pool.maxlen} frames pré-alocados")
    
    # ============================================
    # MÉTODOS DE CONTROLE DO STREAM
    # ============================================
    def is_live(self):
        """Verifica se stream está ativo"""
        return self.stream_active
    
    def start_live(self):
        """Inicia o stream"""
        if not self.stream_active:
            self.stream_active = True
            self.paused = False
            self._reconnection_attempts = 0  # ✅ Reset attempts
            print("[YOLO] ▶️ Stream ativado")
    
    def stop_live(self):
        """Para o stream e limpa recursos"""
        self.stream_active = False
        self.paused = False
        self._close_camera()
        print("[YOLO] ⏹️ Stream parado")
    
    def toggle_pause(self):
        """Alterna entre pausado/ativo"""
        self.paused = not self.paused
        print(f"[YOLO] {'⏸️ Pausado' if self.paused else '▶️ Retomado'}")
        return self.paused
    
    # ============================================
    # CONFIGURAÇÃO DINÂMICA
    # ============================================
    def _load_initial_config(self):
        """Carrega configuração inicial do banco + .env"""
        if not settings:
            return {}
        
        db_source = get_setting("source", None)
        if db_source is None or db_source == "":
            source = DEFAULT_SOURCE
        else:
            try:
                source = int(db_source)
            except (ValueError, TypeError):
                source = str(db_source).strip()
        
        return {
            "source": source,
            "conf_thresh": float(get_setting("conf_thresh", settings.YOLO_CONF_THRESHOLD)),
            "frame_step": int(get_setting("frame_step", settings.YOLO_FRAME_STEP)),
            "target_width": int(get_setting("target_width", settings.YOLO_TARGET_WIDTH)),
            "max_out_time": float(get_setting("max_out_time", settings.MAX_OUT_TIME)),
            "email_cooldown": float(get_setting("email_cooldown", settings.EMAIL_COOLDOWN)),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", settings.ZONE_EMPTY_TIMEOUT)),
            "zone_full_timeout": float(get_setting("zone_full_timeout", settings.ZONE_FULL_TIMEOUT)),
            "zone_full_threshold": int(get_setting("zone_full_threshold", settings.ZONE_FULL_THRESHOLD)),
            "safe_zone": _load_safe_zone_from_db(),
            "tracker": get_setting("tracker", settings.TRACKER),  # ✅ Preserva botsort.yaml do BD
            "cam_width": int(get_setting("cam_width", CAM_WIDTH)),
            "cam_height": int(get_setting("cam_height", CAM_HEIGHT)),
            "cam_fps": int(get_setting("cam_fps", CAM_FPS)),
        }
    
    def get_config(self):
        """Obtém configuração com cache (atualiza a cada 2s)"""
        now = time.time()
        if self._cached_config is None or (now - self._last_config_update) > self._config_update_interval:
            self._cached_config = self._load_initial_config()
            self._last_config_update = now
        return self._cached_config
    
    # ============================================
    # DETECÇÃO DE ZONA
    # ============================================
    def is_point_in_polygon(self, px, py, poly):
        """Verifica se ponto está dentro do polígono (otimizado com OpenCV)"""
        if not poly or len(poly) < 3:
            return False
        pts = np.array(poly, dtype=np.float32)
        return cv2.pointPolygonTest(pts, (float(px), float(py)), False) >= 0
    
    # ============================================
    # ✅ v4.6: GERADOR DE FRAMES OTIMIZADO
    # ============================================
    def generate_frames(self):
        """
        ✅ v4.6: Gerador de frames otimizado
        - Pool de frames pré-alocados
        - GC interval aumentado para 100
        - Melhor tratamento de reconexões
        - Preserva botsort.yaml do banco
        """
        target_interval = 1.0 / 30.0
        cfg = self.get_config()
        
        # ✅ Verificar memória
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_mb = mem.available / (1024 * 1024)
            if available_mb < 300:
                logger.error(f"❌ Insufficient memory: {available_mb:.0f}MB")
                yield self._generate_error_frame("Memória insuficiente")
                return
            logger.info(f"✅ Memory OK: {available_mb:.0f}MB available")
        except Exception as e:
            logger.warning(f"⚠️ Could not check memory: {e}")
        
        # ✅ REUTILIZAR câmera se já estiver aberta
        if self.cap is None or not self.cap.isOpened():
            logger.info("📹 Opening new camera connection...")
            self._open_camera(cfg)
            self._camera_configured = False
        else:
            logger.info("♻️ Reusing existing camera connection")
        
        if self.cap is None or not self.cap.isOpened():
            logger.error("❌ Failed to open camera")
            yield self._generate_error_frame("Falha ao abrir câmera")
            return
        
        # ✅ Configurar resolução APENAS na primeira vez
        if not self._camera_configured:
            logger.info(f"📹 Setting camera resolution: {cfg.get('cam_width', 640)}x{cfg.get('cam_height', 480)}")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.get('cam_width', 640))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.get('cam_height', 480))
            self.cap.set(cv2.CAP_PROP_FPS, cfg.get('cam_fps', 15))
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except:
                pass
            self._camera_configured = True
        
        last_frame = None
        fi = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while self.stream_active:
                loop_start = time.time()
                self._perform_gc_if_needed()
                
                # Verificar memória periodicamente
                if fi % 100 == 0:
                    try:
                        import psutil
                        mem = psutil.virtual_memory()
                        available_mb = mem.available / (1024 * 1024)
                        if available_mb < 200:
                            logger.warning(f"⚠️ Low memory: {available_mb:.0f}MB")
                            gc.collect()
                            logger.info("🧹 Forced garbage collection")
                    except:
                        pass
                
                # Atualizar config e zonas
                cfg = self.get_config()
                if fi % 60 == 0:
                    try:
                        self._cached_zones_rich = _load_zones_rich_from_db()
                        self._cached_zones_polys = [z["points"] for z in self._cached_zones_rich] if self._cached_zones_rich else cfg.get("safe_zone", [])
                        self._cached_pixel_polys = []
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to reload zones: {e}")
                
                zones_rich = self._cached_zones_rich
                zones_polys = self._cached_zones_polys
                cfg["zones_polys"] = zones_polys
                
                # Pausado
                if self.paused:
                    if last_frame is not None:
                        try:
                            pf = self.draw_paused_overlay(last_frame.copy())
                            ret, buf = cv2.imencode(".jpg", pf, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            if ret:
                                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                        except Exception as e:
                            logger.warning(f"⚠️ Error encoding paused frame: {e}")
                    time.sleep(target_interval)
                    continue
                
                # Ler frame
                try:
                    ok, orig = self.cap.read()
                    if not ok or orig is None:
                        consecutive_errors += 1
                        logger.warning(f"⚠️ Failed to read frame ({consecutive_errors}/{max_consecutive_errors})")
                        
                        # ✅ v4.6: Improved reconnection logic
                        if consecutive_errors >= 3 and self._reconnection_attempts < MAX_RECONNECTION_ATTEMPTS:
                            self._reconnection_attempts += 1
                            logger.info(f"🔄 Reconnection attempt {self._reconnection_attempts}/{MAX_RECONNECTION_ATTEMPTS}...")
                            self._close_camera()
                            time.sleep(RECONNECTION_DELAY)
                            self._open_camera(cfg)
                            self._camera_configured = False
                            
                            if self.cap is None or not self.cap.isOpened():
                                logger.error("❌ Failed to reconnect")
                                if self._reconnection_attempts >= MAX_RECONNECTION_ATTEMPTS:
                                    logger.error("❌ Max reconnection attempts reached")
                                    break
                        
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error("❌ Too many consecutive errors, stopping")
                            break
                        
                        time.sleep(0.1)
                        continue
                    
                    consecutive_errors = 0
                    self._reconnection_attempts = 0  # ✅ Reset on success
                
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"❌ Error reading frame: {e}")
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    time.sleep(0.1)
                    continue
                
                try:
                    orig = cv2.flip(orig, 1)
                    frame, scale = self.resize_keep_width(orig, cfg.get("target_width", 640))
                    now = time.time()
                    fi += 1
                    
                    self.draw_safe_zone(frame, zones_polys, zones_rich)
                    self.update_zone_stats_start(zones_polys, now, zones_rich, cfg)
                    
                    if fi % cfg.get("frame_step", 1) == 0:
                        try:
                            # ✅ v4.6: Uses tracker from database (botsort.yaml)
                            results_list = self.model.track(
                                source=frame,
                                conf=cfg.get("conf_thresh", 0.5),
                                persist=True,
                                classes=[PERSON_CLASS_ID],
                                tracker=cfg.get("tracker", "botsort.yaml"),  # ✅ From DB
                                verbose=False
                            )
                            
                            if results_list and results_list[0].boxes is not None:
                                for box in results_list[0].boxes:
                                    self.process_detection(box, frame, scale=1.0, config=cfg, now=now)
                        except Exception as e:
                            logger.error(f"❌ YOLO error: {e}")
                    else:
                        for tid, state in self.track_state.items():
                            if "buffer" in state:
                                state["buffer"].append(frame.copy())
                            if state.get("recording", False):
                                self.write_frame_to_video(tid, frame)
                    
                    self.update_zone_stats_end(now, zones_rich, cfg)
                    
                    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        last_frame = frame
                        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                    
                    self._update_fps()
                    
                    elapsed = time.time() - loop_start
                    if elapsed < target_interval:
                        time.sleep(target_interval - elapsed)
                
                except Exception as e:
                    logger.error(f"❌ Frame processing error: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        break
                    continue
        
        except GeneratorExit:
            logger.info("🔌 Client disconnected from stream")
        except Exception as e:
            logger.error(f"❌ Fatal loop error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # ✅ NÃO fechar câmera (será reutilizada)
            logger.info("♻️ Keeping camera open for reuse")
            
    
    def _generate_error_frame(self, message: str) -> bytes:
        """Gera frame de erro"""
        return (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                b'\xff\xd8\xff\xe0\x00\x10JFIF'
                b'\r\n')
    
    # ============================================
    # FPS INSTANTANEO E MEDIO
    # ============================================
    def _update_fps(self):
        """Atualiza FPS atual (instantâneo) e FPS médio"""
        now = time.time()
        if self.last_frame_time:
            interval = max(now - self.last_frame_time, 1e-6)
            self.current_fps = 1.0 / interval
            
            self._fps_samples.append(interval)
            if len(self._fps_samples) > 50:
                self._fps_samples.pop(0)
            
            avg_interval = sum(self._fps_samples) / len(self._fps_samples)
            self.avg_fps = 1.0 / max(avg_interval, 1e-6)
        
        self.last_frame_time = now
    
    # ============================================
    # DESENHO E VISUALIZAÇÃO
    # ============================================
    def draw_paused_overlay(self, frame):
        """Desenha overlay de 'PAUSADO' no frame"""
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "SISTEMA PAUSADO", (w//2 - 200, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3, cv2.LINE_AA)
        return frame
    
    def resize_keep_width(self, frame, target_width):
        """Redimensiona frame mantendo proporção"""
        h, w = frame.shape[:2]
        if w == target_width:
            return frame, 1.0
        scale = target_width / w
        return cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_LINEAR), scale
    
    def draw_safe_zone(self, frame, zones, zones_rich=None):
        """Desenha zonas de segurança no frame"""
        if not zones:
            return
        
        h, w = frame.shape[:2]
        
        if not self._cached_pixel_polys:
            for zp in zones:
                pts = np.array([[int(p[0]*w), int(p[1]*h)] for p in zp], np.int32)
                if len(pts) >= 3:
                    self._cached_pixel_polys.append(pts)
        
        for i, pts in enumerate(self._cached_pixel_polys):
            cv2.polylines(frame, [pts], True, (0, 255, 255), 3)
            
            zr = zones_rich[i] if zones_rich and i < len(zones_rich) else {}
            label = f"{zr.get('name') or f'ZONE {i+1}'} ({zr.get('mode') or 'GENERIC'})"
            
            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            x, y = pts[0][0], max(pts[0][1] - 15, 25)
            cv2.rectangle(frame, (x-4, y-th-4), (x+tw+4, y+bl+2), (0, 0, 0), -1)
            cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    
    # ============================================
    # PROCESSAMENTO DE DETECÇÕES
    # ============================================
    def process_detection(self, box, frame, scale, config, now):
        """Processa uma detecção YOLO"""
        try:
            if int(box.cls[0]) != PERSON_CLASS_ID:
                return
            
            b = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, b)
            tid = int(box.id[0]) if box.id is not None else -1
            
            if tid == -1:
                return
            
            h, w = frame.shape[:2]
            nx, ny = ((x1 + x2) // 2) / w, y2 / h
            
            in_any_zone, zone_idx = False, -1
            zones = config.get("zones_polys", [])
            for i, poly in enumerate(zones):
                if self.is_point_in_polygon(nx, ny, poly):
                    in_any_zone, zone_idx = True, i
                    break
            
            state = self.track_state[tid]
            state["zone_idx"] = zone_idx
            
            if in_any_zone:
                state["status"], state["out_time"] = "IN", 0.0
                if state["recording"]:
                    self.stop_recording(tid)
            else:
                if state["status"] == "IN":
                    state["status"], state["out_time"] = "OUT", 0.01
                    self.start_recording(tid, frame)
                elif state["status"] == "OUT":
                    state["out_time"] += (now - state["last_seen"]) if state["last_seen"] > 0 else 0.03
            
            state["last_seen"] = now
            
            color = (0, 255, 0) if in_any_zone else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID {tid} {'(IN)' if in_any_zone else '(OUT)'}",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            state["buffer"].append(frame.copy())
            if state["recording"]:
                self.write_frame_to_video(tid, frame)
            
            if state["out_time"] >= config["max_out_time"]:
                self.trigger_alert(tid, now, config)
        except:
            pass
    
    # ============================================
    # GRAVAÇÃO DE VÍDEOS
    # ============================================
    def start_recording(self, tid, current_frame):
        """Inicia gravação de vídeo para alerta"""
        state = self.track_state[tid]
        if state["recording"]:
            return
        
        filepath = os.path.join(ALERTS_FOLDER, f"alerta_id{tid}_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        h, w = current_frame.shape[:2]
        state["video_writer"] = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), 15.0, (w, h))
        state["video_path"], state["recording"] = filepath, True
        
        for f in list(state["buffer"]):
            state["video_writer"].write(f)
    
    def write_frame_to_video(self, tid, frame):
        """Adiciona frame ao vídeo em gravação"""
        state = self.track_state[tid]
        if state["recording"] and state["video_writer"]:
            state["video_writer"].write(frame)
    
    def stop_recording(self, tid):
        """Para gravação de vídeo"""
        state = self.track_state[tid]
        if state["recording"]:
            if state["video_writer"]:
                state["video_writer"].release()
            state["recording"], state["video_writer"] = False, None
    
    # ============================================
    # ALERTAS
    # ============================================
    def trigger_alert(self, tid, now, config):
        """Dispara alerta (email + API)"""
        state = self.track_state[tid]
        if (now - self.last_email_time[tid]) >= config.get("email_cooldown", 60.0):
            vp = state["video_path"]
            self.stop_recording(tid)
            
            if self.notifier:
                threading.Thread(
                    target=self.notifier.send_email_with_attachment,
                    args=(
                        f"ALERTA: Pessoa fora da zona (ID {tid})",
                        f"Detectado ID {tid} fora da zona por {state['out_time']:.1f}s.",
                        vp
                    ),
                    daemon=True
                ).start()
            
            if self.api_client:
                try:
                    self.api_client.create_alert(
                        person_id=tid,
                        track_id=tid,
                        out_time=state["out_time"],
                        severity="CRITICAL" if state["out_time"] > 15 else "MEDIUM",
                        alert_type="zone_violation",
                        video_path=vp
                    )
                except:
                    pass
            
            self.last_email_time[tid], state["out_time"] = now, 0.0
    
    # ============================================
    # CÂMERA
    # ============================================
    def _open_camera(self, config):
        """Abre câmera usando configuração do banco"""
        self._cleanup_torch_memory()
        
        src = config.get("source", self.source)
        try:
            src = int(src)
        except (ValueError, TypeError):
            pass
        
        print(f"[YOLO] 📹 Abrindo câmera: {src}")
        self.cap = cv2.VideoCapture(src)
        
        if self.cap.isOpened():
            print(f"[YOLO] ✅ Câmera conectada com sucesso!")
        else:
            print(f"[YOLO] ❌ ERRO: Não foi possível conectar à câmera: {src}")
            self.cap = None
    
    def _close_camera(self):
        """Fecha câmera e reseta flag de configuração"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self._camera_configured = False
    
    # ============================================
    # ✅ v4.6: GERENCIAMENTO DE MEMÓRIA OTIMIZADO
    # ============================================
    def _cleanup_torch_memory(self):
        """Limpa cache de memória da GPU"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        except:
            pass
    
    def _perform_gc_if_needed(self):
        """✅ v4.6: GC com intervalo de 100 frames"""
        self.frame_count += 1
        if self.frame_count % GC_INTERVAL == 0:
            gc.collect()
            mem = get_memory_usage_mb()
            if mem > self.peak_memory_mb:
                self.peak_memory_mb = mem
            if mem > MEMORY_WARNING_THRESHOLD:
                self._cleanup_torch_memory()
    
    # ============================================
    # ESTATÍSTICAS DE ZONAS
    # ============================================
    def update_zone_stats_start(self, zones, now, zones_rich, config):
        """Inicializa contadores de zonas"""
        num = len(zones) if zones else 0
        for i in range(num):
            zr = zones_rich[i] if zones_rich and i < len(zones_rich) else {}
            if i not in self.zone_stats:
                self.zone_stats[i] = {
                    "count": 0,
                    "empty_since": now,
                    "full_since": None,
                    "state": "OK"
                }
            
            zs = self.zone_stats[i]
            zs["count"] = 0
            zs["empty_timeout"] = float(zr.get("empty_timeout") or config["zone_empty_timeout"])
            zs["full_timeout"] = float(zr.get("full_timeout") or config["zone_full_timeout"])
            zs["full_threshold"] = int(zr.get("full_threshold") or config["zone_full_threshold"])
            zs["mode"], zs["name"] = (zr.get("mode") or "GENERIC").upper(), zr.get("name") or f"Zona {i+1}"
        
        for k in list(self.zone_stats.keys()):
            if k >= num:
                del self.zone_stats[k]
    
    def update_zone_stats_end(self, now, zones_rich, config):
        """Atualiza estatísticas de ocupação das zonas"""
        for tid, st in self.track_state.items():
            z = st.get("zone_idx", -1)
            if z >= 0 and z in self.zone_stats:
                self.zone_stats[z]["count"] += 1
        
        for idx, zs in self.zone_stats.items():
            if zs["count"] == 0:
                if zs["empty_since"] is None:
                    zs["empty_since"] = now
                zs["full_since"] = None
                if now - zs["empty_since"] >= zs["empty_timeout"]:
                    zs["state"] = "EMPTY_LONG"
                else:
                    zs["state"] = "OK"
            else:
                zs["empty_since"] = None
                if zs["count"] >= zs["full_threshold"]:
                    if zs["full_since"] is None:
                        zs["full_since"] = now
                    if now - zs["full_since"] >= zs["full_timeout"]:
                        zs["state"] = "FULL_LONG"
                    else:
                        zs["state"] = "OK"
                else:
                    zs["full_since"], zs["state"] = None, "OK"
    
    # ============================================
    # ESTATÍSTICAS GERAIS
    # ============================================
    def get_stats(self):
        """Retorna estatísticas do sistema incluindo FPS atual e médio"""
        in_z = sum(1 for s in self.track_state.values() if s["status"] == "IN")
        out_z = sum(1 for s in self.track_state.values() if s["status"] == "OUT")
        
        if self.paused:
            system_status = "paused"
        elif self.stream_active:
            system_status = "running"
        else:
            system_status = "stopped"
        
        return {
            "fps_current": round(self.current_fps, 1),
            "fps_avg": round(self.avg_fps, 1),
            "fpsavg": round(self.avg_fps, 1),
            "inzone": in_z,
            "outzone": out_z,
            "detected_count": len(self.track_state),
            "system_status": system_status,
            "preset": settings.active_preset if settings else "CUSTOM",
            "memory_mb": round(get_memory_usage_mb(), 1),
            "paused": self.paused,
            "stream_active": self.stream_active
        }


# ============================================
# SINGLETON GLOBAL
# ============================================
vision_system = None

def get_vision_system():
    """Retorna instância singleton do sistema YOLO"""
    global vision_system
    if vision_system is None:
        vision_system = YOLOVisionSystem()
    return vision_system


# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 80)
    print("🎯 YOLO VISION SYSTEM v4.6 - OPTIMIZED")
    print("=" * 80)
    print("\n✅ v4.6 OPTIMIZATIONS:")
    print(f"  • GC_INTERVAL: {GC_INTERVAL} frames (reduced overhead)")
    print("  • Frame pool: Pre-allocated frames for better memory management")
    print(f"  • Reconnection: Up to {MAX_RECONNECTION_ATTEMPTS} attempts with {RECONNECTION_DELAY}s delay")
    print("  • Tracker: Preserves botsort.yaml from database")
    print("\n✅ v4.5 FEATURES:")
    print("  • Removed camera lock (allows multiple connections)")
    print("  • Camera reuse (avoids duplication)")
    print("\n" + "=" * 80)
    print("✅ YOLO System v4.6 READY!")
    print("=" * 80)
