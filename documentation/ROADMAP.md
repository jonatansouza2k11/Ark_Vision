# 🗺️ Roadmap de Desenvolvimento - ARK YOLO

> Plano estratégico de evolução do sistema

---

## 📊 Versões Planejadas

```
v1.0 (Atual) ─────────────────────────────────
│ ✅ Detecção YOLO v8/v11
│ ✅ Rastreamento BoT-SORT
│ ✅ Dashboard web
│ ✅ Alertas por email
│ ✅ Autenticação
│ ✅ 1 câmera por instância
│
v1.1 (Q1 2026) ────────────────────────────────
│ 🔲 Interface gráfica para zonas
│ 🔲 Múltiplas zonas com nomes
│ 🔲 Histórico detalhado de rastreamento
│ 🔲 Rate limiting de login
│ 🔲 Suporte HTTPS
│
v2.0 (Q2-Q3 2026) ──────────────────────────────
│ 🔲 Múltiplas câmeras simultâneas
│ 🔲 Rastreamento cross-câmera
│ 🔲 Webhook para integrações
│ 🔲 Análise de comportamentos
│ 🔲 Heatmaps de movimentação
│ 🔲 Dashboard multi-câmera
│
v3.0 (Q4 2026+) ────────────────────────────────
│ 🔲 Machine Learning para anomalias
│ 🔲 App mobile (iOS/Android)
│ 🔲 Integração com sistemas de acesso
│ 🔲 Reconhecimento facial (opcional)
│ 🔲 Suporte cloud (AWS/Azure/GCP)
│
v4.0 (2027+) ────────────────────────────────
  🔲 Sistema distribuído com múltiplos nós
  🔲 Análise preditiva
  🔲 Integração com IA generativa
```

---

## 🎯 Versão 1.1 (Curto Prazo - Q1 2026)

### Objetivo
Melhorar usabilidade e adicionar features solicitadas por usuários

### Features

#### 1. Editor Visual de Zonas Seguras
**Status:** Planejado  
**Prioridade:** 🔴 Alta  
**Esforço:** 3-4 dias

**Descrição:**
- Interface no dashboard para desenhar zona segura
- Suporte para polígonos (não apenas retângulos)
- Preview em tempo real
- Salvar/carregar templates

**Design:**

```html
<canvas id="zone-editor" width="960" height="540"></canvas>

<!-- JavaScript -->
document.addEventListener('click', (e) => {
    let [x, y] = canvas.getMousePos(e)
    polygon.push([x, y])
    draw()
})

<!-- Salvar -->
POST /api/safe_zone { zone_data: [...] }
```

**Arquivo Afetado:** `templates/dashboard.html`, `app.py`, `yolo.py`

---

#### 2. Múltiplas Zonas com Nomes
**Status:** Planejado  
**Prioridade:** 🟠 Média  
**Esforço:** 2-3 dias

**Descrição:**
- Criar múltiplas zonas seguras
- Nomeá-las (ex: "entrada", "corredor", "elevador")
- Rastrear em qual zona cada pessoa está
- Alertas diferenciados por zona

**Schema de Dados:**

```python
# settings.safe_zones
[
    {
        "name": "entrada",
        "polygon": [[x,y], [x,y], ...],
        "alert_enabled": true,
        "max_out_time": 30
    },
    {
        "name": "corredor",
        "polygon": [[x,y], ...],
        "alert_enabled": false
    }
]
```

**Arquivo Afetado:** `database.py`, `yolo.py`, `app.py`

---

#### 3. Histórico Detalhado de Rastreamento
**Status:** Planejado  
**Prioridade:** 🟠 Média  
**Esforço:** 2 dias

**Descrição:**
- Nova tabela `track_history` no DB
- Registrar cada movimento de pessoa
- Gerar timeline visual
- Exportar relatórios

**Schema:**

```sql
CREATE TABLE track_history (
    id INTEGER PRIMARY KEY,
    track_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    zone_name TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Arquivo Afetado:** `database.py`, `yolo.py`, `templates/logs.html`

---

#### 4. Rate Limiting no Login
**Status:** Planejado  
**Prioridade:** 🟠 Média  
**Esforço:** 1 dia

**Descrição:**
- Evitar brute force
- Máximo 5 tentativas por minuto por IP
- Bloquear temporariamente após exceder

**Implementação:**

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```

**Arquivo Afetado:** `app.py`

---

#### 5. Suporte HTTPS
**Status:** Planejado  
**Prioridade:** 🟠 Média  
**Esforço:** 1 dia

**Descrição:**
- Gerar certificado SSL
- Configurar Flask para HTTPS
- Redirecionar HTTP → HTTPS

**Implementação:**

