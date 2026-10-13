import os, sqlite3, sys

def add_column(cur, table, column, col_type):
    try:
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
        print(f'Added column {column}')
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e).lower():
            print(f'Column {column} already exists')
        else:
            print(f'Error adding {column}:', e)
            raise

def main():
    db_path = os.path.join('V:/ai-content-origin-detective/backend', 'detective.db')
    if not os.path.isfile(db_path):
        print('Database file not found at', db_path)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    add_column(cur, 'ml_evaluations', 'architecture', 'TEXT')
    add_column(cur, 'ml_evaluations', 'specialization', 'TEXT')
    add_column(cur, 'ml_evaluations', 'known_limitation', 'TEXT')
    conn.commit()
    conn.close()
    print('Schema update complete')

if __name__ == '__main__':
    main()
