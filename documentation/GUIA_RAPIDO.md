# 🚀 Guia de Início Rápido - ARK YOLO

> Sistema de Monitoramento em Tempo Real com Detecção de Pessoas

---

## ⚡ Instalação Rápida (5 minutos)

### 1. Clone o Repositório

```bash
git clone https://github.com/jonatansouza2k11/computacional_vision.git
cd computacional_vision
```

### 2. Crie Ambiente Virtual

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

### 3. Instale Dependências

```bash
pip install -r requeriments.txt
```

### 4. Inicie o Banco de Dados

```bash
python -c "from database import init_db; init_db()"
```

### 5. Execute a Aplicação

```bash
python app.py
```

**Acesse:** http://localhost:5000  
**Login padrão:** `admin` / `admin123`

---

## 📋 Primeira Configuração

### Passo 1: Configurar Câmera

1. Acesse **Settings** (⚙️)
2. Em **Fonte de vídeo**, escolha:
   - `0` = Webcam integrada
   - `1`, `2`, ... = Câmeras USB externas
   - `rtsp://...` = IP Camera (RTSP)
   - `http://...` = IP Camera (HTTP)
3. Clique **Salvar**

### Passo 2: Ajustar Detecção

Em **Detecção YOLO:**

- **Confidence Threshold:** 0.78 (padrão é bom)
- **Modelo:** yolov8n.pt (recomendado)

### Passo 3: Definir Zona Segura

1. Vá ao **Dashboard** (🏠)
2. Clique **"Editar Zona Segura"**
3. Desenhe um retângulo na imagem
4. As coordenadas aparecem automaticamente
5. Clique **"Salvar Zona"**

### Passo 4: Configurar Email (Opcional)

Em **Servidor de E-mail:**

- **Email:** seu_email@gmail.com
- **Senha:** Use "Senha de Aplicativo" do Gmail
- **SMTP Server:** smtp.gmail.com
- **Porta:** 587

**Como gerar Senha de App:**
1. Acesse accounts.google.com
2. Ative "Autenticação em 2 Fatores"
3. Vá em "Senhas de Aplicativo"
4. Gere uma para "Mail"

---

## 🎮 Usando o Dashboard

### Layout

```
┌─────────────────────────────────────────────┐
│  CABEÇALHO (Status, FPS, Pessoas)          │
├─────────────────────────────────────────────┤
│                                             │
│  VÍDEO AO VIVO      │  MÉTRICAS DIREITA     │
│  (Zona segura       │  - Pessoas detectadas │
│   desenhada)        │  - Alertas recentes   │
│                     │  - Status do sistema  │
│                     │  - Mapa da zona       │
└─────────────────────────────────────────────┘
```

### Botões

| Botão | Função |
|-------|--------|
| ▶️ Iniciar | Começa a captura de vídeo |
| ⏸️ Pausar | Pausa o vídeo (mantém tracking) |
| ⏹️ Parar | Encerra captura |
| 🎯 Editar Zona | Desenha nova zona segura |
| 📊 Logs | Ver histórico de alertas |

---

## 🔧 Solução Rápida de Problemas

| Problema | Solução |
|----------|---------|
| "Webcam não funciona" | Tente ID 1, 2, etc em Settings |
| "Detecção muito lenta" | Reduzir target_width em Settings |
| "Muitos falsos positivos" | Aumentar confidence_threshold |
| "Email não envia" | Verificar credenciais em Settings |
| "FPS muito baixo" | Usar yolov8n em vez de yolov8l |

---

## 📁 Estrutura Importante

```
computacional_vision/
├── app.py              ← Executar isto
├── yolo.py             ← Lógica de detecção
├── database.py         ← Dados
├── cv_system.db        ← Banco de dados
├── yolo_models/        ← Modelos YOLO
├── alertas/            ← Snapshots/vídeos dos alertas
└── templates/          ← Páginas HTML
```

---

## 🎯 Fluxo de Funcionamento

```
1. Usuário faz login
           ↓
2. Inicia stream de vídeo
           ↓
3. YOLO detecta pessoas
           ↓
4. Rastreador mantém IDs
           ↓
5. Verifica zona segura
           ↓
6. Se sair: inicia contador
           ↓
7. Se > 30s: dispara alerta
           ↓
8. Envia email com snapshot
           ↓
9. Registra em Histórico
```

---

## 🧪 Testar Tudo

### Testar Câmera

```bash
python test_cam.py
```

### Verificar Instalação

```bash
python -c "from ultralytics import YOLO; print('✓ YOLO OK')"
python -c "import cv2; print('✓ OpenCV OK')"
python -c "from flask import Flask; print('✓ Flask OK')"
```

---

## 📊 Monitorar Logs

**Sistema Logs** (Iniciar/Pausar/Parar):
- Dashboard → "Logs" → "Logs de Sistema"

**Alertas** (Pessoa fora da zona):
- Dashboard → "Logs" → "Histórico de Alertas"
- Clique no vídeo para reproduzir

---

## 🎓 Próximos Passos

1. **Ler a documentação completa:** `DOCUMENTACAO.md`
2. **Explorar Settings avançados** em ⚙️
3. **Adicionar mais usuários** em 👤 (admin)
4. **Configurar múltiplas câmeras** (futuro)
5. **Integrar com sistemas externos** via API

---

## 📞 Ajuda

**Documentação Completa:** Veja `DOCUMENTACAO.md`  
**Instruções de IA:** Veja `.github/copilot-instructions.md`  
**Repositório:** https://github.com/jonatansouza2k11/computacional_vision

---

**Pronto para usar! Divirta-se monitorando! 🎉**

