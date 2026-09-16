from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from src.core.models.base_models import (
    Correspondence, CorrespondenceStatus, CorrespondenceAction,
    Employee, Department,
)


class WorkflowState:
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SIGNED = "SIGNED"
    STAMPED = "STAMPED"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    FORWARDED = "FORWARDED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"


class WorkflowTransition:
    def __init__(
        self,
        from_state: str,
        to_state: str,
        action_name: str,
        requires_permission: Optional[str] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.action_name = action_name
        self.requires_permission = requires_permission


TRANSITIONS: List[WorkflowTransition] = [
    WorkflowTransition(WorkflowState.DRAFT, WorkflowState.REVIEW, "إرسال للمراجعة"),
    WorkflowTransition(WorkflowState.DRAFT, WorkflowState.CANCELLED, "إلغاء"),
    WorkflowTransition(WorkflowState.REVIEW, WorkflowState.APPROVED, "اعتماد"),
    WorkflowTransition(WorkflowState.REVIEW, WorkflowState.DRAFT, "إعادة للمسودة"),
    WorkflowTransition(WorkflowState.REVIEW, WorkflowState.CANCELLED, "إلغاء"),
    WorkflowTransition(WorkflowState.APPROVED, WorkflowState.SIGNED, "توقيع"),
    WorkflowTransition(WorkflowState.APPROVED, WorkflowState.CANCELLED, "إلغاء"),
    WorkflowTransition(WorkflowState.SIGNED, WorkflowState.STAMPED, "ختم"),
    WorkflowTransition(WorkflowState.SIGNED, WorkflowState.SENT, "إرسال بدون ختم"),
    WorkflowTransition(WorkflowState.STAMPED, WorkflowState.SENT, "إرسال"),
    WorkflowTransition(WorkflowState.SENT, WorkflowState.RECEIVED, "استلام"),
    WorkflowTransition(WorkflowState.SENT, WorkflowState.FORWARDED, "إحالة"),
    WorkflowTransition(WorkflowState.FORWARDED, WorkflowState.RECEIVED, "استلام"),
    WorkflowTransition(WorkflowState.FORWARDED, WorkflowState.FORWARDED, "إحالة مجددة"),
    WorkflowTransition(WorkflowState.RECEIVED, WorkflowState.COMPLETED, "تنفيذ"),
    WorkflowTransition(WorkflowState.RECEIVED, WorkflowState.FORWARDED, "إحالة"),
    WorkflowTransition(WorkflowState.COMPLETED, WorkflowState.ARCHIVED, "أرشفة"),
]

VALID_TRANSITIONS = {(t.from_state, t.to_state): t for t in TRANSITIONS}


class CorrespondenceWorkflow:
    def __init__(self, session: Session):
        self.session = session

    def _get_current_state(self, correspondence: Correspondence) -> str:
        if correspondence.status_id:
            status_obj = self.session.query(CorrespondenceStatus).filter(
                CorrespondenceStatus.id == correspondence.status_id
            ).first()
            if status_obj:
                return status_obj.code
        return WorkflowState.DRAFT

    def get_available_transitions(self, correspondence: Correspondence) -> List[WorkflowTransition]:
        current = self._get_current_state(correspondence)
        transitions = []
        for t in TRANSITIONS:
            if t.from_state == current:
                transitions.append(t)
        return transitions

    def can_transition(self, correspondence: Correspondence, target_state: str) -> bool:
        current = self._get_current_state(correspondence)
        return (current, target_state) in VALID_TRANSITIONS

    def execute_transition(
        self,
        correspondence: Correspondence,
        target_state: str,
        employee_id: Optional[str] = None,
        notes: Optional[str] = None,
        to_employee_id: Optional[str] = None,
        to_department_id: Optional[str] = None,
        required_action: Optional[str] = None,
        due_date=None,
    ) -> Tuple[bool, str]:
        current = self._get_current_state(correspondence)
        transition_key = (current, target_state)

        if transition_key not in VALID_TRANSITIONS:
            return False, f"الانتقال من {current} إلى {target_state} غير مسموح"

        transition = VALID_TRANSITIONS[transition_key]

        status = (
            self.session.query(CorrespondenceStatus)
            .filter(CorrespondenceStatus.code == target_state)
            .first()
        )
        if not status:
            return False, f"حالة {target_state} غير موجودة في قاعدة البيانات"

        correspondence.status_id = status.id

        if target_state == WorkflowState.SENT:
            correspondence.is_archived = False
        elif target_state == WorkflowState.ARCHIVED:
            correspondence.is_archived = True
            correspondence.archive_date = datetime.utcnow()

        action = CorrespondenceAction(
            correspondence_id=correspondence.id,
            action_type=transition.action_name,
            from_employee_id=employee_id,
            to_employee_id=to_employee_id,
            from_department_id=correspondence.sender_department_id,
            to_department_id=to_department_id,
            action_date=datetime.utcnow(),
            required_action=required_action,
            due_date=due_date,
            notes=notes,
        )
        self.session.add(action)
        self.session.flush()

        return True, f"تم الانتقال إلى حالة: {target_state}"

    def get_workflow_history(self, correspondence_id: str) -> List[CorrespondenceAction]:
        return (
            self.session.query(CorrespondenceAction)
            .filter(CorrespondenceAction.correspondence_id == correspondence_id)
            .order_by(CorrespondenceAction.action_date.desc())
            .all()
        )

    def forward(
        self,
        correspondence: Correspondence,
        from_employee_id: str,
        to_employee_id: str,
        to_department_id: str,
        required_action: Optional[str] = None,
        due_date=None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        ok, msg = self.execute_transition(
            correspondence,
            WorkflowState.FORWARDED,
            employee_id=from_employee_id,
            notes=notes,
            to_employee_id=to_employee_id,
            to_department_id=to_department_id,
            required_action=required_action,
            due_date=due_date,
        )
        if ok and to_employee_id:
            correspondence.responsible_employee_id = to_employee_id
            if to_department_id:
                correspondence.receiver_department_id = to_department_id
        return ok, msg

    def reject(
        self,
        correspondence: Correspondence,
        employee_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        return self.execute_transition(
            correspondence,
            WorkflowState.DRAFT,
            employee_id=employee_id,
            notes=notes or "مرفوض - يُعاد للمراجعة",
        )

    def get_status_color(self, status_code: str) -> str:
        colors = {
            WorkflowState.DRAFT: "#6b7280",
            WorkflowState.REVIEW: "#f59e0b",
            WorkflowState.APPROVED: "#3b82f6",
            WorkflowState.SIGNED: "#8b5cf6",
            WorkflowState.STAMPED: "#06b6d4",
            WorkflowState.SENT: "#10b981",
            WorkflowState.RECEIVED: "#10b981",
            WorkflowState.FORWARDED: "#f59e0b",
            WorkflowState.COMPLETED: "#059669",
            WorkflowState.ARCHIVED: "#6b7280",
            WorkflowState.CANCELLED: "#ef4444",
        }
        return colors.get(status_code, "#6b7280")

    def get_status_label_ar(self, status_code: str) -> str:
        labels = {
            WorkflowState.DRAFT: "مسودة",
            WorkflowState.REVIEW: "قيد المراجعة",
            WorkflowState.APPROVED: "معتمد",
            WorkflowState.SIGNED: "موقع",
            WorkflowState.STAMPED: "مختم",
            WorkflowState.SENT: "تم الإرسال",
            WorkflowState.RECEIVED: "تم الاستلام",
            WorkflowState.FORWARDED: "محال",
            WorkflowState.COMPLETED: "تم التنفيذ",
            WorkflowState.ARCHIVED: "مؤرشف",
            WorkflowState.CANCELLED: "ملغي",
        }
        return labels.get(status_code, status_code)