```bash
# Gerar certificado auto-assinado
openssl req -x509 -newkey rsa:4096 -nodes \
    -out cert.pem -keyout key.pem -days 365
```

```python
app.run(
    ssl_context=('cert.pem', 'key.pem'),
    host='0.0.0.0',
    port=5000
)
```

**Arquivo Afetado:** `app.py`

---

## 🚀 Versão 2.0 (Médio Prazo - Q2-Q3 2026)

### Objetivo
Escalar para múltiplas câmeras e adicionar análises avançadas

### Features

#### 1. Múltiplas Câmeras Simultâneas
**Prioridade:** 🔴 Alta  
**Esforço:** 5-7 dias

**Arquitetura:**

```python
# cameras.py (novo)
class CameraManager:
    def __init__(self):
        self.cameras = {}  # {camera_id: YOLOVisionSystem}
    
    def add_camera(self, camera_id, source, model):
        vs = YOLOVisionSystem(source, model)
        self.cameras[camera_id] = vs
    
    def get_camera(self, camera_id):
        return self.cameras[camera_id]

# app.py
camera_manager = CameraManager()

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    vs = camera_manager.get_camera(camera_id)
    return Response(vs.generate_frames(), ...)
```

**Database Schema:**

```sql
CREATE TABLE cameras (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    model TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    last_seen TIMESTAMP
)
```

**Arquivo Afetado:** `app.py` (refactor), novo `cameras.py`, `database.py`

---

#### 2. Rastreamento Cross-Câmera
**Prioridade:** 🔴 Alta  
**Esforço:** 4-5 dias

**Conceito:**
- Mesmo track_id persiste entre câmeras
- Usar embedding de re-identificação (ReID)
- Rastrear movimento entre áreas

**Implementação:**

```python
# reid_model.py (novo)
from ultralytics import YOLO

class ReIDModel:
    def __init__(self):
        self.model = YOLO('yolov8n-pose.pt')  # Usar pose para ReID
    
    def get_embedding(self, crop):
        """Retorna embedding da pessoa"""
        results = self.model.predict(crop)
        return results[0].keypoints.data

# yolo.py
def match_across_cameras(embedding1, embedding2):
    """Compara embeddings de 2 câmeras"""
    distance = np.linalg.norm(embedding1 - embedding2)
    return distance < threshold

```

**Arquivo Afetado:** novo `reid_model.py`, `yolo.py`, `app.py`

---

#### 3. Webhook para Integrações
**Prioridade:** 🟠 Média  
**Esforço:** 2-3 dias

**Descrição:**
- Disparar HTTP POST ao ocorrer evento
- Integração com Zapier, Make, etc
- Custom webhooks configuráveis

**Implementação:**

```python
# notifications.py
def send_webhook(alert_data):
    webhook_url = get_setting('webhook_url')
    if not webhook_url:
        return
    
    payload = {
        'event': 'alert',
        'track_id': alert_data['track_id'],
        'timestamp': alert_data['timestamp'],
        'snapshot_url': alert_data['snapshot_url']
    }
    
    requests.post(webhook_url, json=payload)

# Database
INSERT INTO settings (key, value)
VALUES ('webhook_url', 'https://webhook.site/...')
```

**Arquivo Afetado:** `notifications.py`, `database.py`

---

#### 4. Análise de Comportamentos
**Prioridade:** 🟠 Média  
**Esforço:** 4-5 dias

**Comportamentos Suportados:**
- Loitering (ficar muito tempo em um local)
- Movimento rápido (corrida)
- Mudança rápida de direção
- Aglomeração (múltiplas pessoas juntas)

**Implementação:**

```python
# behavior_analyzer.py (novo)
class BehaviorAnalyzer:
    def detect_loitering(self, track_state, threshold=60):
        """Detecta se pessoa está parada"""
        if track_state['stationary_time'] > threshold:
            return True
        return False
    
    def detect_running(self, velocity):
        """Detecta movimento rápido"""
        return velocity > 3.0  # pixels/frame
    
    def detect_crowding(self, nearby_tracks):
        """Detecta aglomeração"""
        return len(nearby_tracks) > 5
```

**Arquivo Afetado:** novo `behavior_analyzer.py`, `yolo.py`

---

#### 5. Heatmaps de Movimentação
**Prioridade:** 🟠 Média  
**Esforço:** 3-4 dias

**Descrição:**
- Visualizar áreas mais movimentadas
- Gráfico de densidade temporal
- Exportar como imagem/vídeo

**Implementação:**

```python
# heatmap.py (novo)
import cv2

def generate_heatmap(track_history):
    """Gera heatmap a partir do histórico"""
    heatmap = np.zeros((540, 960))
    
    for point in track_history:
        x, y = int(point['x']), int(point['y'])
        cv2.circle(heatmap, (x, y), 10, 1, -1)
    
    heatmap = cv2.blur(heatmap, (51, 51))
    heatmap_color = cv2.applyColorMap(
        (heatmap * 255).astype(np.uint8),
        cv2.COLORMAP_JET
    )
    
    return heatmap_color
```

