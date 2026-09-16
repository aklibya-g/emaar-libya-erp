import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'E:\EmarrCoSys\data\emaar_erp.db')
cur = conn.cursor()
wo_id = '14d25ed4-e6c3-4824-bb12-4dda53a350c8'

# Get order data
cur.execute('SELECT destination, trip_from, trip_to, trip_route, departure_date FROM marketing_work_orders WHERE id=?', (wo_id,))
wo = cur.fetchone()
dest = wo[0] or ''
trip_from = wo[1] or ''
trip_to = wo[2] or ''
trip_route = wo[3] or ''
dep_date = wo[4] or ''

# Build route
if trip_from or trip_to:
    route = f"{trip_from} ← {trip_to}"
elif dest:
    route = dest
elif trip_route:
    route = trip_route
else:
    route = '-'

print(f'Route: {route}')
print(f'Departure: {dep_date}')

# Update entitlement
cur.execute('UPDATE marketing_school_driver_entitlements SET route=?, entitlement_date=? WHERE work_order_id=?', (route, dep_date, wo_id))
print(f'Updated {cur.rowcount} rows')
conn.commit()
conn.close()
