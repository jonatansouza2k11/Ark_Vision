# 📦 Resumo Executivo - ARK YOLO v1.0

> **Sistema de Monitoramento Inteligente em Tempo Real**

---

## 🎯 O que é ARK YOLO?

Um **sistema web de monitoramento inteligente** que detecta e rastreia pessoas em vídeo ao vivo, verifica se estão em zonas seguras e dispara alertas automáticos.

**Em Português Simples:** Uma câmera que "vê" pessoas, sabe quem é quem (rastreamento), verifica se estão no lugar certo, e envia um email avisando se alguém sair.

---

## 🎬 Como Funciona?

```
1. CÂMERA CAPTURA IMAGEM
         ↓
2. YOLO DETECTA PESSOAS
         ↓
3. TRACKER MANTÉM IDS (quem é quem)
         ↓
4. VERIFICA ZONA SEGURA (está no lugar certo?)
         ↓
5. SE SAIR > 30s → DISPARA ALERTA
         ↓
6. ENVIA EMAIL COM FOTO/VÍDEO
         ↓
7. REGISTRA EM HISTÓRICO
```

---

## ✨ Principais Features

### ✅ Detecção
- YOLOv8 / YOLOv11 (rápido e preciso)
- Detecção em tempo real
- Configuração de confiança ajustável

### ✅ Rastreamento
- BoT-SORT para múltiplas pessoas
- IDs persistentes (mesma pessoa = mesmo ID)
- Histórico de posições

### ✅ Alertas
- Zona segura customizável
- Tempo máximo fora configurável
- Email com snapshot
- Cooldown para evitar spam

### ✅ Dashboard
- Visualização ao vivo
- Mapa da zona segura
- Métricas em tempo real (FPS, pessoas detectadas)
- Histórico de alertas

### ✅ Segurança
- Login obrigatório
- Roles (admin/user)
- Senhas criptografadas
- Histórico de ações

---

## 📋 Matriz de Compatibilidade

| Recurso | Support |
|---------|---------|
| Webcam USB | ✅ |
| IP Camera (RTSP) | ✅ |
| IP Camera (HTTP) | ✅ |
| Windows | ✅ |
| Linux | ✅ |
| macOS | ✅ |
| GPU NVIDIA | ✅ |
| CPU Only | ✅ (lento) |
| Chrome | ✅ |
| Firefox | ✅ |
| Safari | ✅ |
| Mobile | ⚠️ (web, não app) |

---

## 💾 Stack Técnico

### Backend
- **Framework:** Flask (Python web)
- **Detecção:** YOLOv8/v11 (Ultralytics)
- **Rastreamento:** BoT-SORT (automático do YOLO)
- **Database:** SQLite3
- **Email:** SMTP (Gmail)
- **Imagem:** OpenCV

### Frontend
- **Rendering:** Jinja2 Templates
- **CSS:** Tailwind CSS + DaisyUI
- **JS:** Vanilla JavaScript
- **Vídeo:** MJPEG stream

### DevOps
- **Ambiente:** Python venv
- **Versão:** 3.10+
- **Porta:** 5000
- **Sincronização:** Git

---

## 🚀 Início Rápido

### 1. Instalar (5 min)
```bash
git clone https://github.com/jonatansouza2k11/computacional_vision.git
cd computacional_vision
python -m venv cv_env
cv_env\Scripts\Activate.ps1  # Windows
pip install -r requeriments.txt
```

### 2. Inicializar (2 min)
```bash
python -c "from database import init_db; init_db()"
python app.py
```

### 3. Acessar (1 min)
- URL: http://localhost:5000
- Login: `admin` / `admin123`
- Configurar câmera em Settings
- Definir zona segura no Dashboard

---

## 📊 Estatísticas de Documentação

| Documento | Foco | Linhas |
|-----------|------|--------|
| **DOCUMENTACAO.md** | Guia Completo | 3000+ |
| **GUIA_RAPIDO.md** | Quick Start | 200 |
| **ARQUITETURA_TECNICA.md** | Developers | 1500+ |
| **FAQ_E_CASOS_USO.md** | Implementação | 1000+ |
| **ROADMAP.md** | Futuro | 600+ |
| **INDICE_DOCUMENTACAO.md** | Navegação | 400+ |

**Total:** 6700+ linhas de documentação

---

## 🎯 Casos de Uso

- 🏢 **Segurança:** Monitorar áreas restritas
- 🏭 **Indústria:** Controlar presença em estações
- 🏥 **Hospitalar:** Rastrear pacientes/equipamentos
- 🛍️ **Varejo:** Monitorar VIP areas
- 🏫 **Educação:** Controle de presença em sala
- 🚌 **Transporte:** Fluxo de passageiros
- 🛡️ **24/7:** Monitoramento noturno

---

## 💪 Diferenciais

| Feature | ARK | Alternativas |
|---------|-----|-------------|
| Licença | Open | Fechadas |
| Preço | Gratuito | Caros |
| Instalação | Local | Cloud |
| Dados | Você controla | Terceiros |
| Customização | Fácil | Difícil |
| Suporte | Community | Pago |

---

## ⚙️ Requisitos Mínimos

| Componente | Mínimo | Recomendado |
|-----------|--------|------------|
| CPU | Dual Core | i5/i7 |
| RAM | 4GB | 8GB+ |
| SSD | 20GB | 100GB |
| GPU | Nenhuma | RTX 2060+ |
| Internet | Opcional | 10Mbps |

---

## 🔐 Segurança

### Implementado
- ✅ Autenticação obrigatória
- ✅ Senhas com bcrypt
- ✅ Sessão segura
- ✅ Roles (admin/user)
- ✅ Validação de entrada

