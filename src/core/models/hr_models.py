from __future__ import annotations

import uuid
from datetime import datetime, date, time
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, Date, Time,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.connection import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================================
# EMPLOYEE - COMPREHENSIVE DIGITAL FILE
# ============================================================

class EmployeeProfile(Base):
    """Extended personal data for employee digital file"""
    __tablename__ = "employee_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Extended personal data
    first_name_ar: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    father_name_ar: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    grandfather_name_ar: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    last_name_ar: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    first_name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    father_name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    grandfather_name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    last_name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    passport_number: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    passport_issue_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    passport_expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    passport_issue_place: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    place_of_birth: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    family_members_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    secondary_phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    city: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    region: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    # Extended job data
    job_title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    job_grade: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    job_level: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    start_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    branch_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    cost_center: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    work_hours: Mapped[Optional[str]] = mapped_column(String(50), default="08:00-14:00")
    shift_system: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    rest_days: Mapped[Optional[str]] = mapped_column(String(50), default="Friday")
    # Salary details
    basic_salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    housing_allowance: Mapped[Optional[float]] = mapped_column(Float, default=None)
    transport_allowance: Mapped[Optional[float]] = mapped_column(Float, default=None)
    other_allowances: Mapped[Optional[float]] = mapped_column(Float, default=None)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee", backref="profile")


# ============================================================
# DOCUMENT MANAGEMENT
# ============================================================

class DocumentCategory(Base):
    """Document folder categories"""
    __tablename__ = "document_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document_types: Mapped[List["DocumentType"]] = relationship(back_populates="category")


class DocumentType(Base):
    """Specific document types within categories"""
    __tablename__ = "document_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_categories.id"), nullable=False
    )
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    default_validity_months: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["DocumentCategory"] = relationship(back_populates="document_types")
    employee_documents: Mapped[List["EmployeeDocumentRecord"]] = relationship(back_populates="document_type")

    __table_args__ = (
        UniqueConstraint("category_id", "code", name="uq_doc_type_code"),
    )


class EmployeeDocumentRecord(Base):
    """Employee document records with full metadata"""
    __tablename__ = "employee_document_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    document_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_types.id"), nullable=False
    )
    document_number: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    file_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    ocr_data: Mapped[Optional[str]] = mapped_column(Text, default=None)
    ocr_status: Mapped[Optional[str]] = mapped_column(String(20), default=None)  # pending, verified, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")
    document_type: Mapped["DocumentType"] = relationship(back_populates="employee_documents")


# ============================================================
# ATTENDANCE SYSTEM
# ============================================================

class AttendanceRecord(Base):
    """Daily attendance records"""
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    check_in_time: Mapped[Optional[time]] = mapped_column(Time, default=None)
    check_out_time: Mapped[Optional[time]] = mapped_column(Time, default=None)
    status: Mapped[str] = mapped_column(String(30), default="present")  # present, absent, late, leave, holiday, rest, etc.
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, default=0)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0)
    work_hours: Mapped[float] = mapped_column(Float, default=0.0)
    check_in_signature: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    check_out_signature: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    absence_reason: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    late_reason: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    exit_permit: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    supervisor_signature: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    hr_signature: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_manual_entry: Mapped[bool] = mapped_column(Boolean, default=True)
    entered_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("employee_id", "record_date", name="uq_attendance_date"),
        Index("ix_attendance_date", "record_date"),
        Index("ix_attendance_employee", "employee_id"),
    )


