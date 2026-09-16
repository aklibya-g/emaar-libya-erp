from __future__ import annotations

from datetime import datetime, date, time
from typing import Optional, List

from sqlalchemy import Float, Index, ForeignKey, String, Text, Date, Time, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base
from src.core.models.base_models import generate_uuid, TimestampMixin, VehicleType


class Vehicle(Base, TimestampMixin):
    """السيارات والمركبات"""
    __tablename__ = "vehicles"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    emaar_number: Mapped[Optional[str]] = mapped_column(String(20), default=None, unique=True)
    vehicle_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicle_types.id"), nullable=False
    )
    brand: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    model: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    color: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    engine_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    chassis_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    fuel_type: Mapped[Optional[str]] = mapped_column(String(20), default="gasoline")
    tank_capacity: Mapped[Optional[float]] = mapped_column(Float, default=None)
    seats_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    current_km: Mapped[Optional[float]] = mapped_column(Float, default=0)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date, default=None)
    registration_expiry: Mapped[Optional[date]] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    driver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("drivers.id"), default=None
    )

    vehicle_type: Mapped["VehicleType"] = relationship(back_populates="vehicles")
    driver: Mapped[Optional["Driver"]] = relationship(foreign_keys=[driver_id])
    maintenance_records: Mapped[List["VehicleMaintenance"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["VehicleExpense"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    fuel_records: Mapped[List["VehicleFuel"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    spare_parts: Mapped[List["VehicleSparePart"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    documents: Mapped[List["VehicleDocument"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    driver_logs: Mapped[List["VehicleDriverLog"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )


class VehicleMaintenance(Base, TimestampMixin):
    """سجل الصيانة"""
    __tablename__ = "vehicle_maintenance"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_maintenance_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    next_maintenance_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    cost: Mapped[Optional[float]] = mapped_column(Float, default=0)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="maintenance_records")


class VehicleBreakdown(Base, TimestampMixin):
    """الأعطال"""
    __tablename__ = "vehicle_breakdowns"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    breakdown_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="minor")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    cost: Mapped[Optional[float]] = mapped_column(Float, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle = relationship("Vehicle")


class VehicleExpense(Base, TimestampMixin):
    """المصاريف"""
    __tablename__ = "vehicle_expenses"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    expense_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    receipt_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="expenses")


class VehicleFuel(Base, TimestampMixin):
    """سجل الوقود"""
    __tablename__ = "vehicle_fuel"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    fuel_date: Mapped[date] = mapped_column(Date, nullable=False)
    liters: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_liter: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    odometer_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    fuel_station: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="fuel_records")


class VehicleSparePart(Base, TimestampMixin):
    """قطع الغيار المستخدمة"""
    __tablename__ = "vehicle_spare_parts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    maintenance_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vehicle_maintenance.id"), default=None
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="spare_parts")
    item = relationship("Item")


class VehicleDocument(Base, TimestampMixin):
    """مستندات المركبة"""
    __tablename__ = "vehicle_documents"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="documents")


class VehicleDriverLog(Base, TimestampMixin):
    """سجل تعيين السائقين على المركبات"""
    __tablename__ = "vehicle_driver_logs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="driver_logs")
    driver = relationship("Driver")


class DriverSuspension(Base, TimestampMixin):
    """سجل ايقاف و تفعيل السائقين"""
    __tablename__ = "driver_suspensions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    suspension_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), default=None)

    driver: Mapped["Driver"] = relationship()
