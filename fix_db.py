import sqlite3

db = r"E:\EmarrCoSys\data\emaar_erp.db"
c = sqlite3.connect(db)

cols = [r[1] for r in c.execute("PRAGMA table_info(financial_claims)").fetchall()]
print("Existing columns:", cols)

needed = {
    "trip_type": "VARCHAR(20) DEFAULT 'internal'",
}
for name, typedef in needed.items():
    if name not in cols:
        c.execute(f"ALTER TABLE financial_claims ADD COLUMN {name} {typedef}")
        print(f"Added: {name}")
    else:
        print(f"Already exists: {name}")

c.commit()
c.close()
print("Done!")