**Arquivo Afetado:** novo `heatmap.py`, `app.py` (rota `/heatmap`)

---

## 🤖 Versão 3.0 (Longo Prazo - Q4 2026+)

### Features

#### 1. Detecção de Anomalias com ML
**Descrição:**
- Treinar modelo para detectar movimentos anormais
- Alertar para comportamentos suspeitos
- Usar Isolation Forest ou similar

#### 2. App Mobile
**Descrição:**
- App iOS/Android (Flutter ou React Native)
- Ver stream em tempo real
- Receber notificações push
- Histórico mobile

#### 3. Integração com Sistemas de Acesso
**Descrição:**
- API para integrar com catraca/controle de acesso
- Sincronizar detecção com logs de entrada
- Validar se pessoa tem acesso

#### 4. Reconhecimento Facial
**Descrição:**
- Usar FaceNet ou similar
- Identificar pessoas conhecidas
- Alertas personalizados

---

## 🏗️ Arquitetura Futura (v2.0+)

### Microserviços

```
┌──────────────────────────────────────────────┐
│         GATEWAY API (Flask)                  │
│  - Roteamento                                │
│  - Autenticação                              │
└────────────┬─────────────────────────────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐
│Cam 1 │ │Cam 2 │ │Cam 3 │  VISION SERVICES
│(YOLO)│ │(YOLO)│ │(YOLO)│
└──┬───┘ └──┬───┘ └──┬───┘
   │        │        │
   └────────┼────────┘
            │
     ┌──────▼──────┐
     │  ReID Model │  REID SERVICE
     └──────┬──────┘
            │
     ┌──────▼────────────┐
     │ Cross-Cam Tracker │  TRACKING SERVICE
     └──────┬────────────┘
            │
     ┌──────▼──────────────┐
     │ Behavior Analyzer   │  ANALYTICS SERVICE
     └──────┬──────────────┘
            │
     ┌──────▼──────────┐
     │  Notification   │  NOTIFICATION SERVICE
     │  Email/Webhook  │
     └────────────────┘
            │
     ┌──────▼────────┐
     │  PostgreSQL   │  DATA LAYER
     │  Redis Cache  │
     └───────────────┘
```

---

## 📅 Timeline Proposto

```
2025-Q4
├─ v1.0 ✅ Lançamento
└─ Feedback de usuários

2026-Q1
├─ v1.1 Melhorias
│  ├─ Editor de zonas
│  ├─ Múltiplas zonas
│  ├─ Rate limiting
│  └─ HTTPS
└─ Beta testing

2026-Q2
├─ v2.0 Início
│  ├─ Múltiplas câmeras
│  ├─ Cross-cam tracking
│  └─ Webhook API

2026-Q3
├─ v2.0 Continuação
│  ├─ Análise de comportamento
│  ├─ Heatmaps
│  └─ Optimizações
└─ v2.0 Release

2026-Q4+
└─ v3.0 Features Avançadas
```

---

## 🎯 Métricas de Sucesso

### v1.1
- [ ] 95% de satisfação de usuários
- [ ] 0 bugs críticos
- [ ] Documentação 100% atualizada

### v2.0
- [ ] Suportar 10+ câmeras simultâneas
- [ ] FPS mantido > 15fps por câmera
- [ ] Rastreamento cross-cam 90% acurária

### v3.0
- [ ] App mobile com 10k+ downloads
- [ ] Integração com 5+ sistemas de acesso
- [ ] ML anomalias com 95% precisão

---

## 💰 Estimativa de Esforço

| Versão | Horas | Semanas | Pessoas |
|--------|-------|---------|---------|
| v1.1 | 60-80 | 2-3 | 1-2 |
| v2.0 | 200-250 | 6-8 | 2-3 |
| v3.0 | 300-400 | 10-12 | 3-4 |

---

## 🤝 Como Contribuir

### Reporte de Bugs
1. Descrever o problema
2. Passos para reproduzir
3. Screenshots/logs
4. Abrir issue no GitHub

### Feature Requests
1. Verificar roadmap
2. Descrever caso de uso
3. Discussão com mantenedor
4. Priorização

### Pull Requests
1. Fork do repo
2. Feature branch
3. Testes unitários
4. Documentação atualizada
5. PR review

---

## 📞 Feedback e Sugestões

Envie para: `feedback@ark-system.com` (fictício)

Ou abra uma issue em: https://github.com/jonatansouza2k11/computacional_vision/issues

---

**Roadmap versão 1.0 | Dezembro 2025**

