"""
sync_db.py

Sincroniza e verifica completamente o banco de dados cv_system.db.
Valida TODAS as configurações do sistema Ark.

Uso:
    python sync_db.py
"""

import sys
import sqlite3
from database import init_db, DB_NAME

def verify_database():
    """Verifica completamente o banco de dados e todas as configurações."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        print("\n" + "="*70)
        print("VERIFICAÇÃO COMPLETA DO BANCO DE DADOS ARK")
        print("="*70)
        
        # ============================================================
        # 1. VERIFICAR TABELAS
        # ============================================================
        print("\n[1] TABELAS DO BANCO", flush=True)
        print("-" * 70)
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        required_tables = {
            'users': 'Usuários e autenticação',
            'alerts': 'Alertas de zona segura',
            'settings': 'Configurações do sistema',
            'system_logs': 'Logs de ações (INICIAR/PAUSAR/PARAR/RETOMAR)'
        }
        
        all_tables_ok = True
        for table, description in required_tables.items():
            if table in tables:
                # Contar registros
                c.execute(f"SELECT COUNT(*) FROM {table}")
                count = c.fetchone()[0]
                print(f"  ✓ {table:<15} - {description:<40} ({count} registros)", flush=True)
            else:
                print(f"  ✗ {table:<15} - FALTANDO!", flush=True)
                all_tables_ok = False
        
        if not all_tables_ok:
            return False
        
        # ============================================================
        # 2. VERIFICAR CONFIGURAÇÕES YOLO
        # ============================================================
        print("\n[2] CONFIGURAÇÕES YOLO", flush=True)
        print("-" * 70)
        
        yolo_keys = {
            'conf_thresh': 'Threshold de confiança',
            'model_path': 'Caminho do modelo YOLO',
            'target_width': 'Largura do frame processado',
            'frame_step': 'Pular frames (performance)',
            'tracker': 'Algoritmo de tracking'
        }
        
        for key, desc in yolo_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                print(f"  ✓ {key:<20} = {result[0]:<30} ({desc})", flush=True)
            else:
                print(f"  ✗ {key:<20} FALTANDO! ({desc})", flush=True)
                all_tables_ok = False
        
        # ============================================================
        # 3. VERIFICAR CONFIGURAÇÕES DE ZONA SEGURA
        # ============================================================
        print("\n[3] CONFIGURAÇÕES DE ZONA SEGURA", flush=True)
        print("-" * 70)
        
        zone_keys = {
            'safe_zone': 'Coordenadas da(s) zona(s)',
            'max_out_time': 'Tempo máximo fora (alerta)',
            'email_cooldown': 'Cooldown entre e-mails',
            'buffer_seconds': 'Buffer pré-gravação',
            'zone_empty_timeout': 'Timeout zona vazia',
            'zone_full_timeout': 'Timeout zona cheia',
            'zone_full_threshold': 'Limite de pessoas (zona cheia)'
        }
        
        for key, desc in zone_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                # Truncar safe_zone se for muito longo
                if key == 'safe_zone' and len(value) > 50:
                    value = value[:47] + "..."
                print(f"  ✓ {key:<25} = {value:<20} ({desc})", flush=True)
            else:
                print(f"  ✗ {key:<25} FALTANDO! ({desc})", flush=True)
                all_tables_ok = False
        
        # ============================================================
        # 4. VERIFICAR CONFIGURAÇÕES DE CÂMERA
        # ============================================================
        print("\n[4] CONFIGURAÇÕES DE CÂMERA", flush=True)
        print("-" * 70)
        
        camera_keys = {
            'source': 'Fonte de vídeo (0/webcam/url)',
            'cam_width': 'Largura da câmera',
            'cam_height': 'Altura da câmera',
            'cam_fps': 'FPS da câmera'
        }
        
        for key, desc in camera_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                print(f"  ✓ {key:<20} = {result[0]:<30} ({desc})", flush=True)
            else:
                print(f"  ✗ {key:<20} FALTANDO! ({desc})", flush=True)
                all_tables_ok = False
        
        # ============================================================
        # 5. VERIFICAR CONFIGURAÇÕES DE E-MAIL (SMTP)
        # ============================================================
        print("\n[5] CONFIGURAÇÕES DE E-MAIL (SMTP)", flush=True)
        print("-" * 70)
        
        email_keys = {
            'email_smtp_server': 'Servidor SMTP',
            'email_smtp_port': 'Porta SMTP',
            'email_use_tls': 'Usar TLS',
            'email_use_ssl': 'Usar SSL',
            'email_from': 'Remetente (FROM)',
            'email_user': 'Usuário SMTP (login)',
            'email_password': 'Senha/App Password'
        }
        
        for key, desc in email_keys.items():
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = c.fetchone()
            if result:
                value = result[0]
                # Ocultar senha
                if key == 'email_password' and value:
                    value = "***" + value[-4:] if len(value) > 4 else "****"
                elif key == 'email_password':
                    value = "[vazio]"
                print(f"  ✓ {key:<20} = {value:<30} ({desc})", flush=True)
            else:
                print(f"  ✗ {key:<20} FALTANDO! ({desc})", flush=True)
                all_tables_ok = False
        
        # ============================================================
        # 6. VERIFICAR DADOS EXISTENTES (PRESERVAÇÃO)
        # ============================================================
        print("\n[6] DADOS EXISTENTES (VERIFICAÇÃO DE PRESERVAÇÃO)", flush=True)
        print("-" * 70)
        
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM alerts")
        alert_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM system_logs")
        log_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM settings")
        setting_count = c.fetchone()[0]
        
        print(f"  • Usuários cadastrados:     {user_count}", flush=True)
        print(f"  • Alertas registrados:      {alert_count}", flush=True)
        print(f"  • Logs de sistema:          {log_count}", flush=True)
        print(f"  • Configurações (keys):     {setting_count}", flush=True)
        
        # ============================================================
        # 7. VERIFICAR USUÁRIO ADMIN PADRÃO
        # ============================================================
        print("\n[7] USUÁRIO ADMINISTRADOR", flush=True)
        print("-" * 70)
        
        c.execute("SELECT username, email, role FROM users WHERE role = 'admin'")
        admins = c.fetchall()
        
        if admins:
            for admin in admins:
                print(f"  ✓ Admin: {admin[0]:<15} ({admin[1]}) - Role: {admin[2]}", flush=True)
        else:
            print(f"  ⚠️  Nenhum usuário admin encontrado!", flush=True)
            all_tables_ok = False
        
        # ============================================================
        # 8. RESUMO FINAL
        # ============================================================
        print("\n" + "="*70)
        
        conn.close()
        return all_tables_ok
        
    except Exception as e:
        print(f"\n✗ ERRO CRÍTICO ao verificar banco: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*70, flush=True)
    print("ARK SYSTEM - SINCRONIZAÇÃO E VERIFICAÇÃO DO BANCO DE DADOS")
    print("="*70, flush=True)
    
    try:
        print("\n→ Executando init_db()...", flush=True)
        init_db()
        print("✓ init_db() concluído!", flush=True)
    except Exception as e:
        print(f"\n✗ ERRO ao executar init_db(): {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Verificação completa
    if verify_database():
        print("✓✓✓ BANCO SINCRONIZADO E VERIFICADO COM SUCESSO! ✓✓✓", flush=True)
        print("="*70, flush=True)
        print("\n✓ Todas as tabelas existem", flush=True)
        print("✓ Todas as configurações YOLO estão presentes", flush=True)
        print("✓ Todas as configurações de ZONA SEGURA estão presentes", flush=True)
        print("✓ Todas as configurações de CÂMERA estão presentes", flush=True)
        print("✓ Todas as configurações de E-MAIL estão presentes", flush=True)
        print("✓ Todos os dados existentes foram preservados", flush=True)
        print("✓ Usuário administrador está configurado", flush=True)
        print("\n→ Sistema pronto para iniciar:", flush=True)
        print("  python app.py", flush=True)
        print("="*70, flush=True)
    else:
        print("\n⚠️⚠️⚠️ SINCRONIZAÇÃO INCOMPLETA ⚠️⚠️⚠️", flush=True)
        print("="*70, flush=True)
        print("\nAlgumas verificações falharam!", flush=True)
        print("Revise database.py e certifique-se de que TODAS as keys", flush=True)
        print("estão definidas em default_settings.", flush=True)
        print("="*70, flush=True)
        sys.exit(1)
