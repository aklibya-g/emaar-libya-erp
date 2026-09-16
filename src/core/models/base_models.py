from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Index, UniqueConstraint, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from src.core.database.connection import Base


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


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)


class ActiveMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ============================================================
# AUTH MODELS
# ============================================================

class Role(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[List["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles"
    )
    users: Mapped[List["User"]] = relationship(back_populates="role")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    screen: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    roles: Mapped[List["Role"]] = relationship(
        secondary="role_permissions", back_populates="permissions"
    )

    __table_args__ = (
        UniqueConstraint("module", "screen", "action", name="uq_permission"),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    granted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    role_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("roles.id"), default=None
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    language: Mapped[str] = mapped_column(String(10), default="ar")
    theme: Mapped[str] = mapped_column(String(20), default="dark")

    role: Mapped[Optional["Role"]] = relationship(back_populates="users")
    department: Mapped[Optional["Department"]] = relationship()
    employee: Mapped[Optional["Employee"]] = relationship()
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")
    sidebar_permissions: Mapped[List["UserSidebarPermission"]] = relationship(back_populates="user")
    correspondence_permissions: Mapped[List["UserCorrespondencePermission"]] = relationship(back_populates="user")


# ============================================================
# ORGANIZATION MODELS
# ============================================================

class Company(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    parent_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("companies.id"), default=None
    )
    registration_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    tax_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    city: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    country: Mapped[str] = mapped_column(String(100), default="Libya")
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    website: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    logo_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    stamp_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    letterhead_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    parent_company: Mapped[Optional["Company"]] = relationship(
        remote_side="Company.id", back_populates="sub_companies"
    )
    sub_companies: Mapped[List["Company"]] = relationship(
        back_populates="parent_company"
    )
    departments: Mapped[List["Department"]] = relationship(back_populates="company")


class Department(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("companies.id"), nullable=False
    )
    parent_department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    location: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    company: Mapped["Company"] = relationship(back_populates="departments")
    parent_department: Mapped[Optional["Department"]] = relationship(
        remote_side="Department.id", back_populates="sub_departments"
    )
    sub_departments: Mapped[List["Department"]] = relationship(
        back_populates="parent_department"
    )
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee", remote_side="Employee.id", foreign_keys=[manager_id]
    )
    employees: Mapped[List["Employee"]] = relationship(
        back_populates="department", foreign_keys="Employee.department_id"
    )


class Position(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    min_salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    max_salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    department: Mapped[Optional["Department"]] = relationship()
    employees: Mapped[List["Employee"]] = relationship(back_populates="position")


# ============================================================
# EMPLOYEE MODELS
# ============================================================

class Employee(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    mother_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    full_name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, default=None)
    place_of_birth: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    gender: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    marital_status: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    position_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("positions.id"), default=None
    )
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    hire_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    contract_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    contract_start: Mapped[Optional[date]] = mapped_column(Date, default=None)
    contract_end: Mapped[Optional[date]] = mapped_column(Date, default=None)
    salary: Mapped[Optional[float]] = mapped_column(Float, default=None)
    allowances: Mapped[Optional[float]] = mapped_column(Float, default=None)
    deductions: Mapped[Optional[float]] = mapped_column(Float, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    department: Mapped[Optional["Department"]] = relationship(
        back_populates="employees", foreign_keys=[department_id]
    )
    position: Mapped[Optional["Position"]] = relationship(back_populates="employees")
    manager: Mapped[Optional["Employee"]] = relationship(
        "Employee", remote_side="Employee.id"
    )
    documents: Mapped[List["EmployeeDocument"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    leaves: Mapped[List["EmployeeLeave"]] = relationship(
        back_populates="employee", foreign_keys="[EmployeeLeave.employee_id]",
        cascade="all, delete-orphan"
    )
    evaluations: Mapped[List["EmployeeEvaluation"]] = relationship(
        back_populates="employee", foreign_keys="[EmployeeEvaluation.employee_id]",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_employee_department", "department_id"),
        Index("ix_employee_status", "status"),
    )


class EmployeeDocument(Base, TimestampMixin):
    __tablename__ = "employee_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    issue_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    employee: Mapped["Employee"] = relationship(back_populates="documents")


class EmployeeLeave(Base, TimestampMixin):
    __tablename__ = "employee_leaves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    employee: Mapped["Employee"] = relationship(
        back_populates="leaves", foreign_keys=[employee_id]
    )
    approver: Mapped[Optional["Employee"]] = relationship(
        "Employee", foreign_keys=[approved_by]
    )

    __table_args__ = (
        Index("ix_leave_employee", "employee_id"),
        Index("ix_leave_dates", "start_date", "end_date"),
    )


class EmployeeEvaluation(Base, TimestampMixin):
    __tablename__ = "employee_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[Optional[date]] = mapped_column(Date, default=None)
    period_end: Mapped[Optional[date]] = mapped_column(Date, default=None)
    attendance_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    discipline_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    productivity_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    teamwork_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    commitment_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, default=None)
    manager_notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    recommendations: Mapped[Optional[str]] = mapped_column(Text, default=None)
    evaluated_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)

    employee: Mapped["Employee"] = relationship(back_populates="evaluations")


# ============================================================
# DRIVER MODELS
# ============================================================

class Driver(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    driver_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    full_name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    national_id: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    id_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    id_number: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    mother_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    phone2: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    license_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    license_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    license_issue_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    license_expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    license_issuing_authority: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    join_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    contract_type: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    license_photo_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    employee: Mapped[Optional["Employee"]] = relationship()
    documents: Mapped[List["DriverDocument"]] = relationship(
        back_populates="driver", cascade="all, delete-orphan"
    )


class DriverDocument(Base, TimestampMixin):
    __tablename__ = "driver_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    driver_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    driver: Mapped["Driver"] = relationship(back_populates="documents")


# ============================================================
# CUSTOMER MODELS
# ============================================================

class Customer(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    customer_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    customer_type: Mapped[str] = mapped_column(String(20), default="individual")
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    city: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    country: Mapped[str] = mapped_column(String(100), default="Libya")
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")

    interactions: Mapped[List["CustomerInteraction"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class CustomerInteraction(Base, TimestampMixin):
    __tablename__ = "customer_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    correspondence_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("correspondence.id"), default=None
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    customer: Mapped["Customer"] = relationship(back_populates="interactions")


# ============================================================
# CORRESPONDENCE MODELS
# ============================================================

class CorrespondenceType(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "correspondence_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    numbering_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    correspondences: Mapped[List["Correspondence"]] = relationship(back_populates="cor_type")


class CorrespondenceStatus(Base, TimestampMixin):
    __tablename__ = "correspondence_statuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)


class Correspondence(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "correspondence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    reference_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("correspondence_types.id"), nullable=False
    )
    status_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("correspondence_statuses.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, default=None)
    importance: Mapped[str] = mapped_column(String(20), default="normal")
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    sender_department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    receiver_department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    sender_entity: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    receiver_entity: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    responsible_employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    driver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("drivers.id"), default=None
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("customers.id"), default=None
    )
    linked_correspondence_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("correspondence.id"), default=None
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archive_date: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    version: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    cor_type: Mapped["CorrespondenceType"] = relationship(back_populates="correspondences")
    status: Mapped["CorrespondenceStatus"] = relationship()
    sender_department: Mapped[Optional["Department"]] = relationship(
        "Department", foreign_keys=[sender_department_id]
    )
    receiver_department: Mapped[Optional["Department"]] = relationship(
        "Department", foreign_keys=[receiver_department_id]
    )
    responsible_employee: Mapped[Optional["Employee"]] = relationship(
        "Employee", foreign_keys=[responsible_employee_id]
    )
    creator: Mapped[Optional["Employee"]] = relationship(
        "Employee", foreign_keys=[employee_id]
    )
    driver: Mapped[Optional["Driver"]] = relationship()
    customer: Mapped[Optional["Customer"]] = relationship()
    linked_correspondence: Mapped[Optional["Correspondence"]] = relationship(
        "Correspondence", remote_side="Correspondence.id"
    )
    actions: Mapped[List["CorrespondenceAction"]] = relationship(
        back_populates="correspondence", cascade="all, delete-orphan"
    )
    attachments: Mapped[List["CorrespondenceAttachment"]] = relationship(
        back_populates="correspondence", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cor_reference", "reference_number"),
        Index("ix_cor_date", "date"),
        Index("ix_cor_status", "status_id"),
        Index("ix_cor_direction", "direction"),
    )


class CorrespondenceAction(Base, TimestampMixin):
    __tablename__ = "correspondence_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    correspondence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("correspondence.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_employee_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    to_employee_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    from_department_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    to_department_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    action_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    required_action: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    due_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    correspondence: Mapped["Correspondence"] = relationship(back_populates="actions")


class CorrespondenceAttachment(Base, TimestampMixin):
    __tablename__ = "correspondence_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    correspondence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("correspondence.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    correspondence: Mapped["Correspondence"] = relationship(back_populates="attachments")


# ============================================================
# WAREHOUSE MODELS
# ============================================================

class Warehouse(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")

    manager: Mapped[Optional["Employee"]] = relationship()
    items: Mapped[List["Item"]] = relationship(back_populates="warehouse")


class ItemCategory(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "item_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("item_categories.id"), default=None
    )
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    items: Mapped[List["Item"]] = relationship(back_populates="category")


class ItemUnit(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "item_units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(50), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    symbol: Mapped[Optional[str]] = mapped_column(String(10), default=None)

    items: Mapped[List["Item"]] = relationship(back_populates="unit")


class Supplier(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    address: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")

    items: Mapped[List["Item"]] = relationship(back_populates="supplier")


class Item(Base, TimestampMixin, ActiveMixin, SoftDeleteMixin):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("item_categories.id"), default=None
    )
    unit_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("item_units.id"), default=None
    )
    warehouse_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("warehouses.id"), default=None
    )
    supplier_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("suppliers.id"), default=None
    )
    min_quantity: Mapped[float] = mapped_column(Float, default=0)
    max_quantity: Mapped[float] = mapped_column(Float, default=0)
    current_quantity: Mapped[float] = mapped_column(Float, default=0)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, default=None)
    storage_location: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    shelf_number: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")

    category: Mapped[Optional["ItemCategory"]] = relationship(back_populates="items")
    unit: Mapped[Optional["ItemUnit"]] = relationship(back_populates="items")
    warehouse: Mapped[Optional["Warehouse"]] = relationship(back_populates="items")
    supplier: Mapped[Optional["Supplier"]] = relationship(back_populates="items")
    transactions: Mapped[List["StockTransaction"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_item_code", "code"),
        Index("ix_item_warehouse", "warehouse_id"),
    )


class StockTransaction(Base, TimestampMixin):
    __tablename__ = "stock_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, default=None)
    total_price: Mapped[Optional[float]] = mapped_column(Float, default=None)
    source: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    destination: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    reference_number: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("employees.id"), default=None
    )

    warehouse: Mapped["Warehouse"] = relationship()
    item: Mapped["Item"] = relationship(back_populates="transactions")
    employee: Mapped[Optional["Employee"]] = relationship()

    __table_args__ = (
        Index("ix_stock_trans_item", "item_id"),
        Index("ix_stock_trans_date", "date"),
    )


# ============================================================
# DOCUMENT / TEMPLATE MODELS
# ============================================================

class DocumentTemplate(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_html: Mapped[Optional[str]] = mapped_column(Text, default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    variables: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)


class Signature(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "signatures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, default=None)
    authority_level: Mapped[str] = mapped_column(String(20), default="normal")


class Stamp(Base, TimestampMixin, ActiveMixin):
    __tablename__ = "stamps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stamp_type: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class GeneratedDocument(Base, TimestampMixin):
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    verification_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    correspondence_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("correspondence.id"), default=None
    )
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_templates.id"), default=None
    )
    content_data: Mapped[Optional[str]] = mapped_column(Text, default=None)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    signature_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("signatures.id"), default=None
    )
    stamp_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stamps.id"), default=None
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)


# ============================================================
# NOTIFICATION MODELS
# ============================================================

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)


# ============================================================
# AUDIT LOG MODEL
# ============================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), default=None
    )
    username: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    entity_label: Mapped[Optional[str]] = mapped_column(String(200), default=None)
    old_values: Mapped[Optional[str]] = mapped_column(Text, default=None)
    new_values: Mapped[Optional[str]] = mapped_column(Text, default=None)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), default=None)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


