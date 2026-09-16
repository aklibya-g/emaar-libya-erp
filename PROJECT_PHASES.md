# مراحل تنفيذ مشروع إعمار ليبيا لنقل الركاب

---

## المرحلة 1: الأساسيات والبنية التحتية (أسابيع 1-3)
**الهدف:** بيئة عمل مستقرة + Authentication + Company/Departments + Employees CRUD

### المخرجات:
- [ ] Project structure + Poetry/pyproject.toml
- [ ] Database layer (SQLAlchemy + Alembic + SQLite/PostgreSQL)
- [ ] Models: User, Role, Permission, Company, Department, Employee
- [ ] RBAC system (decorators/checks)
- [ ] Login/Logout + Session management
- [ ] Main Window + Sidebar + TopBar + RTL Support
- [ ] Company Setup Wizard (أول تشغيل)
- [ ] Employee CRUD + Search + Basic Validation
- [ ] Audit Log foundation
- [ ] Unit tests for core models/services

### معايير القبول:
- يمكن إنشاء شركة وأقسام وموظفين
- تسجيل دخول بأدوار مختلفة
- كل عملية تسجل في Audit Log
- الواجهة RTL عربية كاملة

---

## المرحلة 2: المراسلات والأرشفة (أسابيع 4-7)
**الهدف:** نظام مراسلات متكامل مع دورة حياة كاملة

### المخرجات:
- [ ] Models: Correspondence, Type, Status, Route, Action, Attachment, Link
- [ ] Numbering Engine (قواعد ترقيم قابلة للتخصيص)
- [ ] Correspondence Workflow Engine (Draft→Review→Approve→Sign→Stamp→Send→Archive)
- [ ] Inbox/Outbox/Internal/External views مع Advanced Search
- [ ] Referral/Forwarding بين الأقسام مع إشعارات
- [ ] Document Linking (وارد↔صادر، مراسلة↔موظف↔عقد)
- [ ] Template System (Jinja2/HTML + Variables)
- [ ] Signature & Stamp Management (PNG transparent, positioning)
- [ ] PDF Generation (WeasyPrint/ReportLab) مع QR Code + Verification Code
- [ ] Document Versioning
- [ ] Archive Module (تصنيف، بحث، استرجاع)
- [ ] Reports: وارد/صادر/متأخر/حسب القسم/الموظف/الفترة

### معايير القبول:
- إنشاء مراسلة → توليد رقم إشاري تلقائي
- إحالة لقسم آخر → إشعار المستلم
- اعتماد → توقيع → ختم → PDF نهائي غير قابل للتعديل
- بحث متقدم بجميع الفلاتر
- تقارير PDF/Excel جاهزة للطباعة

---

## المرحلة 3: الموارد البشرية والسائقين (أسابيع 8-11)
**الهدف:** ملف موظف إلكتروني كامل + إدارة سائقين

### المخرجات:
- [ ] Employee Service File (عقود، قرارات، مؤهلات، دورات، تقييمات، إنذارات، جزاءات، إجازات)
- [ ] Leave Management (أنواع، رصيد، سير عمل موافقة، تقويم)
- [ ] Performance Evaluation (معايير، فترات، تقارير رسومية)
- [ ] Driver Management (رخص، تواريخ انتهاء، تنبيهات، مستندات، جزاءات)
- [ ] Driver-Employee linking (اختياري)
- [ ] HR Reports: كشوف، عقود منتهية، إجازات، أداء، سائقين
- [ ] Notifications: انتهاء عقود، رخص، إجازات، تقييمات

### معايير القبول:
- ملف موظف كامل مع مرفقات قابلة للفتح
- طلب إجازة → موافقة مدير → تحديث رصيد
- تقييم أداء دوري مع رسوم بيانية
- تنبيه تلقائي: "رخصة سائق تنتهي خلال 30 يوم"

---

## المرحلة 4: العملاء + المخازن + الشؤون الإدارية (أسابيع 12-15)
**الهدف:** الوحدات التشغيلية والداعمة

