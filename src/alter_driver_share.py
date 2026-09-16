import sqlite3

conn = sqlite3.connect(r"E:\EmarrCoSys\data\emaar_erp.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE marketing_work_orders ADD COLUMN trip_type TEXT DEFAULT 'internal'")
    print("Added trip_type")
except Exception as e:
    print(f"trip_type: {e}")

try:
    cur.execute("ALTER TABLE marketing_work_order_buses ADD COLUMN driver_share_pct REAL DEFAULT 10.0")
    print("Added driver_share_pct")
except Exception as e:
    print(f"driver_share_pct: {e}")

try:
    cur.execute("ALTER TABLE marketing_work_order_buses ADD COLUMN driver_share_value REAL DEFAULT 0.0")
    print("Added driver_share_value")
except Exception as e:
    print(f"driver_share_value: {e}")

conn.commit()
conn.close()
print("Done")