class AttendanceStatus:
    PRESENT = "present"
    ABSENT = "absent"
    ABSENT_EXCUSED = "absent_excused"
    ABSENT_UNEXCUSED = "absent_unexcused"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    ANNUAL_LEAVE = "annual_leave"
    SICK_LEAVE = "sick_leave"
    EMERGENCY_LEAVE = "emergency_leave"
    SPECIAL_LEAVE = "special_leave"
    MATERNITY_LEAVE = "maternity_leave"
    UNPAID_LEAVE = "unpaid_leave"
    HAJJ_LEAVE = "hajj_leave"
    MARRIAGE_LEAVE = "marriage_leave"
    BEREAVEMENT_LEAVE = "bereavement_leave"
    MISSION = "mission"
    TRAINING = "training"
    WEEKLY_REST = "weekly_rest"
    OFFICIAL_HOLIDAY = "official_holiday"
    PERMISSION = "permission"
    HALF_DAY = "half_day"
    SUSPENDED = "suspended"
    OVERTIME = "overtime"
    ORDER = "order"

    CHOICES = [
        (PRESENT, "حاضر"),
        (ABSENT, "غائب"),
        (ABSENT_EXCUSED, "غياب بعذر"),
        (ABSENT_UNEXCUSED, "غياب بدون عذر"),
        (LATE, "تأخير"),
        (EARLY_LEAVE, "خروج مبكر"),
        (ANNUAL_LEAVE, "إجازة سنوية"),
        (SICK_LEAVE, "إجازة مرضية"),
        (EMERGENCY_LEAVE, "إجازة طارئة"),
        (SPECIAL_LEAVE, "إجازة خاصة"),
        (MATERNITY_LEAVE, "إجازة أمومة"),
        (UNPAID_LEAVE, "إجازة بدون مرتب"),
        (HAJJ_LEAVE, "إجازة حج"),
        (MARRIAGE_LEAVE, "إجازة زواج"),
        (BEREAVEMENT_LEAVE, "إجازة وفاة"),
        (MISSION, "مأمورية"),
        (TRAINING, "تدريب"),
        (WEEKLY_REST, "راحة أسبوعية"),
        (OFFICIAL_HOLIDAY, "عطلة رسمية"),
        (PERMISSION, "إذن"),
        (HALF_DAY, "نصف يوم"),
        (SUSPENDED, "تعليق عن العمل"),
        (OVERTIME, "عمل إضافي"),
        (ORDER, "أمر"),
    ]


# ============================================================
# LEAVE MANAGEMENT
# ============================================================

class LeaveType(Base):
    """Types of leaves"""
    __tablename__ = "leave_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    default_days: Mapped[int] = mapped_column(Integer, default=0)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    is_accumulative: Mapped[bool] = mapped_column(Boolean, default=False)
    max_consecutive_days: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_workflow: Mapped[Optional[str]] = mapped_column(String(50), default="direct_manager")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    balances: Mapped[List["LeaveBalance"]] = relationship(back_populates="leave_type")
    requests: Mapped[List["LeaveRequest"]] = relationship(back_populates="leave_type")


class LeaveBalance(Base):
    """Employee leave balances per year"""
    __tablename__ = "leave_balances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leave_types.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    entitled_days: Mapped[float] = mapped_column(Float, default=0.0)
    used_days: Mapped[float] = mapped_column(Float, default=0.0)
    carried_over: Mapped[float] = mapped_column(Float, default=0.0)
    adjusted: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")
    leave_type: Mapped["LeaveType"] = relationship(back_populates="balances")

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance"),
    )

    @property
    def remaining_days(self) -> float:
        return self.entitled_days + self.carried_over + self.adjusted - self.used_days


class LeaveRequest(Base):
    """Leave requests with approval workflow"""
    __tablename__ = "leave_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leave_types.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected, cancelled
    request_number: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    # Approval chain
    manager_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    manager_approved: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    manager_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    manager_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    hr_approved: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    hr_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    hr_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    final_approved_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    final_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    rejected_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")
    leave_type: Mapped["LeaveType"] = relationship(back_populates="requests")


class Holiday(Base):
    """Official holidays"""
    __tablename__ = "holidays"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("holiday_date", "year", name="uq_holiday"),
    )


# ============================================================
# DISCIPLINARY ACTIONS
# ============================================================

