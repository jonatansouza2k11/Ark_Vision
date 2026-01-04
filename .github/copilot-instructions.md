# AI Coding Agent Instructions

## Project Overview
This is a **Computer Vision Monitoring System** built with Flask + YOLOv8/YOLOv11 for real-time person detection and tracking in a webcam/IP camera feed. The system maintains a "safe zone" and alerts users when people stay outside it too long.

**Architecture: Three-layer system**
- **Presentation Layer** (`app.py`): Flask web server with authentication, dashboard, and REST APIs
- **Vision Layer** (`yolo.py`): Core YOLO detection + multi-object tracking (BoT-SORT) with zone logic
- **Data Layer** (`database.py`): SQLite for users, alerts, and dynamic configuration

## Key Components

### Vision System (`yolo.py` - YOLOVisionSystem class)
**Critical pattern**: Singleton instance via `get_vision_system()` returned to Flask routes. Not a traditional class—it's a persistent service that maintains:
- **Track state dictionary**: `{track_id: {"last_seen": time, "status": "IN|OUT", "out_time": elapsed_seconds}}`
- **Email cooldown tracking**: Prevents alert spam per person
- **Dynamic config loading**: All thresholds/zones come from `database.get_setting()`, NOT hardcoded

**Frame processing pipeline**:
1. Raw frame → flip horizontally → resize keeping aspect ratio (use `resize_keep_width()`)
2. YOLO detection + BoT-SORT tracking with `persist=True` (maintains track IDs across frames)
3. For each detected person: scale bbox coordinates, find center point, check if in safe zone
4. Update track state: increment `out_time` if OUT, reset if IN
5. Trigger alert if `out_time > max_out_time` AND cooldown passed
6. Encode frame to JPEG and yield for MJPEG streaming

**Safe zone design**: Rectangle coordinates `(x1, y1, x2, y2)` in resized frame space (not original). Stored in DB as string: `"(400, 100, 700, 600)"` (use `eval()` to parse).

**Paused mode**: `toggle_pause()` freezes video but keeps tracking in background. UI shows last frame with "SISTEMA PAUSADO" overlay.

### Database Layer (`database.py`)
- **Users table**: hashed passwords via `werkzeug.security`, roles ('admin'|'user')
- **Alerts table**: person_id, out_time, snapshot_path, email_sent flag
- **Settings table**: key-value pairs loaded dynamically by vision system
  - Critical settings: `conf_thresh`, `target_width`, `frame_step`, `max_out_time`, `email_cooldown`, `safe_zone`
- **Initialization**: Call `init_db()` at startup if DB doesn't exist

### Email Notifications (`notifications.py` - Notifier class)
- Uses Gmail SMTP with app passwords (not regular password)
- Two methods: `send_email()` (blocks) vs `send_email_background()` (threading to avoid video lag)
- Attachments handled via mime-type detection

### Zone Management (`zones.py` - ZoneManager class)
- Polygon-based zone system (for future multi-zone expansion)
- Currently unused but prepared for advanced logic (e.g., "entrada", "corredor_esq", "elevador_1")
- Each zone defined as `np.ndarray` of `[x, y]` vertices in resized frame coordinates

## Development Workflows

### Running the System
```powershell
# Activate venv (Windows)
cv_env\Scripts\Activate.ps1

# Install dependencies (first time)
pip install -r requeriments.txt

# Initialize database
python -c "from database import init_db; init_db()"

# Start Flask server (runs on http://localhost:5000)
python app.py
```

### Key Configuration Points
- **Model selection**: Change `MODEL_PATH` in `yolo.py` (e.g., "yolov8n.pt" vs "yolov11l.pt")
  - Smaller models (n, s) = faster but less accurate
  - Larger models (l, x) = slower but better detection
- **Camera source**: Change `SOURCE` in `yolo.py`:
  - **Webcam**: `SOURCE = 0` (or 1, 2, etc. for multiple cameras)
  - **IP Camera RTSP**: `SOURCE = "rtsp://user:pass@ip:554/stream"` 
  - **IP Camera HTTP**: `SOURCE = "http://ip:8080/video"`
  - See `CAMERA_CONFIG.md` for detailed IP camera setup
