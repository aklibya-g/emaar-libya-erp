from __future__ import annotations

from datetime import date, timedelta

from src.core.database.connection import session_scope
from src.core.models.base_models import (
    Role, Permission, RolePermission, Company, Department, Position,
    Employee, Driver, Customer, Warehouse, ItemCategory, ItemUnit,
    Item, Supplier, CorrespondenceType, CorrespondenceStatus,
    City, VehicleType, LicenseType,
)
from src.core.repositories.base_repository import BaseRepository
from src.core.security.auth_service import hash_password


def seed_roles(session):
    repo = BaseRepository(session, Role)

    roles_data = [
        ("Super Admin", "مسؤول النظام", True),
        ("System Administrator", "مدير النظام", True),
        ("General Manager", "المدير العام", False),
        ("Department Manager", "مدير القسم", False),
        ("HR Officer", "مسؤول الموارد البشرية", False),
        ("Administrative Officer", "مسؤول إداري", False),
        ("Warehouse Officer", "مسؤول المخازن", False),
        ("Correspondence Officer", "مسؤول المراسلات", False),
        ("Auditor", "مدقق", False),
        ("Viewer", "مشاهد", False),
    ]

    roles = {}
    for name, name_ar, is_system in roles_data:
        r = repo.create(name=name, name_ar=name_ar, is_system=is_system)
        roles[name] = r

    perms_repo = BaseRepository(session, Permission)
    modules = {
        "employees": ["view", "create", "update", "delete"],
        "drivers": ["view", "create", "update", "delete"],
        "customers": ["view", "create", "update", "delete"],
        "correspondence": ["view", "create", "update", "delete", "forward", "approve"],
        "warehouses": ["view", "create", "update", "delete"],
        "documents": ["view", "create", "update", "delete", "approve", "sign"],
        "reports": ["view", "export"],
        "settings": ["view", "update"],
        "users": ["view", "create", "update", "delete"],
    }

    for module, actions in modules.items():
        for action in actions:
            p = perms_repo.create(
                module=module,
                screen=module,
                action=action,
                description=f"{module}/{action}",
            )
            for role_name in ["Super Admin", "System Administrator"]:
                rp_repo = BaseRepository(session, RolePermission)
                rp_repo.create(
                    role_id=roles[role_name].id,
                    permission_id=p.id,
                    granted=True,
                )

    return roles


def seed_company(session):
    repo = BaseRepository(session, Company)
    return repo.create(
        name_ar="شركة إعمار ليبيا لنقل الركاب",
        name_en="Emaar Libya Passenger Transport",
        country="Libya",
        address="طرابلس، ليبيا",
        phone="+218 21 XXX XXXX",
        email="info@emaarlibya.com",
    )


def seed_departments(session, company_id):
    repo = BaseRepository(session, Department)
    depts = [
        ("HR", "الموارد البشرية", "Human Resources"),
        ("ADM", "الشؤون الإدارية", "Administrative Affairs"),
        ("FIN", "المالية", "Finance"),
        ("OPS", "التشغيل والنقل", "Operations & Transport"),
        ("WH", "المخازن", "Warehouses"),
        ("IT", "تقنية المعلومات", "Information Technology"),
        ("COR", "المراسلات والأرشيف", "Correspondence & Archive"),
    ]
    departments = {}
    for code, name_ar, name_en in depts:
        d = repo.create(code=code, name_ar=name_ar, name_en=name_en, company_id=company_id)
        departments[code] = d
    return departments


def seed_positions(session, departments):
    repo = BaseRepository(session, Position)
    positions = [
        ("المدير العام", "General Manager", None),
        ("مدير القسم", "Department Manager", None),
        ("مسؤول الموارد البشرية", "HR Officer", "HR"),
        ("محاسب", "Accountant", "FIN"),
        ("مسؤول المراسلات", "Correspondence Officer", "COR"),
        ("مسؤول المخازن", "Warehouse Officer", "WH"),
        ("سائق", "Driver", "OPS"),
        ("موظف إداري", "Administrative Staff", "ADM"),
        ("مهندس شبكات", "Network Engineer", "IT"),
        ("مساعد إداري", "Administrative Assistant", "ADM"),
    ]
    pos_list = []
    for name_ar, name_en, dept_code in positions:
        dept_id = departments[dept_code].id if dept_code and dept_code in departments else None
        p = repo.create(name_ar=name_ar, name_en=name_en, department_id=dept_id)
        pos_list.append(p)
    return pos_list


