# 🏗️ Arquitetura Técnica Detalhada - ARK YOLO

> Especificação técnica completa para desenvolvedores

---

## 📐 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    NAVEGADOR WEB                            │
│                 (Frontend - Jinja2)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│                  FLASK SERVER (app.py)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Roteamento HTTP                                        │ │
│  │ - GET /dashboard      → Dashboard HTML                 │ │
│  │ - GET /video_feed     → MJPEG Stream                   │ │
│  │ - POST /api/stats     → JSON dados                     │ │
│  │ - POST /settings      → Salvar configurações           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Autenticação (auth.py)                                 │ │
│  │ - @login_required     → Validar sessão                 │ │
│  │ - @admin_required     → Validar role = admin           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                     ↓             ↓            ↓
        ┌────────────┴────┐   ┌────────┐   ┌──────────┐
        │   YOLO Vision   │   │Database│   │Notifier  │
        │    System       │   │(SQLite)│   │(Email)   │
        │   (yolo.py)     │   │        │   │          │
        └─────────────────┘   └────────┘   └──────────┘
```

---

## 🔄 Fluxo de Detecção

### Inicialização

```
app.py inicializa
    ↓
get_vision_system() cria YOLOVisionSystem
    ↓
YOLO.load("yolov8n.pt")
    ↓
cv2.VideoCapture(source)
    ↓
Notifier inicializa com credenciais SMTP
    ↓
Pronto para aceitar requisições!
```

### Loop de Processamento (Por Frame)

```python
def generate_frames():
    while True:
        # 1. CAPTURA
        ret, frame = cap.read()
        if not ret: break
        
        # 2. REDIMENSIONAMENTO
        frame = resize_keep_width(frame, target_width=960)
        
        # 3. DETECÇÃO YOLO
        results = model.predict(frame, conf=conf_thresh)
        
        # 4. RASTREAMENTO (BoT-SORT automático)
        # results.boxes contém:
        # - xyxy: coordenadas bbox [x1,y1,x2,y2]
        # - conf: confiança [0-1]
        # - cls: classe (0=person)
        # - id: track_id persistente
        
        # 5. PROCESSAMENTO POR PESSOA
        for box in results.boxes:
            if box.cls == 0:  # Person
                x1,y1,x2,y2 = box.xyxy
                track_id = int(box.id)
                xc, yc = (x1+x2)/2, (y1+y2)/2
                
                # 6. VERIFICAR ZONA SEGURA
                in_zone = point_in_polygon(xc, yc, safe_zone)
                
                # 7. ATUALIZAR ESTADO
                if in_zone:
                    track_state[track_id]["status"] = "IN"
                    track_state[track_id]["out_time"] = 0
                else:
                    track_state[track_id]["status"] = "OUT"
                    track_state[track_id]["out_time"] += dt
                
                # 8. VERIFICAR ALERTA
                if track_state[track_id]["out_time"] > max_out_time:
                    if should_send_alert(track_id):
                        trigger_alert(track_id)
        
        # 9. CODIFICAR PARA MJPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # 10. YIELD PARA HTTP
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + 
               frame_bytes + b'\r\n')
```

---

## 🎯 Pipeline de Alerta

### Estrutura de Dados de Alerta

```python
# Trigger event (em yolo.py)
alert_data = {
    "track_id": 5,
    "out_time": 45.3,
    "timestamp": datetime.now(),
    "frame": np.ndarray,  # último frame
}

# 1. Gerar snapshot
snapshot_path = f"alertas/alert_{alert_id}.jpg"
cv2.imwrite(snapshot_path, frame)

# 2. Registrar em DB
database.log_alert(
    person_id=track_id,
    out_time=out_time,
    snapshot_path=snapshot_path,
    email_sent=False
)

# 3. Enviar email (background)
notifier.send_email_background(
    subject=f"⚠️ Alerta: Track {track_id}",
    body=f"Pessoa fora por {out_time:.1f}s",
    attachment_path=snapshot_path
)

# 4. Atualizar cooldown
last_email_time[track_id] = time.time()
```

### Email Notification

```
┌─────────────────────────────────────────┐
│ send_email_background() triggered       │
└──────────────┬──────────────────────────┘
               │
               ↓ (Thread separada)
┌─────────────────────────────────────────┐
│ _build_message()                        │
│ - Subject: "⚠️ Alerta..."               │
│ - Body: Template HTML                   │
│ - Attachment: snapshot_path             │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│ SMTP Connection (Gmail)                 │
│ smtp.gmail.com:587 (TLS)                │
└──────────────┬──────────────────────────┘
               │
               ↓ Enviado!
┌─────────────────────────────────────────┐
│ Database.alerts.email_sent = True       │
└─────────────────────────────────────────┘
```

---

## 🗄️ Schema do Banco de Dados

### Relações

```
users (1)
  ↓ (sem FK direto, mas lógica em app)
  └─→ session['user'] (autenticação)
  
alerts (N)
  └─→ person_id (track_id do YOLO, não FK)
  
settings (1:1)
  └─→ app.config + yolo.config (sistema inteiro)
  
