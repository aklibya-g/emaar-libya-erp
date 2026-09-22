from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base
from src.core.models.base_models import Employee, Driver, VehicleType  # noqa: F401 - ensure FK targets exist
from src.core.models.vehicle_models import Vehicle  # noqa: F401 - ensure FK targets exist


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=None, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)


# ============================================================
# CLIENT / ENTITY (الجهة) - for CRM
# ============================================================

class MarketingClient(Base, TimestampMixin):
    __tablename__ = "marketing_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    client_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    scope: Mapped[Optional[str]] = mapped_column(String(200), default=None)  # نطاق الجهة
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    contracts: Mapped[List["MarketingContract"]] = relationship(back_populates="client")


# ============================================================
# CONTRACT (العقد)
# ============================================================

class MarketingContract(Base, TimestampMixin):
    __tablename__ = "marketing_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    contract_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketing_clients.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    bus_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # عدد الحافلات
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, cancelled
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    # ملحق التعديل
    amendment_bus_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)  # عدد الحافلات المعدلة
    amendment_value: Mapped[Optional[float]] = mapped_column(Float, default=None)  # القيمة المعدلة
    amendment_description: Mapped[Optional[str]] = mapped_column(String(500), default=None)  # وصف الملحق

    # المسؤول
    responsible_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)  # اسم المسؤول

    client: Mapped["MarketingClient"] = relationship(back_populates="contracts")
    work_orders: Mapped[List["WorkOrder"]] = relationship(back_populates="contract")


# ============================================================
# WORK ORDER (أمر التشغيل)
# ============================================================

class WorkOrder(Base, TimestampMixin):
    __tablename__ = "marketing_work_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)  # 01201
    contract_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("marketing_contracts.id"), default=None
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketing_clients.id"), nullable=False
    )

    # البيانات الأساسية
    destination: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)  # الوجهة المطلوبة
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)  # رقم الهاتف
    trip_route: Mapped[Optional[str]] = mapped_column(String(30), default=None)  # مسار الرحلة
    trip_from: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # رحلة من
    trip_to: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # رحلة الى
    duration_days: Mapped[int] = mapped_column(Integer, default=1)  # المدة ب days

    # التكاليف
    bus_count_requested: Mapped[int] = mapped_column(Integer, default=1)  # عدد الحافلات المطلوبة
    bus_rental_value: Mapped[float] = mapped_column(Float, default=0.0)  # قيمة ايجار الحافلة
    bus_maintenance_value: Mapped[float] = mapped_column(Float, default=0.0)  # قيمة صيانة الحافلة
    driver_transport_value: Mapped[float] = mapped_column(Float, default=0.0)  # قيمة نقل وإعاشة السائق
    trip_price: Mapped[float] = mapped_column(Float, default=0.0)  # سعر الرحلة اليومي
    total_value: Mapped[float] = mapped_column(Float, default=0.0)  # القيمة الاجمالية
    estimated_distance: Mapped[Optional[float]] = mapped_column(Float, default=None)  # المسافة التقديرية كم

    # التخفيض او الزيادة
    adjustment_percent: Mapped[Optional[float]] = mapped_column(Float, default=None)  # نسبة التخفيض/الزيادة
    adjustment_value: Mapped[Optional[float]] = mapped_column(Float, default=None)  # قيمة التخفيض/الزيادة
    adjustment_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)  # reduce/increase

    # التواريخ
    departure_date: Mapped[Optional[date]] = mapped_column(Date, default=None)  # تاريخ خروج الحافلة
    return_date: Mapped[Optional[date]] = mapped_column(Date, default=None)  # تاريخ عودة الحافلة

    # الحالة
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, completed, cancelled
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True)  # في الانتظار
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # محذوف

    # التوقيعات
    marketing_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # قسم التسويق
    marketing_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    marketing_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    finance_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # القسم المالي
    finance_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    finance_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    movement_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # قسم الحركة
    movement_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    movement_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    executive_approved: Mapped[bool] = mapped_column(Boolean, default=False)  # اعتماد المدير التنفيذي
    executive_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    executive_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)

    # تخفيض المدير التنفيذي
    executive_discount_value: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    executive_discount_reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    executive_discount_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    executive_discount_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    final_value: Mapped[Optional[float]] = mapped_column(Float, default=0.0)

    # نظام التعديلات
    order_type: Mapped[str] = mapped_column(String(20), default="new")  # new / amendment
    related_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("marketing_work_orders.id"), default=None
    )
    amendment_reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    amendment_details: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON: تفاصيل التعديل قبل/بعد

    # نوع التسعير (أوتوماتيك من جدول الاسعار / يدوي)
    is_auto_pricing: Mapped[bool] = mapped_column(Boolean, default=False)  # False=يدوي(افتراضي), True=أوتوماتيك

    # نوع الرحلة (داخل المدينة / خارج المدينة)
    trip_type: Mapped[str] = mapped_column(String(20), default="internal")  # internal / external

    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    edited_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    edited_by_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)

    contract: Mapped[Optional["MarketingContract"]] = relationship(back_populates="work_orders")
    client: Mapped["MarketingClient"] = relationship()
    buses: Mapped[List["WorkOrderBus"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")
    annexes: Mapped[List["WorkOrderAnnex"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")
    related_order: Mapped[Optional["WorkOrder"]] = relationship(
        remote_side="WorkOrder.id", foreign_keys=[related_order_id]
    )


# ============================================================
# WORK ORDER BUS (بيانات الحافلة في أمر التشغيل)
# ============================================================

class WorkOrderBus(Base, TimestampMixin):
    __tablename__ = "marketing_work_order_buses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketing_work_orders.id", ondelete="CASCADE"), nullable=False
    )
    vehicle_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vehicles.id"), default=None
    )
    driver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("drivers.id"), default=None
    )
    bus_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    bus_price: Mapped[Optional[float]] = mapped_column(Float, default=None)  # سعر الحافلة باليوم
    passenger_count: Mapped[int] = mapped_column(Integer, default=0)  # عدد الركاب
    driver_share_pct: Mapped[Optional[float]] = mapped_column(Float, default=10.0)  # نسبة السائق %
    driver_share_value: Mapped[Optional[float]] = mapped_column(Float, default=0.0)  # قيمة نسبة السائق
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    work_order: Mapped["WorkOrder"] = relationship(back_populates="buses")
    vehicle: Mapped[Optional["Vehicle"]] = relationship(foreign_keys=[vehicle_id])


