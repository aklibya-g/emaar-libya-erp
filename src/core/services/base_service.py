from __future__ import annotations

from typing import TypeVar, Generic, Optional, List, Type, Any

from sqlalchemy.orm import Session

from src.core.database.connection import Base
from src.core.repositories.base_repository import BaseRepository
from src.core.security.auth_service import AuthService

T = TypeVar("T", bound=Base)


class BaseService(Generic[T]):
    def __init__(self, session: Session, model: Type[T], module_name: str):
        self.session = session
        self.model = model
        self.module_name = module_name
        self.repo = BaseRepository(session, model)
        self.auth = AuthService(session)

    def get_by_id(self, id: str) -> Optional[T]:
        return self.repo.get_by_id(id)

    def get_all(self, **kwargs) -> List[T]:
        return self.repo.get_all(**kwargs)

    def create(self, user_id: Optional[str] = None, username: Optional[str] = None, **kwargs) -> T:
        obj = self.repo.create(**kwargs)
        self.auth.log_audit(
            user_id=user_id,
            username=username,
            action="create",
            module=self.module_name,
            entity_type=self.model.__name__,
            entity_id=obj.id,
            entity_label=self._get_label(obj),
            new_values=str(kwargs),
        )
        return obj

    def update(
        self,
        id: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        **kwargs,
    ) -> Optional[T]:
        old = self.repo.get_by_id(id)
        if not old:
            return None
        old_values = self._get_changes(old, kwargs)
        obj = self.repo.update(id, **kwargs)
        if obj:
            self.auth.log_audit(
                user_id=user_id,
                username=username,
                action="update",
                module=self.module_name,
                entity_type=self.model.__name__,
                entity_id=obj.id,
                entity_label=self._get_label(obj),
                old_values=old_values,
                new_values=str(kwargs),
            )
        return obj

    def delete(self, id: str, user_id: Optional[str] = None, username: Optional[str] = None) -> bool:
        obj = self.repo.get_by_id(id)
        if not obj:
            return False
        label = self._get_label(obj)
        result = self.repo.delete(id, soft=True)
        if result:
            self.auth.log_audit(
                user_id=user_id,
                username=username,
                action="delete",
                module=self.module_name,
                entity_type=self.model.__name__,
                entity_id=id,
                entity_label=label,
            )
        return result

    def count(self, **kwargs) -> int:
        return self.repo.count(**kwargs)

    def _get_label(self, obj: T) -> Optional[str]:
        for attr in ["full_name_ar", "name_ar", "reference_number", "username", "title", "code"]:
            if hasattr(obj, attr):
                return str(getattr(obj, attr))
        return str(obj.id)

    def _get_changes(self, old: T, new_kwargs: dict) -> str:
        changes = []
        for key, value in new_kwargs.items():
            if hasattr(old, key):
                old_val = getattr(old, key)
                if old_val != value:
                    changes.append(f"{key}: {old_val} -> {value}")
        return "; ".join(changes) if changes else ""
