"""
yolo.py

Módulo de computação visual com YOLO (Ultralytics) + Tracking + BoT-SORT/ByteTrack.
Implementa buffer circular para gravar ~2s antes + durante a saída da zona.

✨ MELHORIAS v3.3 (2026-01-01):
- ✅ CORRIGIDO: Duplicação de código API client removida
- ✅ CORRIGIDO: Import de notifications (agora suporta raiz ou backend/)
- ✅ CORRIGIDO: Duplicação em trigger_alert removida
- ✅ Integração completa com FastAPI backend
- ✅ Memory cleanup ativo (gc.collect() periódico)
- ✅ PyTorch cache cleanup (previne fragmentação de memória)

Suporta:
- Webcam local (SOURCE = 0, 1, 2, etc.)
- Câmera IP (SOURCE = "rtsp://user:pass@ip:port/stream")
- Câmera HTTP (SOURCE = "http://ip:port/video")
- Múltiplas safe zones poligonais (normalizadas 0-1)
"""

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Imports padrão
import threading
import time
from collections import defaultdict, deque
import os
import subprocess
import json
import gc

import cv2
import numpy as np
from ultralytics import YOLO

# ✅ Imports do projeto
from backend import config as app_config

try:
    from backend.database_sync import log_alert, get_setting, get_all_settings
except ModuleNotFoundError:
    from database_sync import log_alert, get_setting, get_all_settings

from backend.services.api_client import YOLOApiClient

try:
    from backend.notifications import Notifier
except ImportError:
    try:
        from notifications import Notifier
    except ImportError:
        print("[YOLO] ⚠️  Módulo notifications não encontrado")
        Notifier = None


# =========================
# CONFIG DO config.py
# =========================
SOURCE = app_config.VIDEO_SOURCE
MODEL_PATH = app_config.YOLO_MODEL_PATH
CAM_FPS = app_config.CAM_FPS
BUFFER_SIZE = app_config.BUFFER_SIZE
CAM_WIDTH = app_config.CAM_WIDTH
CAM_HEIGHT = app_config.CAM_HEIGHT
CAM_RESOLUTION = (CAM_WIDTH, CAM_HEIGHT)
GC_INTERVAL = app_config.GC_INTERVAL
MEMORY_WARNING_THRESHOLD = app_config.MEMORY_WARNING_THRESHOLD

PERSON_CLASS_ID = 0
ALERTS_FOLDER = "alertas"
os.makedirs(ALERTS_FOLDER, exist_ok=True)

print(f"[YOLO] ✨ Config carregado do config.py:")
print(f"  - Preset: {app_config.ACTIVE_PRESET}")
print(f"  - Camera: {CAM_RESOLUTION[0]}x{CAM_RESOLUTION[1]} @{CAM_FPS}fps")
print(f"  - Buffer: {BUFFER_SIZE} frames (~{app_config.BUFFER_DURATION_SECONDS}s)")
print(f"  - GC Interval: {GC_INTERVAL} frames")
print(f"  - Memory Threshold: {MEMORY_WARNING_THRESHOLD} MB")


def _load_safe_zone_from_db():
    """
    Lê settings.safe_zone do banco.
    Retorna SEMPRE apenas lista de polígonos: [[[x,y],...], ...]
    """
    raw_safe = get_setting("safe_zone", "[]")
    try:
        s = str(raw_safe).strip()
        if not s or not s.startswith("["):
            return []
        data = json.loads(s)

        # Se for lista de objetos {name, mode, points}, extrai apenas points
        if isinstance(data, list) and data and isinstance(data[0], dict) and "points" in data[0]:
            polys = []
            for z in data:
                pts = z.get("points") or []
                if isinstance(pts, list) and len(pts) >= 3:
                    polys.append(pts)
            return polys

        # Compat: se já for lista de lista de pontos ou zona única, usa direto
        return data
    except Exception:
        return []


def _load_zones_rich_from_db():
    """
    Lê settings.safe_zone do banco no formato rico e normaliza.
    
    Retorna uma lista de dicts com metadados completos.
    """
    raw_safe = get_setting("safe_zone", "[]")
    try:
        s = str(raw_safe).strip()
        if not s or not s.startswith("["):
            return []
        data = json.loads(s)

        # Novo formato: lista de objetos
        if isinstance(data, list) and data and isinstance(data[0], dict):
            zones = []
            for z in data:
                pts = z.get("points") or z.get("polygon") or []
                if isinstance(pts, list) and len(pts) >= 3:
                    zones.append(
                        {
                            "name": z.get("name") or "",
                            "mode": (z.get("mode") or "GENERIC").upper(),
                            "points": pts,
                            "max_out_time": z.get("max_out_time"),
                            "email_cooldown": z.get("email_cooldown"),
                            "empty_timeout": z.get("empty_timeout"),
                            "full_timeout": z.get("full_timeout"),
                            "full_threshold": z.get("full_threshold"),
                        }
                    )
            return zones

        # Formato antigo: lista de polígonos ou zona única
        if isinstance(data, list) and data and isinstance(data[0], list):
            if data and isinstance(data[0], (list, tuple)) and len(data[0]) == 2:
                polys = [data]
            else:
                polys = data

            zones = []
            for pts in polys:
                if isinstance(pts, list) and len(pts) >= 3:
                    zones.append(
                        {
                            "name": "",
                            "mode": "GENERIC",
                            "points": pts,
                            "max_out_time": None,
                            "email_cooldown": None,
                            "empty_timeout": None,
                            "full_timeout": None,
                            "full_threshold": None,
                        }
                    )
            return zones

        return []
    except Exception:
        return []


def get_memory_usage_mb():
    """Retorna uso de memória do processo atual em MB."""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        return mem_info.rss / 1024 / 1024  # MB
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


