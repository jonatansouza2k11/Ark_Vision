# limpar_alertas_antigos.py
import sqlite3

conn = sqlite3.connect("cv_system.db")
c = conn.cursor()

# Remove alertas que apontam para arquivos que não existem mais
c.execute("DELETE FROM alerts WHERE snapshot_path LIKE 'alerta_video_id_%'")
c.execute("DELETE FROM alerts WHERE snapshot_path LIKE 'alerta_id_%'")

conn.commit()
print(f"✅ {c.rowcount} alertas antigos removidos")
conn.close()
