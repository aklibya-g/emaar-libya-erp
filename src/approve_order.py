import urllib.request, urllib.parse, http.cookiejar, re, sys
sys.stdout.reconfigure(encoding='utf-8')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
req = urllib.request.Request('http://127.0.0.1:5000/auth/login')
resp = opener.open(req)
page = resp.read().decode('utf-8')
csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)

data = urllib.parse.urlencode({'username':'admin','password':'admin123','csrf_token':csrf}).encode()
req2 = urllib.request.Request('http://127.0.0.1:5000/auth/login', data=data, method='POST')
resp2 = opener.open(req2)
for i in range(5):
    next_url = resp2.headers.get('Location')
    if not next_url: break
    if next_url.startswith('/'): next_url = 'http://127.0.0.1:5000' + next_url
    resp2 = opener.open(urllib.request.Request(next_url))
print('Logged in')

wo_id = '14d25ed4-e6c3-4824-bb12-4dda53a350c8'
departments = ['marketing', 'movement', 'finance', 'executive']
dept_labels = ['التسويق', 'الحركة', 'المالية', 'المدير التنفيذي']

for i, dept in enumerate(departments):
    # Get CSRF from detail page
    detail_resp = opener.open(urllib.request.Request(f'http://127.0.0.1:5000/marketing/work-orders/{wo_id}'))
    detail_page = detail_resp.read().decode('utf-8')
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', detail_page)
    if not csrf_match:
        print(f'{dept_labels[i]}: CSRF not found!')
        continue
    csrf = csrf_match.group(1)
    
    approve_url = f'http://127.0.0.1:5000/marketing/work-orders/{wo_id}/approve'
    post_data = urllib.parse.urlencode({'csrf_token': csrf, 'department': dept}).encode()
    req3 = urllib.request.Request(approve_url, data=post_data, method='POST')
    try:
        resp3 = opener.open(req3)
        loc = resp3.headers.get('Location', '')
        body = resp3.read().decode('utf-8', errors='ignore')
        # Look for flash messages
        flash_match = re.search(r"alert-(\w+)[^>]*>([^<]+)", body)
        if flash_match:
            print(f'{dept_labels[i]}: {flash_match.group(2)}')
        else:
            print(f'{dept_labels[i]}: OK (redirect: {loc})')
    except urllib.error.HTTPError as e:
        print(f'{dept_labels[i]}: HTTP {e.code}')
        body = e.read().decode('utf-8', errors='ignore')
        flash = re.search(r"alert-(\w+)[^>]*>([^<]+)", body)
        if flash:
            print(f'  Flash: {flash.group(2)}')