# ============================================================
# SETTINGS MODEL
# ============================================================

class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, default=None)
    value_type: Mapped[str] = mapped_column(String(20), default="string")
    category: Mapped[str] = mapped_column(String(50), default="general")
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)


# ============================================================
# MASTER DATA MODELS
# ============================================================

class City(Base, ActiveMixin):
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    country: Mapped[str] = mapped_column(String(100), default="Libya")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class VehicleType(Base, ActiveMixin):
    __tablename__ = "vehicle_types"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    seats_count: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    vehicles = relationship("Vehicle", back_populates="vehicle_type")


class LicenseType(Base, ActiveMixin):
    __tablename__ = "license_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)


# ============================================================
# DELETED ITEM (سلة المحذوفات)
# ============================================================

class DeletedItem(Base, TimestampMixin):
    __tablename__ = "deleted_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # work_order, contract, client, etc.
    item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    item_number: Mapped[Optional[str]] = mapped_column(String(100), default=None)  # رقم العنصر
    item_title: Mapped[Optional[str]] = mapped_column(String(500), default=None)  # عنوان العنصر
    deleted_by: Mapped[Optional[str]] = mapped_column(String(200), default=None)  # اسم المحذف
    deleted_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), default=None)
    original_data: Mapped[Optional[str]] = mapped_column(Text, default=None)  # JSON backup of original data


class UserSidebarPermission(Base, TimestampMixin):
    """صلاحيات القائمة الجانبية للمستخدم"""
    __tablename__ = "user_sidebar_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True)
    can_add: Mapped[bool] = mapped_column(Boolean, default=True)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="sidebar_permissions")


class UserCorrespondencePermission(Base, TimestampMixin):
    """صلاحيات المراسلات للمستخدم"""
    __tablename__ = "user_correspondence_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_department_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("departments.id"), default=None
    )
    can_send: Mapped[bool] = mapped_column(Boolean, default=True)
    can_receive: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="correspondence_permissions")
    target_department: Mapped[Optional["Department"]] = relationship()


class ApprovalStep(Base, TimestampMixin):
    """خطوات الاعتماد
    تحدد ترتيب وشروط اعتماد اوامر التشغيل
    """
    __tablename__ = "approval_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    required_approver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), default="#667eea")
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    required_approver: Mapped[Optional["User"]] = relationship()
