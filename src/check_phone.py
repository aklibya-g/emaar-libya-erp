import urllib.request, urllib.parse, http.cookiejar, re, sys
sys.stdout.reconfigure(encoding='utf-8')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request('http://127.0.0.1:5000/auth/login')
resp = opener.open(req)
page = resp.read().decode('utf-8')
csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)

data = urllib.parse.urlencode({'username':'admin','password':'admin123','csrf_token':csrf}).encode()
req2 = urllib.request.Request('http://127.0.0.1:5000/auth/login', data=data, method='POST')
resp2 = opener.open(req2)
# Follow redirects manually
for i in range(5):
    try:
        next_url = resp2.headers.get('Location')
        if not next_url:
            break
        if next_url.startswith('/'):
            next_url = 'http://127.0.0.1:5000' + next_url
        req_next = urllib.request.Request(next_url)
        resp2 = opener.open(req_next)
    except:
        break

req3 = urllib.request.Request('http://127.0.0.1:5000/marketing/work-orders/add')
resp3 = opener.open(req3)
form = resp3.read().decode('utf-8')

# Check for data-phone
phone_matches = re.findall(r'data-phone="([^"]*)"', form)
print(f"data-phone values found: {len(phone_matches)}")
for i, p in enumerate(phone_matches[:3]):
    print(f"  {i}: '{p}'")

# Check for clientId
if 'clientId' in form:
    print("clientId: FOUND")
else:
    print("clientId: NOT FOUND")

# Check for contactPhone
if 'contactPhone' in form:
    print("contactPhone: FOUND")
else:
    print("contactPhone: NOT FOUND")

# Check loadClientPhone
if 'loadClientPhone' in form:
    print("loadClientPhone: FOUND")
else:
    print("loadClientPhone: NOT FOUND")

# Check the onchange attribute on clientId
match = re.search(r'id="clientId"[^>]*onchange="([^"]*)"', form)
if match:
    print(f"onchange: {match.group(1)}")
elif re.search(r'onchange="[^"]*"[^>]*id="clientId"', form):
    print("onchange found (before id)")
else:
    # Try other order
    idx = form.find('clientId')
    if idx > -1:
        context = form[idx-200:idx+200]
        match2 = re.search(r'onchange="([^"]*)"', context)
        if match2:
            print(f"onchange near clientId: {match2.group(1)}")
