import sys
sys.path.insert(0, r'E:\EmarrCoSys')
from src.web.app import create_app
app = create_app()
app.config['TESTING'] = True
app.config['DEBUG'] = True

with app.test_client() as c:
    r = c.get('/auth/login', follow_redirects=True)
    print(f'Login page: {r.status_code}')
    
    r = c.post('/auth/login', data={'username':'admin','password':'admin123'}, follow_redirects=True)
    print(f'Login post: {r.status_code}')
    
    ids = [
        'fd37af7b-b701-48c2-a6db-134bbee3a0c5',
        '4be7ae92-e0be-42f6-9bd7-fe9cc8939f92',
        '81603f77-2d11-4ac0-b9a7-ca7e8d30cc34',
        'cdffdb7d-2506-4df7-98b7-846c07a2cba6',
        'd56f60fd-d429-4783-8c2f-80e499a914b2',
        '4bd2e102-68a0-4e15-8e50-0f43191c6ba8',
        '937b4d62-4501-457f-adfa-500babf665a6',
        'f2a50b8d-9915-4652-b1ab-996fd646f66c',
        'd33d3b11-52c3-4b62-90c3-9ef2eca3dc2f',
        'cf168acc-7551-487d-9a89-731b11c91da1',
    ]
    for cid in ids:
        try:
            r = c.get(f'/correspondence/{cid}', follow_redirects=True)
            if r.status_code != 200:
                print(f'ERROR {cid[:8]}: {r.status_code}')
                html = r.data.decode('utf-8', errors='replace')
                if 'Traceback' in html or 'Error' in html:
                    import re
                    m = re.search(r'<h1>(.*?)</h1>', html)
                    if m: print(f'  Title: {m.group(1)}')
                    m = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL)
                    if m: print(f'  Detail: {m.group(1)[:500]}')
            else:
                has_err = 'error' in r.data.decode('utf-8','replace').lower() and 'server' in r.data.decode('utf-8','replace').lower()
                print(f'OK {cid[:8]}: {r.status_code} ({len(r.data)} bytes) err_in_html={has_err}')
        except Exception as e:
            print(f'EXCEPTION {cid[:8]}: {e}')
