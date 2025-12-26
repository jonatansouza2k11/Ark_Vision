# 🎯 ARK YOLO - Sistema de Monitoramento com IA

**Real-time Person Detection + Zone Monitoring + Alert System**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![YOLOv8/v11](https://img.shields.io/badge/YOLOv8%2Fv11-Ultralytics-blue.svg)](https://github.com/ultralytics/ultralytics)
[![BoT-SORT](https://img.shields.io/badge/Tracker-BoT--SORT-orange.svg)](https://github.com/NirAharon/BoT-SORT)

---

## 📋 Visão Geral

**ARK YOLO** é um sistema de **monitoramento em tempo real** que:

✅ Detecta pessoas usando **YOLOv8/v11**  
✅ Rastreia com ID único via **BoT-SORT**  
✅ Valida se estão em **zonas seguras**  
✅ Envia **alertas automáticos** por email  
✅ Grava **vídeos de incidentes**  
✅ Mantém histórico em **banco de dados**  

### Use Cases

- 🏭 Monitorar gerentes em fábrica
- 🔒 Vigilância de áreas restritas
- 🚨 Rastreamento de equipes de resgate
- 🏢 Monitoramento de visitantes em prédios

---

## 🚀 Quick Start

### 1. Clone e Preparação

```bash
# Clone o repositório
git clone https://github.com/jonatansouza2k11/computacional_vision.git
cd computacional_vision

# Crie virtual environment
python -m venv cv_env

# Ative (Windows)
cv_env\Scripts\Activate.ps1

# Ou (Linux/Mac)
source cv_env/bin/activate
```

### 2. Instale Dependências

```bash
pip install -r requeriments.txt
```

### 3. Inicialize Banco de Dados

```bash
python -c "from database import init_db; init_db()"
```

### 4. Inicie o Sistema

```bash
python app.py
```

Acesse: **http://localhost:5000**

---

## 📚 Documentação

### 📖 Documentação Geral
- **[GUIA_RAPIDO.md](documentation/GUIA_RAPIDO.md)** - Comece em 15 minutos
- **[DOCUMENTACAO.md](documentation/DOCUMENTACAO.md)** - Referência técnica completa
- **[ARQUITETURA_TECNICA.md](documentation/ARQUITETURA_TECNICA.md)** - Deep dive para developers
- **[COMECE_AQUI.md](documentation/COMECE_AQUI.md)** - Guia por persona

### 🤖 Documentação para Agentes IA
- **[ia_documentation/00_LEIA_PRIMEIRO_CONTEXTO_IA.txt](ia_documentation/00_LEIA_PRIMEIRO_CONTEXTO_IA.txt)** - Comece aqui!
- **[ia_documentation/CONTEXTO_COMPLETO_PARA_IA.md](ia_documentation/CONTEXTO_COMPLETO_PARA_IA.md)** - Contexto em Markdown ⭐
- **[ia_documentation/CONTEXT_FOR_AI_AGENTS.txt](ia_documentation/CONTEXT_FOR_AI_AGENTS.txt)** - Contexto em TXT
- **[ia_documentation/AI_AGENT_CONTEXT.yaml](ia_documentation/AI_AGENT_CONTEXT.yaml)** - Contexto em YAML

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────┐
│     INTERFACE WEB (Flask)               │
│  - Dashboard com vídeo ao vivo          │
│  - Configurações (admin)                │
│  - Histórico de alertas                 │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   YOLO VISION SYSTEM (yolo.py)          │
│  - Detector: YOLOv8/v11                 │
│  - Tracker: BoT-SORT                    │
│  - Safe Zones (poligonais)              │
│  - Gravação de alertas                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│     DATABASE (SQLite)                   │
│  - Usuários                             │
│  - Alertas                              │
│  - Configurações                        │
│  - Logs do sistema                      │
└─────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
ARK-YOLO/
├── app.py                  # Flask server principal
├── yolo.py                 # YOLOVisionSystem (coração do sistema)
├── database.py             # SQLite operations
├── auth.py                 # Autenticação
├── zones.py                # Geometria de zonas
├── notifications.py        # Email alerts
│
├── documentation/          # 📚 Documentação geral
│   ├── DOCUMENTACAO.md
│   ├── GUIA_RAPIDO.md
│   ├── ARQUITETURA_TECNICA.md
│   └── ... (5 mais)
│
├── ia_documentation/       # 🤖 Contexto para agentes IA
│   ├── CONTEXTO_COMPLETO_PARA_IA.md
│   ├── CONTEXT_FOR_AI_AGENTS.txt
│   └── ... (5 mais)
│
├── templates/              # HTML + Jinja2
│   ├── dashboard.html
│   ├── settings.html
│   ├── login.html
│   └── ... (5 mais)
│
├── yolo_models/            # Pesos YOLO (*.pt)
│   ├── yolov8n.pt
│   ├── yolov8m.pt
│   └── ... (mais modelos)
│
├── alertas/                # Vídeos e snapshots de alerta
│
├── cv_system.db            # Database SQLite
├── requeriments.txt        # Dependências Python
└── botsort_reid.yaml       # Config do tracker
```

---

## ⚙️ Configuração

Todas as configurações são **dinâmicas** (no banco de dados):

```python
conf_thresh = 0.85              # Confiança YOLO (0-1)
target_width = 1280             # Dimensão do frame
frame_step = 1                  # Processar cada N frames
max_out_time = 5.0              # Segundos para alerta
safe_zone = "(400,100,700,600)" # Zona segura

# Email
email_user = "seu@email.com"
email_password = "app_password"  # Não sua senha do Gmail!

# Câmera
source = 0                      # 0=webcam, ou URL IP
```

Mude no `/settings` da interface web - **sem reiniciar**!

---

## 🎥 Câmeras Suportadas

```python
# Webcam local
SOURCE = 0  # ou 1, 2, etc.

# IP Camera RTSP
SOURCE = "rtsp://user:pass@192.168.1.100:554/stream"

# IP Camera HTTP
SOURCE = "http://192.168.1.100:8080/video"
```

---

## 📊 Database Schema

### `users` table
```sql
id, username, email, password_hash, role, created_at, last_login
```

### `alerts` table
```sql
id, person_id (track_id), out_time, snapshot_path, email_sent, timestamp
```

### `settings` table
```sql
key, value  -- todas as configurações dinâmicas
```

### `system_logs` table
```sql
id, action, username, reason, timestamp
```

---

## 🔐 Segurança

⚠️ **Issues Conhecidos:**
- [ ] Email credentials no banco (mova para env vars)
- [ ] SECRET_KEY no código (use env var)
- [ ] Sem HTTPS em desenvolvimento
- [ ] Sem rate limiting

---

## 🤝 Como Contribuir

1. Faça um **fork** do repositório
2. Crie uma **branch** com sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. Abra um **Pull Request**

---

## 📝 Licença

Este projeto está sob licença **MIT** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 👨‍💻 Autor

**Jonatan Souza**  
GitHub: [@jonatansouza2k11](https://github.com/jonatansouza2k11)

---

## 📞 Suporte

### Documentação
- 📚 [Documentação Técnica](documentation/)
- 🤖 [Contexto para Agentes IA](ia_documentation/)

### Issues
Para reportar bugs ou sugerir features:
- Abra uma [Issue](https://github.com/jonatansouza2k11/computacional_vision/issues)

---

## 🚀 Roadmap

- [ ] v1.1: Multi-zone analytics
- [ ] v2.0: Cloud storage (S3)
- [ ] v2.1: Advanced analytics + heatmaps
- [ ] v3.0: Mobile app
- [ ] v4.0: WebRTC streaming

---

**Última atualização:** Dezembro 2025  
**Versão:** 1.0  
**Status:** ✅ Production Ready
