from sqlalchemy import text
from src.core.database.connection import engine
from datetime import date, timedelta

conn = engine.connect()

leave_id = "5cf355c9-924f-4bd5-a69d-cb3665681c77"
emp_id = "8a5a094e-076c-448a-b6c2-d0c2fe499f79"
start = date(2026, 9, 13)
end = date(2026, 9, 23)
current = start
created = 0
while current <= end:
    existing = conn.execute(
        text("SELECT id FROM attendance_records WHERE employee_id = :eid AND record_date = :d"),
        {"eid": emp_id, "d": current}
    ).fetchone()
    if not existing:
        conn.execute(
            text("INSERT INTO attendance_records (id, employee_id, record_date, status, notes, is_manual_entry, delay_minutes, early_leave_minutes, overtime_hours, work_hours, created_at) VALUES (:id, :eid, :d, :status, :notes, 1, 0, 0, 0, 0, datetime('now'))"),
            {"id": f"leave-{emp_id[:8]}-{current}", "eid": emp_id, "d": current, "status": "annual_leave", "notes": f"leave approved - {leave_id}"}
        )
        created += 1
        print(f"Created: {current} -> annual_leave")
    else:
        print(f"Exists: {current}")
    current += timedelta(days=1)
conn.commit()
print(f"\nCreated {created} attendance records")
