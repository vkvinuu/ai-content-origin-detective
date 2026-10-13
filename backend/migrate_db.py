import os
import sqlite3
import sys

def check_and_migrate():
    db_path = "V:/ai-content-origin-detective/backend/detective.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print("Existing tables:", tables)
    
    for t in tables:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t});").fetchall()]
        print(f"Table {t} columns: {cols}")

    # Ensure all columns exist for ml_evaluations
    cur_cols = [c[1] for c in cur.execute("PRAGMA table_info(ml_evaluations);").fetchall()]
    expected_ml = {
        "architecture": "TEXT",
        "specialization": "TEXT",
        "known_limitation": "TEXT",
        "normalized_probabilities": "TEXT", # JSON stored as TEXT in sqlite
    }
    for col, col_type in expected_ml.items():
        if col not in cur_cols:
            print(f"Adding column {col} to ml_evaluations")
            cur.execute(f"ALTER TABLE ml_evaluations ADD COLUMN {col} {col_type};")

    conn.commit()

    # Re-verify
    updated_cols = [c[1] for c in cur.execute("PRAGMA table_info(ml_evaluations);").fetchall()]
    print("Updated ml_evaluations columns:", updated_cols)
    conn.close()

if __name__ == "__main__":
    check_and_migrate()
