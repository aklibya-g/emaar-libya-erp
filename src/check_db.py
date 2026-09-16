import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'E:\EmarrCoSys\data\emaar_erp.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    if 'work' in t.lower() or 'entit' in t.lower() or 'school' in t.lower() or 'bus' in t.lower():
        print(t)
print('---recent work orders---')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%work%'")
wo_tables = [r[0] for r in cur.fetchall()]
print('WO tables:', wo_tables)
if wo_tables:
    for t in wo_tables:
        cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 3")
        cols = [d[0] for d in cur.description]
        print(f'\n=== {t} ===')
        print('Columns:', cols)
        for row in cur.fetchall():
            print(dict(zip(cols, row)))
conn.close()