def seed_employees(session, departments, positions):
    repo = BaseRepository(session, Employee)
    employees_data = [
        ("EMP-001", "أحمد محمد علي", "Ahmed Mohammed Ali", "OPS", 1, 1500),
        ("EMP-002", "فاطمة عبد الرحمن", "Fatima Abdelrahman", "HR", 2, 1200),
        ("EMP-003", "عمر سعيد♚", "Omar Said", "FIN", 3, 1200),
        ("EMP-004", "مريم حسن", "Mariam Hassan", "ADM", 4, 1000),
        ("EMP-005", "يوسف إبراهيم", "Yousef Ibrahim", "OPS", 6, 900),
        ("EMP-006", "خديجة محمود", "Khadijah Mahmoud", "COR", 5, 900),
        ("EMP-007", "علي عمر", "Ali Omar", "WH", 6, 850),
        ("EMP-008", "نورة سالم", "Noura Salem", "IT", 9, 1300),
        ("EMP-009", "سالم أحمد", "Salem Ahmed", "OPS", 6, 900),
        ("EMP-010", "هدى محمد", "Huda Mohammed", "HR", 2, 950),
    ]

    dept_map = {d.code: d.id for d in departments.values()}
    employees = []
    for emp_num, name_ar, name_en, dept_code, pos_idx, salary in employees_data:
        dept_id = dept_map.get(dept_code)
        pos_id = positions[pos_idx - 1].id if pos_idx <= len(positions) else None
        e = repo.create(
            employee_number=emp_num,
            full_name_ar=name_ar,
            full_name_en=name_en,
            department_id=dept_id,
            position_id=pos_id,
            hire_date=date(2023, 1, 15) + timedelta(days=len(employees) * 30),
            salary=salary,
            status="active",
            phone=f"+218 91 {1000000 + len(employees):07d}",
        )
        employees.append(e)
    return employees


def seed_drivers(session, employees):
    repo = BaseRepository(session, Driver)
    drivers = []
    drivers_data = [
        ("DRV-001", "عبد الله محمد", "Abdullah Mohammed", "+218 92 1234567", "C"),
        ("DRV-002", "حسن علي", "Hassan Ali", "+218 92 2345678", "C"),
        ("DRV-003", "مصطفى إبراهيم", "Mustafa Ibrahim", "+218 92 3456789", "C"),
        ("DRV-004", "إبراهيم خالد", "Ibrahim Khalid", "+218 92 4567890", "C"),
        ("DRV-005", "أنس سعيد", "Anas Said", "+218 92 5678901", "C"),
    ]
    for drv_num, name_ar, name_en, phone, lic_type in drivers_data:
        d = repo.create(
            driver_number=drv_num,
            full_name_ar=name_ar,
            full_name_en=name_en,
            phone=phone,
            license_type=lic_type,
            license_number=f"LY-{drv_num[-3:]}",
            license_issue_date=date(2024, 1, 1),
            license_expiry_date=date(2026, 12, 31),
            license_issuing_authority="مرور طرابلس",
            join_date=date(2023, 6, 1),
            status="active",
        )
        drivers.append(d)
    return drivers


