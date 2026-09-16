from __future__ import annotations

from typing import TypeVar, Generic, Optional, List, Type

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from src.core.database.connection import Base
from src.core.models.base_models import generate_uuid

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        if "id" not in self.model.__table__.columns:
            return None
        return self.session.query(self.model).filter(self.model.id == id).first()

    def get_all(
        self,
        active_only: bool = False,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[T]:
        q = self.session.query(self.model)
        if active_only and hasattr(self.model, "is_active"):
            q = q.filter(self.model.is_active == True)
        if order_by and hasattr(self.model, order_by):
            q = q.order_by(asc(getattr(self.model, order_by)))
        elif hasattr(self.model, "created_at"):
            q = q.order_by(desc(self.model.created_at))
        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)
        return q.all()

    def create(self, **kwargs) -> T:
        has_id_col = "id" in self.model.__table__.columns
        if has_id_col and "id" not in kwargs:
            kwargs["id"] = generate_uuid()
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, id: str, **kwargs) -> Optional[T]:
        obj = self.get_by_id(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)
        self.session.flush()
        return obj

    def delete(self, id: str, soft: bool = True) -> bool:
        obj = self.get_by_id(id)
        if not obj:
            return False
        if soft and hasattr(obj, "is_deleted"):
            obj.is_deleted = True
            from datetime import datetime
            obj.deleted_at = datetime.utcnow()
        else:
            self.session.delete(obj)
        self.session.flush()
        return True

    def count(self, active_only: bool = False) -> int:
        q = self.session.query(self.model)
        if active_only and hasattr(self.model, "is_active"):
            q = q.filter(self.model.is_active == True)
        return q.count()

    def exists(self, **kwargs) -> bool:
        return self.session.query(self.model).filter_by(**kwargs).first() is not None
