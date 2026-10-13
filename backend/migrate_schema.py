import os
import sqlite3
import shutil
from datetime import datetime

def migrate_local_sqlite():
    db_path = "V:/ai-content-origin-detective/backend/detective.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    # 1. Create safety backup
    backup_path = f"V:/ai-content-origin-detective/backend/detective_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(db_path, backup_path)
    print(f"Safety backup created at {backup_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Drop old blockchain_provenance table if it exists
    cur.execute("DROP TABLE IF EXISTS blockchain_provenance;")
    print("Dropped legacy blockchain_provenance table.")

    # Check and add user_id, storage_path, report_storage_path to analyses
    cur.execute("PRAGMA table_info(analyses);")
    analyses_cols = [c[1] for c in cur.fetchall()]
    
    if "user_id" not in analyses_cols:
        cur.execute("ALTER TABLE analyses ADD COLUMN user_id TEXT;")
        print("Added column user_id to analyses")
    if "storage_path" not in analyses_cols:
        cur.execute("ALTER TABLE analyses ADD COLUMN storage_path TEXT;")
        print("Added column storage_path to analyses")
    if "report_storage_path" not in analyses_cols:
        cur.execute("ALTER TABLE analyses ADD COLUMN report_storage_path TEXT;")
        print("Added column report_storage_path to analyses")

    # Check forensic_signals
    cur.execute("PRAGMA table_info(forensic_signals);")
    signals_cols = [c[1] for c in cur.fetchall()]
    if "ela_storage_path" not in signals_cols:
        cur.execute("ALTER TABLE forensic_signals ADD COLUMN ela_storage_path TEXT;")
        print("Added column ela_storage_path to forensic_signals")
    if "fft_storage_path" not in signals_cols:
        cur.execute("ALTER TABLE forensic_signals ADD COLUMN fft_storage_path TEXT;")
        print("Added column fft_storage_path to forensic_signals")

    conn.commit()
    conn.close()
    print("SQLite migration finished successfully.")

if __name__ == "__main__":
    migrate_local_sqlite()