def seed_customers(session):
    repo = BaseRepository(session, Customer)
    customers = []
    customers_data = [
        ("CUS-001", "محمد عبدالله", "Libya Tours", "individual", "+218 91 1111111", "طرابلس"),
        ("CUS-002", "أحمد سالم", "Tripoli Transport Co.", "corporate", "+218 91 2222222", "طرابلس"),
        ("CUS-003", "سارة حسن", "Benghazi Express", "corporate", "+218 91 3333333", "بنغازي"),
        ("CUS-004", "خالد محمد", "Misrata Logistics", "corporate", "+218 91 4444444", "مصراتة"),
        ("CUS-005", "ليلى أحمد", "Sabratha Travel", "individual", "+218 91 5555555", "صبراتة"),
        ("CUS-006", "عمر فتحي", "Zliten Transport", "corporate", "+218 91 6666666", "الزليتن"),
        ("CUS-007", "نجلاء علي", "Sirte Express", "individual", "+218 91 7777777", "سرت"),
        ("CUS-008", "ياسر صلاح", "Derba Moving", "corporate", "+218 91 8888888", "درنة"),
        ("CUS-009", "هدى عبد الله", "Tobruk Services", "individual", "+218 91 9999999", "طبرق"),
        ("CUS-010", "ماجد سعيد", "Fezzan Transport", "corporate", "+218 91 0000000", "سبها"),
    ]
    for cus_num, name_ar, comp, ctype, phone, city in customers_data:
        c = repo.create(
            customer_number=cus_num,
            name_ar=name_ar,
            company_name=comp,
            customer_type=ctype,
            phone=phone,
            city=city,
            country="Libya",
            status="active",
        )
        customers.append(c)
    return customers


def seed_warehouses(session):
    repo = BaseRepository(session, Warehouse)
    wh = []
    warehouses = [
        ("WH-001", "المخزن الرئيسي", "Main Warehouse"),
        ("WH-002", "مخزن الوقود", "Fuel Warehouse"),
        ("WH-003", "مخزن قطع الغيار", "Spare Parts Warehouse"),
    ]
    for code, name_ar, name_en in warehouses:
        w = repo.create(code=code, name_ar=name_ar, name_en=name_en, status="active")
        wh.append(w)
    return wh


def seed_items(session, warehouses):
    cat_repo = BaseRepository(session, ItemCategory)
    unit_repo = BaseRepository(session, ItemUnit)
    item_repo = BaseRepository(session, Item)

    cats = {
        "FUEL": cat_repo.create(code="FUEL", name_ar="وقود", name_en="Fuel"),
        "SPARE": cat_repo.create(code="SPARE", name_ar="قطع غيار", name_en="Spare Parts"),
        "MAINT": cat_repo.create(code="MAINT", name_ar="صيانة", name_en="Maintenance"),
        "OFFICE": cat_repo.create(code="OFFICE", name_ar="مكاتب", name_en="Office Supplies"),
    }

    units = {
        "LTR": unit_repo.create(name_ar="لتر", name_en="Liter", symbol="L"),
        "PCS": unit_repo.create(name_ar="قطعة", name_en="Piece", symbol="pc"),
        "BOX": unit_repo.create(name_ar="علبة", name_en="Box", symbol="box"),
        "KG": unit_repo.create(name_ar="كيلوجرام", name_en="Kilogram", symbol="kg"),
    }

    items_data = [
        ("ITM-001", "بنزين 95", "Petrol 95", "FUEL", "LTR", 0, 10000, 5000, 1.2, warehouses[1].id),
        ("ITM-002", "ديزل", "Diesel", "FUEL", "LTR", 0, 15000, 8000, 0.9, warehouses[1].id),
        ("ITM-003", "زيت محرك", "Engine Oil", "SPARE", "LTR", 10, 100, 45, 15.0, warehouses[2].id),
        ("ITM-004", "فلتر زيت", "Oil Filter", "SPARE", "PCS", 20, 200, 80, 8.0, warehouses[2].id),
        ("ITM-005", "فلتر هواء", "Air Filter", "SPARE", "PCS", 15, 150, 60, 6.5, warehouses[2].id),
        ("ITM-006", "فرامل أمامية", "Front Brake Pads", "SPARE", "PCS", 10, 50, 25, 35.0, warehouses[2].id),
        ("ITM-007", "شريط ورق", "Paper Ream", "OFFICE", "BOX", 20, 100, 50, 5.0, warehouses[0].id),
        ("ITM-008", "حبر طابعة", "Printer Ink", "OFFICE", "PCS", 10, 50, 30, 12.0, warehouses[0].id),
        ("ITM-009", "شاحن بطارية", "Battery Charger", "MAINT", "PCS", 5, 20, 10, 25.0, warehouses[2].id),
        ("ITM-010", "مصباح سيارة", "Car Light", "SPARE", "PCS", 10, 40, 20, 18.0, warehouses[2].id),
    ]

    items = []
    for code, name_ar, name_en, cat, unit, min_q, max_q, cur, price, wh_id in items_data:
        i = item_repo.create(
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            category_id=cats[cat].id,
            unit_id=units[unit].id,
            warehouse_id=wh_id,
            min_quantity=min_q,
            max_quantity=max_q,
            current_quantity=cur,
            unit_price=price,
            status="active",
        )
        items.append(i)
    return items