- **Confidence threshold**: `conf_thresh` in database (default 0.78)
- **Email credentials**: Hardcoded in `yolo.py` line ~45 (SECURITY ISSUE—should move to env vars)

### Testing Detection Quality
- Frame step = 2 processes every 2nd frame (saves CPU, can miss fast movement)
- Target width = 960 default (resize for speed; bigger = more accurate but slower)
- Visualize safe zone rectangle in `/dashboard` route

## Project-Specific Patterns

### Authentication Decorator Pattern
- `@login_required`: Checks `session['user']` exists, redirects to login
- `@admin_required`: Also checks `session['user']['role'] == 'admin'`
- Both in `auth.py`—reuse for all protected routes

### Settings as a Configuration Store
Settings flow: HTML form → `app.py` POST → `database.set_setting()` → Cached by `YOLOVisionSystem.get_config()` on next frame
**Important**: Settings are fetched fresh every frame cycle (inside `generate_frames()` loop) to allow live tuning without restart.

### MJPEG Streaming Pattern
- Flask route `/video_feed` calls `vs.generate_frames()` generator
- Yields JPEG bytes with MJPEG boundary headers: `b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"`
- Client displays via `<img src="/video_feed">` in HTML template

### Multi-Threading Considerations
- Flask app runs with `threaded=True`
- Email notifications use background threads (`threading.Thread`)
- Vision system state (track_state dict) accessed by multiple threads—currently no locks (low contention for now, but risky if expanded)

## Integration Points

### External Dependencies
- **ultralytics.YOLO**: Model loading + inference + tracking
- **cv2 (OpenCV)**: Frame processing, drawing, encoding
- **torch/torchvision**: Implicit (ultralytics dependency)
- **Flask**: HTTP server, session management, templating
- **SQLite3**: Built-in Python module, no setup needed
- **werkzeug**: Password hashing

### Data Flow
1. Webcam/IP camera → YOLO model (via ultralytics)
2. Track results → `YOLOVisionSystem` state
3. State changes → `database.log_alert()` + email via `Notifier`
4. Settings updates → `database.set_setting()` + picked up in next frame cycle

## Common Modification Points

### Adding a New Setting
1. Add key-value pair to `/settings` form in template
2. In `app.py` POST handler: `set_setting('my_key', request.form.get('my_key'))`
3. In `yolo.py` `get_config()`: `'my_key': type(get_setting('my_key', 'default'))`
4. Use `config['my_key']` in `generate_frames()` or `process_detection()`

### Changing Safe Zone
- Admin UI: Modify in `/settings` route (currently not editable in UI, only database)
- Database: Update `safe_zone` setting value as string `"(x1, y1, x2, y2)"`
- Or dynamically: `set_setting('safe_zone', str((x1, y1, x2, y2)))`

### Adding Alert Conditions
- In `process_detection()`: After `state["out_time"]` check, add new conditions
- Call `trigger_alert()` or add logic to `log_alert()` in database
- Example: alert if `in_zone` AND `xc > threshold` (custom zone logic)

### Model Switching
- All `.pt` files in root directory are pre-downloaded YOLO weights
- Change `MODEL_PATH` in `yolo.py` line 16 and restart Flask
- YOLOv8 vs YOLOv11: Different model names but same `ultralytics` API

## Security Notes
⚠️ **Current Issues**:
- Email credentials hardcoded in `yolo.py` (should use environment variables)
- Flask secret key hardcoded in `app.py` (should use env var or config file)
- No HTTPS in development
- Admin password not enforced (created via `/register` endpoint)

## File Reference
- **Core Logic**: `yolo.py` (290 lines), `app.py` (151 lines), `database.py` (148 lines)
- **Config**: `botsort_reid.yaml` (tracker config), `.github/copilot-instructions.md` (this file)
- **Templates**: `templates/` (HTML + Jinja2)
- **Models**: `*.pt` files (YOLO weights, ~30-350 MB each)
- **Data**: `pallet_dataset/`, `datasets/coco8/` (training data, not used at runtime)
