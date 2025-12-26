# 🔐 Configuração de Variáveis de Ambiente

> **⚠️ IMPORTANTE**: O arquivo `.env` contém dados sensíveis (senhas, chaves) e NUNCA deve ser commitado no GitHub. Está protegido pelo `.gitignore`.

## 📋 Quick Start

```bash
# 1. Copie o template
cp .env.example .env

# 2. Configure seus valores reais no arquivo .env
# (veja as instruções abaixo)

# 3. Instale a dependência python-dotenv
pip install python-dotenv

# 4. Teste a configuração
python config.py
```

---

## 🔧 Configuração Passo a Passo

### 1. **FLASK_SECRET_KEY** (Crítico em Produção)

Gere uma chave segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Exemplo de saída:
```
a3f8c9e2b1d4f6a7c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
```

Cole no `.env`:
```env
FLASK_SECRET_KEY=a3f8c9e2b1d4f6a7c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
```

---

### 2. **EMAIL_SENDER & EMAIL_APP_PASSWORD** (Para Alertas)

#### Opção A: Gmail (Recomendado)

1. **Acesse sua conta Gmail:**
   - Vá para https://myaccount.google.com/apppasswords
   - Ou: Settings → Security → App passwords

2. **Gere uma App Password:**
   - Selecione: Mail + Windows Computer
   - Google gerará uma senha de 16 caracteres

3. **Configure no `.env`:**
   ```env
   EMAIL_SENDER=seu-email@gmail.com
   EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

#### Opção B: Outro provedor SMTP

Atualize também:
```env
SMTP_SERVER=smtp.seuservidor.com
SMTP_PORT=587
EMAIL_SENDER=seu-email@seuservidor.com
EMAIL_APP_PASSWORD=sua-senha-aqui
```

---

### 3. **DATABASE_PATH** (Onde guardar o banco)

Padrão (recomendado):
```env
DATABASE_PATH=cv_system.db
```

Ou caminho customizado:
```env
DATABASE_PATH=/opt/ark_yolo/data/cv_system.db
```

---

### 4. **YOLO_MODEL_PATH** (Qual modelo usar)

Modelos disponíveis:
```env
# Rápido (recomendado para CPU)
YOLO_MODEL_PATH=yolo_models/yolov8n.pt

# Balanceado (recomendado para GPU)
YOLO_MODEL_PATH=yolo_models/yolov8m.pt

# Preciso mas lento
YOLO_MODEL_PATH=yolo_models/yolov8l.pt

# Últimos modelos (experimental)
YOLO_MODEL_PATH=yolo_models/yolo11n.pt
```

---

### 5. **VIDEO_SOURCE** (De onde capturar vídeo)

**Webcam:**
```env
VIDEO_SOURCE=0
```

**Câmera IP (RTSP):**
```env
VIDEO_SOURCE=rtsp://user:password@192.168.1.100:554/stream
```

**Câmera IP (HTTP):**
```env
VIDEO_SOURCE=http://192.168.1.100:8080/video
```

**Arquivo de vídeo (para teste):**
```env
VIDEO_SOURCE=/caminho/para/video.mp4
```

---

### 6. **SAFE_ZONE** (Zona segura de monitoramento)

Define o retângulo seguro em coordenadas do frame redimensionado.

**Formato:** `(x1,y1,x2,y2)` sem espaços

Exemplo:
```env
# Zona de (400,100) até (700,600) em frame 960x720
SAFE_ZONE=(400,100,700,600)
```

**Como descobrir as coordenadas:**
1. Acesse o dashboard: `http://localhost:5000/dashboard`
2. A zona segura é mostrada como retângulo verde no vídeo
3. Use ferramentas de screenshot para medir pixels (canto superior-esquerdo = 0,0)

---

### 7. **PERFORMANCE** (Otimizar velocidade)

```env
# Use GPU (10x mais rápido!)
USE_GPU=true

# Tamanho de redimensionamento (lower = faster)
YOLO_TARGET_WIDTH=960

# Processar cada N-ésimo frame (higher = faster)
YOLO_FRAME_STEP=2

# Confiança mínima (higher = menos falsos positivos)
YOLO_CONF_THRESHOLD=0.78
```

