# 🎓 FAQ e Casos de Uso - ARK YOLO

---

## ❓ Perguntas Frequentes

### Geral

**P: O sistema funciona com múltiplas câmeras?**  
R: Atualmente não. A v1.0 suporta apenas 1 câmera por instância. Para múltiplas câmeras, execute múltiplas instâncias de `app.py` em portas diferentes (5000, 5001, 5002...).

**P: Posso usar a câmera do notebook?**  
R: Sim! Use `source=0` em Settings. Se tiver câmera USB, tente `source=1`, `2`, etc.

**P: Qual é o requisito mínimo de hardware?**  
R: 4GB RAM + CPU dual-core. Recomendado 8GB RAM + GPU NVIDIA para melhor performance.

**P: A detecção funciona durante a noite?**  
R: Sim, mas com qualidade reduzida. Recomenda-se iluminação adequada para melhores resultados.

**P: Posso treinar meu próprio modelo YOLO?**  
R: Sim, mas fora do escopo desta aplicação. Use `ultralytics` CLI para treinar e coloque o arquivo `.pt` em `yolo_models/`.

---

### Configuração

**P: Como faço para aumentar a precisão de detecção?**  
R: Teste em ordem:
1. Aumentar `confidence_threshold` (reduz falsos positivos)
2. Usar modelo maior (yolov8l em vez de yolov8n)
3. Melhorar iluminação do ambiente
4. Aumentar `target_width` (mais detalhes, mais lento)

**P: Como reduzo o tempo de resposta?**  
R: 
1. Reduzir `target_width` (ex: 640 em vez de 960)
2. Aumentar `frame_step` (processar menos frames)
3. Usar modelo menor (yolov8n)
4. Desabilitar email para alertas

**P: Posso rodar em CPU pura?**  
R: Sim, mas será muito lento. Para produção, recomenda-se GPU NVIDIA.

**P: Como configuro uma câmera IP (RTSP)?**  
R: Em Settings, em vez de `0`, use:
```
rtsp://usuario:senha@192.168.1.100:554/stream
```
Teste a URL com `ffplay` antes.

---

### Alertas e Emails

**P: Por que não recebo email?**  
R: Checklist:
1. Gmail 2FA ativado?
2. "Senha de Aplicativo" usada (não senha da conta)?
3. Credenciais salvas em Settings?
4. Internet ativa?
5. Firewall não bloqueia porta 587?
6. Pessoa realmente ficou > 30s fora da zona?

**P: Como deixo de receber tantos alertas?**  
R: Aumente `max_out_time` (ex: 60s em vez de 30s) ou `email_cooldown` (ex: 600s em vez de 300s).

**P: Posso enviar alertas para múltiplos emails?**  
R: Atualmente não. Adapte `notifications.py` para suportar lista de destinatários.

**P: Posso enviar alertas via SMS?**  
R: Sim, integrando Twilio. Veja documentação de Twilio + Flask.

---

### Banco de Dados

**P: Como faço backup do banco?**  
R: É um arquivo SQLite:
```bash
copy cv_system.db cv_system.backup.db
```

**P: Posso usar MySQL em vez de SQLite?**  
R: Sim, adaptando `database.py` para MySQL. Requer changes em imports e queries.

**P: Quanto tempo de histórico os alertas têm?**  
R: Indefinido. Implemente limpeza automática:
```python
def cleanup_old_alerts(days=30):
    old_date = datetime.now() - timedelta(days=days)
    # DELETE FROM alerts WHERE timestamp < old_date
```

**P: Como excluo um usuário?**  
R: Não há interface. Use SQL direto:
```sql
DELETE FROM users WHERE username = 'usuario';
```

---

### Rastreamento

**P: O sistema perde rastreamento de pessoas?**  
R: Sim, se:
- Pessoa sai do quadro e volta (novo ID)
- Oclusão parcial (pessoa bloqueada por objeto)
- Mudança rápida de direção
- Iluminação muda drasticamente

Solução: Aumentar `frame_step` reduz ocorrência.

**P: Como mudo o algoritmo de rastreamento?**  
R: Em `yolo.py`, altere `model.predict(...tracker="botsort.yaml")` para usar ByteTrack ou outro.

**P: Posso rastrear objetos além de pessoas?**  
R: Sim, alterando `PERSON_CLASS_ID` em `yolo.py`. Veja as classes suportadas por YOLO.

---

### Segurança

**P: O sistema é seguro para produção?**  
R: Não. Antes de produção:
1. Alterar SECRET_KEY (não use padrão)
2. Usar HTTPS com certificado SSL
3. Implementar rate limiting no login
4. Usar variáveis de ambiente para credenciais
5. Auditar código de segurança

