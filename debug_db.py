"""
debug_db.py

Script para inspecionar o conteúdo do banco cv_system.db
"""

import sqlite3
import os

DB_NAME = "cv_system.db"

def check_database():
    if not os.path.exists(DB_NAME):
        print(f"❌ Banco de dados '{DB_NAME}' não encontrado!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    print("=" * 80)
    print("📊 INSPEÇÃO DO BANCO DE DADOS cv_system.db")
    print("=" * 80)
    
    # 1. Verifica estrutura da tabela alerts
    print("\n1️⃣ ESTRUTURA DA TABELA 'alerts':")
    c.execute("PRAGMA table_info(alerts)")
    columns = c.fetchall()
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    # 2. Lista todos os alertas
    print("\n2️⃣ ALERTAS REGISTRADOS:")
    c.execute("SELECT id, person_id, out_time, timestamp, email_sent, snapshot_path FROM alerts ORDER BY timestamp DESC LIMIT 10")
    alerts = c.fetchall()
    
    if not alerts:
        print("   ⚠️ Nenhum alerta encontrado no banco!")
    else:
        for alert in alerts:
            print(f"\n   📌 Alerta ID: {alert[0]}")
            print(f"      Pessoa ID: {alert[1]}")
            print(f"      Tempo fora: {alert[2]:.1f}s")
            print(f"      Timestamp: {alert[3]}")
            print(f"      E-mail enviado: {'✅ Sim' if alert[4] == 1 else '❌ Não'}")
            print(f"      Caminho arquivo: '{alert[5]}'")
            
            # Verifica se o arquivo existe
            if alert[5]:
                # Remove vírgulas e espaços extras (caso tenha múltiplos arquivos)
                files = [f.strip() for f in alert[5].split(',')]
                for file_path in files:
                    if os.path.exists(file_path):
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"         ✅ Arquivo existe: {file_path} ({size_mb:.2f} MB)")
                    else:
                        print(f"         ❌ Arquivo NÃO encontrado: {file_path}")
    
    # 3. Estatísticas
    print("\n3️⃣ ESTATÍSTICAS:")
    c.execute("SELECT COUNT(*) FROM alerts")
    total = c.fetchone()[0]
    print(f"   Total de alertas: {total}")
    
    c.execute("SELECT COUNT(*) FROM alerts WHERE email_sent = 1")
    emails_sent = c.fetchone()[0]
    print(f"   E-mails enviados: {emails_sent}")
    
    c.execute("SELECT COUNT(*) FROM alerts WHERE snapshot_path LIKE '%.mp4'")
    videos = c.fetchone()[0]
    print(f"   Vídeos gravados: {videos}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ Inspeção concluída!")
    print("=" * 80)

if __name__ == "__main__":
    check_database()