def seed_correspondence_types(session):
    repo = BaseRepository(session, CorrespondenceType)
    types = [
        ("IN", "وارد", "Incoming", "و"),
        ("OUT", "صادر", "Outgoing", "ص"),
        ("INT", "داخلي", "Internal", "د"),
        ("EXT", "خارجي", "External", "خ"),
        ("MEMO", "مذكرة", "Memo", "م"),
        ("DEC", "قرار", "Decision", "ق"),
        ("CIRC", "تعميم", "Circular", "ت"),
        ("LET", "خطاب", "Letter", "ل"),
    ]
    for code, name_ar, name_en, prefix in types:
        repo.create(code=code, name_ar=name_ar, name_en=name_en, numbering_prefix=prefix, direction=code)


def seed_correspondence_statuses(session):
    repo = BaseRepository(session, CorrespondenceStatus)
    statuses = [
        ("DRAFT", "مسودة", 0, "#6b7280", False),
        ("REVIEW", "قيد المراجعة", 1, "#f59e0b", False),
        ("APPROVED", "معتمد", 2, "#3b82f6", False),
        ("SIGNED", "موقع", 3, "#8b5cf6", False),
        ("STAMPED", "مختم", 4, "#06b6d4", False),
        ("SENT", "تم الإرسال", 5, "#10b981", False),
        ("RECEIVED", "تم الاستلام", 6, "#10b981", False),
        ("FORWARDED", "محال", 7, "#f59e0b", False),
        ("COMPLETED", "تم التنفيذ", 8, "#059669", False),
        ("ARCHIVED", "مؤرشف", 9, "#6b7280", True),
        ("CANCELLED", "ملغي", 10, "#ef4444", True),
    ]
    for code, name_ar, order, color, terminal in statuses:
        repo.create(code=code, name_ar=name_ar, sort_order=order, color=color, is_terminal=terminal)


def seed_master_data(session):
    city_repo = BaseRepository(session, City)
    cities = [
        ("طرابلس", "Tripoli", 1),
        ("بنغازي", "Benghazi", 2),
        ("مصراتة", "Misrata", 3),
        ("الزليتن", "Zliten", 4),
        ("صبراتة", "Sabratha", 5),
        ("سرت", "Sirte", 6),
        ("درنة", "Derna", 7),
        ("طبرق", "Tobruk", 8),
        ("سبها", "Sabha", 9),
        ("غدامس", "Ghadames", 10),
    ]
    for ar, en, order in cities:
        city_repo.create(name_ar=ar, name_en=en, country="Libya", sort_order=order)

    vt_repo = BaseRepository(session, VehicleType)
    vtypes = [("B BUS", "باص كبير"), ("S BUS", "باص صغير"), ("VAN", "فان"), ("CAR", "سيارة")]
    for code, name in vtypes:
        vt_repo.create(code=code, name_ar=name)

    lt_repo = BaseRepository(session, LicenseType)
    ltypes = [("C", "رخصة قيادة عامة"), ("D", "رخصة قيادة عامة"), ("B1", "رخصة خاصة")]
    for code, name in ltypes:
        lt_repo.create(code=code, name_ar=name)


def run_seed():
    with session_scope() as session:
        roles = seed_roles(session)
        company = seed_company(session)
        departments = seed_departments(session, company.id)
        positions = seed_positions(session, departments)
        employees = seed_employees(session, departments, positions)
        drivers = seed_drivers(session, employees)
        customers = seed_customers(session)
        warehouses = seed_warehouses(session)
        items = seed_items(session, warehouses)
        seed_correspondence_types(session)
        seed_correspondence_statuses(session)
        seed_master_data(session)
        print("Seed data created successfully!")


if __name__ == "__main__":
    from src.core.database.connection import init_database
    from src.app.config import ensure_directories
    ensure_directories()
    init_database()
    run_seed()