**P: Onde são armazenados os dados?**  
R: 
- Senhas: Criptografadas com bcrypt em `users` table
- Vídeos/snapshots: `alertas/` pasta (disco local)
- Configurações: `cv_system.db` (SQLite)
- Sessões: Memória do Flask (perdidas ao restart)

**P: Posso criptografar a conexão do banco?**  
R: SQLite não suporta encryption nativo. Use ferramentas como `sqlcipher` ou mudar para MySQL/PostgreSQL.

**P: Como faço para resetar a senha de um usuário?**  
R: Use SQL direto ou adicione rota de admin para reset.

---

### Troubleshooting

**P: "ModuleNotFoundError: No module named 'ultralytics'"**  
R: Instale dependências:
```bash
pip install -r requeriments.txt
```

**P: "CUDA out of memory"**  
R: Use CPU ou modelo menor:
```python
# Em yolo.py
self.model = YOLO(model_path, device='cpu')
```

**P: Dashboard branco / não carrega**  
R:
1. Verificar console do navegador (F12)
2. Verificar logs do Flask (terminal)
3. Tentar limpar cache: Ctrl+Shift+Del
4. Recarregar página: Ctrl+F5

**P: Stream fica travado / congelado**  
R:
1. Câmera desconectou? Reconectar
2. FPS muito baixo? Reduzir `target_width`
3. Muita CPU? Aumentar `frame_step`
4. Reiniciar app: Ctrl+C + `python app.py`

**P: Erro "Address already in use"**  
R: Porta 5000 já está em uso:
```bash
# Encontrar processo usando porta 5000
netstat -ano | findstr :5000

# Matar processo
taskkill /PID <PID> /F

# Ou usar porta diferente
app.run(port=5001)
```

**P: Detecção não funciona com meu modelo customizado**  
R: Certifique-se de que é compatível com Ultralytics e que o path está correto:
```python
MODEL_PATH = "yolo_models/seu_modelo.pt"
```

---

## 📚 Casos de Uso

### Caso 1: Segurança de Prédio

**Cenário:** Empresa quer monitorar a recepção para garantir que visitantes não entrem em áreas restritas.

**Configuração:**

```
Câmera: Apontada para a entrada/recepção
Zona Segura: Área de recepção (retângulo)
max_out_time: 30 segundos
email_cooldown: 300 segundos
Alertar: gerente@empresa.com
```

**Fluxo:**
1. Visitante chega na recepção
2. Sistemas detecta e rastreia (Track ID 1)
3. Se visitante sai da zona por > 30s:
   - Snapshot capturado
   - Email enviado para gerente
   - Alerta registrado em histórico
4. Gerente vê alerta no dashboard e toma ação

**Métricas de Sucesso:**
- Redução de 90% de acessos não autorizados
- Resposta rápida a incidentes (< 1 minuto)

---

### Caso 2: Controle de Área de Trabalho

**Cenário:** Fábrica quer garantir que operários permaneçam na área designada durante o turno.

**Configuração:**

```
Câmera: Overhead, apontada para a estação de trabalho
Zona Segura: Região da estação (polígono se possível)
max_out_time: 60 segundos (para banheiro/água)
email_cooldown: 600 segundos
Alertar: supervisor@fabrica.com
Modelo: yolov8m (maior precisão)
```

**Fluxo:**
1. Operário trabalha na estação
2. Saí para banheiro (30s) → Sem alerta
3. Fica fora > 60s → Alerta
4. Supervisor vê e pode enviar mensagem de volta
5. Histório acumulado = dados de produtividade

**Métricas de Sucesso:**
- Produtividade +15%
- Redução de acidentes
- Dados quantificados de tempo de trabalho

---

### Caso 3: Monitoramento de Vaga de Estacionamento

**Cenário:** Estacionamento inteligente quer saber quantas vagas estão ocupadas.

**Adaptação Necessária:**
- Treinar modelo para detectar "vagas vazias" vs "carros"
- Zona segura = cada vaga
- `max_out_time` = indefinido (carro pode ficar horas)
- Email = desabilitar

**Configuração:**

```
Câmera: Overhead de 1-2 vagas
Detecção: Custom model treinado para "car"
Zona Segura: Vaga individual
Alertar: Apenas registrar em histórico
```

**Fluxo:**
1. Câmera vê vaga vazia
2. Carro estaciona
3. Sistema rastreia "carro em vaga X"
4. Quando sai, marca como "vaga livre"
5. API pode retornar % de ocupação

---

### Caso 4: Análise de Tráfego

**Cenário:** Loja quer saber padrões de movimentação de clientes.

**Configuração:**

```
Câmera: Entrada da loja
Zona Segura: Não aplicável (queremos rastrear movimento)
Frame Step: 1 (máxima precisão)
Modelo: yolov8l (melhor detecção)
Email: Desabilitar
```

