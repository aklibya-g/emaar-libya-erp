from __future__ import annotations

import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.core.models.base_models import User, AuditLog


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = (
            self.session.query(User)
            .filter(User.username == username, User.is_active == True, User.is_deleted == False)
            .first()
        )
        if not user:
            return None

        if user.locked_until and user.locked_until > datetime.utcnow():
            return None

        if not verify_password(password, user.password_hash):
            user.login_attempts += 1
            if user.login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            self.session.commit()
            return None

        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.session.commit()
        return user

    def create_user(
        self,
        username: str,
        password: str,
        full_name_ar: str,
        role_id: str,
        full_name_en: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        department_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> User:
        user = User(
            username=username,
            password_hash=hash_password(password),
            full_name_ar=full_name_ar,
            full_name_en=full_name_en,
            email=email,
            phone=phone,
            role_id=role_id,
            department_id=department_id,
            employee_id=employee_id,
            created_by=created_by,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def change_password(self, user_id: str, new_password: str) -> bool:
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        user.password_hash = hash_password(new_password)
        self.session.commit()
        return True

    def check_permission(self, user: User, module: str, screen: str, action: str) -> bool:
        if not user.role:
            return False
        from src.core.models.base_models import RolePermission, Permission

        perm = (
            self.session.query(Permission)
            .filter(
                Permission.module == module,
                Permission.screen == screen,
                Permission.action == action,
            )
            .first()
        )
        if not perm:
            return False

        rp = (
            self.session.query(RolePermission)
            .filter(
                RolePermission.role_id == user.role_id,
                RolePermission.permission_id == perm.id,
                RolePermission.granted == True,
            )
            .first()
        )
        return rp is not None

    def log_audit(
        self,
        user_id: Optional[str],
        username: Optional[str],
        action: str,
        module: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_label: Optional[str] = None,
        old_values: Optional[str] = None,
        new_values: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        self.session.add(log)
        self.session.flush()