**Recomendações:**
- **CPU fraco**: `TARGET_WIDTH=480, FRAME_STEP=5`
- **GPU moderna**: `TARGET_WIDTH=960, FRAME_STEP=1`
- **Produção rápida**: `TARGET_WIDTH=640, FRAME_STEP=2`

---

### 8. **DESENVOLVIMENTO vs PRODUÇÃO**

**Para desenvolvimento:**
```env
FLASK_ENV=development
FLASK_DEBUG=true
DEBUG_MODE=false
```

**Para produção:**
```env
FLASK_ENV=production
FLASK_DEBUG=false
DEBUG_MODE=false
VERBOSE_ERRORS=false
```

---

## ✅ Validar Configuração

```bash
# Testa se todas as configs estão OK
python config.py
```

Saída esperada:
```
============================================================
🔧 ARK YOLO Configuration Summary
============================================================
Environment: DEVELOPMENT
Debug: false
Flask Port: 5000
Database: cv_system.db
YOLO Model: yolo_models/yolov8n.pt
Confidence Threshold: 0.78
Target Width: 960px
Frame Step: 2
Safe Zone: (400, 100, 700, 600)
Max Out Time: 30s
Email Configured: ✅
Use GPU: true
============================================================

✅ Configuração válida!
```

---

## 🐛 Troubleshooting

### Erro: `Import "dotenv" could not be resolved`
```bash
pip install python-dotenv
```

### Erro: `Modelo YOLO não encontrado`
- Verifique o caminho em `YOLO_MODEL_PATH`
- Ou baixe o modelo: `python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"`

### Emails não enviando
1. **Confirmou App Password?** (não é senha regular)
   - https://myaccount.google.com/apppasswords
2. **Removeu espaços da senha?** `EMAIL_APP_PASSWORD=xxxxxxxxxx` (sem espaços)
3. **Testou com:**
   ```bash
   python -c "from notifications import Notifier; Notifier().send_email('test@example.com', 'Test', 'Test message')"
   ```

### Câmera IP não conecta
- **Verifique ping:** `ping 192.168.1.100`
- **Teste URL em navegador:** Coloque a URL do `VIDEO_SOURCE` no navegador
- **Credenciais:** Certifique-se que estão na URL

---

## 📁 Estrutura de Arquivos

```
projeto/
├── .env                 ← Seu arquivo real (NUNCA commite!)
├── .env.example         ← Template de exemplo (seguro commitar)
├── config.py            ← Carrega as variáveis
├── app.py               ← Usa config.FLASK_SECRET_KEY
├── yolo.py              ← Usa config.VIDEO_SOURCE, etc
└── requeriments.txt     ← Inclui python-dotenv
```

---

## 🔒 Segurança

### ✅ Fazendo Certo

```env
# Em produção, use valores aleatórios
FLASK_SECRET_KEY=a3f8c9e2b1d4f6a7c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b

# Use App Password (não senha regular)
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Defina ambiente
FLASK_ENV=production
```

### ❌ NÃO Faça

```env
# ❌ NUNCA commite este arquivo
.env

# ❌ Não use valores genéricos em produção
FLASK_SECRET_KEY=dev-key

# ❌ Não hardcode senhas no código
# Use config.EMAIL_APP_PASSWORD em vez disso
```

---

## 📚 Referência Rápida

| Variável | Exemplo | Crítico |
|----------|---------|---------|
| `FLASK_SECRET_KEY` | `a3f8c9...` | ✅ Sim (produção) |
| `EMAIL_APP_PASSWORD` | `xxxx xxxx xxxx xxxx` | ✅ Sim (alertas) |
| `DATABASE_PATH` | `cv_system.db` | ⚠️ Recomendado |
| `VIDEO_SOURCE` | `0` ou `rtsp://...` | ⚠️ Recomendado |
| `SAFE_ZONE` | `(400,100,700,600)` | ⚠️ Recomendado |
| `USE_GPU` | `true` | ⚠️ Performance |

---

## 🚀 Próximos Passos

1. **Configure seu `.env`** com os valores reais
2. **Instale dependências:** `pip install -r requeriments.txt`
3. **Valide configuração:** `python config.py`
4. **Inicie a aplicação:** `python app.py`
5. **Acesse:** http://localhost:5000

---

Dúvidas? Veja o arquivo `.env.example` ou leia `config.py` para mais detalhes!