### المخرجات:
- [ ] Customer CRM (بيانات، تعاملات، شكاوى، عقود، مراسلات، فواتير مستقبلية)
- [ ] Warehouse Management (مخازن، أصناف، تصنيفات، وحدات، موردين، حركات، جرد، تنبيهات حد أدنى)
- [ ] Administrative Affairs (قرارات، تكليفات، إخطارات، محاضر، عهد، أصول، سيارات، نماذج)
- [ ] Cross-module linking (مراسلة↔عميل، صرف مخزن↔مراسلة، قرار↔موظف)
- [ ] Reports: عملاء، مخزون، حركات، جرد، شؤون إدارية

### معايير القبول:
- إدارة كاملة لعملاء النقل
- حركة مخزون دقيقة مع أرصدة فورية
- شؤون إدارية مرقمة ومحفوظة

---

## المرحلة 5: التقارير المتقدمة + الإعدادات + النشر (أسابيع 16-18)
**الهدف:** نظام Production-Ready

### المخرجات:
- [ ] Report Engine مركزي (Preview/Print/PDF/Excel/CSV + Grouping/Sorting/Headers)
- [ ] Dashboard Analytics (Charts: Bar/Line/Pie/KPI/Trend - بيانات حقيقية)
- [ ] Notification Center + Task Center
- [ ] Global Search (موظف/سائق/عميل/مراسلة/مستند/عقد)
- [ ] Settings Module (شركة، ترقيم، مراسلات، توقيعات، أختام، تemplates، Backup، لغة، عملة)
- [ ] Backup Manager (Manual/Scheduled/Restore/History)
- [ ] Form Designer (Custom Fields - اختياري)
- [ ] PyInstaller Build + Installer (Shortcuts، Data Folder)
- [ ] Seed Data واقعي للاختبار
- [ ] Documentation (README، API Docs، User Guide)
- [ ] Integration Tests + E2E Tests

### معايير القبول:
- Dashboard تفاعلي مع Charts حقيقية
- Backup/Restore يعمل
- Installable .exe على Windows
- النظام جاهز للاستخدام الفعلي

---

## مصفوفة الاعتماديات

| المرحلة | تعتمد على |
|----------|-----------|
| 1 | لا شيء (الأساس) |
| 2 | 1 (Users، Departments، Audit، Templates) |
| 3 | 1 (Employees، Departments، Users) |
| 4 | 1، 2 (مراسلات مرتبطة بعملاء/مخازن/شؤون) |
| 5 | 1-4 (تجمع كل شيء) |

---

## تقنية موحدة لكل المراحل

| الطبقة | التقنية |
|---------|---------|
| UI | PySide6 (Qt6) + QSS Theming |
| ORM | SQLAlchemy 2.0 + Alembic |
| DB | SQLite (dev) / PostgreSQL (prod) |
| PDF | WeasyPrint (HTML/CSS) + ReportLab (للجداول المعقدة) |
| Excel | OpenPyXL |
| Crypto | bcrypt (passwords) + cryptography (sensitive data) |
| Charts | Qt Charts / PyQtGraph |
| Testing | pytest + pytest-qt |
| Packaging | PyInstaller + NSIS/Inno Setup |
| Config | pydantic-settings + .env |

---

## قواعد التطوير (غير قابلة للتفاوض)

1. **لا UI بدون Service Layer** - كل شاشة لها Service مُختبر
2. **لا Service بدون Repository** - فصل كامل للبيانات
3. **لا Model بدون Migration** - Alembic لكل تغيير
4. **لا Feature بدون Permission Check** - RBAC على مستوى Action
5. **لا عملية حساسة بدون Audit Log** - تلقائي عبر Decorator/Event
5. **لا Hardcoding** - كل شيء في Settings/Config/Master Data
6. **Type Hints إلزامية** + Docstrings للـ Public API
7. **Tests لكل Module** - Unit + Integration قبل الانتقال للمرحلة التالية