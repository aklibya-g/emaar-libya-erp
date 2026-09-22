from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import Float, ForeignKey, String, Text, Date, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base
from src.core.models.base_models import generate_uuid, TimestampMixin


# ============================================================
# MAINTENANCE REQUEST (طلب صيانة)
# ============================================================

class MaintenanceRequest(Base, TimestampMixin):
    __tablename__ = "maintenance_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    request_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id"), nullable=False
    )
    requested_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    request_date: Mapped[date] = mapped_column(Date, nullable=False)

    maintenance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    current_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    status: Mapped[str] = mapped_column(String(20), default="draft")

    maintenance_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    maintenance_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    warehouse_approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    warehouse_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    completed_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)

    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle = relationship("Vehicle")
    items: Mapped[List["MaintenanceItem"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    logs: Mapped[List["MaintenanceLog"]] = relationship(
        back_populates="request"
    )
    part_returns: Mapped[List["MaintenancePartReturn"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    vehicle_parts_installed: Mapped[List["VehiclePart"]] = relationship(
        foreign_keys="[VehiclePart.install_request_id]",
        back_populates="install_request"
    )
    vehicle_parts_removed: Mapped[List["VehiclePart"]] = relationship(
        foreign_keys="[VehiclePart.remove_request_id]",
        back_populates="remove_request"
    )


# ============================================================
# MAINTENANCE ITEMS (قطع الغيار المطلوبة)
# ============================================================

class MaintenanceItem(Base, TimestampMixin):
    __tablename__ = "maintenance_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit: Mapped[str] = mapped_column(String(20), default="قطعة")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    warehouse_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="items")


# ============================================================
# MAINTENANCE LOGS (سجل الصيانة لكل سيارة)
# ============================================================

class MaintenanceLog(Base, TimestampMixin):
    __tablename__ = "maintenance_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id"), nullable=False
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("maintenance_requests.id"), default=None
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    km_reading: Mapped[Optional[float]] = mapped_column(Float, default=None)
    maintenance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle = relationship("Vehicle")
    request: Mapped[Optional["MaintenanceRequest"]] = relationship(back_populates="logs")


# ============================================================
# VEHICLE PARTS (قطع الغيار المثبتة/المفككة على كل سيارة)
# ============================================================

class VehiclePart(Base, TimestampMixin):
    __tablename__ = "vehicle_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)

    installed_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    installed_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    expected_km_life: Mapped[Optional[float]] = mapped_column(Float, default=None)
    condition: Mapped[str] = mapped_column(String(20), default="new")
    install_request_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("maintenance_requests.id"), default=None
    )

    status: Mapped[str] = mapped_column(String(20), default="installed")
    removed_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    removed_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    removed_reason: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    remove_request_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("maintenance_requests.id"), default=None
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle = relationship("Vehicle")
    install_request: Mapped[Optional["MaintenanceRequest"]] = relationship(
        foreign_keys=[install_request_id], back_populates="vehicle_parts_installed"
    )
    remove_request: Mapped[Optional["MaintenanceRequest"]] = relationship(
        foreign_keys=[remove_request_id], back_populates="vehicle_parts_removed"
    )


# ============================================================
# MAINTENANCE PART RETURNS (إعادات القطع للمخزن)
# ============================================================

class MaintenancePartReturn(Base, TimestampMixin):
    __tablename__ = "maintenance_part_returns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    return_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("maintenance_requests.id"), nullable=False
    )
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    condition: Mapped[str] = mapped_column(String(20), default="used")
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    purchase_value: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    supplier: Mapped[Optional[str]] = mapped_column(String(200), default=None)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    received_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    warehouse_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    request: Mapped["MaintenanceRequest"] = relationship(back_populates="part_returns")
    vehicle = relationship("Vehicle")


# ============================================================
# MAINTENANCE SCHEDULE (الصيانة الدورية)
# ============================================================

class MaintenanceSchedule(Base, TimestampMixin):
    __tablename__ = "maintenance_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vehicles.id"), nullable=False
    )
    maintenance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    interval_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    interval_days: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    last_performed_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    last_performed_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    next_due_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    next_due_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    vehicle = relationship("Vehicle")
