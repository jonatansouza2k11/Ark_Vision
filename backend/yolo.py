"""
yolo.py

Módulo de computação visual com YOLO (Ultralytics) + Tracking + BoT-SORT/ByteTrack.
Implementa buffer circular para gravar ~2s antes + durante a saída da zona.

✨ MELHORIAS v4.3 (2026-01-02) - COMPATIBILIDADE TOTAL COM API:
- ✅ ADICIONADO: Métodos is_live(), start_live(), stop_live() e toggle_pause() exigidos pelo stream.py
- ✅ ALINHADO: Nomenclatura de campos no get_stats() para bater com o frontend (inzone, outzone, fpsavg, etc.)
- ✅ ALINHADO: Integração total com backend.config.settings (Pydantic)
- ✅ OTIMIZADO: Cache de configurações e zonas (redução de I/O e parsing JSON)
- ✅ OTIMIZADO: Uso de cv2.pointPolygonTest para detecção de zona (C++ performance)
"""

import sys
import threading
import time
import os
import json
import gc
from pathlib import Path
from collections import defaultdict, deque

import cv2
import numpy as np
from ultralytics import YOLO

# ✅ Configuração de caminhos
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ✅ Imports do projeto alinhados
try:
    from backend.config import settings
    from backend.database_sync import log_alert, get_setting, get_all_settings
except ImportError:
    try:
        from config import settings
        from database_sync import log_alert, get_setting, get_all_settings
    except ImportError:
        print("[YOLO] ⚠️ Erro ao importar configurações do backend")
        settings = None

from backend.services.api_client import YOLOApiClient

try:
    from backend.notifications import Notifier
except ImportError:
    Notifier = None

# =========================
# CONFIGURAÇÕES (Settings)
# =========================
SOURCE = settings.video_source_parsed if settings else "0"
MODEL_PATH = settings.YOLO_MODEL_PATH if settings else "yolo_models/yolov8n.pt"
CAM_FPS = settings.CAM_FPS if settings else 30
BUFFER_SIZE = settings.BUFFER_SIZE if settings else 40
CAM_WIDTH = settings.CAM_WIDTH if settings else 960
CAM_HEIGHT = settings.CAM_HEIGHT if settings else 540
CAM_RESOLUTION = (CAM_WIDTH, CAM_HEIGHT)
GC_INTERVAL = settings.GC_INTERVAL if settings else 50
MEMORY_WARNING_THRESHOLD = settings.MEMORY_WARNING_THRESHOLD if settings else 1024

PERSON_CLASS_ID = 0
ALERTS_FOLDER = "alertas"
os.makedirs(ALERTS_FOLDER, exist_ok=True)

def _load_safe_zone_from_db():
    raw_safe = get_setting("safe_zone", "[]")
    try:
        data = json.loads(str(raw_safe).strip())
        if isinstance(data, list) and data and isinstance(data[0], dict) and "points" in data[0]:
            return [z.get("points") or [] for z in data if len(z.get("points") or []) >= 3]
        return data
    except: return []

def _load_zones_rich_from_db():
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
    except: return []

def get_memory_usage_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 / 1024
    except: return 0.0

