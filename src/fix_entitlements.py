import sys
sys.path.insert(0, r"E:\EmarrCoSys")
from src.core.database.connection import get_web_session
from src.core.models.marketing_models import WorkOrder, WorkOrderBus, SchoolDriverEntitlement
from datetime import datetime

with get_web_session() as session:
    wo = session.query(WorkOrder).filter(WorkOrder.order_number == "1198").first()
    if not wo:
        print("Order not found")
    else:
        print(f"Order: {wo.order_number}, trip_type: {wo.trip_type}, status: {wo.status}")
        for wb in wo.buses:
            print(f"  Bus: {wb.bus_number}, driver: {wb.driver_name}, share_value: {wb.driver_share_value}")
            if wb.driver_name and wb.driver_share_value and wb.driver_share_value > 0:
                existing = session.query(SchoolDriverEntitlement).filter(
                    SchoolDriverEntitlement.work_order_id == wo.id,
                    SchoolDriverEntitlement.bus_number == wb.bus_number,
                ).first()
                if existing:
                    print("  -> Already exists")
                else:
                    trip_from = wo.trip_from or ""
                    trip_to = wo.trip_to or ""
                    route = f"{trip_from} <- {trip_to}" if trip_from or trip_to else wo.destination or ""
                    ent = SchoolDriverEntitlement(
                        month=wo.departure_date.month if wo.departure_date else datetime.now().month,
                        year=wo.departure_date.year if wo.departure_date else datetime.now().year,
                        driver_name=wb.driver_name,
                        driver_id=wb.driver_id,
                        school_name=wo.client.name_ar if wo.client else "",
                        bus_number=wb.bus_number,
                        trip_count=wo.duration_days or 1,
                        driver_type="school",
                        work_order_id=wo.id,
                        work_order_number=wo.order_number,
                        route=route,
                        trip_value=(wb.bus_price or 0) * (wo.duration_days or 1),
                        driver_share=wb.driver_share_value,
                        overnight_stay=wo.bus_maintenance_value or 0,
                        total_share=wb.driver_share_value + (wo.bus_maintenance_value or 0),
                        net_entitlement=wb.driver_share_value + (wo.bus_maintenance_value or 0),
                        entitlement_value=(wb.bus_price or 0) * (wo.duration_days or 1),
                        status="pending",
                    )
                    session.add(ent)
                    print("  -> Created!")
        session.commit()
        print("Done")