system_logs (N)
  └─→ username (referência a users, informal)
```

### Exemplo de Dados Reais

**users**:
```sql
id=1, username='admin', email='admin@email.com', role='admin'
id=2, username='gerente', email='gerente@empresa.com', role='user'
```

**settings**:
```sql
key='conf_thresh', value='0.78'
key='target_width', value='960'
key='max_out_time', value='30'
key='safe_zone', value='(400, 100, 700, 600)'
key='email_user', value='sender@gmail.com'
```

**alerts**:
```sql
id=1, person_id=5, out_time=45.2, 
      snapshot_path='alertas/alert_1.jpg', 
      email_sent=1, 
      timestamp='2025-12-26 14:30:00'
```

**system_logs**:
```sql
id=1, action='START', username='admin', 
      timestamp='2025-12-26 14:00:00'
id=2, action='PAUSE', username='admin', reason='Manutenção',
      timestamp='2025-12-26 14:15:00'
```

---

## 🔐 Fluxo de Autenticação

```
Usuário acessa /login
        ↓
POST com username + password
        ↓
database.verify_user(username, password)
  ├─ SELECT * FROM users WHERE username = ?
  ├─ check_password_hash(db_password, input_password)
  └─ Retorna user ou None
        ↓
Se sucesso:
  ├─ session['user'] = {...}
  ├─ database.update_last_login(username)
  └─ Redirect /dashboard
        ↓
Se falha:
  └─ Flash error, reload /login
```

### Proteção de Rotas

```python
@app.route('/dashboard')
@login_required  # <- Verifica session['user']
def dashboard():
    user = session['user']  # Já existe!
    return render_template('dashboard.html', user=user)

@app.route('/settings', methods=['POST'])
@admin_required  # <- Verifica session['user']['role']
def settings():
    if session['user']['role'] != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    # ... salvar configurações ...
```

---

## 🎬 MJPEG Streaming

### HTTP Response Header

```
HTTP/1.1 200 OK
Content-Type: multipart/x-mixed-replace; boundary=frame
Connection: keep-alive
Cache-Control: no-cache
...
```

### Body (Boundary Delimited)

```
--frame
Content-Type: image/jpeg

[JPEG binary data ~60KB]

--frame
Content-Type: image/jpeg

[JPEG binary data ~60KB]

--frame
...
```

### Browser Rendering

```html
<img src="/video_feed" />
```

O navegador:
1. Faz GET /video_feed
2. Recebe multipart stream
3. Decodifica cada JPEG entre boundaries
4. Exibe sequencialmente (30 FPS)

---

## 📊 Performance Metrics

### FPS Calculation

```python
def update_fps():
    current_time = time.time()
    if last_frame_time is not None:
        dt = current_time - last_frame_time
        self.current_fps = 1.0 / dt
        
        # Média móvel (últimas 10 frames)
        self._fps_samples.append(self.current_fps)
        if len(self._fps_samples) > 10:
            self._fps_samples.pop(0)
        self.avg_fps = sum(self._fps_samples) / len(self._fps_samples)
    
    last_frame_time = current_time
```

### Memory Management

```
Frame buffer:  deque(maxlen=40)
  └─ ~40 frames × 960×540 × 3 bytes ≈ 60-80 MB

Track state:   defaultdict
  └─ ~10-50 pessoas × ~500 bytes ≈ 5-25 KB

Video recording:  VideoWriter
  └─ H.264 codec, bitrate ~5-10 Mbps
  └─ ~10s de vídeo ≈ 6-12 MB por alerta
```

---

## 🎮 API Endpoints Detail

### GET /api/stats

**Resposta Completa (JSON)**:

```json
{
  "fps": 28.5,
  "people_count": 3,
  "alerts_count": 1,
  "system_status": "RUNNING|PAUSED|STOPPED",
  "model_name": "yolov8n.pt",
  "video_source_label": "Webcam 0",
  "confidence_threshold": 0.78,
  "target_width": 960,
  "frame_step": 2,
  "max_out_time": 30,
  "email_cooldown": 300,
  "recent_alerts": [
    {
      "id": 1,
      "person_id": 5,
      "out_time": 45.2,
      "timestamp": "2025-12-26T14:30:00",
      "snapshot_path": "alertas/alert_1.jpg"
    }
  ],
  "system_logs": [
    {
      "id": 1,
      "action": "START|PAUSE|RESUME|STOP",
      "username": "admin",
      "reason": null,
      "timestamp": "2025-12-26T14:00:00"
    }
  ],
  "safe_zone": [[400,100], [700,100], [700,600], [400,600]],
  "current_tracks": {
    "5": {
      "status": "OUT",
      "out_time": 45.2,
      "last_seen": 14.5,
      "center_x": 550,
      "center_y": 300
    }
  }
}
```

**Intervalo de Chamadas**: A cada 2 segundos do dashboard

---

## 🔧 Extensão e Modificação

### Adicionar Nova Rota

```python
@app.route('/api/custom', methods=['POST'])
@login_required
def custom_endpoint():
    """Sua descrição aqui."""
    data = request.json
    
    # Processar
    result = {"status": "ok", "data": data}
    
    return jsonify(result)