# ============================================================
# WORK ORDER ANNEX (ملحق أمر التشغيل)
# ============================================================

class WorkOrderAnnex(Base, TimestampMixin):
    __tablename__ = "marketing_work_order_annexes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("marketing_work_orders.id", ondelete="CASCADE"), nullable=False
    )
    annex_number: Mapped[str] = mapped_column(String(30), nullable=False)  # 012/1, 012/2
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # التعديلات
    extended_days: Mapped[int] = mapped_column(Integer, default=0)  # ايام اضافية
    new_bus_count: Mapped[int] = mapped_column(Integer, default=0)  # عدد حافلات جديد
    reduction_days: Mapped[int] = mapped_column(Integer, default=0)  # ايام تقليل
    reduction_value: Mapped[float] = mapped_column(Float, default=0.0)  # قيمة التقليل

    # بيانات الحافلة البديلة (عند نقل السيارة)
    replacement_bus_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    replacement_driver_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)

    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, completed
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    work_order: Mapped["WorkOrder"] = relationship(back_populates="annexes")


# ============================================================
# TRIP (الرحلة) - for daily trip sheet
# ============================================================

class Trip(Base, TimestampMixin):
    __tablename__ = "marketing_trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    trip_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)  # 1137, 1138...
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("marketing_work_orders.id"), default=None
    )
    client_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("marketing_clients.id"), default=None
    )

    entity_name: Mapped[str] = mapped_column(String(200), nullable=False)  # اسم الجهة
    trip_date: Mapped[date] = mapped_column(Date, nullable=False)  # التاريخ
    trip_type: Mapped[str] = mapped_column(String(50), default="school")  # school, transport, external
    value: Mapped[float] = mapped_column(Float, default=0.0)  # القيمة
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, cancelled

    # بيانات الحافلة وال سائق
    bus_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    route: Mapped[Optional[str]] = mapped_column(String(200), default=None)  # مسار الرحلة
    passenger_count: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)


# ============================================================
# SCHOOL DRIVER ENTITLEMENT (مستحقات سائقي المدارس)
# ============================================================

class SchoolDriverEntitlement(Base, TimestampMixin):
    __tablename__ = "marketing_school_driver_entitlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # الشهر 1-12
    year: Mapped[int] = mapped_column(Integer, nullable=False)  # السنة
    driver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("drivers.id"), default=None
    )
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)  # اسم المدرسة
    bus_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    trip_count: Mapped[int] = mapped_column(Integer, default=0)  # عدد الرحلات
    driver_type: Mapped[str] = mapped_column(String(50), default="school")  # school, trip, reserve
    entitlement_value: Mapped[float] = mapped_column(Float, default=0.0)  # تستحق
    company_share: Mapped[float] = mapped_column(Float, default=0.0)  # نسبت الشركة 10%
    net_entitlement: Mapped[float] = mapped_column(Float, default=0.0)  # صافي المستحق
    entitlement_date: Mapped[Optional[date]] = mapped_column(Date, default=None)  # تاريخ الاستحقاق
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    # New fields
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("marketing_work_orders.id"), default=None
    )
    work_order_number: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # رقم امر التشغيل
    route: Mapped[Optional[str]] = mapped_column(String(200), default=None)  # خط السير
    trip_value: Mapped[float] = mapped_column(Float, default=0.0)  # قيمة الرحلة
    driver_share: Mapped[float] = mapped_column(Float, default=0.0)  # نسبة السائق 10%
    overnight_stay: Mapped[float] = mapped_column(Float, default=0.0)  # مبيت السائق
    total_share: Mapped[float] = mapped_column(Float, default=0.0)  # اجمالي النسبة = مبيت + 10%

    work_order: Mapped[Optional["WorkOrder"]] = relationship()


