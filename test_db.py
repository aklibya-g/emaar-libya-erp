from sqlalchemy import text
from src.core.database.connection import engine
r = engine.connect().execute(text("SELECT full_name_ar, contract_type, driver_number FROM drivers WHERE is_deleted=0 AND status='active'"))
for row in r.all():
    print(f"Name: {row[0]}, Type: {row[1]}, Number: {row[2]}")
