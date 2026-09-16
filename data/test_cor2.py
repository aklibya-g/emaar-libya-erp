import sys, re
sys.path.insert(0, r'E:\EmarrCoSys')
from src.web.app import create_app
app = create_app()
app.config['TESTING'] = True

with app.test_client() as c:
    r = c.get('/auth/login')
    m = re.search(r'name="csrf_token".*?value="([^"]+)"', r.data.decode('utf-8','replace'))
    csrf = m.group(1) if m else ''
    print(f'CSRF: {csrf[:20]}...')
    
    r = c.post('/auth/login', data={'username':'admin','password':'admin123','csrf_token':csrf}, follow_redirects=True)
    print(f'Login: {r.status_code} len={len(r.data)}')
    
    r = c.get('/correspondence/fd37af7b-b701-48c2-a6db-134bbee3a0c5', follow_redirects=True)
    html = r.data.decode('utf-8','replace')
    print(f'Detail: {r.status_code} len={len(r.data)}')
    print(f'Has attachments: {"المرفقات" in html}')
    print(f'Has test_doc: {"test_doc" in html}')
    
    # Check for error in rendered HTML
    if 'Internal Server Error' in html or '500' in html[:200]:
        print('ERROR FOUND IN PAGE')
        idx = html.find('Internal')
        if idx >= 0:
            print(html[idx:idx+500])
    else:
        print('Page OK - no errors')
