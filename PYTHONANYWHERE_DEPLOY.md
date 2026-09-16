# دليل الرفع على PythonAnywhere

## الخطوة 1: إنشاء حساب
1. اذهب إلى https://www.pythonanywhere.com
2. اضغط **Pricing & Signup**
3. اختر **Create a beginner account** (مجاني)
4. سجّل الدخول بـ GitHub أو الإيميل

## الخطوة 2: رفع الملفات
1. من Dashboard اضغط **Files**
2. اضغط **Upload a file** وارفع المجلد الكامل `E:\EmarrCoSys`
3. أو استخدم **Git** من Console:
```bash
cd ~
git clone https://github.com/aklibya-g/emaar-libya-erp.git
```

## الخطوة 3: إعداد Web App
1. من Dashboard اضغط **Web**
2. اضغط **Add a new web app**
3. اختر **Manual configuration**
4. اختر **Python 3.12**
5. في قسم **Source code**: اختر `emaar-libya-erp`

## الخطوة 4: إعداد WSGI
1. اضغط على ملف **WSGI configuration file** (الرابط会在 نهاية الصفحة)
2. احذف المحتوى الحالي وضع هذا الكود:

```python
import os
import sys

# Add project directory to path
project_home = os.path.expanduser('~/emaar-libya-erp')
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_APP'] = 'src.web.app:create_app'

from src.web.app import create_app
application = create_app()
```

3. اضغط **Save**

## الخطوة 5: تثبيت المكتبات
1. من Dashboard اضغط **Console**
2. شغّل الأوامر التالية:

```bash
cd ~/emaar-libya-erp
pip3 install --user Flask Flask-Login Flask-WTF SQLAlchemy alembic pydantic pydantic-settings bcrypt Jinja2 WTForms gunicorn python-dotenv Pillow reportlab openpyxl qrcode pyjwt loguru cryptography
```

## الخطوة 6: إعداد قاعدة البيانات
1. من Console شغّل:

```bash
cd ~/emaar-libya-erp
python3 -c "
from src.web.app import create_app
app = create_app()
with app.app_context():
    from src.core.database.connection import init_database
    init_database()
    print('Database initialized!')
"
```

## الخطوة 7: تشغيل الموقع
1. من Dashboard اضغط **Web**
2. اضغط **Reload**
3. الموقع يعمل على: `https://yourusername.pythonanywhere.com`

## بيانات الدخول الافتراضية
- المستخدم: `admin`
- كلمة المرور: `admin123`

## ملاحظات مهمة
- الموقع مجاني دائماً (لا يتوقف)
- MySQL مجاني (1GB)
- لا يحتاج بطاقة ائتمان
- يمكنك الترقية لاحقاً ($5/شهر) لتحسين الأداء
