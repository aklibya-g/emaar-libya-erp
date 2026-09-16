import sqlite3
conn = sqlite3.connect('E:/EmarrCoSys/data/emaar_erp.db')
c = conn.cursor()
for col, typ in [
    ('order_type', 'VARCHAR(20) DEFAULT "new"'),
    ('related_order_id', 'VARCHAR(36) DEFAULT NULL'),
    ('amendment_reason', 'TEXT DEFAULT NULL'),
    ('amendment_details', 'TEXT DEFAULT NULL'),
]:
    try:
        c.execute(f'ALTER TABLE marketing_work_orders ADD COLUMN {col} {typ}')
        print(f'{col} added')
    except Exception as e:
        print(f'{col} exists: {e}')
conn.commit()
conn.close()
print('Done')
