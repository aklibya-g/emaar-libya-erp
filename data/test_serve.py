import sys, re
sys.path.insert(0, r'E:\EmarrCoSys')
from src.web.app import create_app
app = create_app()
app.config['TESTING'] = True

with app.test_client() as c:
    r = c.get('/auth/login')
    m = re.search(r'name="csrf_token".*?value="([^"]+)"', r.data.decode('utf-8','replace'))
    csrf = m.group(1) if m else ''
    c.post('/auth/login', data={'username':'admin','password':'admin123','csrf_token':csrf}, follow_redirects=True)
    
    r = c.get('/correspondence/attachment/1cf2792e-899f-446f-a42c-b17d3969a647/serve', follow_redirects=True)
    print(f'Serve PNG: {r.status_code} content_type={r.content_type} len={len(r.data)}')
    
    r = c.get('/correspondence/attachment/2b769f05-2df9-49ae-b03e-e8721e3e0eaf/serve', follow_redirects=True)
    print(f'Serve PNG2: {r.status_code} content_type={r.content_type} len={len(r.data)}')
    
    r = c.get('/correspondence/attachment/e8ba03e7-42fd-428d-b2d2-4c7c7949065d/serve', follow_redirects=True)
    print(f'Serve missing: {r.status_code}')
