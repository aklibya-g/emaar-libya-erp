from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak,
)
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.core.models.base_models import (
    GeneratedDocument, Correspondence, Company, Signature, Stamp,
)


class PDFGenerator:
    def __init__(self, output_dir: str = "data/generated_pdfs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._setup_fonts()

    def _setup_fonts(self):
        try:
            pdfmetrics.registerFont(TTFont("Arabic", "assets/fonts/NotoSansArabic-Regular.ttf"))
        except Exception:
            pass

    def generate_correspondence_pdf(
        self,
        correspondence: Correspondence,
        company: Optional[Company] = None,
        signature: Optional[Signature] = None,
        stamp: Optional[Stamp] = None,
        output_filename: Optional[str] = None,
    ) -> str:
        if not output_filename:
            ref = (correspondence.reference_number or "doc").replace("/", "-").replace("\\", "-")
            output_filename = f"{ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        output_path = os.path.join(self.output_dir, output_filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=25 * mm,
            leftMargin=25 * mm,
            topMargin=30 * mm,
            bottomMargin=25 * mm,
        )

        styles = getSampleStyleSheet()
        elements = []

        company_name = company.name_ar if company else "شركة إعمار ليبيا لنقل الركاب"
        company_en = company.name_en if company else "Emaar Libya Passenger Transport"
        company_addr = company.address if company else ""

        header_style = ParagraphStyle(
            "Header",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=4,
            textColor=HexColor("#1e40af"),
        )
        sub_header_style = ParagraphStyle(
            "SubHeader",
            parent=styles["Heading2"],
            alignment=TA_CENTER,
            fontSize=11,
            spaceAfter=2,
            textColor=HexColor("#6b7280"),
        )
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            alignment=TA_RIGHT,
            fontSize=12,
            leading=18,
            spaceAfter=8,
        )
        ref_style = ParagraphStyle(
            "Ref",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontSize=11,
            spaceAfter=6,
            textColor=HexColor("#374151"),
        )
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontSize=9,
            textColor=HexColor("#9ca3af"),
        )

        elements.append(Paragraph(company_name, header_style))
        elements.append(Paragraph(company_en, sub_header_style))
        elements.append(Spacer(1, 10))

        line = Table([[""]], colWidths=[160 * mm])
        line.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 2, HexColor("#1e40af")),
        ]))
        elements.append(line)
        elements.append(Spacer(1, 15))

        ref_text = f"الرقم الإشاري: {correspondence.reference_number or '-'}"
        date_text = f"التاريخ: {correspondence.date.strftime('%Y-%m-%d') if correspondence.date else '-'}"
        info_table = Table(
            [[Paragraph(ref_text, ref_style), Paragraph(date_text, ref_style)]],
            colWidths=[80 * mm, 80 * mm],
        )
        info_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        importance_map = {"high": "عاجل", "normal": "عادي", "low": "منخفض"}
        importance = importance_map.get(correspondence.importance, "عادي")
        elements.append(Paragraph(f"<b>الأهمية:</b> {importance}", ref_style))
        elements.append(Spacer(1, 8))

        if correspondence.sender_entity:
            elements.append(Paragraph(f"<b>الجهة المرسلة:</b> {correspondence.sender_entity}", ref_style))
        if correspondence.receiver_entity:
            elements.append(Paragraph(f"<b>الجهة المستلمة:</b> {correspondence.receiver_entity}", ref_style))
        elements.append(Spacer(1, 10))

        subject_style = ParagraphStyle(
            "Subject",
            parent=body_style,
            fontSize=13,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=15,
        )
        elements.append(Paragraph(f"<b>الموضوع: {correspondence.subject}</b>", subject_style))

        if correspondence.body:
            body_text = correspondence.body.replace("\n", "<br/>")
            elements.append(Paragraph(body_text, body_style))

        elements.append(Spacer(1, 30))

        sig_stamp_data = []
        if signature:
            sig_stamp_data.append([
                Paragraph(f"<b>التوقيع:</b> {signature.title or ''}", ref_style),
                Paragraph(f"<b>الختم:</b> {stamp.name if stamp else ''}", ref_style),
            ])
        else:
            sig_stamp_data.append([
                Paragraph("", ref_style),
                Paragraph("", ref_style),
            ])

        sig_table = Table(sig_stamp_data, colWidths=[80 * mm, 80 * mm])
        sig_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(sig_table)

        elements.append(Spacer(1, 20))

        if correspondence.is_confidential:
            elements.append(Paragraph(
                "<b>سري -سري-</b>",
                ParagraphStyle("Secret", parent=ref_style, alignment=TA_CENTER, textColor=HexColor("#ef4444")),
            ))
            elements.append(Spacer(1, 10))

        elements.append(Paragraph(
            f"تم إنشاء هذا المستند إلكترونيًا - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            footer_style,
        ))

        doc.build(elements)
        return output_path

    def generate_from_html(self, html_content: str, output_filename: str) -> str:
        output_path = os.path.join(self.output_dir, output_filename)
        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(output_path)
        except ImportError:
            from reportlab.platypus import SimpleDocTemplate
            from reportlab.lib.pagesizes import A4
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            from reportlab.platypus import Paragraph as RLParagraph
            from reportlab.lib.styles import getSampleStyleSheet
            styles = getSampleStyleSheet()
            elements = [RLParagraph(html_content[:2000], styles["Normal"])]
            doc.build(elements)
        return output_path
