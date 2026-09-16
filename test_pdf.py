import sys
sys.path.insert(0, 'E:/EmarrCoSys')
from src.web.app import create_app
app = create_app()
app.config['LOGIN_DISABLED'] = True
with app.test_client() as c:
    r = c.get('/hr/attendance/report/pdf?year=2026&month=9&person_type=employees')
    print(f'Status: {r.status_code}, Size: {len(r.data)} bytes')
    if r.status_code == 200 and len(r.data) > 500:
        with open('E:/EmarrCoSys/test.pdf', 'wb') as f:
            f.write(r.data)
        print('PDF saved!')
    else:
        print(f'Error: {r.data[:500].decode(errors="replace")}')
