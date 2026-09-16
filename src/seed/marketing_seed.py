"""
بيانات شهر اغسطس 2026 التجريبية
ựa على الصور المرفقة من التصميم
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from datetime import date, datetime
from src.core.database.connection import init_database, get_web_session
from src.core.models.marketing_models import (
    MarketingClient, MarketingContract, WorkOrder, WorkOrderBus, WorkOrderAnnex,
    Trip, SchoolDriverEntitlement
)

def seed_august_2026():
    init_database()

    with get_web_session() as session:
        # ============================================================
        # 1. العملاء (الجهات)
        # ============================================================
        clients_data = [
            {"name_ar": "شركة فاوكية", "phone": "091-1234567", "scope": "نقل موظفين"},
            {"name_ar": "شركة جسر الرواد", "phone": "092-2345678", "scope": "نقل طلاب"},
            {"name_ar": "شركة التميز", "phone": "093-3456789", "scope": "نقل ركاب"},
            {"name_ar": "المركز الليبي للتنمية", "phone": "094-4567890", "scope": "تدريب"},
            {"name_ar": "كشف", "phone": "095-5678901", "scope": "نقل موظفين"},
            {"name_ar": "مدرسة المجايدة الاساسية للبنين", "phone": "096-6789012", "scope": "نقل طلاب"},
            {"name_ar": "مدرسة ملta سوق الجمعة للبنات", "phone": "097-7890123", "scope": "نقل طلاب"},
            {"name_ar": "مدرسة ابومنقار الاساسية للبنين", "phone": "098-8901234", "scope": "نقل طلاب"},
            {"name_ar": "مدرسة凭据区 الاساسية للبنات", "phone": "099-9012345", "scope": "نقل طلاب"},
            {"name_ar": "الهيئة العامة للنفط", "phone": "091-0123456", "scope": "نقل موظفين"},
            {"name_ar": "جامعة طرابلس", "phone": "092-1234568", "scope": "نقل طلاب"},
            {"name_ar": "شركة ال振华", "phone": "093-2345679", "scope": "نقل موظفين"},
            {"name_ar": " bankruptcies", "phone": "094-3456780", "scope": "نقل ركاب"},
            {"name_ar": "school chiara", "phone": "095-4567891", "scope": "نقل طلاب"},
            {"name_ar": "sse type", "phone": "096-5678902", "scope": "نقل ركاب"},
            {"name_ar": "الشركة الليبية للاتصالات", "phone": "097-6789013", "scope": "نقل موظفين"},
            {"name_ar": "Bank of Commerce and Development", "phone": "098-7890124", "scope": "نقل موظفين"},
            {"name_ar": "Sebha University", "phone": "099-8901235", "scope": "نقل طلاب"},
            {"name_ar": "Tripoli International Airport", "phone": "091-9012346", "scope": "نقل ركاب"},
            {"name_ar": "Ministry of Education", "phone": "092-0123457", "scope": "نقل موظفين"},
            {"name_ar": " Libyan Iron and Steel Company", "phone": "093-1234569", "scope": "نقل موظفين"},
            {"name_ar": "GECOL", "phone": "094-2345670", "scope": "نقل موظفين"},
            {"name_ar": "Libyan Post Corporation", "phone": "095-3456781", "scope": "نقل موظفين"},
            {"name_ar": "Water Authority", "phone": "096-4567892", "scope": "نقل موظفين"},
            {"name_ar": "Ministry of Health", "phone": "097-5678903", "scope": "نقل موظفين"},
            {"name_ar": "National Oil Corporation", "phone": "098-6789014", "scope": "نقل موظفين"},
            {"name_ar": "Central Bank of Libya", "phone": "099-7890125", "scope": "نقل موظفين"},
            {"name_ar": "Libyan Investment Authority", "phone": "091-8901236", "scope": "نقل موظفين"},
            {"name_ar": "TMC", "phone": "092-9012347", "scope": "نقل ركاب"},
            {"name_ar": "Al-Madar Telecom", "phone": "093-0123458", "scope": "نقل موظفين"},
            {"name_ar": "Libyana", "phone": "094-1234560", "scope": "نقل موظفين"},
            {"name_ar": "Hakeem", "phone": "095-2345671", "scope": "نقل موظفين"},
            {"name_ar": "Aman", "phone": "096-3456782", "scope": "نقل موظفين"},
            {"name_ar": "Alsharee3", "phone": "097-4567893", "scope": "نقل ركاب"},
            {"name_ar": "Bin Qasim", "phone": "098-5678904", "scope": "نقل ركاب"},
            {"name_ar": "Al-Wahat", "phone": "099-6789015", "scope": "نقل ركاب"},
            {"name_ar": "Murqab", "phone": "091-7890126", "scope": "نقل ركاب"},
            {"name_ar": "Tajoura", "phone": "092-8901237", "scope": "نقل ركاب"},
            {"name_ar": "Souq Al-Juma", "phone": "093-9012348", "scope": "نقل طلاب"},
            {"name_ar": "Ain Zara", "phone": "094-0123459", "scope": "نقل طلاب"},
            {"name_ar": "Surman", "phone": "095-1234561", "scope": "نقل ركاب"},
            {"name_ar": "Sabratha", "phone": "096-2345672", "scope": "نقل ركاب"},
            {"name_ar": "Zliten", "phone": "097-3456783", "scope": "نقل طلاب"},
            {"name_ar": "Khoms", "phone": "098-4567894", "scope": "نقل طلاب"},
            {"name_ar": "Misrata", "phone": "099-5678905", "scope": "نقل ركاب"},
            {"name_ar": "Sirte", "phone": "091-6789016", "scope": "نقل ركاب"},
            {"name_ar": "Benghazi", "phone": "092-7890127", "scope": "نقل ركاب"},
            {"name_ar": "Tobruk", "phone": "093-8901238", "scope": "نقل ركاب"},
            {"name_ar": "Derna", "phone": "094-9012349", "scope": "نقل ركاب"},
            {"name_ar": "Baida", "phone": "095-0123450", "scope": "نقل ركاب"},
        ]

        clients = []
        for i, client_data in enumerate(clients_data, 1):
            client = MarketingClient(
                client_number=f"C{i:04d}",
                name_ar=client_data["name_ar"],
                phone=client_data.get("phone"),
                scope=client_data.get("scope"),
                is_active=True
            )
            session.add(client)
            clients.append(client)

        session.flush()

        # ============================================================
        # 2. اوامر التشغيل (1137-1179 = 43 أمر تشغيل)
        # ============================================================
        orders_data = []
        trip_numbers = list(range(1137, 1180))  # 43 رقم

        for i, trip_num in enumerate(trip_numbers):
            client_idx = i % len(clients)
            client = clients[client_idx]

            order = WorkOrder(
                order_number=str(trip_num),
                client_id=client.id,
                destination=client.name_ar,
                duration_days=1,
                total_value=1500 + (i * 100),
                status="active",
                is_draft=False,
                departure_date=date(2026, 8, 1 + (i % 28)),
                return_date=date(2026, 8, 1 + (i % 28)),
                marketing_approved=True,
                finance_approved=True,
                movement_approved=True,
                executive_approved=True,
            )
            session.add(order)
            orders_data.append(order)

        session.flush()

        # ============================================================
        # 3. الرحلات (بيانات اغسطس 2026)
        # ============================================================
        trips_data = [
            {"trip_number": "1137", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1138", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1139", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1140", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1141", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1142", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1143", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1144", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1145", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1146", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1147", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1148", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1149", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1150", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1151", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1152", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1153", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1154", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1155", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1156", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1157", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1158", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1159", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1160", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1161", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1162", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1163", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1164", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1165", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1166", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1167", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1168", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1169", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1170", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1171", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1172", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1173", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1174", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
            {"trip_number": "1175", "entity_name": "شركة التميز", "value": 1800, "bus_number": "B004", "driver_name": "علي مصطفى"},
            {"trip_number": "1176", "entity_name": "المركز الليبي للتنمية", "value": 2500, "bus_number": "B005", "driver_name": "محمد سالم"},
            {"trip_number": "1177", "entity_name": "شركة فاوكية", "value": 1500, "bus_number": "B001", "driver_name": "عبدالله احمد"},
            {"trip_number": "1178", "entity_name": "كشف", "value": 2000, "bus_number": "B002", "driver_name": "سالم احمد"},
            {"trip_number": "1179", "entity_name": "شركة جسر الرواد", "value": 1200, "bus_number": "B003", "driver_name": "عمر السنوسي"},
        ]

        for trip_data in trips_data:
            trip = Trip(
                trip_number=trip_data["trip_number"],
                entity_name=trip_data["entity_name"],
                trip_date=date(2026, 8, 1 + int(trip_data["trip_number"]) % 28),
                value=trip_data["value"],
                bus_number=trip_data["bus_number"],
                driver_name=trip_data["driver_name"],
                status="completed",
            )
            session.add(trip)

        # ============================================================
        # 4. مستحقات سائقي المدارس (22 سائق - 55 رحلة)
        # ============================================================
        school_drivers_data = [
            {"driver_name": "عبدالله احمد الابراهيم", "school_name": "مدرسة المجايدة الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "سالم احمدonor", "school_name": "مدرسة ملta سوق الجمعة للبنات", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "عمر السنوسي", "school_name": "مدرسة ابومنقار الاساسية للبنين", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "علي مصطفى", "school_name": "مدرسة凭据区 الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "محمد سالم", "school_name": "مدرسة التحرير الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "عادل احمد الشهادي", "school_name": "مدرسة الزهراء الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "عبدالمحسن سالم", "school_name": "مدرسة النصر الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "اشرف محمد", "school_name": "مدرسة الامل الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "بلال علي", "school_name": "مدرسة السلام الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "حسن احمد", "school_name": "مدرسة الشهداء الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "خالد سالم", "school_name": "مدرسة الفجر الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "راشد علي", "school_name": "مدرسة النور الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "سعيد احمد", "school_name": "مدرسة الريادة الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "صالح محمد", "school_name": "مدرسة التربية الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "طارق عمر", "school_name": "مدرسة الانطلاق الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "عامر حسن", "school_name": "مدرسة التفوق الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "فهد سالم", "school_name": "مدرسة النخبة الاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "مبروك احمد", "school_name": "مدرسة الابداع الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "منصور علي", "school_name": "مدرسة الاkeyالاساسية للبنين", "trip_count": 3, "driver_type": "school", "entitlement_value": 9000},
            {"driver_name": "ياسر محمد", "school_name": "مدرسة المشارقة الاساسية للبنات", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "احمد سالم", "school_name": "مدرسة المدارج الاساسية للبنين", "trip_count": 2, "driver_type": "school", "entitlement_value": 6000},
            {"driver_name": "EMARR driver", "school_name": "مدرسة SEBHA الاساسية للبنين", "trip_count": 1, "driver_type": "school", "entitlement_value": 3000},
        ]

        for ent_data in school_drivers_data:
            entitlement = SchoolDriverEntitlement(
                month=8,
                year=2026,
                driver_name=ent_data["driver_name"],
                school_name=ent_data["school_name"],
                trip_count=ent_data["trip_count"],
                driver_type=ent_data["driver_type"],
                entitlement_value=ent_data["entitlement_value"],
                company_share=ent_data["entitlement_value"] * 0.10,
                net_entitlement=ent_data["entitlement_value"] * 0.90,
                entitlement_date=date(2026, 9, 1),
                status="pending",
            )
            session.add(entitlement)

        session.commit()
        print("تم اضافة بيانات شهر اغسطس 2026 بنجاح!")
        print(f"- {len(clients)} عميل")
        print(f"- {len(orders_data)} امر تشغيل")
        print(f"- {len(trips_data)} رحلة")
        print(f"- {len(school_drivers_data)} سائق مدارس")

if __name__ == "__main__":
    seed_august_2026()
