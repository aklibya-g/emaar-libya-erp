from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.models.base_models import Correspondence, CorrespondenceType, Setting


class NumberingEngine:
    """
    محرك الترقيم الإشاري للمراسلات.

    يولد أرقام مثل:
      - و/مراسلات/2026/00125
      - ADM-OUT-2026-000123
      - م.إ/2026/123

    القواعد قابلة للتعديل من الإعدادات.
    """

    DEFAULT_FORMAT = "{prefix}/{type_code}/{year}/{sequence:05d}"
    YEARLY_RESET = True

    def __init__(self, session: Session):
        self.session = session

    def generate(self, type_code: str, department_code: Optional[str] = None) -> str:
        fmt = self._get_format()
        year = datetime.now().year
        prefix = self._get_prefix(type_code, department_code)
        sequence = self._get_next_sequence(type_code, year)

        try:
            ref = fmt.format(
                prefix=prefix,
                type_code=type_code,
                year=year,
                sequence=sequence,
                dept_code=department_code or "",
                date=datetime.now().strftime("%Y%m%d"),
            )
        except (KeyError, IndexError):
            ref = f"{prefix}/{type_code}/{year}/{sequence:05d}"

        while self._reference_exists(ref):
            sequence += 1
            ref = f"{prefix}/{type_code}/{year}/{sequence:05d}"

        return ref

    def _get_format(self) -> str:
        setting = (
            self.session.query(Setting)
            .filter(Setting.key == "numbering_format")
            .first()
        )
        return setting.value if setting else self.DEFAULT_FORMAT

    def _get_prefix(self, type_code: str, department_code: Optional[str] = None) -> str:
        setting = (
            self.session.query(Setting)
            .filter(Setting.key == "numbering_prefix")
            .first()
        )
        if setting:
            return setting.value

        type_obj = (
            self.session.query(CorrespondenceType)
            .filter(CorrespondenceType.code == type_code)
            .first()
        )
        return type_obj.numbering_prefix if type_obj else type_code

    def _get_next_sequence(self, type_code: str, year: int) -> int:
        latest = (
            self.session.query(Correspondence)
            .filter(
                Correspondence.type_id.in_(
                    self.session.query(CorrespondenceType.id).filter(
                        CorrespondenceType.code == type_code
                    )
                ),
                func.strftime("%Y", Correspondence.date) == str(year),
            )
            .order_by(Correspondence.reference_number.desc())
            .first()
        )

        if latest and latest.reference_number:
            parts = latest.reference_number.split("/")
            try:
                return int(parts[-1]) + 1
            except (ValueError, IndexError):
                pass

        first_of_year = (
            self.session.query(Correspondence)
            .filter(
                Correspondence.type_id.in_(
                    self.session.query(CorrespondenceType.id).filter(
                        CorrespondenceType.code == type_code
                    )
                ),
                func.strftime("%Y", Correspondence.date) == str(year),
            )
            .count()
        )
        return first_of_year + 1

    def _reference_exists(self, ref: str) -> bool:
        return (
            self.session.query(Correspondence)
            .filter(Correspondence.reference_number == ref)
            .count()
            > 0
        )

    def preview(self, type_code: str, department_code: Optional[str] = None) -> str:
        return self.generate(type_code, department_code)

    def get_format_options(self) -> list[dict]:
        return [
            {
                "name": "ال FORMAT الافتراضي",
                "format": "{prefix}/{type_code}/{year}/{sequence:05d}",
                "example": "و/OUT/2026/00045",
            },
            {
                "name": "القسم-النوع-السنة-الرقم",
                "format": "{dept_code}-{type_code}-{year}-{sequence:06d}",
                "example": "ADM-OUT-2026-000123",
            },
            {
                "name": "صيغة عربية",
                "format": "م.{type_code}/{year}/{sequence}",
                "example": "م.و/2026/45",
            },
            {
                "name": "بدون قسم",
                "format": "{type_code}/{year}/{sequence:05d}",
                "example": "OUT/2026/00045",
            },
        ]