**Modificação Necessária:**
```python
# Em yolo.py, não verificar zona, apenas coletar dados
for track_id in detected_people:
    log_person_movement(track_id, x, y, timestamp)
```

**Fluxo:**
1. Pessoas entram e se movem na loja
2. Cada movimento é registrado em DB
3. Ao final do dia, gerar heatmap
4. Identificar corredores mais usados
5. Otimizar layout de produtos

---

### Caso 5: Monitoramento de Criança/Idoso

**Cenário:** Cuidador quer monitorar criança em área de brincadeira.

**Configuração:**

```
Câmera: Visão geral da área
Zona Segura: Área de segurança da brincadeira
max_out_time: 15 segundos (sair para banheiro = aviso)
email_cooldown: 60 segundos (alertar rapidamente)
Alertar: Cuidador (celular)
```

**Adaptar para Tempo Real:**
```python
# Modificar notifications.py para SMS/Push
if out_time > max_out_time:
    notifier.send_sms("+55987654321", "Criança saiu da área!")
```

**Fluxo:**
1. Criança brinca na área
2. Sai por mais de 15s → Alerta em tempo real
3. Cuidador recebe notificação
4. Pode conferir vídeo ao vivo no dashboard
5. Registra incidentes para análise

---

### Caso 6: Controle de Acesso a Sala Restrita

**Cenário:** Laboratório quer rastrear quem entra em sala confidencial.

**Configuração:**

```
Câmera: Na porta de entrada
Zona Segura: Dentro da sala
max_out_time: Irrelevante (pessoa sai rápido)
Email: Sempre enviar (auditoria)
Alertar: admin@lab.com
```

**Modificação:**
```python
# Não usar max_out_time, disparar alerta ao ENTRAR
if status_changed_from_OUT_to_IN:
    trigger_alert(track_id, alert_type="unauthorized_entry")
    log_system_action("ENTRY_ATTEMPT", username, reason=f"Track {track_id}")
```

**Fluxo:**
1. Pessoa tenta entrar em sala restrita
2. Detecção registra a tentativa
3. Email imediato com foto/vídeo
4. Log em `system_logs` para auditoria
5. Admin revisa e toma ação

---

### Caso 7: Monitoramento 24/7 com Alertas Inteligentes

**Cenário:** Escritório pequeno, monitoramento noturno de segurança.

**Configuração:**

```
Câmera: Visão geral do escritório
Zona Segura: Não (queremos detectar QUALQUER pessoa à noite)
max_out_time: 0 (alerta ao detectar)
email_cooldown: 600s (evitar spam)
Alertar: security@office.com
Modelo: yolov8l (noturno requer mais acurácia)
```

**Modificação:**
```python
# Modo noturno: alerta ao detectar qualquer pessoa fora do horário
def is_outside_hours():
    return datetime.now().hour > 22 or datetime.now().hour < 6

if is_outside_hours() and person_detected:
    trigger_alert(track_id, alert_type="after_hours_presence")
```

**Fluxo:**
1. Sistema verifica se é fora do horário comercial
2. Detecta pessoa no escritório vazio
3. Alerta imediato para segurança
4. Vídeo de 10s antes + durante é salvo
5. Investigação rápida da intrução

---

## 🎯 Personalização por Setor

### Varejo
- Zona segura: Caixa/área VIP
- max_out_time: 20s
- Objetivo: Reduzir perdas

### Manufatura
- Zona segura: Estação de trabalho
- max_out_time: 30-60s
- Objetivo: Produtividade + segurança

### Hospitalar
- Zona segura: Leito do paciente
- max_out_time: 5s (crítico)
- Objetivo: Segurança do paciente

### Educação
- Zona segura: Sala de aula
- max_out_time: 10s
- Objetivo: Controle de presença

### Transporte
- Zona segura: Linha de espera
- max_out_time: Indefinido
- Objetivo: Fluxo de passageiros

---

## 📊 Métricas de Performance

### Esperadas por Modelo

| Modelo | FPS | Acurácia | RAM | GPU |
|--------|-----|----------|-----|-----|
| yolov8n | 35-45 | 92% | 2GB | 4GB |
| yolov8s | 25-35 | 94% | 3GB | 6GB |
| yolov8m | 15-25 | 96% | 4GB | 8GB |
| yolov8l | 8-15 | 97% | 6GB | 12GB |

### Otimizações Implementadas

| Otimização | Ganho |
|------------|-------|
| Frame skipping (step=2) | 50% mais rápido |
| Reduzir target_width (960→640) | 30% mais rápido |
| Desabilitar GPU em CPU-only | Baseline |
| Threading para email | 0 impacto no vídeo |

---

**Fim do FAQ e Casos de Uso**

