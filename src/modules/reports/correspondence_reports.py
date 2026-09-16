from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    Department, Employee,
)
from src.modules.correspondence.service import CorrespondenceService


class CorrespondenceReports:
    def __init__(self, session: Session):
        self.session = session

    def correspondence_summary(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        department_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        q = self.session.query(Correspondence).filter(Correspondence.is_deleted == False)
        if date_from:
            q = q.filter(Correspondence.date >= date_from)
        if date_to:
            q = q.filter(Correspondence.date <= date_to)
        if department_id:
            q = q.filter(
                or_(
                    Correspondence.sender_department_id == department_id,
                    Correspondence.receiver_department_id == department_id,
                )
            )

        total = q.count()
        by_direction = {}
        for direction in ["IN", "OUT", "INT", "EXT"]:
            count = q.filter(Correspondence.direction == direction).count()
            by_direction[direction] = count

        by_status = {}
        statuses = self.session.query(CorrespondenceStatus).all()
        for s in statuses:
            count = q.filter(Correspondence.status_id == s.id).count()
            if count > 0:
                by_status[s.name_ar] = count

        by_importance = {}
        for imp in ["normal", "high", "critical"]:
            count = q.filter(Correspondence.importance == imp).count()
            by_importance[imp] = count

        overdue = q.filter(
            and_(
                Correspondence.due_date < date.today(),
                Correspondence.is_archived == False,
            )
        ).count()

        return {
            "total": total,
            "by_direction": by_direction,
            "by_status": by_status,
            "by_importance": by_importance,
            "overdue": overdue,
        }

    def department_statistics(self) -> List[Dict[str, Any]]:
        depts = self.session.query(Department).filter(Department.is_active == True).all()
        results = []
        for dept in depts:
            sent = self.session.query(Correspondence).filter(
                Correspondence.sender_department_id == dept.id,
                Correspondence.is_deleted == False,
            ).count()
            received = self.session.query(Correspondence).filter(
                Correspondence.receiver_department_id == dept.id,
                Correspondence.is_deleted == False,
            ).count()
            results.append({
                "department": dept.name_ar,
                "department_id": dept.id,
                "sent": sent,
                "received": received,
                "total": sent + received,
            })
        results.sort(key=lambda x: x["total"], reverse=True)
        return results

    def employee_workload(self, limit: int = 10) -> List[Dict[str, Any]]:
        emps = self.session.query(Employee).filter(Employee.status == "active").all()
        results = []
        for emp in emps:
            assigned = self.session.query(Correspondence).filter(
                Correspondence.responsible_employee_id == emp.id,
                Correspondence.is_deleted == False,
                Correspondence.is_archived == False,
            ).count()
            overdue = self.session.query(Correspondence).filter(
                Correspondence.responsible_employee_id == emp.id,
                Correspondence.is_deleted == False,
                Correspondence.is_archived == False,
                Correspondence.due_date < date.today(),
            ).count()
            results.append({
                "employee": emp.full_name_ar,
                "employee_id": emp.id,
                "assigned": assigned,
                "overdue": overdue,
            })
        results.sort(key=lambda x: x["assigned"], reverse=True)
        return results[:limit]

    def daily_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        from datetime import timedelta
        today = date.today()
        trends = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            count = self.session.query(Correspondence).filter(
                Correspondence.date == d,
                Correspondence.is_deleted == False,
            ).count()
            trends.append({"date": d.isoformat(), "count": count})
        return trends

    def overdue_report(self) -> List[Dict[str, Any]]:
        overdue = self.session.query(Correspondence).filter(
            Correspondence.is_deleted == False,
            Correspondence.is_archived == False,
            Correspondence.due_date < date.today(),
        ).order_by(Correspondence.due_date).all()

        results = []
        for cor in overdue:
            results.append({
                "reference": cor.reference_number,
                "subject": cor.subject,
                "due_date": str(cor.due_date),
                "status": cor.status.name_ar if cor.status else "-",
                "responsible": cor.responsible_employee.full_name_ar if cor.responsible_employee else "-",
                "department": cor.receiver_department.name_ar if cor.receiver_department else "-",
            })
        return results
