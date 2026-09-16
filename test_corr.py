import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.web.app import create_app
app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.test_client() as c:
    r = c.post('/auth/login', data={'username':'admin','password':'admin123'}, follow_redirects=True)
    
    # First GET to see the form
    r2 = c.get('/correspondence/add')
    
    # Check what types exist
    import re
    html = r2.data.decode('utf-8')
    types = re.findall(r'<option value="([^"]*)">', html)
    print('Options in type_code:', types[:10])
    
    # POST exactly like browser would
    r3 = c.post('/correspondence/add', data={
        'type_code': 'IN',
        'subject': 'اختبار ارسال',
        'body': 'محتوى اختبار',
        'importance': 'normal',
        'date': '2026-09-08',
        'sender_department_id': '',
        'receiver_department_id': '',
        'responsible_employee_id': '',
        'sender_employee_id': '',
        'notes': '',
        'due_date': '',
    }, follow_redirects=True)
    
    html3 = r3.data.decode('utf-8')
    if 'تم إنشاء' in html3:
        print('SUCCESS: Mail created!')
    elif 'alert-danger' in html3:
        matches = re.findall(r'<div[^>]*alert-danger[^>]*>(.*?)</div>', html3, re.DOTALL)
        for m in matches:
            print('ERROR:', re.sub(r'<[^>]+>', '', m).strip())
    elif 'خطأ' in html3:
        print('ERROR found in page')
    else:
        print('Status:', r3.status_code)
        # Check if still on form page
        if 'إنشاء مراسلة' in html3:
            print('Still on form page - submission failed silently')
            # Look for any error text
            alerts = re.findall(r'class="alert[^"]*"[^>]*>(.*?)</div>', html3, re.DOTALL)
            for a in alerts:
                print('Alert:', re.sub(r'<[^>]+>', '', a).strip()[:200])
