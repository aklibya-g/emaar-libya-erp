from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from jinja2 import Template
from sqlalchemy.orm import Session

from src.core.models.base_models import (
    DocumentTemplate, GeneratedDocument, Correspondence,
    Company, Signature, Stamp, Employee,
)
from src.core.repositories.base_repository import BaseRepository


class TemplateEngine:
    def __init__(self, session: Session):
        self.session = session
        self.template_repo = BaseRepository(session, DocumentTemplate)
        self.doc_repo = BaseRepository(session, GeneratedDocument)

    def get_templates(self, template_type: Optional[str] = None) -> List[DocumentTemplate]:
        q = self.session.query(DocumentTemplate).filter(DocumentTemplate.is_active == True)
        if template_type:
            q = q.filter(DocumentTemplate.template_type == template_type)
        return q.all()

    def get_default_template(self, template_type: str) -> Optional[DocumentTemplate]:
        return (
            self.session.query(DocumentTemplate)
            .filter(
                DocumentTemplate.template_type == template_type,
                DocumentTemplate.is_default == True,
                DocumentTemplate.is_active == True,
            )
            .first()
        )

    def render_template(
        self,
        template_id: str,
        context: Dict[str, Any],
    ) -> str:
        template = self.template_repo.get_by_id(template_id)
        if not template:
            raise ValueError("القالب غير موجود")

        html = template.content_html or ""
        if not html and template.file_path and os.path.exists(template.file_path):
            with open(template.file_path, "r", encoding="utf-8") as f:
                html = f.read()

        jinja_template = Template(html)
        return jinja_template.render(**context)

    def build_context(
        self,
        correspondence: Correspondence,
        company: Optional[Company] = None,
        signature: Optional[Signature] = None,
        stamp: Optional[Stamp] = None,
    ) -> Dict[str, Any]:
        if not company:
            company = self.session.query(Company).first()

        sender_dept = None
        receiver_dept = None
        if correspondence.sender_department_id:
            sender_dept = self.session.query(Employee).filter(
                Employee.id == correspondence.responsible_employee_id
            ).first()
        if correspondence.receiver_department_id:
            receiver_dept_name = None

        responsible = None
        if correspondence.responsible_employee_id:
            responsible = self.session.query(Employee).filter(
                Employee.id == correspondence.responsible_employee_id
            ).first()

        return {
            "company_name": company.name_ar if company else "",
            "company_name_en": company.name_en if company else "",
            "company_address": company.address if company else "",
            "company_phone": company.phone if company else "",
            "company_email": company.email if company else "",
            "reference_number": correspondence.reference_number or "",
            "date": correspondence.date.strftime("%Y-%m-%d") if correspondence.date else "",
            "date_ar": self._format_date_ar(correspondence.date) if correspondence.date else "",
            "subject": correspondence.subject or "",
            "body": correspondence.body or "",
            "importance": correspondence.importance or "",
            "sender_entity": correspondence.sender_entity or "",
            "receiver_entity": correspondence.receiver_entity or "",
            "responsible_employee": responsible.full_name_ar if responsible else "",
            "responsible_position": responsible.position.name_ar if responsible and responsible.position else "",
            "signature_name": signature.title if signature else "",
            "signature_image": signature.image_path if signature else "",
            "stamp_name": stamp.name if stamp else "",
            "stamp_image": stamp.image_path if stamp else "",
            "qr_code": "",
            "verification_code": "",
            "attachments": "",
            "notes": correspondence.notes or "",
        }

    def generate_document(
        self,
        correspondence_id: str,
        template_id: str,
        signature_id: Optional[str] = None,
        stamp_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> GeneratedDocument:
        correspondence = self.session.query(Correspondence).filter(
            Correspondence.id == correspondence_id
        ).first()
        if not correspondence:
            raise ValueError("المراسلة غير موجودة")

        signature = None
        if signature_id:
            signature = self.session.query(Signature).filter(Signature.id == signature_id).first()

        stamp = None
        if stamp_id:
            stamp = self.session.query(Stamp).filter(Stamp.id == stamp_id).first()

        context = self.build_context(correspondence, signature=signature, stamp=stamp)
        rendered_html = self.render_template(template_id, context)

        doc_uuid = str(uuid.uuid4())
        verification_code = f"EMR-{datetime.now().year}-{doc_uuid[:8].upper()}"

        generated = GeneratedDocument(
            id=doc_uuid,
            document_uuid=doc_uuid,
            verification_code=verification_code,
            title=correspondence.subject,
            document_type=correspondence.cor_type.code if correspondence.cor_type else "",
            correspondence_id=correspondence_id,
            template_id=template_id,
            content_data=rendered_html,
            signature_id=signature_id,
            stamp_id=stamp_id,
            status="draft",
            version=1,
            generated_by=user_id,
        )
        self.session.add(generated)
        self.session.flush()

        return generated

    def approve_document(
        self,
        document_id: str,
        user_id: Optional[str] = None,
    ) -> GeneratedDocument:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise ValueError("المستند غير موجود")
        doc.status = "approved"
        doc.approved_by = user_id
        doc.approval_date = datetime.utcnow()
        self.session.flush()
        return doc

    def finalize_document(self, document_id: str) -> GeneratedDocument:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise ValueError("المستند غير موجود")
        doc.status = "final"
        doc.is_final = True
        self.session.flush()
        return doc

    def _format_date_ar(self, d) -> str:
        if not d:
            return ""
        months = [
            "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
        ]
        return f"{d.day} {months[d.month]} {d.year}"

    def get_document_variables(self) -> List[Dict[str, str]]:
        return [
            {"variable": "{{company_name}}", "description": "اسم الشركة بالعربية"},
            {"variable": "{{company_name_en}}", "description": "اسم الشركة بالإنجليزية"},
            {"variable": "{{reference_number}}", "description": "الرقم الإشاري"},
            {"variable": "{{date}}", "description": "التاريخ"},
            {"variable": "{{date_ar}}", "description": "التاريخ بالعربية"},
            {"variable": "{{subject}}", "description": "الموضوع"},
            {"variable": "{{body}}", "description": "نص المراسلة"},
            {"variable": "{{sender_entity}}", "description": "الجهة المرسلة"},
            {"variable": "{{receiver_entity}}", "description": "الجهة المستلمة"},
            {"variable": "{{responsible_employee}}", "description": "الموظف المسؤول"},
            {"variable": "{{responsible_position}}", "description": "صفة المسؤول"},
            {"variable": "{{signature_image}}", "description": "صورة التوقيع"},
            {"variable": "{{stamp_image}}", "description": "صورة الختم"},
            {"variable": "{{qr_code}}", "description": "رمز QR"},
            {"variable": "{{verification_code}}", "description": "رمز التحقق"},
            {"variable": "{{attachments}}", "description": "المرفقات"},
            {"variable": "{{notes}}", "description": "الملاحظات"},
        ]
