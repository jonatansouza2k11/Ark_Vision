# 🔐 Integração do Sistema de Configuração

## O que foi feito

Você agora tem um **sistema completo de variáveis de ambiente** para guardar dados sensíveis:

### ✅ Arquivos Criados/Modificados

| Arquivo | O quê | Status |
|---------|-------|--------|
| `.env.example` | Template de configuração (seguro commitar) | ✅ Criado |
| `.env` | Suas configurações reais (ignorado por git) | ✅ Criado |
| `config.py` | Carregador de variáveis de ambiente | ✅ Criado |
| `SETUP_ENV.md` | Guia completo de setup | ✅ Criado |
| `requeriments.txt` | Adicionado `python-dotenv` | ✅ Atualizado |
| `app.py` | Usa `config.FLASK_SECRET_KEY` | ✅ Atualizado |

---

## 🚀 Como Usar

### 1. **Configure seu `.env`**

```bash
# Copie o template
cp .env.example .env

# Edite com seus valores reais
# Abra em seu editor preferido e preencha:
# - FLASK_SECRET_KEY (gere uma chave segura)
# - EMAIL_SENDER e EMAIL_APP_PASSWORD (para alertas)
# - VIDEO_SOURCE (webcam ou câmera IP)
# - SAFE_ZONE (coordenadas da zona segura)
```

### 2. **Instale a dependência**

```bash
pip install python-dotenv
# Ou
pip install -r requeriments.txt
```

### 3. **Valide a configuração**

```bash
python config.py
```

Deve exibir:
```
============================================================
🔧 ARK YOLO Configuration Summary
============================================================
Environment: development
Debug: false
...
✅ Configuração válida!
```

### 4. **Inicie a aplicação**

```bash
python app.py
```

Agora automaticamente:
- ✅ Carrega `.env`
- ✅ Valida configurações
- ✅ Exibe resumo de startup
- ✅ Reclama se faltar algo crítico

---

## 📚 Arquivos que AINDA PRECISAM SER ATUALIZADOS

Para integração completa, estes arquivos deveriam usar `config.py`:

### 1. **yolo.py** (Prioridade: ALTA)

```python
# ANTES (hardcoded)
SOURCE = 0
MODEL_PATH = "yolo_models/yolov8n.pt"
CONF_THRESHOLD = 0.78
TARGET_WIDTH = 960

# DEPOIS (do config.py)
import config

SOURCE = config.VIDEO_SOURCE
MODEL_PATH = config.YOLO_MODEL_PATH
CONF_THRESHOLD = config.YOLO_CONF_THRESHOLD
TARGET_WIDTH = config.YOLO_TARGET_WIDTH
```

### 2. **notifications.py** (Prioridade: ALTA)

```python
# ANTES (hardcoded)
sender = "seu-email@gmail.com"
password = "sua-senha-aqui"
smtp_server = "smtp.gmail.com"

# DEPOIS (do config.py)
import config

sender = config.EMAIL_SENDER
password = config.EMAIL_APP_PASSWORD
smtp_server = config.SMTP_SERVER
smtp_port = config.SMTP_PORT
```

### 3. **database.py** (Prioridade: MÉDIA)

```python
# DEPOIS (opcional, mas recomendado)
import config

DB_PATH = config.DATABASE_PATH
PASSWORD_HASH_ROUNDS = config.PASSWORD_HASH_ROUNDS
```

---

## 🔒 Segurança - O que melhorou

### ❌ ANTES
```python
# app.py - INSEGURO!
app.config["SECRET_KEY"] = "sua_chave_secreta_super_segura_aqui_2025"

# yolo.py - INSEGURO!
sender_email = "seu-email@gmail.com"
sender_password = "sua-senha-de-app-aqui"

# Todos podem ver as credenciais no código!
```

### ✅ DEPOIS
```python
# app.py - SEGURO!
app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY  # Do .env

# yolo.py - SEGURO! (quando atualizar)
sender_email = config.EMAIL_SENDER  # Do .env
sender_password = config.EMAIL_APP_PASSWORD  # Do .env

# Credenciais NUNCA no código, apenas em .env (ignorado)
```

---

## 📋 Próximos Passos (Recomendados)

### Step 1: Atualizar `yolo.py`

```bash
# Edite yolo.py linha ~16-45
# Substitua valores hardcoded por config.VARIAVEL
```

**Mudanças necessárias:**
```python
# Adicione no topo
import config

# Substitua estas linhas:
SOURCE = config.VIDEO_SOURCE
MODEL_PATH = config.YOLO_MODEL_PATH
CONF_THRESHOLD = config.YOLO_CONF_THRESHOLD
TARGET_WIDTH = config.YOLO_TARGET_WIDTH
FRAME_STEP = config.YOLO_FRAME_STEP
MAX_OUT_TIME = config.MAX_OUT_TIME
```

### Step 2: Atualizar `notifications.py`

```bash
# Edite notifications.py linhas ~30-50
# Substitua credenciais hardcoded
```

**Mudanças necessárias:**
```python
# Adicione no topo
import config

# Na classe Notifier.__init__:
self.sender_email = config.EMAIL_SENDER
self.sender_password = config.EMAIL_APP_PASSWORD
self.smtp_server = config.SMTP_SERVER
self.smtp_port = config.SMTP_PORT
self.recipients = config.EMAIL_RECIPIENTS_LIST
```

### Step 3: Atualizar `database.py`

```bash
# Edite database.py linha ~1
```

**Mudanças necessárias:**
```python
# Adicione no topo
import config

# Use em consultas relevantes:
DB_PATH = config.DATABASE_PATH
```

---

## ✨ Benefícios Finais

Com essas atualizações você terá:

| Aspecto | Status Atual | Após Atualizar |
|--------|-------------|------------------|
| Credenciais no código | ❌ Sim (inseguro!) | ✅ Não (no .env) |
| Config em múltiplos arquivos | ❌ Espalhado | ✅ Centralizado |
| Fácil mudar sem código | ❌ Não | ✅ Sim (só .env) |
| Suporta múltiplos ambientes | ❌ Não | ✅ Sim |
| CI/CD pronto | ❌ Não | ✅ Sim |

---

## 🐛 Troubleshooting

### "ImportError: No module named 'config'"
```bash
pip install python-dotenv
python config.py  # Valida setup
```

### "KeyError: 'FLASK_SECRET_KEY'"
```bash
# Certifique-se que .env existe e foi preenchido
ls -la .env
# Se não existir:
cp .env.example .env
```

### "EMAIL_APP_PASSWORD não configurado"
```bash
# Edite .env e preencha:
EMAIL_SENDER=seu-email@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## 📖 Documentação Completa

Para detalhes completos sobre setup, veja:
- **SETUP_ENV.md** - Guia passo-a-passo
- **config.py** - Código comentado com defaults
- **.env.example** - Template com todas as opções

---

## 🎯 Resumo

✅ **Sistema de variáveis de ambiente está implementado!**

Próximo: Atualizar `yolo.py` e `notifications.py` para usar `config.py` (remover hardcoding de credenciais).

Quer que eu faça isso agora? 🚀
