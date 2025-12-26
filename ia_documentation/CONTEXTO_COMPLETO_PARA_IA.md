# 🤖 CONTEXTO COMPLETO DO PROJETO PARA AGENTE DE IA

**Data:** Dezembro 2025  
**Versão:** 1.0  
**Projeto:** ARK YOLO - Sistema de Monitoramento com IA  
**Linguagem:** Python 3.10+  
**Framework Web:** Flask  

---

## 📋 ÍNDICE RÁPIDO

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Componentes Técnicos](#componentes-técnicos)
4. [Database Schema](#database-schema)
5. [Fluxo de Dados](#fluxo-de-dados)
6. [Configurações Principais](#configurações-principais)
7. [Como Executar](#como-executar)
8. [Pontos de Extensão](#pontos-de-extensão)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 VISÃO GERAL DO PROJETO

### O que é?
**ARK YOLO** é um **sistema de monitoramento de pessoas em tempo real** usando:
- **YOLOv8/v11** (detecção de pessoas)
- **BoT-SORT** (rastreamento multi-objeto)
- **Safe Zones** (áreas de interesse poligonais)
- **Alertas automáticos** por email

### Para que serve?
Monitorar se pessoas saem de uma **zona segura** por tempo prolongado e enviar **alertas automáticos**.

**Exemplos de uso:**
- Monitorar gerentes em uma fábrica
- Vigilância de áreas restritas
- Rastreamento de equipes de resgate
- Monitoramento de visitantes em prédios

### Componentes principais
```
┌─────────────────────────────────────────┐
│          INTERFACE WEB (Flask)          │
│  - Login/Register                       │
│  - Dashboard com video ao vivo          │
│  - Configurações                        │
│  - Histórico de alertas                 │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   YOLO VISION SYSTEM (yolo.py)          │
│  - Detector: YOLOv8n/m/l/x              │
│  - Tracker: BoT-SORT                    │
│  - Safe Zones (poligonais)              │
│  - Buffer circular (pré-gravação 2s)    │
│  - Gravação de alertas                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│        DATABASE (SQLite)                │
│  - Usuários (autenticação)              │
│  - Alertas (histórico)                  │
│  - Configurações (dinâmicas)            │
│  - Logs do sistema                      │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│    EMAIL NOTIFICATIONS (SMTP)           │
│  - Notifica quando pessoa sai da zona   │
│  - Anexa snapshot + vídeo               │
│  - Cooldown para não spammar            │
└─────────────────────────────────────────┘
```

---

## 🏗️ ARQUITETURA DO SISTEMA

### Camadas

#### 1️⃣ **Presentation Layer** (`app.py` - 814 linhas)
**Responsável por:** HTTP, templates, sessões, autenticação

```python
# Principais rotas
/login              → Autenticação
/dashboard          → Interface principal com vídeo ao vivo
/video_feed         → Stream MJPEG em tempo real
/api/stats          → JSON com métricas
/settings           → Configurações (admin)
/alerts             → Histórico de alertas
/users              → Gerenciar usuários (admin)
```

**Padrão de autenticação:**
```python
from auth import login_required, admin_required

@app.route("/settings", methods=["GET", "POST"])
@admin_required  # ← Verifica se role == 'admin'
def settings():
    # Apenas admin pode acessar
```

#### 2️⃣ **Vision Layer** (`yolo.py` - 810 linhas)
**Responsável por:** Detecção, rastreamento, gravação

**Classe central:** `YOLOVisionSystem`

```python
class YOLOVisionSystem:
    def __init__(self, source=0, model_path="yolo_models/yolov8n.pt"):
        self.model = YOLO(model_path)  # Modelo YOLO
        self.track_state = defaultdict(dict)  # Estado dos rastreados
        self.paused = False  # Pausar captura
        self.notifier = Notifier(...)  # Email
        
    def generate_frames(self):
        """
        Retorna frames em MJPEG em tempo real.
        Processa:
        1. Captura frame
        2. Detecta pessoas
        3. Rastreia (BoT-SORT)
        4. Valida safe zones
        5. Envia alertas
        6. Codifica para JPEG
        """
        while True:
            frame = self.cap.read()
            results = self.model(frame, conf=self.conf_thresh)
            # ... processamento
            yield b'--frame\r\n' + jpeg_bytes + b'\r\n'
```

**Track State (coração do sistema):**
```python
self.track_state = {
    track_id: {
        "last_seen": 0.0,           # Quando visto pela última vez
        "status": "IN" | "OUT",      # Dentro ou fora da zona
        "out_time": 5.2,             # Segundos fora da zona
        "video_writer": obj,         # Gravador de vídeo
        "recording": True,           # Gravando?
        "buffer": deque(40 frames),  # Buffer circular pré-gravação
        "zone_idx": 0,               # Qual zona
    }
}
```

#### 3️⃣ **Data Layer** (`database.py` - 148 linhas)
**Responsável por:** Persistência, configurações dinâmicas

```python
# Funções principais
verify_user(username, password)      # Login
create_user(username, email, pwd)    # Registrar
get_setting(key, default)            # Lê config
set_setting(key, value)              # Escreve config
log_alert(person_id, out_time, ...)  # Registra alerta
log_system_action(action, user)      # Log de ações
```

#### 4️⃣ **Zones Layer** (`zones.py` - 143 linhas)
**Responsável por:** Geometria de polígonos, detecção de ponto em zona

```python
class ZoneManager:
    def __init__(self, target_width=1200):
        self.zones = {
            "entrada": np.array([[50,600], [1150,600], ...]),
            "corredor_esq": np.array([...]),
            "elevador_1": np.array([...]),
        }
    
    def point_zone(self, xc, yc):
        """Retorna nome da zona que contém (xc, yc), ou None"""
        for name, poly in self.zones.items():
            if cv2.pointPolygonTest(poly, (xc, yc), False) >= 0:
                return name
        return None
```

#### 5️⃣ **Notifications Layer** (`notifications.py` - 112 linhas)
**Responsável por:** Email SMTP com anexos

```python
class Notifier:
    def send_email(self, to_email, subject, body, attachments=[]):
        """Síncrono - bloqueia"""
        # SMTP com TLS
        
    def send_email_background(self, ...):
        """Assíncrono - threading"""
        threading.Thread(target=self.send_email, ...).start()
```

---

## 🔧 COMPONENTES TÉCNICOS

### 1. YOLO (Detecção)
**Arquivo:** `yolo_models/` (contém `.pt` files)

**Modelos disponíveis:**
```
yolov8n.pt   ← Nano (rápido, menos preciso)
yolov8s.pt   ← Small
yolov8m.pt   ← Medium
yolov8l.pt   ← Large
yolov8x.pt   ← Extra-Large (lento, muito preciso)
yolov11n.pt  ← v11 Nano (mais rápido que v8)
yolov11l.pt  ← v11 Large
```

**Como mudar:**
```python
# Em yolo.py linha 25
MODEL_PATH = "yolo_models\\yolov8m.pt"  # ← Mude aqui
```

**Configuração:**
```python
conf_thresh = get_setting("conf_thresh", 0.85)  # 85% confiança
model = YOLO(MODEL_PATH)
results = model(frame, conf=conf_thresh)
```

### 2. BoT-SORT (Rastreamento)
**Arquivo:** `botsort_reid.yaml`

**O que faz:**
- Associa detecções entre frames (mesma pessoa = mesmo ID)
- Mantém ID mesmo se sair de quadro por tempo
- Usa `persist=True` para manter histórico

**Config:**
```python
results = model.track(
    frame,
    persist=True,           # ← Mantém IDs
    tracker="botsort.yaml"  # ← Configuração
)
```

### 3. Camera Compatibility

**Webcam local:**
```python
SOURCE = 0          # Webcam padrão
SOURCE = 1          # Webcam segunda (se houver)
```

**IP Camera RTSP:**
```python
SOURCE = "rtsp://user:pass@192.168.1.100:554/stream"
```

**IP Camera HTTP:**
```python
SOURCE = "http://192.168.1.100:8080/video"
```

### 4. Redimensionamento e Performance

```python
target_width = int(get_setting("target_width", 1280))
frame_step = int(get_setting("frame_step", 1))

# Resize preservando aspecto
frame = cv2.resize(frame, (target_width, h_novo))

# Processar cada N frames
if frame_number % frame_step == 0:
    results = model(frame)  # Processa
else:
    # Salta frame para ganhar FPS
```

---

## 📊 DATABASE SCHEMA

### Tabela: `users`
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,        -- bcrypt via werkzeug
    role TEXT DEFAULT 'user',  -- 'user' ou 'admin'
    created_at TIMESTAMP,
    last_login TIMESTAMP
);
```

**Exemplo:**
```
id | username | email              | role  | created_at
1  | admin    | admin@example.com  | admin | 2025-01-01
2  | joao     | joao@example.com   | user  | 2025-01-02
```

### Tabela: `alerts`
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    person_id INTEGER,           -- track_id da pessoa
    out_time REAL,               -- Segundos fora (ex: 5.2)
    snapshot_path TEXT,          -- Caminho para foto
    email_sent INTEGER,          -- 1 = já enviou email
    timestamp TIMESTAMP
);
```

**Exemplo:**
```
id | person_id | out_time | snapshot_path           | email_sent | timestamp
1  | 42        | 5.2      | alertas/42_20250101.jpg | 1          | 2025-01-01
```

### Tabela: `settings`
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

**Configurações padrão:**
```
key                 | value
conf_thresh         | 0.85
target_width        | 1280
frame_step          | 1
max_out_time        | 5.0          -- Segundos
safe_zone           | (400,100,700,600)
model_path          | yolo_models\yolov8n.pt
email_smtp_server   | smtp.gmail.com
email_smtp_port     | 587
email_user          | seu_email@gmail.com
email_password      | sua_senha_app_específica
```

### Tabela: `system_logs`
```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY,
    action TEXT,      -- 'PAUSE', 'RESUME', 'START', 'STOP'
    username TEXT,
    reason TEXT,
    email_sent INTEGER,
    timestamp TIMESTAMP
);
```

---

## 🔄 FLUXO DE DADOS

### Pipeline de um frame

```
1. CAPTURA
   cap.read() → frame bruto (1280x720)
   
2. PRÉ-PROCESSAMENTO
   frame = resize(frame, target_width=1280, keep_aspect=True)
   frame = flip horizontal (câmera espelhada)
   
3. DETECÇÃO YOLO
   results = model(frame, conf=0.85)
   boxes = [x1, y1, x2, y2, conf, class_id]
   
4. RASTREAMENTO BoT-SORT
   results = model.track(frame, persist=True)
   → Cada pessoa = track_id único
   → boxes + track_ids
   
5. PROCESSAMENTO POR PESSOA
   for cada pessoa detectada:
       a. Calcular centro bbox
       b. Verificar safe zone
       c. Atualizar track_state
       d. Decidir se fora há > max_out_time
       
6. ALERTA (se necessário)
   if out_time > max_out_time AND cooldown passou:
       a. Pausar buffer circular e salvar vídeo
       b. Tirar snapshot
       c. Log no banco
       d. Enviar email (thread)
       
7. GRAVAÇÃO
   if recording: escrever frame em arquivo
   
8. STREAMING
   frame → JPEG → MJPEG boundary headers → Cliente
```

### Exemplo de detecção de saída da zona

```python
def process_detection(track_id, bbox, class_id):
    # bbox = [x1, y1, x2, y2]
    xc = (bbox[0] + bbox[2]) / 2  # Centro X
    yc = (bbox[1] + bbox[3]) / 2  # Centro Y
    
    # Verificar se está na safe zone
    in_zone = is_point_in_safe_zone(xc, yc)
    
    # Atualizar state
    if not in_zone:
        if self.track_state[track_id]["status"] == "IN":
            # Saiu agora
            self.track_state[track_id]["status"] = "OUT"
            self.track_state[track_id]["out_time"] = 0.0
        else:
            # Continua fora
            self.track_state[track_id]["out_time"] += frame_delta
            
            # Alerta?
            if self.track_state[track_id]["out_time"] > max_out_time:
                if time.time() - self.last_email_time[track_id] > email_cooldown:
                    self.send_alert_email(track_id)
                    self.last_email_time[track_id] = time.time()
    else:
        # Voltou para zona segura
        self.track_state[track_id]["status"] = "IN"
        self.track_state[track_id]["out_time"] = 0.0
```

---

## ⚙️ CONFIGURAÇÕES PRINCIPAIS

### Via DATABASE (Dinâmicas - sem reiniciar)

Todas em `cv_system.db` → `settings` table

```python
# YOLO
conf_thresh = "0.85"              # Confiança da detecção (0-1)
model_path = "yolo_models\yolov8n.pt"
target_width = "1280"             # Largura do frame redimensionado
frame_step = "1"                  # Processar 1 frame, pular 1

# Zona
safe_zone = "(400, 100, 700, 600)"  # Retângulo (x1,y1,x2,y2)
max_out_time = "5.0"              # Segundos para alertar
zone_empty_timeout = "10.0"       # Timeout zona vazia
zone_full_threshold = "5"         # N pessoas para "cheio"

# Email
email_smtp_server = "smtp.gmail.com"
email_smtp_port = "587"
email_user = "seu_email@gmail.com"
email_password = "sua_senha_app"  # ⚠️ NÃO sua senha do Gmail!
email_cooldown = "10.0"           # Espera 10s entre emails

# Câmera
source = "0"                      # 0=webcam, ou URL IP camera
cam_fps = "30"
```

### Via CÓDIGO (Estáticas - precisa reiniciar)

Em `yolo.py` linha 25-35:
```python
SOURCE = 0                                    # Webcam
MODEL_PATH = "yolo_models\\yolov8n.pt"  # Qual modelo
CAM_RESOLUTION = (1280, 720)
CAM_FPS = 30
```

---

## 🚀 COMO EXECUTAR

### 1. Instalação Inicial

```powershell
# Ativar venv
cd d:\Archivos\Downloads\Edx\IA\CV\OpenCV
cv_env\Scripts\Activate.ps1

# Instalar dependências
pip install -r requeriments.txt

# Inicializar banco de dados
python -c "from database import init_db; init_db()"
```

### 2. Iniciar Sistema

```powershell
# Terminal 1: Flask server
python app.py
# → Abre em http://localhost:5000

# Terminal 2 (opcional): Monitorar
while($true) { 
    Get-ChildItem alertas | Measure-Object | % Count
    Start-Sleep 5
}
```

### 3. Acessar Interface

```
URL: http://localhost:5000
Credenciais padrão (se init_db criou):
  - Crie uma conta em /register
  - OU altere no banco em COMECE_AQUI.md
```

### 4. Configurar

Na interface web:
1. Vá para `/settings` (admin)
2. Ajuste:
   - `conf_thresh` (confiança YOLO)
   - `max_out_time` (segundos para alerta)
   - `safe_zone` (coordenadas)
   - Email e SMTP
3. Clique "Salvar"
4. Sistema detecta mudanças no próximo frame

---

## 🔌 PONTOS DE EXTENSÃO

### ✅ Adicionar Nova Configuração

**Passo 1:** Adicione ao formulário em `templates/settings.html`
```html
<input type="text" name="minha_config" value="{{ minha_config }}">
```

**Passo 2:** Processe em `app.py` route `/settings`
```python
if request.method == "POST":
    set_setting("minha_config", request.form.get("minha_config"))
```

**Passo 3:** Use em `yolo.py`
```python
config = self._load_initial_config()
minha_config = config.get("minha_config", "default")
```

---

### ✅ Adicionar Nova Zona

**Em `zones.py`:**
```python
self.zones["minha_zona"] = np.array([
    [x1, y1],
    [x2, y2],
    [x3, y3],
    [x4, y4],
], dtype=np.int32)
```

**Depois use em `yolo.py`:**
```python
current_zone = self.zone_manager.point_zone(xc, yc)
if current_zone == "minha_zona":
    # Lógica especial
```

---

### ✅ Adicionar Novo Alerta

**Em `yolo.py` método `process_detection()`:**
```python
# Alerta customizado
if condition_especial:
    self.notifier.send_email_background(
        to=email,
        subject="Alerta Customizado",
        body="Algo aconteceu!",
        attachments=[snapshot_path]
    )
```

---

### ✅ Mudar Modelo YOLO

**Opção 1: Via código (reiniciar)**
```python
# yolo.py linha 25
MODEL_PATH = "yolo_models\\yolov11l.pt"
```

**Opção 2: Via settings (não precisa reiniciar)**
```python
# Apenas upload novo .pt para yolo_models/
# Ajuste model_path no banco → próximo frame já usa
```

---

### ✅ Adicionar Novo Evento de LOG

**Em `app.py`:**
```python
log_system_action(
    action="MEU_EVENTO",
    username=session["user"]["username"],
    reason="Descrição do que aconteceu"
)
```

---

## 🐛 TROUBLESHOOTING

### ❌ "ImportError: No module named 'ultralytics'"

**Solução:**
```powershell
pip install ultralytics
```

---

### ❌ Câmera não abre / "Cannot open camera"

**Verificar:**
```powershell
# Teste com Python direto
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
# Retorna True = OK, False = problema
```

**Causas:**
- Câmera ocupada por outro app
- Número da câmera errado (tente 1, 2, etc)
- IP camera offline

**Solução:**
```python
# yolo.py linha 23
SOURCE = 0  # Tente 1, 2, 3...
# OU
SOURCE = "rtsp://user:pass@ip:554/stream"
```

---

### ❌ Alertas não enviando / "SMTP Connection Error"

**Verificar:**
```python
# database.py - settings
email_smtp_server = "smtp.gmail.com"  # ✅ OK
email_smtp_port = "587"               # ✅ OK
email_use_tls = "1"                   # ✅ OK

# IMPORTANTE: Gmail requer "App Password"
# NÃO use sua senha do Gmail!
# Gere em: https://myaccount.google.com/apppasswords
```

**Solução:**
1. Gere app password no Gmail
2. Copie em `settings` na interface web
3. Teste com botão "Enviar Email Teste"

---

### ❌ Pessoa detectada, mas não alerta

**Verificar:**
1. `conf_thresh` muito alto? (reduza para 0.7)
2. `max_out_time` muito alto? (reduza para 3.0)
3. `safe_zone` cobre a pessoa? (visualize no dashboard)
4. Pessoa está realmente fora? (check zona)

**Debug:**
```python
# Em yolo.py adicione print
print(f"Track {track_id}: status={status}, out_time={out_time}")
```

---

### ❌ Vídeo muito lento / FPS baixo

**Causas comuns:**
1. Modelo muito grande (yolov8x)
2. `target_width` muito alto
3. `frame_step=1` processa cada frame

**Soluções:**
```python
# Opção 1: Modelo menor
MODEL_PATH = "yolo_models\\yolov8n.pt"  # ← Nano

# Opção 2: Resize maior
target_width = 640  # ← Menor = mais rápido

# Opção 3: Pule frames
frame_step = 2  # ← Processa cada 2º frame
```

---

### ❌ "Database is locked"

**Causa:** Múltiplas instâncias escrevendo no banco

**Solução:**
```powershell
# Feche TODAS as instâncias do Flask
# Aguarde 10s
python app.py  # Inicie novamente
```

---

## 🔐 SEGURANÇA

### ⚠️ Problemas Conhecidos

1. **Email hardcoded no banco**
   - Solução: Use variáveis de ambiente
   ```python
   email_user = os.environ.get("EMAIL_USER", "default")
   ```

2. **SECRET_KEY no código**
   - Solução: Use variável ambiente
   ```python
   app.config["SECRET_KEY"] = os.environ.get("ARK_SECRET_KEY")
   ```

3. **Sem HTTPS em produção**
   - Solução: Use Nginx + Let's Encrypt

4. **Sem rate limiting**
   - Solução: Use Flask-Limiter

---

## 📞 SUPORTE RÁPIDO

| Problema | Solução |
|----------|---------|
| Câmera não abre | `SOURCE = 0` → teste 1, 2, 3 |
| Email não funciona | Gere Gmail app password |
| Muito lento | Use yolov8n.pt + target_width=640 |
| Não detecta pessoas | Aumente campo de visão, reduza conf_thresh |
| Alertas não enviam | Verifique cooldown + email credenciais |
| Banco corrompido | Delete `cv_system.db`, execute `init_db()` |

---

## 🎓 PARA AGENTES DE IA

### Ao trabalhar com este projeto, lembre:

✅ **Estado do sistema é em `track_state` dictionary**
- Cada `track_id` mapeia para estado da pessoa

✅ **Configurações são dinâmicas**
- Leia do banco, não hardcode

✅ **Zonas são poligonais**
- Use `cv2.pointPolygonTest()` para teste

✅ **Email é assíncrono**
- Use threading para não travar vídeo

✅ **YOLO retorna resultados normalizados**
- Coordenadas estão no espaço do frame redimensionado

✅ **BoT-SORT precisa de `persist=True`**
- Sem isso, IDs mudam a cada frame

✅ **Safe zone em settings pode ser JSON ou tupla**
- Faça parse correto em `parse_safe_zone()`

---

## 📚 REFERÊNCIA RÁPIDA

```python
# Importar sistema
from yolo import get_vision_system
vs = get_vision_system()

# Gerar frames
for frame_bytes in vs.generate_frames():
    # Escrever para cliente

# Estado de rastreamento
track_state = vs.track_state  # dict[track_id] → estado
track_state[42]["out_time"]   # Segundos fora

# Configuração
from database import get_setting, set_setting
conf = get_setting("conf_thresh", "0.85")
set_setting("max_out_time", "10.0")

# Notificações
from notifications import Notifier
notifier = Notifier(...)
notifier.send_email_background(
    to="admin@example.com",
    subject="Alerta",
    body="Pessoa fora da zona"
)

# Zonas
from zones import ZoneManager
zm = ZoneManager(target_width=1280)
zona = zm.point_zone(xc, yc)  # "entrada", "corredor", None
```

---

**Versão:** 1.0  
**Última atualização:** Dezembro 2025  
**Licença:** MIT  
**Suporte:** Ver arquivos de documentação complementares
