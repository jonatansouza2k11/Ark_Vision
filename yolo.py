"""
yolo.py

Módulo de computação visual com YOLO (Ultralytics) + Tracking + BoT-SORT/ByteTrack.
Implementa buffer circular para gravar ~2s antes + durante a saída da zona.

Suporta:
- Webcam local (SOURCE = 0, 1, 2, etc.)
- Câmera IP (SOURCE = "rtsp://user:pass@ip:port/stream")
- Câmera HTTP (SOURCE = "http://ip:port/video")
- Múltiplas safe zones poligonais (normalizadas 0-1)
"""

import time
from collections import defaultdict, deque
import os
import subprocess
import json

import cv2
import numpy as np
from ultralytics import YOLO

from notifications import Notifier
from database import log_alert, get_setting

# =========================
# CONFIG PADRÃO
# =========================
SOURCE = 0
MODEL_PATH = "yolo_models\\yolov8n.pt"

CAM_RESOLUTION = (1280, 720)
CAM_FPS = 30

PERSON_CLASS_ID = 0
ALERTS_FOLDER = "alertas"
os.makedirs(ALERTS_FOLDER, exist_ok=True)

BUFFER_SIZE = 40


def _load_safe_zone_from_db():
    """
    Lê settings.safe_zone do banco.

    Formato esperado (novo formato):
    - JSON lista de zonas ricas: [{"name": "...", "mode": "...", "points": [[x,y], ...]}, ...]
    - JSON lista de polígonos: [[[x,y],...], [[x,y],...]]
    - JSON zona única: [[x,y], ...]
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


class YOLOVisionSystem:
    def __init__(self, source=SOURCE, model_path=MODEL_PATH):
        base_source = source
        base_model = model_path
        cfg = self._load_initial_config(base_source, base_model)

        self.source = cfg.get("source", base_source)
        self.model_path = cfg.get("model_path", base_model)
        self.model = YOLO(self.model_path)

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

        smtp_server = get_setting("email_smtp_server", "smtp.gmail.com")
        smtp_port = int(get_setting("email_smtp_port", "587"))
        email_user = get_setting("email_user", "")
        email_password = get_setting("email_password", "")
        email_from = get_setting("email_from", email_user)
        email_to = email_from or email_user

        self.notifier = None
        if smtp_server and email_user and email_password and email_to:
            self.notifier = Notifier(
                email_user=email_user,
                email_app_password=email_password,
                email_to=email_to,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
            )

        self.zone_stats = {}

        self.zone_empty_timeout = cfg.get("zone_empty_timeout", 10.0)
        self.zone_full_timeout = cfg.get("zone_full_timeout", 20.0)
        self.zone_full_threshold = cfg.get("zone_full_threshold", 5)

        print(f"[YOLO] Sistema inicializado. Source: {self.source} | Model: {self.model_path}")
        print(
            f"[YOLO] Zone params: empty_timeout={self.zone_empty_timeout}s, "
            f"full_timeout={self.zone_full_timeout}s, full_threshold={self.zone_full_threshold}"
        )

    # =========================
    # INTERNAL CONFIG LOAD (INICIAL)
    # =========================
    def _load_initial_config(self, source, model_path):
        safe_zone = _load_safe_zone_from_db()

        cfg = {
            "conf_thresh": float(get_setting("conf_thresh", "0.78")),
            "target_width": int(get_setting("target_width", "1280")),
            "frame_step": int(get_setting("frame_step", "2")),
            "safe_zone": safe_zone,
            "max_out_time": float(get_setting("max_out_time", "5.0")),
            "email_cooldown": float(get_setting("email_cooldown", "10.0")),
            "source": get_setting("source", source),
            "cam_width": int(get_setting("cam_width", str(CAM_RESOLUTION[0]))),
            "cam_height": int(get_setting("cam_height", str(CAM_RESOLUTION[1]))),
            "cam_fps": int(get_setting("cam_fps", str(CAM_FPS))),
            "model_path": get_setting("model_path", model_path),
            "tracker": get_setting("tracker", "botsort.yaml"),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", "10.0")),
            "zone_full_timeout": float(get_setting("zone_full_timeout", "20.0")),
            "zone_full_threshold": int(get_setting("zone_full_threshold", "5")),
        }
        return cfg

    # =========================
    # SETTINGS / CONFIG (USADO EM RUNTIME)
    # =========================
    def get_config(self):
        safe_zone = _load_safe_zone_from_db()

        return {
            "conf_thresh": float(get_setting("conf_thresh", "0.78")),
            "target_width": int(get_setting("target_width", "1280")),
            "frame_step": int(get_setting("frame_step", "2")),
            "safe_zone": safe_zone,
            "max_out_time": float(get_setting("max_out_time", "5.0")),
            "email_cooldown": float(get_setting("email_cooldown", "10.0")),
            "source": get_setting("source", self.source),
            "cam_width": int(get_setting("cam_width", str(CAM_RESOLUTION[0]))),
            "cam_height": int(get_setting("cam_height", str(CAM_RESOLUTION[1]))),
            "cam_fps": int(get_setting("cam_fps", str(CAM_FPS))),
            "model_path": get_setting("model_path", self.model_path),
            "tracker": get_setting("tracker", "botsort.yaml"),
            "zone_empty_timeout": float(get_setting("zone_empty_timeout", str(self.zone_empty_timeout))),
            "zone_full_timeout": float(get_setting("zone_full_timeout", str(self.zone_full_timeout))),
            "zone_full_threshold": int(get_setting("zone_full_threshold", str(self.zone_full_threshold))),
        }

    # =========================
    # STREAM CONTROL
    # =========================
    def start_live(self):
        if self.stream_active:
            return False
        self.stream_active = True
        print("[YOLO] Stream iniciado")
        return True

    def stop_live(self):
        if not self.stream_active:
            return False
        self.stream_active = False
        for tid, state in list(self.track_state.items()):
            if state["recording"]:
                self.stop_recording(tid, convert=False)
        print("[YOLO] Stream parado")
        return True

    def is_live(self):
        return self.stream_active

    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    def is_paused(self):
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
                print("[YOLO] Vídeo convertido para H264")
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

    def draw_safe_zone(self, frame, zones):
        """
        Desenha apenas zonas poligonais normalizadas:
        - [[x_norm,y_norm], ...] (zona única)
        - [[[x,y],...], [[x,y],...]] (múltiplas zonas)
        """
        if not zones:
            return

        h, w = frame.shape[:2]

        if isinstance(zones, list) and len(zones) > 0:
            is_multi = (
                isinstance(zones[0], list)
                and len(zones[0]) > 0
                and isinstance(zones[0][0], (list, tuple))
            )

            if is_multi:
                for zone_idx, zone in enumerate(zones):
                    try:
                        pts = []
                        for p in zone:
                            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                                continue
                            xn, yn = float(p[0]), float(p[1])
                            x = int(xn * w)
                            y = int(yn * h)
                            pts.append([x, y])

                        if len(pts) < 3:
                            continue

                        pts_np = np.array(pts, dtype=np.int32)
                        cv2.polylines(
                            frame,
                            [pts_np],
                            isClosed=True,
                            color=(255, 255, 0),
                            thickness=2,
                        )

                        x0, y0 = pts[0]
                        cv2.putText(
                            frame,
                            f"ZONE {zone_idx + 1}",
                            (x0, max(y0 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 255, 0),
                            2,
                        )
                    except Exception:
                        continue
            else:
                try:
                    pts = []
                    for p in zones:
                        if not (isinstance(p, (list, tuple)) and len(p) == 2):
                            continue
                        xn, yn = float(p[0]), float(p[1])
                        x = int(xn * w)
                        y = int(yn * h)
                        pts.append([x, y])

                    if len(pts) >= 3:
                        pts_np = np.array(pts, dtype=np.int32)
                        cv2.polylines(
                            frame,
                            [pts_np],
                            isClosed=True,
                            color=(255, 255, 0),
                            thickness=2,
                        )

                        x0, y0 = pts[0]
                        cv2.putText(
                            frame,
                            "SAFE ZONE",
                            (x0, max(y0 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 255, 0),
                            2,
                        )
                except Exception:
                    pass

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
        vw = cv2.VideoWriter(vp, fourcc, 30.0, (w, h))
        if vw.isOpened():
            state["video_writer"] = vw
            state["video_path"] = vp
            state["recording"] = True

            for bf in state["buffer"]:
                vw.write(bf)

            print(f"[YOLO] Gravação iniciada (com buffer de {len(state['buffer'])} frames)")

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

        return vp

    # =========================
    # ZONE HELPERS
    # =========================
    def get_zone_index(self, px, py, zones, frame_w, frame_h):
        """
        Retorna o índice da zona em que (px,py) está, ou -1 se estiver fora.
        Considera apenas zonas poligonais normalizadas.
        """
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

        zone_idx = self.get_zone_index(xc, yc, config["safe_zone"], w, h)
        inside = zone_idx >= 0

        state = self.track_state[tid]
        dt = now - state["last_seen"] if state["last_seen"] > 0 else 0.0
        state["last_seen"] = now

        state["buffer"].append(frame.copy())
        state["zone_idx"] = zone_idx

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

        if state["out_time"] > config["max_out_time"]:
            if now - self.last_email_time[tid] < config["email_cooldown"]:
                return
            self.trigger_alert(tid, state, frame, now)

    def trigger_alert(self, tid, state, frame, now):
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
            log_alert(tid, state["out_time"], vf, email_sent=True)
            print(f"[ALERTA] Vídeo salvo: {vp}")

        self.last_email_time[tid] = now
        state["out_time"] = 0.0

    # =========================
    # CAMERA OPEN/CLOSE
    # =========================
    def _open_camera(self, config):
        self._close_camera()

        src = config.get("source", self.source)
        try:
            src = int(src)
        except (ValueError, TypeError):
            pass

        print(f"[CAM] Conectando a: {src}")
        self.cap = cv2.VideoCapture(src)

        if not self.cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir a câmera: {src}")

        w = int(config.get("cam_width", CAM_RESOLUTION[0]))
        h = int(config.get("cam_height", CAM_RESOLUTION[1]))
        fps = int(config.get("cam_fps", CAM_FPS))

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        real_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        real_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        real_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[CAM] Solicitado: {w}x{h}@{fps}fps | Obtido: {real_w}x{real_h}@{real_fps:.1f}fps")

    def _close_camera(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    # =========================
    # MAIN GENERATOR (Flask MJPEG)
    # =========================
    def generate_frames(self):
        self.stream_active = True
        target_interval = 1.0 / 60.0

        init_config = self.get_config()
        self.zone_empty_timeout = init_config.get("zone_empty_timeout", self.zone_empty_timeout)
        self.zone_full_timeout = init_config.get("zone_full_timeout", self.zone_full_timeout)
        self.zone_full_threshold = init_config.get("zone_full_threshold", self.zone_full_threshold)
        self._open_camera(init_config)

        last_frame = None
        stopped_frame = None
        fi = 0

        try:
            while True:
                loop_start = time.time()

                config = self.get_config()
                self.zone_empty_timeout = config.get("zone_empty_timeout", self.zone_empty_timeout)
                self.zone_full_timeout = config.get("zone_full_timeout", self.zone_full_timeout)
                self.zone_full_threshold = config.get("zone_full_threshold", self.zone_full_threshold)

                if not self.stream_active:
                    if stopped_frame is None and last_frame is not None:
                        stopped_frame = self.draw_stopped_overlay(last_frame.copy())

                    if stopped_frame is not None:
                        ret, buf = cv2.imencode(".jpg", stopped_frame)
                        if ret:
                            yield (
                                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                                + buf.tobytes()
                                + b"\r\n"
                            )
                    time.sleep(0.2)
                    continue

                ok, orig = self.cap.read()
                if not ok or orig is None:
                    elapsed = time.time() - loop_start
                    if elapsed < target_interval:
                        time.sleep(target_interval - elapsed)
                    continue

                orig = cv2.flip(orig, 1)

                frame, scale = self.resize_keep_width(orig, config["target_width"])
                now = time.time()

                self.draw_safe_zone(frame, config["safe_zone"])

                if self.paused:
                    if last_frame is not None:
                        pf = self.draw_paused_overlay(last_frame.copy())
                        ret, buf = cv2.imencode(".jpg", pf)
                        if ret:
                            yield (
                                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                                + buf.tobytes()
                                + b"\r\n"
                            )

                    elapsed = time.time() - loop_start
                    if elapsed < target_interval:
                        time.sleep(target_interval - elapsed)
                    continue

                fi += 1

                self.update_zone_stats_start(config["safe_zone"], now)

                if fi % config["frame_step"] == 0:
                    results_list = self.model.track(
                        source=frame,
                        conf=config["conf_thresh"],
                        persist=True,
                        classes=[PERSON_CLASS_ID],
                        tracker=config.get("tracker", "botsort.yaml"),
                        verbose=False,
                    )
                    results = (
                        results_list[0]
                        if isinstance(results_list, list) and len(results_list) > 0
                        else None
                    )

                    if results is not None and results.boxes is not None:
                        for box in results.boxes:
                            self.process_detection(box, frame, scale=1.0, config=config, now=now)
                else:
                    for tid, state in self.track_state.items():
                        state["buffer"].append(frame.copy())
                        if state["recording"]:
                            self.write_frame_to_video(tid, frame)

                self.update_zone_stats_end(now)

                ret, buf = cv2.imencode(".jpg", frame)
                if ret:
                    last_frame = frame.copy()
                    yield (
                        b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                        + buf.tobytes()
                        + b"\r\n"
                    )

                now2 = time.time()
                if self.last_frame_time is not None:
                    inst = 1.0 / max(now2 - self.last_frame_time, 1e-6)
                    self.current_fps = inst
                    self._fps_samples.append(inst)
                    if len(self._fps_samples) > 50:
                        self._fps_samples.pop(0)
                    self.avg_fps = sum(self._fps_samples) / len(self._fps_samples)
                self.last_frame_time = now2

                elapsed = now2 - loop_start
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)

        finally:
            self._close_camera()

    # =========================
    # ZONE STATS
    # =========================
    def update_zone_stats_start(self, zones, now):
        """
        Inicializa contadores por frame para cada zona poligonal.
        """
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
            if idx not in self.zone_stats:
                self.zone_stats[idx] = {
                    "count": 0,
                    "empty_since": now,
                    "full_since": None,
                    "state": "OK",
                }
            else:
                self.zone_stats[idx]["count"] = 0

        for idx in list(self.zone_stats.keys()):
            if idx >= num_zones:
                del self.zone_stats[idx]

    def update_zone_stats_end(self, now):
        for tid, st in self.track_state.items():
            z = st.get("zone_idx", -1)
            if z is not None and z >= 0 and z in self.zone_stats:
                self.zone_stats[z]["count"] += 1

        for idx, zs in self.zone_stats.items():
            c = zs["count"]

            if c == 0:
                if zs["empty_since"] is None:
                    zs["empty_since"] = now
                zs["full_since"] = None

                if now - zs["empty_since"] >= self.zone_empty_timeout:
                    zs["state"] = "EMPTY_LONG"
                else:
                    zs["state"] = "OK"
            else:
                zs["empty_since"] = None
                if c >= self.zone_full_threshold:
                    if zs["full_since"] is None:
                        zs["full_since"] = now
                    if now - zs["full_since"] >= self.zone_full_timeout:
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
                    "count": zs["count"],
                    "empty_for": empty_for,
                    "full_for": full_for,
                    "state": zs["state"],
                }
            )

        return {
            "in_zone": in_zone,
            "out_zone": out_zone,
            "detections": total_detections,
            "paused": self.paused,
            "stream_active": self.stream_active,
            "system_status": system_status,
            "fps_inst": self.current_fps,
            "fps_avg": self.avg_fps,
            "zones": zones_list,
        }


vision_system = None
notifier = None


def get_vision_system():
    global vision_system, notifier
    if vision_system is None:
        vision_system = YOLOVisionSystem()
        notifier = vision_system.notifier
    return vision_system
