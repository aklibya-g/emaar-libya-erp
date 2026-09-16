import sqlite3
conn = sqlite3.connect('E:/EmarrCoSys/data/emaar_erp.db')
c = conn.cursor()
try:
    c.execute('''CREATE TABLE marketing_bus_rental_prices (
        id VARCHAR(36) PRIMARY KEY,
        vehicle_type_id VARCHAR(36) NOT NULL,
        seats_count INTEGER,
        daily_price FLOAT NOT NULL DEFAULT 0.0,
        notes TEXT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME,
        created_by VARCHAR(36),
        updated_by VARCHAR(36)
    )''')
    print('Table created')
except Exception as e:
    print(f'Error: {e}')
conn.commit()
conn.close()
print('Done')