# ============================================================
# MONTHLY TRIP SHEET (كشف الرحلات الشهرية)
# ============================================================

class MonthlyTripSheet(Base, TimestampMixin):
    __tablename__ = "monthly_trip_sheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, approved
    approved_by_marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_finance: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_movement: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_executive: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)


# ============================================================
# BUS RENTAL PRICE (سعر ايجار الحافلة باليوم)
# ============================================================

class BusRentalPrice(Base, TimestampMixin):
    __tablename__ = "marketing_bus_rental_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicle_types.id"), nullable=False
    )
    seats_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    daily_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle_type: Mapped["VehicleType"] = relationship()


# ============================================================
# FINANCIAL CLAIM (مطالبة مالية - تنشأ تلقائياً)
# ============================================================

class FinancialClaim(Base, TimestampMixin):
    __tablename__ = "financial_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    claim_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    work_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketing_work_orders.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketing_clients.id"), nullable=False)
    contract_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("marketing_contracts.id"), default=None)
    claim_date: Mapped[date] = mapped_column(Date, nullable=False)

    order_number: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    destination: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    trip_route: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    trip_from: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    trip_to: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    route_description: Mapped[Optional[str]] = mapped_column(String(300), default=None)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    departure_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    return_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    bus_count: Mapped[int] = mapped_column(Integer, default=0)
    trip_type: Mapped[Optional[str]] = mapped_column(String(20), default="internal")

    bus_rental_value: Mapped[float] = mapped_column(Float, default=0.0)
    bus_maintenance_value: Mapped[float] = mapped_column(Float, default=0.0)
    driver_transport_value: Mapped[float] = mapped_column(Float, default=0.0)
    trip_price: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_distance: Mapped[Optional[float]] = mapped_column(Float, default=None)

    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    adjustment_percent: Mapped[Optional[float]] = mapped_column(Float, default=None)
    adjustment_value: Mapped[float] = mapped_column(Float, default=0.0)
    adjustment_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    executive_discount_value: Mapped[float] = mapped_column(Float, default=0.0)
    final_value: Mapped[float] = mapped_column(Float, default=0.0)
    received_amount: Mapped[float] = mapped_column(Float, default=0.0)
    remaining_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_fully_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    work_order: Mapped["WorkOrder"] = relationship(foreign_keys=[work_order_id])
    client: Mapped["MarketingClient"] = relationship(foreign_keys=[client_id])
    contract: Mapped[Optional["MarketingContract"]] = relationship(foreign_keys=[contract_id])
    receipts: Mapped[List["PaymentReceipt"]] = relationship(back_populates="claim")


# ============================================================
# PAYMENT RECEIPT (سند استلام)
# ============================================================

class PaymentReceipt(Base, TimestampMixin):
    __tablename__ = "payment_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    receipt_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    financial_claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("financial_claims.id"), nullable=False)
    work_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketing_work_orders.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketing_clients.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_received: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payment_method: Mapped[str] = mapped_column(String(20), default="cash")
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    claim: Mapped["FinancialClaim"] = relationship(back_populates="receipts")
    work_order: Mapped["WorkOrder"] = relationship(foreign_keys=[work_order_id])
    client: Mapped["MarketingClient"] = relationship(foreign_keys=[client_id])


# ============================================================
# DRIVER PAYOUT (سند صرف سائقين)
# ============================================================

class DriverPayout(Base, TimestampMixin):
    __tablename__ = "driver_payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    payout_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    work_order_id: Mapped[str] = mapped_column(String(36), ForeignKey("marketing_work_orders.id"), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("drivers.id"), default=None)
    school_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    bus_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    trip_value: Mapped[float] = mapped_column(Float, default=0.0)
    driver_share: Mapped[float] = mapped_column(Float, default=0.0)
    overnight_stay: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    paid_at: Mapped[Optional[date]] = mapped_column(Date, default=None)
    paid_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    work_order: Mapped["WorkOrder"] = relationship(foreign_keys=[work_order_id])