class DisciplinaryType(Base):
    """Types of disciplinary actions"""
    __tablename__ = "disciplinary_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    severity_level: Mapped[int] = mapped_column(Integer, default=1)  # 1=minor, 2=moderate, 3=severe
    can_deduct_salary: Mapped[bool] = mapped_column(Boolean, default=False)
    max_deduction_days: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    actions: Mapped[List["DisciplinaryAction"]] = relationship(back_populates="disciplinary_type")


class DisciplinaryAction(Base):
    """Disciplinary actions records"""
    __tablename__ = "disciplinary_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    disciplinary_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("disciplinary_types.id"), nullable=False
    )
    decision_number: Mapped[str] = mapped_column(String(50), nullable=False)
    violation_date: Mapped[date] = mapped_column(Date, nullable=False)
    violation_description: Mapped[str] = mapped_column(Text, nullable=False)
    article_reference: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    investigation_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    deduction_days: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    deduction_amount: Mapped[Optional[float]] = mapped_column(Float, default=None)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    issued_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, appealed, revoked
    appeal_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")
    disciplinary_type: Mapped["DisciplinaryType"] = relationship(back_populates="actions")


# ============================================================
# CONTRACTS
# ============================================================

class Contract(Base):
    """Employee contracts"""
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    contract_number: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)  # permanent, temporary, part_time, etc.
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    probation_period_months: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    allowances: Mapped[Optional[float]] = mapped_column(Float, default=None)
    benefits: Mapped[Optional[str]] = mapped_column(Text, default=None)
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, terminated, renewed
    renewal_of: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    approval_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee", backref="contracts")


# ============================================================
# DRIVER CONTRACTS (عقود السائقين)
# ============================================================

class DriverContract(Base):
    """Driver contracts"""
    __tablename__ = "driver_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    contract_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_type: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # نوع الخدمة
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    allowances: Mapped[Optional[float]] = mapped_column(Float, default=None)
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    renewal_of: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    approval_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    driver = relationship("Driver", backref="contracts")


# ============================================================
# ONBOARDING / DIRECT WORK
# ============================================================

class Onboarding(Base):
    """Employee onboarding / direct work"""
    __tablename__ = "onboardings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    decision_number: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    job_title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    work_location: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    branch: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, active
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    approval_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee", backref="onboardings")


# ============================================================
# SHIFTS & WORK SCHEDULES
# ============================================================

class WorkShift(Base):
    """Work shifts definitions"""
    __tablename__ = "work_shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assignments: Mapped[List["ShiftAssignment"]] = relationship(back_populates="shift")


class ShiftAssignment(Base):
    """Employee shift assignments"""
    __tablename__ = "shift_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    shift_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_shifts.id"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, default=None)
    day_of_week: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee")
    shift: Mapped["WorkShift"] = relationship(back_populates="assignments")


# ============================================================
# OVERTIME
# ============================================================

class OvertimeRequest(Base):
    """Overtime requests"""
    __tablename__ = "overtime_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    overtime_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    employee = relationship("Employee")


# ============================================================
# PROMOTIONS & TRANSFERS
# ============================================================

class Promotion(Base):
    """Employee promotions"""
    __tablename__ = "promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    decision_number: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_position: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    to_position: Mapped[str] = mapped_column(String(200), nullable=False)
    from_grade: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    to_grade: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    from_salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    to_salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="promotions")


class Transfer(Base):
    """Employee transfers"""
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    decision_number: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_department: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    to_department: Mapped[str] = mapped_column(String(200), nullable=False)
    from_branch: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    to_branch: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    transfer_type: Mapped[str] = mapped_column(String(50), default="transfer")  # transfer, delegation, secondment
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="transfers")


class Termination(Base):
    """Employee termination"""
    __tablename__ = "terminations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    decision_number: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_type: Mapped[str] = mapped_column(String(50), nullable=False)  # resignation, retirement, end_of_contract, dismissal
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    end_of_service_benefits: Mapped[Optional[float]] = mapped_column(Float, default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="terminations")