# =========================
# YOLO VISION SYSTEM
# =========================
class YOLOVisionSystem:
    def __init__(self, source=SOURCE, model_path=MODEL_PATH):
        base_source = source
        base_model = model_path
        cfg = self._load_initial_config(base_source, base_model)

        self.source = cfg.get("source", base_source)
        self.model_path = cfg.get("model_path", base_model)
        self.cam_width = cfg.get("cam_width", CAM_WIDTH)
        self.cam_height = cfg.get("cam_height", CAM_HEIGHT)
        self.cam_fps = cfg.get("cam_fps", CAM_FPS)
        self.buffer_size = BUFFER_SIZE

        print(f"[YOLO] 🔄 Carregando modelo: {self.model_path}")
        self.model = YOLO(self.model_path)
        
        # ✅ WORKAROUND: Desabilita fuse() para PyTorch 2.6+
        def dummy_fuse(verbose=False):
            """Dummy fuse - modelo já está otimizado"""
            print("[YOLO] ⚠️ fuse() bypass (PyTorch 2.6+ compatibility)")
            return self.model.model  # Retorna o modelo interno

        # Sobrescreve o método fuse
        self.model.fuse = dummy_fuse
        self.model.model.is_fused = lambda: True        
        #self.cam_lock = threading.Lock()  # ✅ ADICIONAR

        print(f"[YOLO] ✅ Modelo carregado com sucesso")

        self.track_state = defaultdict(
            lambda: {
                "last_seen": 0.0,
                "status": "OUT",
                "out_time": 0.0,
                "video_writer": None,
                "video_path": None,
                "recording": False,
                "buffer": deque(maxlen=BUFFER_SIZE),
                "zone_idx": -1,
            }
        )
        self.last_email_time = defaultdict(lambda: 0.0)

        self.paused = False
        self.stream_active = True

        self.last_frame_time = None
        self.current_fps = 0.0
        self.avg_fps = 0.0
        self._fps_samples = []

        self.cap = None

        # ✨ Contadores de memória
        self.frame_count = 0
        self.last_gc_time = time.time()
        self.last_memory_warning = 0
        self.peak_memory_mb = 0.0

        # ✨ Email/Notifier setup
        smtp_server = get_setting("email_smtp_server", app_config.SMTP_SERVER)
        smtp_port = int(get_setting("email_smtp_port", str(app_config.SMTP_PORT)))
        email_user = get_setting("email_user", app_config.EMAIL_SENDER)
        email_password = get_setting("email_password", app_config.EMAIL_APP_PASSWORD)
        email_from = get_setting("email_from", email_user)
        email_to = email_from or email_user

        self.notifier = None
        if Notifier and smtp_server and email_user and email_password and email_to:
            self.notifier = Notifier(
                email_user=email_user,
                email_app_password=email_password,
                email_to=email_to,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
            )
            print("[YOLO] ✅ Notificações de email configuradas")
        else:
            print("[YOLO] ⚠️  Notificações de email NÃO configuradas")

        # ✨ API Client para integração com FastAPI backend
        api_enabled = get_setting("api_integration_enabled", "true").lower() == "true"
        api_base_url = get_setting("api_base_url", "http://localhost:8000")
        api_username = get_setting("api_username", "admin")
        api_password = get_setting("api_password", "admin123")
        
        self.api_client = None
        if api_enabled:
            try:
                self.api_client = YOLOApiClient(
                    base_url=api_base_url,
                    username=api_username,
                    password=api_password,
                    enabled=True
                )
                print("[YOLO] ✅ Integração com API FastAPI configurada")
            except Exception as e:
                print(f"[YOLO] ⚠️  Falha ao conectar API: {e}")
                self.api_client = None
        else:
            print("[YOLO] ⚠️  Integração com API desabilitada")

        self.zone_stats = {}

        self.zone_empty_timeout = cfg.get("zone_empty_timeout", app_config.ZONE_EMPTY_TIMEOUT)
        self.zone_full_timeout = cfg.get("zone_full_timeout", app_config.ZONE_FULL_TIMEOUT)
        self.zone_full_threshold = cfg.get("zone_full_threshold", app_config.ZONE_FULL_THRESHOLD)

        print(f"[YOLO] ✅ Sistema inicializado")
        print(f"  - Source: {self.source}")
        print(f"  - Model: {os.path.basename(self.model_path)}")
        print(f"  - Zone params: empty_timeout={self.zone_empty_timeout}s, "
              f"full_timeout={self.zone_full_timeout}s, full_threshold={self.zone_full_threshold}")

        # Loga todas as zonas configuradas
        zones_rich = _load_zones_rich_from_db()
        if zones_rich:
            print("[YOLO] 📍 Zonas configuradas:")
            for i, z in enumerate(zones_rich):
                name = z.get("name") or f"Zona {i+1}"
                mode = (z.get("mode") or "GENERIC").upper()
                max_out = z.get("max_out_time")
                email_cd = z.get("email_cooldown")
                empty_t = z.get("empty_timeout")
                full_t = z.get("full_timeout")
                full_thr = z.get("full_threshold")
                print(
                    f"  - #{i+1}: '{name}' (mode={mode}, max_out={max_out}s, "
                    f"email_cd={email_cd}s, empty_t={empty_t}s, full_t={full_t}s, full_thr={full_thr})"
                )
        else:
            print("[YOLO] ⚠️  Nenhuma zona configurada em settings.safe_zone")

    def _load_initial_config(self, source, model_path):
        safe_zone = _load_safe_zone_from_db()

        cfg = {
            "conf_thresh": float(get_setting("conf_thresh", str(app_config.YOLO_CONF_THRESHOLD))),
            "target_width": int(get_setting("target_width", str(app_config.YOLO_TARGET_WIDTH))),
            "frame_step": int(get_setting("frame_step", str(app_config.YOLO_FRAME_STEP))),
            "safe_zone": safe_zone,
            "max_out_time": float(get_setting("max_out_time", str(app_config.MAX_OUT_TIME))),
            "email_cooldown": float(get_setting("email_cooldown", str(app_config.EMAIL_COOLDOWN))),
            "source": get_setting("source", source),
            "cam_width": int(get_setting("cam_width", str(CAM_RESOLUTION[0]))),
            "cam_height": int(get_setting("cam_height", str(CAM_RESOLUTION[1]))),
            "cam_fps": int(get_setting("cam_fps", str(CAM_FPS))),
            "model_path": get_setting("model_path", model_path),
            "tracker": get_setting("tracker", app_config.TRACKER),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", str(app_config.ZONE_EMPTY_TIMEOUT))),
            "zone_full_timeout": float(get_setting("zone_full_timeout", str(app_config.ZONE_FULL_TIMEOUT))),
            "zone_full_threshold": int(get_setting("zone_full_threshold", str(app_config.ZONE_FULL_THRESHOLD))),
        }
        return cfg

    def get_config(self):
        safe_zone = _load_safe_zone_from_db()

        return {
            "conf_thresh": float(get_setting("conf_thresh", str(app_config.YOLO_CONF_THRESHOLD))),
            "target_width": int(get_setting("target_width", str(app_config.YOLO_TARGET_WIDTH))),
            "frame_step": int(get_setting("frame_step", str(app_config.YOLO_FRAME_STEP))),
            "safe_zone": safe_zone,
            "max_out_time": float(get_setting("max_out_time", str(app_config.MAX_OUT_TIME))),
            "email_cooldown": float(get_setting("email_cooldown", str(app_config.EMAIL_COOLDOWN))),
            "source": get_setting("source", self.source),
            "cam_width": int(get_setting("cam_width", str(CAM_RESOLUTION[0]))),
            "cam_height": int(get_setting("cam_height", str(CAM_RESOLUTION[1]))),
            "cam_fps": int(get_setting("cam_fps", str(CAM_FPS))),
            "model_path": get_setting("model_path", self.model_path),
            "tracker": get_setting("tracker", app_config.TRACKER),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", str(self.zone_empty_timeout))),
            "zone_full_timeout": float(get_setting("zone_full_timeout", str(self.zone_full_timeout))),
            "zone_full_threshold": int(get_setting("zone_full_threshold", str(self.zone_full_threshold))),
        }

    # =========================
    # STREAM CONTROL
    # =========================
    def start_live(self):
        """▶️ Inicia o stream (reconecta câmera se necessário)"""
        if self.stream_active:
            print("[YOLO] ⚠️  Stream já está ativo")
            return False
        
        # ✅ Reconectar câmera se estiver fechada
        if self.cap is None or not self.cap.isOpened():
            print("[CAM] 🎥 Reconectando câmera...")
            
            # Limpa cache antes de reconectar
            self._cleanup_torch_memory()
            gc.collect()
            
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                print("[CAM] ❌ ERRO: Falha ao reconectar câmera!")
                return False
            
            # Reaplica configurações usando os atributos da classe
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.cam_fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
            
            # Verifica configurações obtidas
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"[CAM] ✅ Solicitado: {self.cam_width}x{self.cam_height}@{self.cam_fps}fps | Obtido: {actual_w}x{actual_h}@{actual_fps}fps")
        
        self.stream_active = True
        self.paused = False
        print("[YOLO] ▶️  Stream iniciado")
        return True



    def stop_live(self):
        """⏹️ Para o stream e FECHA a câmera"""
        if not self.stream_active:
            print("[YOLO] ⚠️  Stream já está parado")
            return False
        
        self.stream_active = False
        self.paused = False  # ✅ Reset pause flag
        
        # Para gravações ativas
        for tid, state in list(self.track_state.items()):
            if state["recording"]:
                self.stop_recording(tid, convert=False)
        
        # ✅ FECHA a câmera imediatamente
        self._close_camera()
        
        # ✨ Limpa cache PyTorch
        self._cleanup_torch_memory()
        gc.collect()
        
        print("[YOLO] ⏹️  Stream parado + memória limpa")
        return True


    def is_live(self):
        """Retorna se o stream está ativo"""
        return self.stream_active


    def toggle_pause(self):
        """⏸️ Pausa/Resume SEM fechar a câmera"""
        if not self.stream_active:
            print("[YOLO] ⚠️  Stream não está ativo, não é possível pausar")
            return False
        
        self.paused = not self.paused
        status = "⏸️  pausado" if self.paused else "▶️  retomado"
        print(f"[YOLO] Stream {status}")
        return self.paused


    def is_paused(self):
        """Retorna se o stream está pausado"""
        return self.paused


    # =========================
    # VIDEO CONVERSION
    # =========================
    def convert_video_to_h264(self, input_path):
        output_path = input_path.replace(".mp4", "_h264.mp4")
        try:
            cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "28",
                "-movflags",
                "+faststart",
                "-y",
                output_path,
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            if result.returncode == 0 and os.path.exists(output_path):
                os.remove(input_path)
                os.rename(output_path, input_path)
                print("[YOLO] 🎬 Vídeo convertido para H264")
                return True
            return False
        except Exception:
            return False

    # =========================
    # FRAME UTILS
    # =========================
    @staticmethod
    def resize_keep_width(frame, target_width):
        h, w = frame.shape[:2]
        if w <= 0:
            return frame, 1.0
        scale = target_width / float(w)
        return cv2.resize(frame, (target_width, int(h * scale))), scale

    @staticmethod
    def point_in_polygon(px, py, poly):
        inside = False
        n = len(poly)
        if n < 3:
            return False
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            intersect = ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
            )
            if intersect:
                inside = not inside
            j = i
        return inside


    def generate_frames(self):
            """
            ✨ v3.5: CORREÇÃO - Shutdown imediato + proteção contra múltiplos generators
            """
            self.stream_active = True
            target_interval = 1.0 / 60.0


            init_config = self.get_config()
            self.zone_empty_timeout = init_config.get("zone_empty_timeout", self.zone_empty_timeout)
            self.zone_full_timeout = init_config.get("zone_full_timeout", self.zone_full_timeout)
            self.zone_full_threshold = init_config.get("zone_full_threshold", self.zone_full_threshold)
            self._open_camera(init_config)


            # ✅ PROTEÇÃO: Verifica se câmera foi aberta com sucesso
            if self.cap is None or not self.cap.isOpened():
                print("❌ [YOLO] Câmera não disponível - stream já ativo em outro generator")
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b'\xff\xd8\xff\xe0' + b'\r\n'
                return


            last_frame = None
            stopped_frame = None
            fi = 0


            print(f"[YOLO] 🚀 Stream iniciado com preset '{app_config.ACTIVE_PRESET}'")


            try:
                while self.stream_active:  # ✅ MUDANÇA: Condição do while
                    loop_start = time.time()


                    # ✨ Garbage collection periódico + PyTorch cleanup
                    self._perform_gc_if_needed()


                    cfg = self.get_config()
                    self.zone_empty_timeout = cfg.get("zone_empty_timeout", self.zone_empty_timeout)
                    self.zone_full_timeout = cfg.get("zone_full_timeout", self.zone_full_timeout)
                    self.zone_full_threshold = cfg.get("zone_full_threshold", self.zone_full_threshold)


                    # Zonas ricas + fallback globais
                    global_max_out = cfg["max_out_time"]
                    global_email_cd = cfg["email_cooldown"]
                    global_empty_t = cfg["zone_empty_timeout"]
                    global_full_t = cfg["zone_full_timeout"]
                    global_full_thr = cfg["zone_full_threshold"]


                    zones_rich = _load_zones_rich_from_db()
                    zones_polys = [z["points"] for z in zones_rich] if zones_rich else cfg["safe_zone"]
                    cfg["zones_polys"] = zones_polys


                    # ✅ Paused (verifica ANTES da câmera e ANTES de read())
                    if self.paused:
                        if last_frame is not None:
                            pf = self.draw_paused_overlay(last_frame.copy())
                            ret, buf = cv2.imencode(".jpg", pf)
                            del pf
                        
                            if ret:
                                frame_bytes = buf.tobytes()
                                del buf
                            
                                yield (
                                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                                    + frame_bytes
                                    + b"\r\n"
                                )
                            
                                del frame_bytes


                        elapsed = time.time() - loop_start
                        if elapsed < target_interval:
                            time.sleep(target_interval - elapsed)
                        continue  # ✅ PULA verificação de câmera e read()


                    # ✅ Verifica câmera (somente quando rodando)
                    if self.cap is None or not self.cap.isOpened():
                        print("⚠️ [YOLO] Câmera desconectada durante execução")
                        
                        # ✅ Verifica se stream foi parado externamente
                        if not self.stream_active:
                            print("[YOLO] 🛑 Stream parado, saindo do loop")
                            break
                        
                        # ✅ Tenta reconectar (máximo 3 tentativas)
                        if not hasattr(self, '_reconnect_attempts'):
                            self._reconnect_attempts = 0
                        
                        self._reconnect_attempts += 1
                        
                        if self._reconnect_attempts > 3:
                            print("[YOLO] ❌ Falha ao reconectar câmera após 3 tentativas, parando stream")
                            self.stream_active = False
                            break
                        
                        print(f"[YOLO] 🔄 Tentando reconectar ({self._reconnect_attempts}/3)...")
                        time.sleep(2)  # Aguarda 2s antes de tentar reconectar
                        
                        # Tenta reconectar
                        #self._connect_camera()
                        
                        elapsed = time.time() - loop_start
                        if elapsed < target_interval:
                            time.sleep(target_interval - elapsed)
                        continue



                    # Read frame
                    ok, orig = self.cap.read()
                    if not ok or orig is None:
                        elapsed = time.time() - loop_start
                        if elapsed < target_interval:
                            time.sleep(target_interval - elapsed)
                        continue


                    orig = cv2.flip(orig, 1)
                    frame, scale = self.resize_keep_width(orig, cfg["target_width"])
                    del orig
                
                    now = time.time()


                    self.draw_safe_zone(frame, zones_polys, zones_rich)


                    fi += 1


                    self.update_zone_stats_start(
                        zones_polys, now, zones_rich, global_empty_t, global_full_t, global_full_thr
                    )


                    # YOLO detection
                    if fi % cfg["frame_step"] == 0:
                        results_list = self.model.track(
                            source=frame,
                            conf=cfg["conf_thresh"],
                            persist=True,
                            classes=[PERSON_CLASS_ID],
                            tracker=cfg.get("tracker", app_config.TRACKER),
                            verbose=False,
                        )
                        results = (
                            results_list[0]
                            if isinstance(results_list, list) and len(results_list) > 0
                            else None
                        )


                        if results is not None and results.boxes is not None:
                            for box in results.boxes:
                                self.process_detection(box, frame, scale=1.0, config=cfg, now=now)
                    else:
                        for tid, state in self.track_state.items():
                            state["buffer"].append(frame.copy())
                            if state["recording"]:
                                self.write_frame_to_video(tid, frame)


                    self.update_zone_stats_end(
                        now, zones_rich, global_empty_t, global_full_t, global_full_thr
                    )


                    # Encode frame
                    ret, buf = cv2.imencode(".jpg", frame)
                    if ret:
                        if last_frame is not None:
                            del last_frame
                        last_frame = frame.copy()
                    
                        frame_bytes = buf.tobytes()
                        del buf
                        del frame
                    
                        yield (
                            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                            + frame_bytes
                            + b"\r\n"
                        )
                    
                        del frame_bytes


                    # FPS calculation
                    now2 = time.time()
                    if self.last_frame_time is not None:
                        inst = 1.0 / max(now2 - self.last_frame_time, 1e-6)
                        self.current_fps = inst
                        self._fps_samples.append(inst)
                        if len(self._fps_samples) > 50:
                            self._fps_samples.pop(0)
                        self.avg_fps = sum(self._fps_samples) / len(self._fps_samples)
                    self.last_frame_time = now2


                    # Frame timing
                    elapsed = now2 - loop_start
                    if elapsed < target_interval:
                        time.sleep(target_interval - elapsed)


                # ✅ Loop terminou porque stream_active=False
                # Renderiza frame "stopped" antes de finalizar
                if stopped_frame is None and last_frame is not None:
                    stopped_frame = self.draw_stopped_overlay(last_frame.copy())


                if stopped_frame is not None:
                    for _ in range(3):  # Envia 3x para garantir que chegue
                        ret, buf = cv2.imencode(".jpg", stopped_frame)
                        if ret:
                            frame_bytes = buf.tobytes()
                            del buf
                        
                            yield (
                                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                                + frame_bytes
                                + b"\r\n"
                            )
                        
                            del frame_bytes
                        time.sleep(0.1)


            except MemoryError as e:
                print(f"❌ [MEMORY ERROR] {e}")
                print("🚑 Forçando garbage collection de emergência...")
                self._cleanup_torch_memory()
                gc.collect()
                time.sleep(2)
            
            except Exception as e:
                print(f"❌ [ERROR] {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                self._close_camera()
                self._cleanup_torch_memory()
            
                if last_frame is not None:
                    del last_frame
                if stopped_frame is not None:
                    del stopped_frame
                gc.collect()
            
                print("[YOLO] 🛑 Stream finalizado + memória limpa")

        

    def draw_paused_overlay(self, frame):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        blend = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)
        text = "SISTEMA PAUSADO"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 4)
        cv2.putText(
            blend,
            text,
            ((w - tw) // 2, (h + th) // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            2.0,
            (0, 0, 255),
            4,
        )
        return blend

    def draw_stopped_overlay(self, frame):
        h, w = frame.shape[:2]
        black = frame.copy()
        cv2.rectangle(black, (0, 0), (w, h), (0, 0, 0), -1)
        text = "STREAM DESLIGADO"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
        cv2.putText(
            black,
            text,
            ((w - tw) // 2, (h + th) // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (100, 100, 100),
            3,
        )
        return black

    # =========================
    # RECORDING
    # =========================
    def start_recording(self, tid, frame):
        state = self.track_state[tid]
        if state["recording"]:
            return

        h, w = frame.shape[:2]
        ts = time.strftime("%Y%m%d_%H%M%S")
        vf = f"alerta_id_{tid}_{ts}.mp4"
        vp = os.path.join(ALERTS_FOLDER, vf)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(vp, fourcc, 20.0, (w, h))
        if vw.isOpened():
            state["video_writer"] = vw
            state["video_path"] = vp
            state["recording"] = True

            # ✅ CORREÇÃO: Cria cópia do buffer antes de iterar
            buffer_copy = list(state["buffer"])
            for bf in buffer_copy:
                vw.write(bf)

            print(f"[YOLO] 🎥 Gravação iniciada para ID {tid} (buffer: {len(buffer_copy)} frames)")


    def write_frame_to_video(self, tid, frame):
        state = self.track_state[tid]
        if state["recording"] and state["video_writer"] is not None:
            state["video_writer"].write(frame)

    def stop_recording(self, tid, convert=False):
        state = self.track_state[tid]
        if not state["recording"]:
            return None

        if state["video_writer"] is not None:
            state["video_writer"].release()

        vp = state["video_path"]
        state["video_writer"] = None
        state["video_path"] = None
        state["recording"] = False

        if convert and vp and os.path.exists(vp):
            self.convert_video_to_h264(vp)

        print(f"[YOLO] ⏹️  Gravação finalizada para ID {tid}")
        return vp

    # =========================
    # ZONE HELPERS
    # =========================
    def get_zone_index(self, px, py, zones, frame_w, frame_h):
        """Retorna o índice da zona em que (px,py) está, ou -1 se estiver fora."""
        if not zones:
            return -1

        if isinstance(zones, list) and len(zones) > 0:
            is_multi = (
                isinstance(zones[0], list)
                and len(zones[0]) > 0
                and isinstance(zones[0][0], (list, tuple))
            )

            if is_multi:
                for idx, zone in enumerate(zones):
                    pts = []
                    for p in zone:
                        try:
                            xn, yn = float(p[0]), float(p[1])
                            x = int(xn * frame_w)
                            y = int(yn * frame_h)
                            pts.append((x, y))
                        except Exception:
                            continue
                    if len(pts) >= 3 and self.point_in_polygon(px, py, pts):
                        return idx
                return -1

            pts = []
            for p in zones:
                try:
                    xn, yn = float(p[0]), float(p[1])
                    x = int(xn * frame_w)
                    y = int(yn * frame_h)
                    pts.append((x, y))
                except Exception:
                    continue
            if len(pts) >= 3 and self.point_in_polygon(px, py, pts):
                return 0

        return -1

    def is_point_in_any_zone(self, px, py, zones, frame_w, frame_h):
        idx = self.get_zone_index(px, py, zones, frame_w, frame_h)
        return idx >= 0

    # =========================
    # DETECTION PROCESS
    # =========================
    def process_detection(self, box, frame, scale, config, now):
        if box.id is None:
            return

        tid = int(box.id[0])
        cls = int(box.cls[0])
        if cls != PERSON_CLASS_ID:
            return

        x1b, y1b, x2b, y2b = map(float, box.xyxy[0])
        x1b, y1b, x2b, y2b = int(x1b * scale), int(y1b * scale), int(x2b * scale), int(y2b * scale)

        xc, yc = (x1b + x2b) // 2, (y1b + y2b) // 2

        h, w = frame.shape[:2]

        zones = config.get("zones_polys", config.get("safe_zone"))
        zone_idx = self.get_zone_index(xc, yc, zones, w, h)
        inside = zone_idx >= 0

        state = self.track_state[tid]
        dt = now - state["last_seen"] if state["last_seen"] > 0 else 0.0
        state["last_seen"] = now

        state["buffer"].append(frame.copy())
        state["zone_idx"] = zone_idx

        # Carrega tempos/mode da zona específica (override dos globais)
        g_max_out = config.get("max_out_time", app_config.MAX_OUT_TIME)
        g_email_cd = config.get("email_cooldown", app_config.EMAIL_COOLDOWN)

        zones_rich = _load_zones_rich_from_db()
        if zone_idx >= 0 and zones_rich and zone_idx < len(zones_rich):
            zr = zones_rich[zone_idx]
            mode = (zr.get("mode") or "GENERIC").upper()
            max_out_time = float(zr.get("max_out_time") or g_max_out)
            email_cooldown = float(zr.get("email_cooldown") or g_email_cd)
        else:
            mode = "GENERIC"
            max_out_time = g_max_out
            email_cooldown = g_email_cd

        state["mode"] = mode
        state["max_out_time_zone"] = max_out_time
        state["email_cooldown_zone"] = email_cooldown

        # Lógica IN/OUT + GRAVAÇÃO
        if inside:
            state["status"] = "IN"
            state["out_time"] = 0.0
            color = (0, 255, 0)

            if state["recording"]:
                vp = self.stop_recording(tid, convert=False)
                if vp and os.path.exists(vp):
                    os.remove(vp)
        else:
            state["status"] = "OUT"
            state["out_time"] += dt
            color = (0, 0, 255)

            if not state["recording"]:
                self.start_recording(tid, frame)

            if state["recording"]:
                self.write_frame_to_video(tid, frame)

        # Desenho da bbox
        cv2.rectangle(frame, (x1b, y1b), (x2b, y2b), color, 2)
        rec = " REC" if state["recording"] else ""
        lbl_zone = f" Z{zone_idx + 1}" if zone_idx >= 0 else " OUTZONE"
        lbl = f"ID {tid}{lbl_zone} {state['status']} {state['out_time']:.1f}s{rec}"
        cv2.putText(
            frame,
            lbl,
            (x1b, max(y1b - 10, 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

        # Alerta por zona
        if state["out_time"] > max_out_time:
            if now - self.last_email_time[tid] < email_cooldown:
                return
            self.trigger_alert(tid, state, frame, now)

    def trigger_alert(self, tid, state, frame, now):
        """✅ CORRIGIDO: Duplicação removida"""
        cv2.putText(
            frame,
            f"ALERTA ID {tid}",
            (50, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3,
        )

        vp = self.stop_recording(tid, convert=True)
        if vp and os.path.exists(vp):
            subj = "Alerta zona YOLO"
            body = f"Pessoa ID {tid} fora por {state['out_time']:.1f}s."
            if self.notifier:
                self.notifier.send_email_background(subject=subj, body=body, attachment_path=vp)

            vf = os.path.basename(vp)
            
            # ✅ Mantém log local (compatibilidade)
            log_alert(tid, state["out_time"], vf, email_sent=True)
            
            # ✨ Envia também para API FastAPI
            if self.api_client:
                try:
                    # Determina severidade baseado no tempo
                    if state["out_time"] > 15:
                        severity = "CRITICAL"
                    elif state["out_time"] > 10:
                        severity = "HIGH"
                    elif state["out_time"] > 5:
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"
                    
                    # Pega zone_id se disponível
                    zone_idx = state.get("zone_idx", -1)
                    zone_id = zone_idx + 1 if zone_idx >= 0 else None
                    
                    # Envia para API
                    self.api_client.create_alert(
                        person_id=tid,
                        track_id=tid,
                        out_time=state["out_time"],
                        zone_id=zone_id,
                        severity=severity,
                        alert_type="zone_violation",
                        description=f"Pessoa {tid} fora da zona por {state['out_time']:.1f}s",
                        video_path=vp,
                        email_sent=True,
                        metadata={
                            "mode": state.get("mode"),
                            "frame_count": self.frame_count
                        }
                    )
                    print(f"[YOLO] ✅ Alerta enviado para API (ID {tid})")
                except Exception as e:
                    print(f"[YOLO] ⚠️  Erro ao enviar alerta para API: {e}")
            
            print(f"[YOLO] 🚨 ALERTA! Vídeo salvo: {vp}")

        self.last_email_time[tid] = now
        state["out_time"] = 0.0

    # =========================
    # CAMERA OPEN/CLOSE
    # =========================
    def _open_camera(self, config):
        self._cleanup_torch_memory()
        self._close_camera()

        src = config.get("source", self.source)
        try:
            src = int(src)
        except (ValueError, TypeError):
            pass

        print(f"[CAM] 🎥 Conectando a: {src}")
        self.cap = cv2.VideoCapture(src)

        if not self.cap.isOpened():
            raise RuntimeError(f"❌ Não foi possível abrir a câmera: {src}")

        w = int(config.get("cam_width", CAM_RESOLUTION[0]))
        h = int(config.get("cam_height", CAM_RESOLUTION[1]))
        fps = int(config.get("cam_fps", CAM_FPS))

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[CAM] ✅ Solicitado: {w}x{h}@{fps}fps | Obtido: {real_w}x{real_h}@{real_fps:.1f}fps")

    def _close_camera(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    # =========================
    # MEMORY CLEANUP
    # =========================
    def _cleanup_torch_memory(self):
        """✨ Limpa cache do PyTorch e força GC."""
        try:
            import torch
            
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                print("[TORCH] 🧹 GPU cache limpo")
            
            gc.collect()
            
            if hasattr(torch, '_C') and hasattr(torch._C, '_cuda_emptyCache'):
                try:
                    torch._C._cuda_emptyCache()
                except:
                    pass
            
            print("[TORCH] 🧹 CPU cache limpo")
            
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  [TORCH] Erro ao limpar cache: {e}")

    def _perform_gc_if_needed(self):
        """✨ GC mais agressivo com cleanup de PyTorch periódico"""
        self.frame_count += 1
        now = time.time()
        
        if self.frame_count % GC_INTERVAL == 0:
            gc.collect()
            
            if self.frame_count % (GC_INTERVAL * 10) == 0:
                self._cleanup_torch_memory()
            
            mem_mb = get_memory_usage_mb()
            if mem_mb > 0:
                if mem_mb > self.peak_memory_mb:
                    self.peak_memory_mb = mem_mb
                
                if self.frame_count % 500 == 0:
                    print(f"[MEMORY] Frame {self.frame_count}: {mem_mb:.1f} MB (pico: {self.peak_memory_mb:.1f} MB)")
                
                if mem_mb > MEMORY_WARNING_THRESHOLD and (now - self.last_memory_warning) > 60:
                    print(f"⚠️  [MEMORY WARNING] Uso alto: {mem_mb:.1f} MB (threshold: {MEMORY_WARNING_THRESHOLD} MB)")
                    print("🚑 Forçando cleanup agressivo (PyTorch + GC)...")
                    
                    self._cleanup_torch_memory()
                    gc.collect()
                    
                    self.last_memory_warning = now

    def draw_safe_zone(self, frame, zones, zones_rich=None):
        """✨ Desenha zonas poligonais com nomes reais dos metadados"""
        if not zones:
            return

        h, w = frame.shape[:2]
        
        if not isinstance(zones, list) or len(zones) == 0:
            return
        
        first_item = zones[0]
        is_multi_zone = (
            isinstance(first_item, list) and 
            len(first_item) > 0 and 
            isinstance(first_item[0], (list, tuple))
        )
        
        if is_multi_zone:
            # Múltiplas zonas
            for zone_idx, zone_points in enumerate(zones):
                try:
                    pixel_points = []
                    for point in zone_points:
                        if not isinstance(point, (list, tuple)) or len(point) < 2:
                            continue
                        
                        try:
                            x_norm, y_norm = float(point[0]), float(point[1])
                            x_pixel = int(x_norm * w)
                            y_pixel = int(y_norm * h)
                            pixel_points.append([x_pixel, y_pixel])
                        except (ValueError, TypeError):
                            continue
                    
                    if len(pixel_points) < 3:
                        continue
                    
                    # Desenha polígono
                    pts_array = np.array(pixel_points, dtype=np.int32)
                    cv2.polylines(
                        frame,
                        [pts_array],
                        isClosed=True,
                        color=(0, 255, 255),  # Ciano
                        thickness=3
                    )
                    
                    # Extrai nome e modo dos metadados
                    zone_name = f"ZONE {zone_idx + 1}"
                    zone_mode = "GENERIC"
                    
                    if zones_rich and isinstance(zones_rich, list):
                        if zone_idx < len(zones_rich):
                            zone_metadata = zones_rich[zone_idx]
                            if isinstance(zone_metadata, dict):
                                zone_name = zone_metadata.get("name", zone_name)
                                if not zone_name or zone_name.strip() == "":
                                    zone_name = f"ZONE {zone_idx + 1}"
                                
                                zone_mode = zone_metadata.get("mode", zone_mode)
                                if not zone_mode or zone_mode.strip() == "":
                                    zone_mode = "GENERIC"
                                
                                zone_mode = zone_mode.upper()
                    
                    label = f"{zone_name} ({zone_mode})"
                    
                    # Desenha label com fundo
                    x0, y0 = pixel_points[0]
                    text_y = max(y0 - 15, 25)
                    
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        2
                    )
                    
                    # Fundo preto
                    cv2.rectangle(
                        frame,
                        (x0 - 4, text_y - text_height - 4),
                        (x0 + text_width + 4, text_y + baseline + 2),
                        (0, 0, 0),
                        -1
                    )
                    
                    # Texto ciano
                    cv2.putText(
                        frame,
                        label,
                        (x0, text_y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2,
                        cv2.LINE_AA
                    )
                    
                except Exception as e:
                    print(f"⚠️  [DRAW] Erro ao desenhar zona {zone_idx}: {e}")
                    continue
        
        else:
            # Zona única (formato antigo/legado)
            try:
                pixel_points = []
                for point in zones:
                    if not isinstance(point, (list, tuple)) or len(point) < 2:
                        continue
                    
                    try:
                        x_norm, y_norm = float(point[0]), float(point[1])
                        x_pixel = int(x_norm * w)
                        y_pixel = int(y_norm * h)
                        pixel_points.append([x_pixel, y_pixel])
                    except (ValueError, TypeError):
                        continue
                
                if len(pixel_points) < 3:
                    return
                
                pts_array = np.array(pixel_points, dtype=np.int32)
                cv2.polylines(
                    frame,
                    [pts_array],
                    isClosed=True,
                    color=(0, 255, 255),
                    thickness=3
                )
                
                zone_name = "SAFE ZONE"
                zone_mode = ""
                
                if zones_rich and isinstance(zones_rich, list) and len(zones_rich) > 0:
                    zone_metadata = zones_rich[0]
                    if isinstance(zone_metadata, dict):
                        zone_name = zone_metadata.get("name", zone_name)
                        zone_mode = zone_metadata.get("mode", "")
                        
                        if not zone_name or zone_name.strip() == "":
                            zone_name = "SAFE ZONE"
                        
                        if zone_mode:
                            zone_mode = zone_mode.upper()
                
                if zone_mode and zone_mode.strip() != "":
                    label = f"{zone_name} ({zone_mode})"
                else:
                    label = zone_name
                
                x0, y0 = pixel_points[0]
                text_y = max(y0 - 15, 25)
                
                (text_width, text_height), baseline = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    2
                )
                
                cv2.rectangle(
                    frame,
                    (x0 - 4, text_y - text_height - 4),
                    (x0 + text_width + 4, text_y + baseline + 2),
                    (0, 0, 0),
                    -1
                )
                
                cv2.putText(
                    frame,
                    label,
                    (x0, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA
                )
                
            except Exception as e:
                print(f"⚠️  [DRAW] Erro ao desenhar zona única: {e}")

    # =========================
    # ZONE STATS
    # =========================
    def update_zone_stats_start(self, zones, now, zones_rich, g_empty_t, g_full_t, g_full_thr):
        """Inicializa contadores por frame para cada zona poligonal."""
        if not zones:
            num_zones = 0
        elif isinstance(zones, list):
            is_multi = (
                len(zones) > 0
                and isinstance(zones[0], list)
                and len(zones[0]) > 0
                and isinstance(zones[0][0], (list, tuple))
            )
            num_zones = len(zones) if is_multi else 1
        else:
            num_zones = 0

        for idx in range(num_zones):
            zr = zones_rich[idx] if zones_rich and idx < len(zones_rich) else None

            empty_t = float(zr.get("empty_timeout") or g_empty_t) if zr else g_empty_t
            full_t = float(zr.get("full_timeout") or g_full_t) if zr else g_full_t
            full_thr = int(zr.get("full_threshold") or g_full_thr) if zr else g_full_thr
            mode = (zr.get("mode") or "GENERIC").upper() if zr else "GENERIC"
            name = zr.get("name") or f"Zona {idx+1}" if zr else f"Zona {idx+1}"

            if idx not in self.zone_stats:
                self.zone_stats[idx] = {
                    "count": 0,
                    "empty_since": now,
                    "full_since": None,
                    "state": "OK",
                    "empty_timeout": empty_t,
                    "full_timeout": full_t,
                    "full_threshold": full_thr,
                    "mode": mode,
                    "name": name,
                }
            else:
                zs = self.zone_stats[idx]
                zs["count"] = 0
                zs["empty_timeout"] = empty_t
                zs["full_timeout"] = full_t
                zs["full_threshold"] = full_thr
                zs["mode"] = mode
                zs["name"] = name

        # Remove índices que não existem mais
        for idx in list(self.zone_stats.keys()):
            if idx >= num_zones:
                del self.zone_stats[idx]

    def update_zone_stats_end(self, now, zones_rich, g_empty_t, g_full_t, g_full_thr):
        for tid, st in self.track_state.items():
            z = st.get("zone_idx", -1)
            if z is not None and z >= 0 and z in self.zone_stats:
                self.zone_stats[z]["count"] += 1

        for idx, zs in self.zone_stats.items():
            c = zs["count"]

            empty_t = zs.get("empty_timeout", g_empty_t)
            full_t = zs.get("full_timeout", g_full_t)
            full_thr = zs.get("full_threshold", g_full_thr)

            if c == 0:
                if zs["empty_since"] is None:
                    zs["empty_since"] = now
                zs["full_since"] = None

                if now - zs["empty_since"] >= empty_t:
                    zs["state"] = "EMPTY_LONG"
                else:
                    zs["state"] = "OK"
            else:
                zs["empty_since"] = None
                if c >= full_thr:
                    if zs["full_since"] is None:
                        zs["full_since"] = now
                    if now - zs["full_since"] >= full_t:
                        zs["state"] = "FULL_LONG"
                    else:
                        zs["state"] = "OK"
                else:
                    zs["full_since"] = None
                    zs["state"] = "OK"

    # =========================
    # STATS
    # =========================
    def get_stats(self):
        in_zone = sum(1 for s in self.track_state.values() if s["status"] == "IN")
        out_zone = sum(1 for s in self.track_state.values() if s["status"] == "OUT")
        total_detections = len(self.track_state)

        if not self.stream_active:
            system_status = "stopped"
        elif self.paused:
            system_status = "paused"
        else:
            system_status = "running"

        zones_list = []
        now = time.time()
        for idx, zs in sorted(self.zone_stats.items(), key=lambda x: x[0]):
            empty_for = None
            full_for = None
            if zs["empty_since"] is not None:
                empty_for = max(0.0, now - zs["empty_since"])
            if zs["full_since"] is not None:
                full_for = max(0.0, now - zs["full_since"])

            zones_list.append(
                {
                    "index": idx,
                    "name": zs.get("name", f"Zona {idx+1}"),
                    "mode": zs.get("mode", "GENERIC"),
                    "count": zs["count"],
                    "empty_for": empty_for,
                    "full_for": full_for,
                    "state": zs["state"],
                }
            )

        mem_mb = get_memory_usage_mb()

        return {
            "in_zone": in_zone,
            "out_zone": out_zone,
            "detected_count": total_detections,
            "paused": self.paused,
            "stream_active": self.stream_active,
            "system_status": system_status,
            "fps": round(self.avg_fps, 1),
            "fps_inst": round(self.current_fps, 1),
            "fps_avg": round(self.avg_fps, 1),
            "zones": zones_list,
            "memory_mb": mem_mb if mem_mb > 0 else None,
            "peak_memory_mb": self.peak_memory_mb if self.peak_memory_mb > 0 else None,
            "frame_count": self.frame_count,
            "preset": app_config.ACTIVE_PRESET,
        }


# =========================
# SINGLETON
# =========================
vision_system = None
notifier = None


def get_vision_system():
    global vision_system, notifier
    if vision_system is None:
        vision_system = YOLOVisionSystem()
        notifier = vision_system.notifier
    return vision_system