### Recomendações
- 🔲 Mudar SECRET_KEY
- 🔲 Configurar HTTPS
- 🔲 Usar .env para credenciais
- 🔲 Rate limiting no login
- 🔲 Backup diário do banco

---

## 📱 API Summary

### Endpoints Principais

```
GET  /                    Redireciona
GET  /login               Página de login
POST /login               Autenticar
GET  /dashboard           Dashboard principal
GET  /video_feed          Stream MJPEG ao vivo
GET  /api/stats           Dados em JSON
POST /api/safe_zone       Atualizar zona
POST /start_stream        Iniciar captura
POST /stop_stream         Parar captura
```

---

## 📈 Performance

### Esperado (yolov8n com 960x540)
- **FPS:** 30-45
- **Latência:** 50-100ms
- **RAM:** 2-3GB
- **CPU:** 50-70%
- **Detecção:** 92-95%

---

## 🛠️ Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Webcam não funciona | Tente ID 1, 2, ... em Settings |
| Muito lento | Reduzir target_width ou usar GPU |
| Email não envia | Verificar Gmail + senha de app |
| FPS baixo | Aumentar frame_step ou usar modelo menor |
| Dashboard branco | Limpar cache (Ctrl+Shift+Del) |

---

## 📚 Documentação Completa

- 📖 **DOCUMENTACAO.md** → Guia completo (leia tudo)
- ⚡ **GUIA_RAPIDO.md** → Comece em 5 min
- 🏗️ **ARQUITETURA_TECNICA.md** → Para developers
- ❓ **FAQ_E_CASOS_USO.md** → Dúvidas e exemplos
- 🗺️ **ROADMAP.md** → Futuro do projeto
- 📑 **INDICE_DOCUMENTACAO.md** → Mapa de navegação

---

## 🎓 Próximas Etapas

### Iniciante
1. Ler GUIA_RAPIDO.md
2. Instalar e rodar
3. Explorar dashboard

### Intermediário
1. Ler DOCUMENTACAO.md
2. Editar configurações
3. Testar diferentes câmeras

### Avançado
1. Ler ARQUITETURA_TECNICA.md
2. Modificar código
3. Adicionar features

---

## 📞 Suporte

### Para Problemas
1. Verificar FAQ_E_CASOS_USO.md
2. Buscar em DOCUMENTACAO.md
3. Abrir issue no GitHub

### Para Contribuir
1. Fork do repositório
2. Feature branch
3. Pull request

### Repositório
https://github.com/jonatansouza2k11/computacional_vision

---

## ✅ Checklist de Implementação

- [ ] Python 3.10+ instalado
- [ ] Git configurado
- [ ] Ambiente virtual criado
- [ ] Dependências instaladas
- [ ] Banco de dados inicializado
- [ ] App rodando em localhost:5000
- [ ] Login funcionando
- [ ] Câmera detectada
- [ ] Zona segura definida
- [ ] Email configurado (opcional)
- [ ] Histórico funcionando
- [ ] Múltiplos usuários criados

---

## 🎯 KPIs (Key Performance Indicators)

### Produção
- **Uptime:** > 99%
- **Detecção Accuracy:** > 90%
- **Alerta Latência:** < 100ms
- **Email Delivery:** > 98%
- **Dashboard Response:** < 500ms

### Desenvolvimento
- **Test Coverage:** > 80%
- **Documentation:** 100%
- **Code Review:** 2+ approvals
- **Performance:** FPS > 15

---

## 🌟 Destaques v1.0

✨ **O que torna especial:**
- Completamente open-source
- Sem dependências de cloud
- YOLO v11 (estado da arte)
- BoT-SORT nativo (tracking superior)
- Dashboard bonito e responsivo
- Documentação extensiva
- Pronto para produção

---

## 🚀 Visão Futura

### v1.1 (Q1 2026)
- Editor visual de zonas
- Múltiplas zonas
- HTTPS nativo

### v2.0 (Q2-Q3 2026)
- Múltiplas câmeras
- Cross-cam tracking
- Análise comportamental

### v3.0 (Q4 2026+)
- App mobile
- Machine Learning
- Reconhecimento facial

---

## 📊 Comparação com Alternativas

| Recurso | ARK | Axis | Genetec | Milestone |
|---------|-----|------|---------|-----------|
| Preço | Grátis | $$$ | $$$$ | $$$ |
| Open Source | ✅ | ❌ | ❌ | ❌ |
| YOLO v11 | ✅ | ❌ | ❌ | ❌ |
| Fácil Install | ✅ | ❌ | ❌ | ❌ |
| Customizável | ✅ | ❌ | ❌ | ❌ |
| Escalável | ⚠️ | ✅ | ✅ | ✅ |
| Suporte Prof | ❌ | ✅ | ✅ | ✅ |

---

## 🎁 Bônus

### Templates Inclusos
- Dashboard responsivo
- Login/Register
- Settings admin
- Histórico de logs
- Diagnóstico do sistema

### Scripts Úteis
- `test_cam.py` → Testar câmera
- `test.py` → Testes gerais
- `clear.py` → Limpar dados
- `sync_db.py` → Sincronizar banco

---

## 📝 Última Atualização

**Data:** Dezembro 2025  
**Versão:** 1.0  
**Status:** Estável e pronto para produção  
**Suporte:** Comunidade open-source  

---

## 🙏 Créditos

**Desenvolvedor:** Jonathan Souza (@jonatansouza2k11)  
**Baseado em:** YOLO Ultralytics  
**Framework:** Flask + Tailwind  
**Tema:** Cyberpunk 🌌  

---

**Obrigado por usar ARK YOLO! Divirta-se monitorando! 🚀**

---

### 📞 Contato
- GitHub: https://github.com/jonatansouza2k11/computacional_vision
- Issues: Abra uma issue para bugs/features