# ============================================================
# HR RULES ENGINE
# ============================================================

class HRRule(Base):
    """Configurable HR rules"""
    __tablename__ = "hr_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # attendance, leave, overtime, etc.
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_value: Mapped[str] = mapped_column(Text, nullable=False)
    rule_value_type: Mapped[str] = mapped_column(String(20), default="string")  # string, int, float, bool, time, json
    description_ar: Mapped[Optional[str]] = mapped_column(Text, default=None)
    description_en: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("category", "rule_key", name="uq_hr_rule"),
    )


# ============================================================
# ALERTS & NOTIFICATIONS
# ============================================================

class Alert(Base):
    """System alerts"""
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # passport_expiry, contract_expiry, document_missing, etc.
    employee_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    severity: Mapped[str] = mapped_column(String(20), default="warning")  # info, warning, critical
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    __table_args__ = (
        Index("ix_alert_type", "alert_type"),
        Index("ix_alert_employee", "employee_id"),
    )


# ============================================================
# MEDICAL RECORDS
# ============================================================

class MedicalRecord(Base):
    """Employee medical records"""
    __tablename__ = "medical_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(50), nullable=False)  # health_certificate, medical_exam, fitness
    certificate_number: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    medical_authority: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    doctor_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    result: Mapped[Optional[str]] = mapped_column(Text, default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="medical_records")


# ============================================================
# QUALIFICATIONS & EXPERIENCE
# ============================================================

class Qualification(Base):
    """Employee qualifications"""
    __tablename__ = "qualifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    qualification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # degree, certificate, diploma
    degree_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    university: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    grade: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="qualifications")


class Experience(Base):
    """Employee work experience"""
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    duration_years: Mapped[Optional[float]] = mapped_column(Float, default=None)
    reason_for_leaving: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="experiences")


# ============================================================
# DRIVER-SPECIFIC (for transport company)
# ============================================================

class DriverLicense(Base):
    """Driver licenses"""
    __tablename__ = "driver_licenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    license_number: Mapped[str] = mapped_column(String(50), nullable=False)
    license_type: Mapped[str] = mapped_column(String(20), nullable=False)  # A, B, C, D
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    attachment_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", backref="driver_licenses")


class DriverTrip(Base):
    """Driver trip records"""
    __tablename__ = "driver_trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    trip_date: Mapped[date] = mapped_column(Date, nullable=False)
    route: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    vehicle_id: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    passengers_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    start_time: Mapped[Optional[time]] = mapped_column(Time, default=None)
    end_time: Mapped[Optional[time]] = mapped_column(Time, default=None)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, default=None)
    fuel_cost: Mapped[Optional[float]] = mapped_column(Float, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
# EMPLOYEE LOAN (سلف الموظفين)
# ============================================================

class EmployeeLoan(Base):
    """Employee loan/advance records"""
    __tablename__ = "employee_loans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    loan_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    loan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # advance, personal, emergency
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    loan_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, cancelled
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)

    employee = relationship("Employee", backref="loans")


# ============================================================
# EMPLOYEE LOAN PAYMENT (اقساط السلف)
# ============================================================

class EmployeeLoanPayment(Base):
    """Loan installment payments"""
    __tablename__ = "employee_loan_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    loan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employee_loans.id", ondelete="CASCADE"), nullable=False
    )
    payment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    loan = relationship("EmployeeLoan", backref="payments")


# ============================================================
# ATTENDANCE SETTINGS
# ============================================================

class AttendanceSettings(Base):
    """Settings for attendance records"""
    __tablename__ = "attendance_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    setting_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# ATTENDANCE APPROVAL
# ============================================================

class AttendanceApproval(Base):
    """Tracks monthly attendance report approvals"""
    __tablename__ = "attendance_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    person_type: Mapped[str] = mapped_column(String(20), default="employees")
    executive_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    executive_approved_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    executive_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    hr_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    hr_approved_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    hr_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