# =========================
# YOLO VISION SYSTEM
# =========================
class YOLOVisionSystem:
    def __init__(self, source=SOURCE, model_path=MODEL_PATH):
        self.source = source
        self.model_path = model_path
        self.cam_width = CAM_WIDTH
        self.cam_height = CAM_HEIGHT
        self.cam_fps = CAM_FPS
        self.buffer_size = BUFFER_SIZE

        print(f"[YOLO] 🔄 Carregando modelo: {self.model_path}")
        self.model = YOLO(self.model_path)
        
        def dummy_fuse(verbose=False): return self.model.model
        self.model.fuse = dummy_fuse
        self.model.model.is_fused = lambda: True

        self.track_state = defaultdict(lambda: {
            "last_seen": 0.0, "status": "OUT", "out_time": 0.0, "video_writer": None,
            "video_path": None, "recording": False, "buffer": deque(maxlen=BUFFER_SIZE), "zone_idx": -1
        })
        self.last_email_time = defaultdict(lambda: 0.0)
        
        # ✅ Estados exigidos pelo stream.py
        self.paused = False
        self.stream_active = False # Inicia parado conforme main.py
        
        self.last_frame_time = None
        self.current_fps = 0.0
        self.avg_fps = 0.0
        self._fps_samples = []
        self.cap = None
        self.frame_count = 0
        self.peak_memory_mb = 0.0

        # Notifier & API Client Setup
        self.notifier = None
        if Notifier and settings and settings.EMAIL_SENDER and settings.EMAIL_APP_PASSWORD:
            self.notifier = Notifier(email_user=settings.EMAIL_SENDER, email_app_password=settings.EMAIL_APP_PASSWORD, email_to=settings.EMAIL_SENDER, smtp_server=settings.SMTP_SERVER, smtp_port=settings.SMTP_PORT)

        api_enabled = get_setting("api_integration_enabled", "true").lower() == "true"
        if api_enabled:
            try: self.api_client = YOLOApiClient(base_url=get_setting("api_base_url", "http://localhost:8000"), username=get_setting("api_username", "admin"), password=get_setting("api_password", "admin123"), enabled=True)
            except: self.api_client = None
        else: self.api_client = None

        self.zone_stats = {}
        self._cached_config = None
        self._cached_zones_rich = None
        self._cached_zones_polys = None
        self._cached_pixel_polys = []
        self._last_config_update = 0
        self._config_update_interval = 2.0

    # ✅ MÉTODOS DE CONTROLE EXIGIDOS PELO STREAM.PY
    def is_live(self): return self.stream_active
    
    def start_live(self):
        if not self.stream_active:
            self.stream_active = True
            self.paused = False
            print("[YOLO] ▶️ Stream ativado")
            
    def stop_live(self):
        self.stream_active = False
        self.paused = False
        self._close_camera()
        print("[YOLO] ⏹️ Stream parado")
        
    def toggle_pause(self):
        self.paused = not self.paused
        print(f"[YOLO] {'⏸️ Pausado' if self.paused else '▶️ Retomado'}")
        return self.paused

    def _load_initial_config(self):
        if not settings: return {}
        return {
            "source": self.source,
            "conf_thresh": float(get_setting("yolo_conf_thresh", settings.YOLO_CONF_THRESHOLD)),
            "frame_step": int(get_setting("yolo_frame_step", settings.YOLO_FRAME_STEP)),
            "target_width": int(get_setting("yolo_target_width", settings.YOLO_TARGET_WIDTH)),
            "max_out_time": float(get_setting("max_out_time", settings.MAX_OUT_TIME)),
            "email_cooldown": float(get_setting("email_cooldown", settings.EMAIL_COOLDOWN)),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", settings.ZONE_EMPTY_TIMEOUT)),
            "zone_full_timeout": float(get_setting("zone_full_timeout", settings.ZONE_FULL_TIMEOUT)),
            "zone_full_threshold": int(get_setting("zone_full_threshold", settings.ZONE_FULL_THRESHOLD)),
            "safe_zone": _load_safe_zone_from_db(),
            "tracker": get_setting("yolo_tracker", settings.TRACKER),
        }

    def get_config(self):
        now = time.time()
        if self._cached_config is None or (now - self._last_config_update) > self._config_update_interval:
            self._cached_config = self._load_initial_config()
            self._last_config_update = now
        return self._cached_config

    def is_point_in_polygon(self, px, py, poly):
        if not poly or len(poly) < 3: return False
        pts = np.array(poly, dtype=np.float32)
        return cv2.pointPolygonTest(pts, (float(px), float(py)), False) >= 0

    def generate_frames(self):
        target_interval = 1.0 / 60.0
        cfg = self.get_config()
        self._open_camera(cfg)

        if self.cap is None or not self.cap.isOpened():
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b'\xff\xd8\xff\xe0' + b'\r\n'
            return

        last_frame = None
        fi = 0
        try:
            while self.stream_active:
                loop_start = time.time()
                self._perform_gc_if_needed()
                cfg = self.get_config()
                
                if fi % 60 == 0:
                    self._cached_zones_rich = _load_zones_rich_from_db()
                    self._cached_zones_polys = [z["points"] for z in self._cached_zones_rich] if self._cached_zones_rich else cfg["safe_zone"]
                    self._cached_pixel_polys = [] 

                zones_rich = self._cached_zones_rich
                zones_polys = self._cached_zones_polys
                cfg["zones_polys"] = zones_polys

                if self.paused:
                    if last_frame is not None:
                        pf = self.draw_paused_overlay(last_frame.copy())
                        ret, buf = cv2.imencode(".jpg", pf)
                        if ret: yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
                    time.sleep(target_interval)
                    continue

                ok, orig = self.cap.read()
                if not ok or orig is None:
                    if not self.stream_active: break
                    time.sleep(0.1)
                    continue

                orig = cv2.flip(orig, 1)
                frame, scale = self.resize_keep_width(orig, cfg["target_width"])
                now = time.time()
                fi += 1

                self.draw_safe_zone(frame, zones_polys, zones_rich)
                self.update_zone_stats_start(zones_polys, now, zones_rich, cfg)

                if fi % cfg["frame_step"] == 0:
                    results_list = self.model.track(source=frame, conf=cfg["conf_thresh"], persist=True, classes=[PERSON_CLASS_ID], tracker=cfg["tracker"], verbose=False)
                    if results_list and results_list[0].boxes is not None:
                        for box in results_list[0].boxes:
                            self.process_detection(box, frame, scale=1.0, config=cfg, now=now)
                else:
                    for tid, state in self.track_state.items():
                        state["buffer"].append(frame.copy())
                        if state["recording"]: self.write_frame_to_video(tid, frame)

                self.update_zone_stats_end(now, zones_rich, cfg)

                ret, buf = cv2.imencode(".jpg", frame)
                if ret:
                    last_frame = frame
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

                self._update_fps()
                elapsed = time.time() - loop_start
                if elapsed < target_interval: time.sleep(target_interval - elapsed)

        except Exception as e: print(f"❌ [YOLO] Loop Error: {e}")
        finally:
            self._close_camera()
            self._cleanup_torch_memory()
            gc.collect()

    def _update_fps(self):
        now = time.time()
        if self.last_frame_time:
            inst = 1.0 / max(now - self.last_frame_time, 1e-6)
            self.current_fps = inst
            self._fps_samples.append(inst)
            if len(self._fps_samples) > 50: self._fps_samples.pop(0)
            self.avg_fps = sum(self._fps_samples) / len(self._fps_samples)
        self.last_frame_time = now

    def draw_paused_overlay(self, frame):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "SISTEMA PAUSADO", (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3, cv2.LINE_AA)
        return frame

    def resize_keep_width(self, frame, target_width):
        h, w = frame.shape[:2]
        if w == target_width: return frame, 1.0
        scale = target_width / w
        return cv2.resize(frame, (target_width, int(h * scale)), interpolation=cv2.INTER_LINEAR), scale

    def process_detection(self, box, frame, scale, config, now):
        try:
            if int(box.cls[0]) != PERSON_CLASS_ID: return
            b = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = map(int, b)
            tid = int(box.id[0]) if box.id is not None else -1
            if tid == -1: return

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
                if state["recording"]: self.stop_recording(tid)
            else:
                if state["status"] == "IN":
                    state["status"], state["out_time"] = "OUT", 0.01
                    self.start_recording(tid, frame)
                elif state["status"] == "OUT":
                    state["out_time"] += (now - state["last_seen"]) if state["last_seen"] > 0 else 0.03
            
            state["last_seen"] = now
            color = (0, 255, 0) if in_any_zone else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID {tid} {'(IN)' if in_any_zone else '(OUT)'}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            state["buffer"].append(frame.copy())
            if state["recording"]:
                self.write_frame_to_video(tid, frame)
                if state["out_time"] >= config["max_out_time"]: self.trigger_alert(tid, now, config)
        except: pass

    def start_recording(self, tid, current_frame):
        state = self.track_state[tid]
        if state["recording"]: return
        filepath = os.path.join(ALERTS_FOLDER, f"alerta_id{tid}_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        h, w = current_frame.shape[:2]
        state["video_writer"] = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), 15.0, (w, h))
        state["video_path"], state["recording"] = filepath, True
        for f in list(state["buffer"]): state["video_writer"].write(f)

    def write_frame_to_video(self, tid, frame):
        state = self.track_state[tid]
        if state["recording"] and state["video_writer"]: state["video_writer"].write(frame)

    def stop_recording(self, tid):
        state = self.track_state[tid]
        if state["recording"]:
            if state["video_writer"]: state["video_writer"].release()
            state["recording"], state["video_writer"] = False, None

    def trigger_alert(self, tid, now, config):
        state = self.track_state[tid]
        if (now - self.last_email_time[tid]) >= config.get("email_cooldown", 60.0):
            vp = state["video_path"]
            self.stop_recording(tid)
            if self.notifier:
                threading.Thread(target=self.notifier.send_email_with_attachment, args=(f"ALERTA: Pessoa fora da zona (ID {tid})", f"Detectado ID {tid} fora da zona por {state['out_time']:.1f}s.", vp), daemon=True).start()
            if self.api_client:
                try: self.api_client.create_alert(person_id=tid, track_id=tid, out_time=state["out_time"], severity="CRITICAL" if state["out_time"] > 15 else "MEDIUM", alert_type="zone_violation", video_path=vp)
                except: pass
            self.last_email_time[tid], state["out_time"] = now, 0.0

    def _open_camera(self, config):
        self._cleanup_torch_memory()
        self._close_camera()
        src = config.get("source", self.source)
        try: src = int(src)
        except: pass
        self.cap = cv2.VideoCapture(src)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _close_camera(self):
        if self.cap: self.cap.release()
        self.cap = None

    def _cleanup_torch_memory(self):
        try:
            import torch
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            gc.collect()
        except: pass

    def _perform_gc_if_needed(self):
        self.frame_count += 1
        if self.frame_count % GC_INTERVAL == 0:
            gc.collect()
            mem = get_memory_usage_mb()
            if mem > self.peak_memory_mb: self.peak_memory_mb = mem
            if mem > MEMORY_WARNING_THRESHOLD: self._cleanup_torch_memory()

    def draw_safe_zone(self, frame, zones, zones_rich=None):
        if not zones: return
        h, w = frame.shape[:2]
        if not self._cached_pixel_polys:
            for zp in zones:
                pts = np.array([[int(p[0]*w), int(p[1]*h)] for p in zp], np.int32)
                if len(pts) >= 3: self._cached_pixel_polys.append(pts)

        for i, pts in enumerate(self._cached_pixel_polys):
            cv2.polylines(frame, [pts], True, (0, 255, 255), 3)
            zr = zones_rich[i] if zones_rich and i < len(zones_rich) else {}
            label = f"{zr.get('name') or f'ZONE {i+1}'} ({zr.get('mode') or 'GENERIC'})"
            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            x, y = pts[0][0], max(pts[0][1] - 15, 25)
            cv2.rectangle(frame, (x-4, y-th-4), (x+tw+4, y+bl+2), (0,0,0), -1)
            cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    def update_zone_stats_start(self, zones, now, zones_rich, config):
        num = len(zones) if zones else 0
        for i in range(num):
            zr = zones_rich[i] if zones_rich and i < len(zones_rich) else {}
            if i not in self.zone_stats: self.zone_stats[i] = {"count": 0, "empty_since": now, "full_since": None, "state": "OK"}
            zs = self.zone_stats[i]
            zs["count"] = 0
            zs["empty_timeout"] = float(zr.get("empty_timeout") or config["zone_empty_timeout"])
            zs["full_timeout"] = float(zr.get("full_timeout") or config["zone_full_timeout"])
            zs["full_threshold"] = int(zr.get("full_threshold") or config["zone_full_threshold"])
            zs["mode"], zs["name"] = (zr.get("mode") or "GENERIC").upper(), zr.get("name") or f"Zona {i+1}"
        for k in list(self.zone_stats.keys()):
            if k >= num: del self.zone_stats[k]

    def update_zone_stats_end(self, now, zones_rich, config):
        for tid, st in self.track_state.items():
            z = st.get("zone_idx", -1)
            if z >= 0 and z in self.zone_stats: self.zone_stats[z]["count"] += 1
        for idx, zs in self.zone_stats.items():
            if zs["count"] == 0:
                if zs["empty_since"] is None: zs["empty_since"] = now
                zs["full_since"] = None
                if now - zs["empty_since"] >= zs["empty_timeout"]: zs["state"] = "EMPTY_LONG"
                else: zs["state"] = "OK"
            else:
                zs["empty_since"] = None
                if zs["count"] >= zs["full_threshold"]:
                    if zs["full_since"] is None: zs["full_since"] = now
                    if now - zs["full_since"] >= zs["full_timeout"]: zs["state"] = "FULL_LONG"
                    else: zs["state"] = "OK"
                else: zs["full_since"], zs["state"] = None, "OK"

    # ✅ MÉTODO get_stats() ALINHADO COM stream.py (inzone, outzone, fpsavg, etc.)
    def get_stats(self):
        in_z = sum(1 for s in self.track_state.values() if s["status"] == "IN")
        out_z = sum(1 for s in self.track_state.values() if s["status"] == "OUT")
        
        # Determinar status do sistema
        if self.paused: system_status = "paused"
        elif self.stream_active: system_status = "running"
        else: system_status = "stopped"
        
        return {
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

vision_system = None
def get_vision_system():
    global vision_system
    if vision_system is None: vision_system = YOLOVisionSystem()
    return vision_system
