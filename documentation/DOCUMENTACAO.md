# 📋 Documentação Completa - Sistema ARK de Monitoramento YOLO

**Versão:** 1.0  
**Data:** Dezembro 2025  
**Linguagem:** Python 3.10+  
**Projeto:** Sistema de Monitoramento e Detecção de Pessoas em Tempo Real

---

## 📑 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Requisitos e Instalação](#requisitos-e-instalação)
4. [Estrutura de Pastas](#estrutura-de-pastas)
5. [Componentes Principais](#componentes-principais)
6. [Configuração e Uso](#configuração-e-uso)
7. [API REST](#api-rest)
8. [Banco de Dados](#banco-de-dados)
9. [Segurança](#segurança)
10. [Troubleshooting](#troubleshooting)
11. [Desenvolvimentos Futuros](#desenvolvimentos-futuros)

---

## 🎯 Visão Geral

O **ARK** é um sistema web de monitoramento inteligente em tempo real que utiliza **YOLOv8/YOLOv11** para detectar pessoas em feeds de vídeo (webcam ou câmeras IP). O sistema:

- ✅ Detecta pessoas em vídeo ao vivo
- ✅ Rastreia múltiplas pessoas simultaneamente usando **BoT-SORT**
- ✅ Define "zonas seguras" onde as pessoas devem estar
- ✅ Gera alertas quando alguém sai da zona segura por muito tempo
- ✅ Envia notificações por email com snapshot/vídeo do incidente
- ✅ Fornece dashboard interativo com análise em tempo real
- ✅ Mantém histórico completo de alertas e logs
- ✅ Controla acesso por autenticação de usuários

### Caso de Uso Típico

Uma empresa monitora sua área de recepção para garantir que visitantes não saiam de uma zona segura sem autorização. O sistema detecta quando alguém sai desta zona e envia um alerta por email ao gerente responsável.

---

## 🏗️ Arquitetura do Sistema

O projeto segue uma arquitetura **3-camadas**:

```
┌─────────────────────────────────────────────────────┐
│        CAMADA DE APRESENTAÇÃO (app.py)              │
│  - Flask Web Server                                 │
│  - Autenticação de Usuários (Login/Register)        │
│  - Dashboard Interativo                             │
│  - API REST para Configuração                       │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│        CAMADA DE VISÃO (yolo.py)                    │
│  - Detecção com YOLO (Ultralytics)                  │
│  - Rastreamento Multi-objeto (BoT-SORT)             │
│  - Lógica de Zona Segura                            │
│  - Streaming MJPEG                                  │
│  - Gravação de Vídeo (H.264)                        │
└─────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────┐
│        CAMADA DE DADOS (database.py)                │
│  - SQLite Database                                  │
│  - Usuários e Autenticação                          │
│  - Histórico de Alertas                             │
│  - Configurações Dinâmicas                          │
│  - Logs de Sistema                                  │
└─────────────────────────────────────────────────────┘
```

### Fluxo de Processamento

```
Câmera (Webcam/IP) 
    ↓
Captura Frame
    ↓
Redimensionar (manter aspect ratio)
    ↓
YOLO Detection (inferência)
    ↓
BoT-SORT Tracking (manter IDs)
    ↓
Validar Zona Segura
    ↓
Atualizar Estado de Rastreamento
    ↓
Checar Limites de Tempo
    ↓
Disparar Alerta (se necessário)
    ↓
Enviar Email (background thread)
    ↓
Codificar Frame → MJPEG Stream
```

---

## 📦 Requisitos e Instalação

### Requisitos do Sistema

- **Python:** 3.10 ou superior
- **OS:** Windows, Linux ou macOS
- **RAM:** Mínimo 8GB (recomendado 16GB)
- **GPU:** Opcional (NVIDIA com CUDA para melhor performance)
- **Câmera:** Webcam USB ou Câmera IP (RTSP/HTTP)

### Dependências Python

```
ultralytics          # YOLO v8/v11
torch                # Deep Learning Framework
torchvision          # Computer Vision Utilities
numpy                # Processamento de Arrays
pandas               # Análise de Dados
scikit-learn         # Machine Learning Utils
flask                # Web Framework
opencv-python        # Processamento de Imagem
werkzeug             # Utilitários HTTP (segurança)
ffmpeg               # Conversão de Vídeo
```

### Instalação Passo a Passo

#### 1. Clone ou Baixe o Repositório

```bash
git clone https://github.com/jonatansouza2k11/computacional_vision.git
cd computacional_vision
```

#### 2. Crie um Ambiente Virtual

**Windows (PowerShell):**
```powershell
python -m venv cv_env
cv_env\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv cv_env
source cv_env/bin/activate
```

#### 3. Instale as Dependências

```bash
pip install -r requeriments.txt
```

#### 4. Inicialize o Banco de Dados

```bash
python -c "from database import init_db; init_db()"
```

Isso criará:
- Tabelas de usuários, alertas, configurações e logs
- Usuário admin padrão: `admin` / `admin123`

#### 5. Execute a Aplicação

```bash
python app.py
```

Acesse em: **http://localhost:5000**

---

## 📁 Estrutura de Pastas

```
computacional_vision/
├── app.py                          # Flask main app
├── yolo.py                         # Detecção e rastreamento
├── database.py                     # Gerenciamento de dados
├── auth.py                         # Decoradores de autenticação
├── zones.py                        # Gerenciamento de zonas
├── notifications.py                # Notificações por email
│
├── requeriments.txt                # Dependências Python
├── README.md                       # Documentação básica
├── DOCUMENTACAO.md                 # Esta documentação
│
├── templates/                      # Arquivos HTML (Jinja2)
│   ├── base.html                   # Template base
│   ├── base_auth.html              # Template para login/register
│   ├── login.html                  # Página de login
│   ├── register.html               # Página de registro
│   ├── dashboard.html              # Dashboard principal
│   ├── settings.html               # Configurações (admin)
│   ├── users.html                  # Gerenciamento de usuários
│   ├── logs.html                   # Histórico de alertas
│   ├── diagnostics.html            # Diagnóstico do sistema
│   └── sidebar.html                # Menu lateral
│
├── yolo_models/                    # Modelos pré-treinados
│   ├── yolov8n.pt                  # YOLO v8 Nano (rápido)
│   ├── yolov8s.pt                  # YOLO v8 Small
│   ├── yolov8m.pt                  # YOLO v8 Medium
│   ├── yolov8l.pt                  # YOLO v8 Large
│   ├── yolov8x.pt                  # YOLO v8 Extra Large
│   ├── yolov11n.pt                 # YOLO v11 Nano
│   ├── yolov11s.pt                 # YOLO v11 Small
│   ├── yolov11m.pt                 # YOLO v11 Medium
│   ├── yolov11l.pt                 # YOLO v11 Large
│   ├── yolov11x.pt                 # YOLO v11 Extra Large
│   └── yolo11l.torchscript         # Formato TorchScript otimizado
│
├── alertas/                        # Armazena snapshots e vídeos
│   ├── alert_*.jpg                 # Snapshots de alertas
│   └── video_*.mp4                 # Vídeos de incidentes
│
├── cv_env/                         # Ambiente Virtual Python
│   ├── Scripts/ (Windows)
│   ├── bin/ (Linux/macOS)
│   └── Lib/ (site-packages)
│
├── cv_system.db                    # Banco de dados SQLite
├── botsort_reid.yaml               # Configuração do BoT-SORT
├── .github/
│   └── copilot-instructions.md     # Instruções para IA
└── .gitignore                      # Arquivos ignorados por Git
```

---

## 🔧 Componentes Principais

### 1. **app.py** - Servidor Flask (151 linhas)

**Responsabilidade:** Camada de apresentação web

**Principais Funções:**

| Função | Método | Descrição |
|--------|--------|-----------|
| `/` | GET | Redireciona para dashboard ou login |
| `/login` | GET/POST | Autenticação de usuários |
| `/register` | GET/POST | Registro de novos usuários |
| `/logout` | GET | Encerrar sessão |
| `/dashboard` | GET | Dashboard principal (mapa interativo) |
| `/video_feed` | GET | Stream MJPEG em tempo real |
| `/start_stream` | POST | Inicia captura de vídeo |
| `/stop_stream` | POST | Para captura de vídeo |
| `/toggle_camera` | POST | Pausa/retoma stream |
| `/logs` | GET | Histórico de alertas |
| `/users` | GET | Gerenciar usuários (admin) |
| `/settings` | GET/POST | Configurações de detecção (admin) |
| `/api/stats` | GET | Dados em tempo real para dashboard |
| `/api/safe_zone` | POST | Editar zona segura |
| `/diagnostics` | GET | Diagnóstico do sistema (admin) |

**Variáveis de Configuração:**

```python
app.config["SECRET_KEY"]  # Chave secreta da sessão Flask
```

**Estrutura de Sessão:**

```python
session['user'] = {
    'username': str,
    'email': str,
    'role': 'admin' | 'user',
    'id': int
}
```

---

### 2. **yolo.py** - Sistema de Visão (810 linhas)

**Responsabilidade:** Detecção, rastreamento e processamento de vídeo

**Classe Principal: `YOLOVisionSystem`**

#### Atributos Principais

```python
self.source              # Fonte de vídeo (webcam ID ou URL)
self.model_path         # Caminho para arquivo .pt do YOLO
self.model              # Instância carregada do YOLO
self.track_state        # Dict: track_id → estado da pessoa
self.paused             # Booleano: stream pausado?
self.stream_active      # Booleano: stream ativo?
self.current_fps        # FPS atual do processamento
self.cap                # Objeto VideoCapture do OpenCV
```

#### Estado de Rastreamento por Pessoa

```python
track_state[track_id] = {
    "last_seen": float,           # Timestamp último quadro
    "status": "IN" | "OUT",       # Dentro ou fora da zona
    "out_time": float,            # Segundos fora da zona
    "video_writer": VideoWriter,  # Para gravação
    "video_path": str,            # Caminho do vídeo
    "recording": bool,            # Gravando?
    "buffer": deque,              # Buffer circular de frames
    "zone_idx": int               # Índice da zona (-1 = nenhuma)
}
```

#### Métodos Principais

| Método | Descrição |
|--------|-----------|
| `__init__(source, model_path)` | Inicializa sistema e carrega modelo |
| `get_config()` | Retorna configurações do banco de dados |
| `start_live()` | Inicia captura de vídeo |
| `stop_live()` | Para captura de vídeo |
| `toggle_pause()` | Pausa/retoma stream |
| `generate_frames()` | Generator para stream MJPEG |
| `process_detection(results, frame)` | Processa resultados do YOLO |
| `start_recording(track_id, frame)` | Inicia gravação de vídeo |
| `stop_recording(track_id, convert)` | Para gravação e converte |
| `get_zone_index(x, y, zones, w, h)` | Detecta zona do ponto |
| `draw_safe_zone(frame, zones)` | Desenha zonas no frame |
| `resize_keep_width(frame, width)` | Redimensiona mantendo aspect ratio |

#### Algoritmo de Rastreamento

O sistema usa **BoT-SORT** (Bag-of-Tricks SORT):

1. **Detecção:** YOLO encontra bounding boxes de pessoas
2. **Associação:** BoT-SORT associa boxes de frames consecutivos a IDs únicos
3. **Estado:** Para cada ID, mantém histórico de posição e status
4. **Zona:** Verifica se centro da bbox está na zona segura
5. **Alerta:** Se `out_time > max_out_time`, dispara alerta
6. **Email:** Envia notificação em thread separada

#### Configurações Dinâmicas Carregadas do DB

| Setting | Padrão | Descrição |
|---------|--------|-----------|
| `conf_thresh` | 0.78 | Confiança mínima de detecção |
| `target_width` | 960 | Largura do frame redimensionado |
| `frame_step` | 2 | Processar cada N-ésimo frame |
| `max_out_time` | 30 | Segundos máximos fora antes de alerta |
| `email_cooldown` | 300 | Segundos entre emails (mesma pessoa) |
| `safe_zone` | "(400,100,700,600)" | Zona segura (tupla ou JSON) |

---

### 3. **database.py** - Gerenciamento de Dados (148 linhas)

**Responsabilidade:** Persistência de dados em SQLite

#### Tabelas

##### Tabela: `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
)
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | ID único do usuário |
| `username` | TEXT | Nome de login (único) |
| `email` | TEXT | Email (único) |
| `password_hash` | TEXT | Senha criptografada (bcrypt via werkzeug) |
| `role` | TEXT | 'admin' ou 'user' |
| `created_at` | TIMESTAMP | Data de criação |
| `last_login` | TIMESTAMP | Último acesso |

##### Tabela: `alerts`

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    out_time REAL NOT NULL,
    snapshot_path TEXT,
    email_sent INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | ID único do alerta |
| `person_id` | INTEGER | ID do rastreamento (track_id) |
| `out_time` | REAL | Segundos que a pessoa ficou fora |
| `snapshot_path` | TEXT | Caminho para arquivo JPEG/vídeo |
| `email_sent` | INTEGER | 1 = email enviado, 0 = não |
| `timestamp` | TIMESTAMP | Quando o alerta foi gerado |

##### Tabela: `settings`

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

Armazena todos os parâmetros configuráveis do sistema como pares chave-valor.

**Exemplo de valores:**

```
conf_thresh          → "0.78"
target_width         → "960"
max_out_time         → "30"
safe_zone            → "(400, 100, 700, 600)"
email_user           → "seu_email@gmail.com"
email_password       → "sua_senha_app"
```

##### Tabela: `system_logs`

```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    username TEXT NOT NULL,
    reason TEXT,
    email_sent INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Registra ações do sistema: INICIAR, PAUSAR, RETOMAR, PARAR.

#### Funções Principais

| Função | Descrição |
|--------|-----------|
| `init_db()` | Cria tabelas e dados padrão |
| `create_user(username, email, password)` | Registra novo usuário |
| `verify_user(username, password)` | Autentica usuário |
| `update_last_login(username)` | Atualiza timestamp |
| `get_setting(key, default)` | Obtém configuração |
| `set_setting(key, value)` | Salva configuração |
| `log_alert(person_id, out_time, snapshot_path)` | Registra alerta |
| `get_recent_alerts(limit)` | Últimos alertas |
| `delete_alert(person_id, timestamp)` | Remove alerta |
| `log_system_action(action, username, reason)` | Registra log |
| `get_system_logs(limit)` | Últimos logs |

---

### 4. **auth.py** - Autenticação (36 linhas)

**Responsabilidade:** Decoradores para controlar acesso a rotas

#### Decoradores

```python
@login_required      # Apenas usuários logados
@admin_required      # Apenas administradores
```

**Uso:**

```python
@app.route('/dashboard')
@login_required
def dashboard():
    # Código aqui só executa se usuário está logado
    ...

@app.route('/settings', methods=['POST'])
@admin_required
def settings():
    # Código aqui só executa se usuário é admin
    ...
```

---

### 5. **zones.py** - Gerenciamento de Zonas (143 linhas)

**Responsabilidade:** Definir e validar zonas poligonais

#### Classe: `ZoneManager`

```python
class ZoneManager:
    def __init__(self, target_width: int = 1200):
        self.target_width = target_width
        self.zones = {
            'entrada': np.array([[50,600], [1150,600], ...]),
            'corredor_esq': np.array([...]),
            'elevador_1': np.array([...]),
            # ... mais zonas
        }
```

#### Métodos

| Método | Descrição |
|--------|-----------|
| `draw_zones(frame)` | Desenha todos os polígonos no frame |
| `point_zone(xc, yc)` | Retorna nome da zona ou None |

**Zona Segura Atualmente:** Retângulo simples (x1, y1, x2, y2)

**Extensão Futura:** Polígonos customizáveis via interface web

---

### 6. **notifications.py** - Notificações por Email (112 linhas)

**Responsabilidade:** Enviar alertas por email com anexos

#### Classe: `Notifier`

```python
notifier = Notifier(
    email_user="seu_email@gmail.com",
    email_app_password="sua_senha_app",  # não a senha da conta!
    email_to="admin@empresa.com"
)
```

#### Métodos

| Método | Descrição |
|--------|-----------|
| `send_email(subject, body, to, attachment)` | Envio síncrono |
| `send_email_background(...)` | Envio em thread (não bloqueia) |

**Exemplo de Uso:**

```python
notifier.send_email_background(
    subject="⚠️ Alerta: Pessoa Fora da Zona Segura",
    body=f"Track ID {track_id} ficou fora por {out_time:.1f}s",
    attachment_path="alertas/alert_123.jpg"
)
```

**Configuração Gmail:**

1. Ativar autenticação em 2 fatores em accounts.google.com
2. Gerar "Senha de Aplicativo" em accounts.google.com/apppasswords
3. Usar essa senha em vez da senha da conta
4. Salvar em settings do banco: `email_user` e `email_password`

---

## ⚙️ Configuração e Uso

### Inicialização

**Arquivo: `app.py` - Linha ~167**

```python
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",      # Acessível de qualquer IP
        port=5000,           # Porta do servidor
        debug=False,         # Desabilitar em produção
        threaded=True        # Suportar requisições concorrentes
    )
```

### Primeira Execução

```bash
# 1. Ativar ambiente virtual
cv_env\Scripts\Activate.ps1

# 2. Iniciar app
python app.py

# 3. Acessar http://localhost:5000
# 4. Login: admin / admin123
# 5. Configurar câmera e zona segura em Settings
```

### Seleção de Câmera

**Em Settings > Fonte de vídeo:**

| Tipo | Valor | Exemplo |
|------|-------|---------|
| Webcam integrada | `0` | Built-in camera |
| Webcam USB | `1`, `2`, etc | External USB camera |
| IP Camera (RTSP) | `rtsp://url` | `rtsp://admin:pass@192.168.1.100:554/stream` |
| IP Camera (HTTP) | `http://url` | `http://192.168.1.100:8080/video` |

**Recomendação:** Teste com `test_cam.py` antes de usar na aplicação

```bash
python test_cam.py
```

### Seleção de Modelo YOLO

**Em Settings > Detecção YOLO > Modelo:**

| Modelo | Velocidade | Acurácia | Uso |
|--------|-----------|----------|-----|
| yolov8n | Rápido ⚡ | Boa | Produção (tempo real) |
| yolov8s | Médio | Melhor | Balanço |
| yolov8m | Lento | Excelente | Análise |
| yolov8l | Muito Lento | Excelente | Pesquisa |
| yolov11n | Rápido ⚡ | Ótima | Novo modelo |

**Padrão:** `yolov8n.pt` (equilibrado)

### Parâmetros Principais

#### 🎯 Detecção YOLO

**Confidence Threshold (conf_thresh):**
- Intervalo: 0.0 - 1.0
- Padrão: 0.78
- Maior = menos detecções, menos falsos positivos
- Menor = mais detecções, mais ruído

#### ⚡ Performance

**Frame Step (frame_step):**
- Padrão: 2
- Processa cada 2º frame (economiza CPU)
- Aumentar = mais rápido mas perde detecções rápidas

**Target Width (target_width):**
- Padrão: 960px
- Maior = mais detalhes mas mais lento
- Menor = mais rápido mas menos preciso

#### ⏱️ Alertas

**Max Out Time (max_out_time):**
- Padrão: 30 segundos
- Tempo máximo que pessoa pode ficar fora

**Email Cooldown (email_cooldown):**
- Padrão: 300 segundos
- Evita spam: só envia 1 email a cada 5 minutos por pessoa

#### 📹 Zona Segura

**Formatos Aceitos:**

1. **Tupla (retângulo):** `(x1, y1, x2, y2)`
   ```
   (400, 100, 700, 600)
   ```

2. **JSON (polígono):** `[[x,y], [x,y], ...]`
   ```json
   [[400, 100], [700, 100], [700, 600], [400, 600]]
   ```

**Obter Coordenadas:**
1. Ir ao Dashboard
2. Clicar em "Editar Zona Segura"
3. Desenhar retângulo na imagem
4. Coordenadas aparecem automaticamente

---

## 📡 API REST

### Autenticação

Todas as rotas (exceto `/login` e `/register`) requerem sessão ativa:

```python
@login_required  # Verifica session['user']
```

### Endpoints

#### **GET `/api/stats`** - Dados em Tempo Real

**Resposta:**

```json
{
  "fps": 28.5,
  "people_count": 3,
  "alerts_count": 1,
  "system_status": "RUNNING",
  "model_name": "yolov8n.pt",
  "video_source_label": "Webcam 0",
  "recent_alerts": [
    {
      "id": 1,
      "person_id": 5,
      "out_time": 45.2,
      "timestamp": "2025-12-26 14:30:00",
      "snapshot_path": "alertas/alert_1.jpg"
    }
  ],
  "system_logs": [
    {
      "id": 1,
      "action": "START",
      "username": "admin",
      "timestamp": "2025-12-26 14:00:00"
    }
  ],
  "safe_zone": [[400, 100], [700, 100], [700, 600], [400, 600]]
}
```

#### **POST `/api/safe_zone`** - Atualizar Zona Segura

**Body (JSON):**

```json
{
  "zone_data": [[400, 100], [700, 100], [700, 600], [400, 600]]
}
```

**Resposta:**

```json
{
  "success": true,
  "message": "Zona segura atualizada"
}
```

#### **POST `/start_stream`** - Iniciar Captura

**Body:**

```json
{
  "source": "0",
  "model": "yolov8n.pt"
}
```

#### **POST `/stop_stream`** - Parar Captura

#### **POST `/toggle_camera`** - Pausar/Retomar

---

## 🗄️ Banco de Dados

### Arquivo

```
cv_system.db  (SQLite)
```

### Inicialização

```python
from database import init_db
init_db()
```

### Backup e Recuperação

**Backup:**
```bash
# Windows
copy cv_system.db cv_system.db.backup

# Linux
cp cv_system.db cv_system.db.backup
```

**Restaurar:**
```bash
copy cv_system.db.backup cv_system.db
```

### Consultas Úteis

**Listar todos os usuários:**
```sql
SELECT id, username, email, role, created_at FROM users;
```

**Últimos 10 alertas:**
```sql
SELECT person_id, out_time, timestamp FROM alerts ORDER BY timestamp DESC LIMIT 10;
```

**Configurações atuais:**
```sql
SELECT * FROM settings;
```

**Ver logs de sistema:**
```sql
SELECT action, username, timestamp FROM system_logs ORDER BY timestamp DESC LIMIT 20;
```

---

## 🔒 Segurança

### Implementado ✅

- ✅ Senhas criptografadas com bcrypt (via werkzeug)
- ✅ Sessão Flask com SECRET_KEY
- ✅ Autenticação obrigatória para rotas protegidas
- ✅ Validação de roles (admin vs user)
- ✅ Email via SMTP seguro (TLS)

### Recomendações de Segurança ⚠️

#### 1. **Mude a Chave Secreta**

**Problema:** Chave padrão é pública no código

**Solução:** Use variável de ambiente

```bash
# Windows (PowerShell)
$env:ARK_SECRET_KEY = "sua_chave_super_segura_aqui_2025"
python app.py
```

**Ou edite em `app.py`:**

```python
import os
app.config["SECRET_KEY"] = os.environ.get("ARK_SECRET_KEY")
```

#### 2. **Credenciais de Email**

**Problema:** Email/senha podem estar hardcoded

**Solução:** Use arquivo `.env`

```bash
pip install python-dotenv
```

**Arquivo `.env`:**

```
EMAIL_USER=seu_email@gmail.com
EMAIL_PASSWORD=sua_senha_app
EMAIL_SMTP=smtp.gmail.com
EMAIL_PORT=587
```

**Em `yolo.py`:**

```python
from dotenv import load_dotenv
load_dotenv()

email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
```

#### 3. **HTTPS em Produção**

**Desenvolvimento:** HTTP é ok  
**Produção:** Configure HTTPS com certificado SSL

```bash
pip install pyopenssl
```

```python
app.run(ssl_context='adhoc')  # Requer certificado
```

#### 4. **Acesso CORS**

Se frontend estiver em outro domínio:

```python
pip install flask-cors
from flask_cors import CORS
CORS(app, origins=["https://seu_dominio.com"])
```

#### 5. **Rate Limiting**

Evite brute force no login:

```python
pip install flask-limiter
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    ...
```

---

## 🚨 Troubleshooting

### Problema: "Webcam não encontrada"

**Solução:**

```bash
# Verificar câmeras disponíveis
python test_cam.py

# Testar com ID diferente
# Tente 0, 1, 2, etc em Settings
```

### Problema: "YOLO model not found"

```bash
# Verificar se os arquivos .pt existem
dir yolo_models

# Se não existem, descarregar:
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Problema: "CUDA out of memory"

**Solução:** Use modelo menor ou desabilite GPU

```python
# Em yolo.py
self.model = YOLO(model_path, device='cpu')  # Força CPU
```

### Problema: "Email não envia"

**Checklist:**

1. ✅ Gmail com 2FA ativado
2. ✅ "Senha de Aplicativo" gerada em accounts.google.com/apppasswords
3. ✅ Credenciais corretas em Settings
4. ✅ Conexão de internet ativa
5. ✅ Firewall não bloqueia porta 587

**Debug:**

```python
# Em notifications.py, descomente logs
print(f"[Notifier] Enviando para {to_addr}...")
```

### Problema: "Muitos alertas (spam)"

**Solução:** Aumentar `email_cooldown` em Settings

```
Padrão: 300s (5 min)
Aumentar para: 600s (10 min) ou mais
```

### Problema: "FPS muito baixo"

**Checklist:**

1. Reduzir `target_width` (default 960)
2. Aumentar `frame_step` (processar menos frames)
3. Usar modelo menor (yolov8n em vez de yolov8l)
4. Usar GPU se disponível
5. Fechar outras aplicações pesadas

---

## 📊 Fluxo de Um Alerta

```
Pessoa entra no quadro
       ↓
YOLO detecta (conf > 0.78)
       ↓
BoT-SORT atribui track_id
       ↓
Verifica: está na zona segura?
       ↓
SIM: status = "IN", out_time = 0
NÃO: status = "OUT", incrementa out_time
       ↓
out_time > max_out_time (30s)?
       ↓
SIM: Checar email_cooldown
       ↓
Cooldown passou (300s desde último email)?
       ↓
SIM: Dispara alerta!
  1. Registra em database.alerts
  2. Gera screenshot do frame
  3. Inicia gravação de vídeo
       ↓
Email enviado (background thread)
  1. Corpo com detalhes
  2. Anexo: screenshot ou vídeo
       ↓
Salva em alertas/
```

---

## 🔮 Desenvolvimentos Futuros

### Curto Prazo (v1.1)

- [ ] Interface gráfica para desenhar zona poligonal customizada
- [ ] Suporte para múltiplas zonas com nomes
- [ ] Reuso de zona por modelo (template)
- [ ] Configuração HTTPS
- [ ] Rate limiting de login

### Médio Prazo (v2.0)

- [ ] Integração com Google Drive para backup de vídeos
- [ ] Webhook para integração com sistemas externos
- [ ] Detecção de comportamentos (corrida, queda, etc)
- [ ] Heatmap de movimentação
- [ ] Análise de padrões (hora de pico, etc)

### Longo Prazo (v3.0)

- [ ] Múltiplas câmeras simultâneas
- [ ] Rastreamento cross-câmera
- [ ] Dashboard em tempo real para múltiplas locais
- [ ] ML para detecção de anomalias
- [ ] App mobile (iOS/Android)
- [ ] Integração com sistemas de acesso

---

## 📚 Referências

### Documentação Oficial

- **YOLO Ultralytics:** https://docs.ultralytics.com
- **Flask:** https://flask.palletsprojects.com
- **OpenCV:** https://docs.opencv.org
- **SQLite:** https://www.sqlite.org/docs.html

### Papers e Artigos

- **YOLOv8:** Ultralytics YOLOv8 (2023)
- **BoT-SORT:** Bag-of-Tricks SORT (2023)
- **ByteTrack:** Multi-Object Tracking by Associating Every Detection Box (2021)

---

## 📞 Suporte e Contribuição

**Autor:** Jonathan Souza (@jonatansouza2k11)  
**Repositório:** https://github.com/jonatansouza2k11/computacional_vision  
**License:** MIT (presumido)

### Como Contribuir

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona minha feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

---

## 📝 Changelog

### v1.0 (Dezembro 2025)

- ✅ Detecção com YOLO v8/v11
- ✅ Rastreamento multi-objeto com BoT-SORT
- ✅ Dashboard web interativo
- ✅ Alertas por email com anexos
- ✅ Histórico de eventos
- ✅ Gerenciamento de usuários
- ✅ Configuração dinâmica (sem restart)

---

## 📋 Checklist de Implantação

Para colocar o sistema em produção:

- [ ] Alterar SECRET_KEY (não use padrão)
- [ ] Configurar credenciais de email
- [ ] Testar câmera específica
- [ ] Validar detecção com YOLO
- [ ] Definir zona segura correta
- [ ] Testar envio de email
- [ ] Configurar backup do banco de dados
- [ ] Limpar logs antigos periodicamente
- [ ] Monitorar performance (FPS)
- [ ] Documentar localização das câmeras
- [ ] Treinar usuários admin
- [ ] Configurar HTTPS se necessário
- [ ] Testar fail-over de câmera

---

**Fim da Documentação**

Para dúvidas ou sugestões, consulte o arquivo `.github/copilot-instructions.md` para contexto técnico detalhado.

