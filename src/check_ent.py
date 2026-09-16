import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r'E:\EmarrCoSys\data\emaar_erp.db')
cur = conn.cursor()
wo_id = '14d25ed4-e6c3-4824-bb12-4dda53a350c8'
cur.execute('SELECT destination, trip_from, trip_to, trip_route, departure_date, return_date, client_id FROM marketing_work_orders WHERE id=?', (wo_id,))
wo = cur.fetchone()
print(f'destination: "{wo[0]}"')
print(f'trip_from: "{wo[1]}"')
print(f'trip_to: "{wo[2]}"')
print(f'trip_route: "{wo[3]}"')
print(f'departure: "{wo[4]}"')
print(f'return: "{wo[5]}"')

# Get client name
cur.execute('SELECT name_ar FROM marketing_clients WHERE id=?', (wo[6],))
cl = cur.fetchone()
print(f'client: "{cl[0] if cl else "?"}"')
conn.close()