```

### Adicionar Nova Setting

**1. Template (settings.html)**:

```html
<div>
  <label>Meu Parâmetro</label>
  <input name="meu_parametro" value="{{ current_value }}" />
</div>
```

**2. Backend (app.py)**:

```python
@app.route('/settings', methods=['POST'])
@admin_required
def settings():
    meu_parametro = request.form.get('meu_parametro')
    set_setting('meu_parametro', meu_parametro)
    flash('Salvo!', 'success')
    return redirect(url_for('settings'))
```

**3. Uso em yolo.py**:

```python
def get_config(self):
    return {
        'meu_parametro': float(get_setting('meu_parametro', '1.0'))
    }

def generate_frames(self):
    config = self.get_config()
    meu_valor = config['meu_parametro']
    # usar...
```

### Adicionar Novo Tipo de Alerta

```python
def trigger_alert(self, track_id, alert_type='out_of_zone'):
    """
    alert_type pode ser:
    - 'out_of_zone': Pessoa saiu da zona
    - 'loitering': Pessoa ficando muito tempo em um lugar
    - 'abnormal_movement': Movimento anômalo
    """
    
    if alert_type == 'out_of_zone':
        # Lógica atual...
        pass
    
    elif alert_type == 'loitering':
        # Nova lógica...
        if out_time > 60:  # 1 minuto parado
            # Trigger...
            pass
```

---

## 🧪 Testing

### Unit Test Exemplo

```python
# test_yolo.py
import unittest
from yolo import YOLOVisionSystem

class TestYOLO(unittest.TestCase):
    def setUp(self):
        self.vs = YOLOVisionSystem(source=0, model_path="yolo_models/yolov8n.pt")
    
    def test_zone_detection(self):
        # Ponto dentro da zona
        result = self.vs.get_zone_index(550, 350, [(400,100,700,600)], 1280, 720)
        self.assertEqual(result, 0)
        
        # Ponto fora
        result = self.vs.get_zone_index(100, 100, [(400,100,700,600)], 1280, 720)
        self.assertEqual(result, -1)
    
    def test_resize_aspect_ratio(self):
        frame = np.zeros((720, 1280, 3))  # 16:9
        resized = self.vs.resize_keep_width(frame, 960)
        
        aspect_orig = 1280 / 720  # 1.78
        aspect_new = resized.shape[1] / resized.shape[0]
        self.assertAlmostEqual(aspect_orig, aspect_new, places=2)
```

### Integration Test

```python
# test_integration.py
def test_alert_flow():
    """Testa fluxo completo: detecção → alerta → email"""
    vs = get_vision_system()
    
    # Simular pessoa fora da zona por 35 segundos
    vs.track_state[1] = {
        "status": "OUT",
        "out_time": 35.0,
        "last_seen": time.time()
    }
    
    # Deve disparar alerta
    assert vs.should_send_alert(1)
```

---

## 🚀 Otimizações Implementadas

### 1. Frame Skipping
```python
frame_step = 2  # Processa a cada 2º frame
if frame_idx % frame_step != 0:
    continue  # Skip YOLO inference
```

### 2. Aspect Ratio Preservation
```python
def resize_keep_width(frame, width):
    h, w = frame.shape[:2]
    scale = width / w
    new_h = int(h * scale)
    return cv2.resize(frame, (width, new_h))
```

### 3. Cooldown para Spam
```python
def should_send_alert(track_id):
    last_time = last_email_time.get(track_id, 0)
    now = time.time()
    return (now - last_time) > email_cooldown  # 300s padrão
```

### 4. Threading para Email
```python
thread = threading.Thread(
    target=notifier.send_email,
    args=(subject, body, attachment),
    daemon=True
)
thread.start()  # Não bloqueia vídeo!
```

---

## 🔌 Integrações Externas

### SMTP Gmail
```
Host: smtp.gmail.com
Port: 587
Auth: TLS
Sender: seu_email@gmail.com
AppPassword: [gerado em accounts.google.com]
```

### YOLO Ultralytics API
```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model.predict(
    source=frame,
    conf=0.78,
    persist=True,  # Mantém tracking IDs
    device=0       # GPU (ou 'cpu')
)
```

### OpenCV VideoCapture
```python
cap = cv2.VideoCapture(source)
# source = 0 (webcam) ou "rtsp://..." (IP)

while True:
    ret, frame = cap.read()
    if not ret: break
    # processar frame...

cap.release()
```

---

## 📋 Checklist de Deployment

- [ ] Alterar SECRET_KEY em app.py
- [ ] Configurar credenciais de email
- [ ] Testar YOLO com câmera específica
- [ ] Definir zona segura correta
- [ ] Validar envio de email
- [ ] Configurar backup automático do DB
- [ ] Limpar alertas/vídeos antigos periodicamente
- [ ] Monitorar uso de memória
- [ ] Testar com carga (múltiplas pessoas)
- [ ] Documentar localização de câmeras
- [ ] Treinar admins do sistema
- [ ] Configurar HTTPS se necessário

---

**Documento Técnico - v1.0 | Dezembro 2025**

