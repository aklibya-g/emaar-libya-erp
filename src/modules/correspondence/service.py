from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import or_, and_, func, desc, asc
from sqlalchemy.orm import Session

from src.core.models.base_models import (
    Correspondence, CorrespondenceType, CorrespondenceStatus,
    CorrespondenceAction, CorrespondenceAttachment, Employee, Department,
    generate_uuid,
)
from src.core.repositories.base_repository import BaseRepository
from src.core.security.auth_service import AuthService
from src.modules.correspondence.numbering import NumberingEngine
from src.modules.correspondence.workflow import CorrespondenceWorkflow, WorkflowState


class CorrespondenceService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BaseRepository(session, Correspondence)
        self.auth = AuthService(session)
        self.numbering = NumberingEngine(session)
        self.workflow = CorrespondenceWorkflow(session)

    def create(
        self,
        type_code: str,
        subject: str,
        direction: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        body: Optional[str] = None,
        importance: str = "normal",
        is_confidential: bool = False,
        sender_department_id: Optional[str] = None,
        receiver_department_id: Optional[str] = None,
        sender_entity: Optional[str] = None,
        receiver_entity: Optional[str] = None,
        responsible_employee_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        driver_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        linked_correspondence_id: Optional[str] = None,
        cor_date=None,
        due_date=None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        cor_type = (
            self.session.query(CorrespondenceType)
            .filter(CorrespondenceType.code == type_code)
            .first()
        )
        if not cor_type:
            raise ValueError(f"نوع المراسلة {type_code} غير موجود")

        draft_status = (
            self.session.query(CorrespondenceStatus)
            .filter(CorrespondenceStatus.code == WorkflowState.DRAFT)
            .first()
        )
        if not draft_status:
            raise ValueError("حالة DRAFT غير موجودة")

        ref_number = self.numbering.generate(type_code)

        dept_code = None
        if sender_department_id:
            dept = self.session.query(Department).filter(Department.id == sender_department_id).first()
            if dept:
                dept_code = dept.code

        correspondence = Correspondence(
            id=generate_uuid(),
            reference_number=ref_number,
            type_id=cor_type.id,
            status_id=draft_status.id,
            direction=direction,
            date=cor_date if cor_date else date.today(),
            subject=subject,
            body=body,
            importance=importance,
            is_confidential=is_confidential,
            sender_department_id=sender_department_id,
            receiver_department_id=receiver_department_id,
            sender_entity=sender_entity,
            receiver_entity=receiver_entity,
            responsible_employee_id=responsible_employee_id if responsible_employee_id and self.session.query(Employee).filter(Employee.id == responsible_employee_id, Employee.is_deleted == False).first() else None,
            employee_id=employee_id if employee_id and self.session.query(Employee).filter(Employee.id == employee_id, Employee.is_deleted == False).first() else None,
            driver_id=driver_id,
            customer_id=customer_id,
            linked_correspondence_id=linked_correspondence_id,
            due_date=due_date,
            notes=notes,
            created_by=user_id,
        )
        self.session.add(correspondence)
        self.session.flush()

        self.auth.log_audit(
            user_id=user_id,
            username=username,
            action="create",
            module="correspondence",
            entity_type="Correspondence",
            entity_id=correspondence.id,
            entity_label=ref_number,
            new_values=f"Subject: {subject}",
        )

        return correspondence

    def update(self, id: str, user_id: Optional[str] = None, username: Optional[str] = None, **kwargs):
        cor = self.repo.get_by_id(id)
        if not cor:
            return None
        if cor.status and cor.status.code not in [WorkflowState.DRAFT]:
            raise ValueError("لا يمكن تعديل مراسلة ليست في حالة مسودة")
        return self.repo.update(id, **kwargs)

    def get_by_id(self, id: str) -> Optional[Correspondence]:
        return self.repo.get_by_id(id)

    def get_by_reference(self, reference: str) -> Optional[Correspondence]:
        return (
            self.session.query(Correspondence)
            .filter(Correspondence.reference_number == reference)
            .first()
        )

    def search(
        self,
        query: Optional[str] = None,
        direction: Optional[str] = None,
        type_code: Optional[str] = None,
        status_code: Optional[str] = None,
        department_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        importance: Optional[str] = None,
        is_confidential: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        customer_id: Optional[str] = None,
        driver_id: Optional[bool] = None,
        overdue_only: bool = False,
    ) -> List[Correspondence]:
        q = self.session.query(Correspondence).filter(Correspondence.is_deleted == False)

        if query:
            search_filter = or_(
                Correspondence.reference_number.ilike(f"%{query}%"),
                Correspondence.subject.ilike(f"%{query}%"),
                Correspondence.body.ilike(f"%{query}%"),
                Correspondence.sender_entity.ilike(f"%{query}%"),
                Correspondence.receiver_entity.ilike(f"%{query}%"),
            )
            q = q.filter(search_filter)

        if direction:
            q = q.filter(Correspondence.direction == direction)

        if type_code:
            type_ids = self.session.query(CorrespondenceType.id).filter(
                CorrespondenceType.code == type_code
            )
            q = q.filter(Correspondence.type_id.in_(type_ids))

        if status_code:
            status_ids = self.session.query(CorrespondenceStatus.id).filter(
                CorrespondenceStatus.code == status_code
            )
            q = q.filter(Correspondence.status_id.in_(status_ids))

        if department_id:
            q = q.filter(
                or_(
                    Correspondence.sender_department_id == department_id,
                    Correspondence.receiver_department_id == department_id,
                )
            )

        if employee_id:
            q = q.filter(
                or_(
                    Correspondence.employee_id == employee_id,
                    Correspondence.responsible_employee_id == employee_id,
                )
            )

        if date_from:
            q = q.filter(Correspondence.date >= date_from)
        if date_to:
            q = q.filter(Correspondence.date <= date_to)

        if importance:
            q = q.filter(Correspondence.importance == importance)

        if is_confidential is not None:
            q = q.filter(Correspondence.is_confidential == is_confidential)

        if is_archived is not None:
            q = q.filter(Correspondence.is_archived == is_archived)

        if customer_id:
            q = q.filter(Correspondence.customer_id == customer_id)

        if driver_id:
            q = q.filter(Correspondence.driver_id.isnot(None))

        if overdue_only:
            q = q.filter(
                and_(
                    Correspondence.due_date < date.today(),
                    Correspondence.is_archived == False,
                )
            )

        return q.order_by(desc(Correspondence.date), desc(Correspondence.created_at)).all()

    def get_inbox(self, department_id: Optional[str] = None, employee_id: Optional[str] = None) -> List[Correspondence]:
        return self.search(
            direction="IN",
            department_id=department_id,
            employee_id=employee_id,
            is_archived=False,
        )

    def get_outbox(self, department_id: Optional[str] = None, employee_id: Optional[str] = None) -> List[Correspondence]:
        return self.search(
            direction="OUT",
            department_id=department_id,
            employee_id=employee_id,
            is_archived=False,
        )

    def get_pending(self, employee_id: Optional[str] = None) -> List[Correspondence]:
        q = self.session.query(Correspondence).filter(
            Correspondence.is_deleted == False,
            Correspondence.is_archived == False,
            Correspondence.due_date < date.today(),
        )
        if employee_id:
            q = q.filter(Correspondence.responsible_employee_id == employee_id)
        return q.order_by(Correspondence.due_date).all()

    def add_attachment(
        self,
        correspondence_id: str,
        filename: str,
        file_path: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> CorrespondenceAttachment:
        att = CorrespondenceAttachment(
            id=generate_uuid(),
            correspondence_id=correspondence_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            notes=notes,
        )
        self.session.add(att)
        self.session.flush()
        return att

    def get_attachments(self, correspondence_id: str) -> List[CorrespondenceAttachment]:
        return (
            self.session.query(CorrespondenceAttachment)
            .filter(CorrespondenceAttachment.correspondence_id == correspondence_id)
            .all()
        )

    def link_correspondences(
        self,
        source_id: str,
        target_id: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> bool:
        cor = self.repo.get_by_id(source_id)
        if cor:
            cor.linked_correspondence_id = target_id
            self.auth.log_audit(
                user_id=user_id,
                username=username,
                action="link",
                module="correspondence",
                entity_type="Correspondence",
                entity_id=source_id,
                entity_label=cor.reference_number,
                new_values=f"Linked to: {target_id}",
            )
            return True
        return False

    def get_statistics(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        base_q = self.session.query(Correspondence).filter(Correspondence.is_deleted == False)
        if department_id:
            base_q = base_q.filter(
                or_(
                    Correspondence.sender_department_id == department_id,
                    Correspondence.receiver_department_id == department_id,
                )
            )

        total = base_q.count()
        incoming = base_q.filter(Correspondence.direction == "IN").count()
        outgoing = base_q.filter(Correspondence.direction == "OUT").count()
        internal = base_q.filter(Correspondence.direction == "INT").count()
        archived = base_q.filter(Correspondence.is_archived == True).count()
        overdue = base_q.filter(
            and_(
                Correspondence.due_date < date.today(),
                Correspondence.is_archived == False,
            )
        ).count()

        draft = base_q.filter(
            Correspondence.status_id.in_(
                self.session.query(CorrespondenceStatus.id).filter(
                    CorrespondenceStatus.code == WorkflowState.DRAFT
                )
            )
        ).count()

        in_review = base_q.filter(
            Correspondence.status_id.in_(
                self.session.query(CorrespondenceStatus.id).filter(
                    CorrespondenceStatus.code == WorkflowState.REVIEW
                )
            )
        ).count()

        return {
            "total": total,
            "incoming": incoming,
            "outgoing": outgoing,
            "internal": internal,
            "archived": archived,
            "overdue": overdue,
            "draft": draft,
            "in_review": in_review,
        }

    def get_monthly_trend(self, months: int = 12) -> List[Dict[str, Any]]:
        from datetime import timedelta
        today = date.today()
        trends = []
        for i in range(months - 1, -1, -1):
            d = today.replace(day=1)
            if d.month - i <= 0:
                year = d.year - 1
                month = 12 + (d.month - i)
            else:
                year = d.year
                month = d.month - i
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1)
            else:
                end = date(year, month + 1, 1)

            count = (
                self.session.query(Correspondence)
                .filter(
                    Correspondence.is_deleted == False,
                    Correspondence.date >= start,
                    Correspondence.date < end,
                )
                .count()
            )
            trends.append({"month": f"{year}-{month:02d}", "count": count})
        return trends

    def delete(self, id: str, user_id: Optional[str] = None, username: Optional[str] = None) -> bool:
        cor = self.repo.get_by_id(id)
        if not cor:
            return False
        if cor.status and cor.status.code != WorkflowState.DRAFT:
            raise ValueError("لا يمكن حذف مراسلة ليست في حالة مسودة")
        return self.repo.delete(id, soft=True)
