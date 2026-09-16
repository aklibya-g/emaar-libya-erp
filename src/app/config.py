from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class DatabaseSettings(BaseSettings):
    url: str = Field(default="")
    echo: bool = False
    pool_pre_ping: bool = True

    model_config = {"env_prefix": "DATABASE_"}

    def get_url(self):
        if self.url:
            return self.url
        env_url = os.environ.get("DATABASE_URL", "")
        if env_url:
            if env_url.startswith("postgres://"):
                env_url = env_url.replace("postgres://", "postgresql://", 1)
            return env_url
        return f"sqlite:///{BASE_DIR / 'data' / 'emaar_erp.db'}"


class CompanyDefaults(BaseSettings):
    country: str = "Libya"
    currency: str = "LYD"
    language: str = "ar"
    timezone: str = "Africa/Tripoli"

    model_config = {"env_prefix": "DEFAULT_"}


class SecuritySettings(BaseSettings):
    secret_key: str = "change-me-in-production"
    password_min_length: int = 8
    session_timeout_minutes: int = 480
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    model_config = {"env_prefix": ""}


class BackupSettings(BaseSettings):
    enabled: bool = True
    directory: str = str(BASE_DIR / "data" / "backups")
    retention_days: int = 30
    auto_backup_enabled: bool = False
    auto_backup_interval_hours: int = 24

    model_config = {"env_prefix": "BACKUP_"}


class AppSettings(BaseSettings):
    name: str = "Emaar Libya ERP"
    version: str = "1.0.0"
    debug: bool = False

    database: DatabaseSettings = DatabaseSettings()
    company: CompanyDefaults = CompanyDefaults()
    security: SecuritySettings = SecuritySettings()
    backup: BackupSettings = BackupSettings()

    base_dir: Path = BASE_DIR
    assets_dir: Path = BASE_DIR / "assets"
    templates_dir: Path = BASE_DIR / "assets" / "templates"
    stamps_dir: Path = BASE_DIR / "assets" / "stamps"
    signatures_dir: Path = BASE_DIR / "assets" / "signatures"
    fonts_dir: Path = BASE_DIR / "assets" / "fonts"
    data_dir: Path = BASE_DIR / "data"
    logs_dir: Path = BASE_DIR / "logs"
    config_dir: Path = BASE_DIR / "config"

    model_config = {"env_prefix": "APP_"}


settings = AppSettings()


def ensure_directories() -> None:
    for d in [
        settings.data_dir,
        settings.logs_dir,
        settings.assets_dir,
        settings.templates_dir,
        settings.stamps_dir,
        settings.signatures_dir,
        settings.fonts_dir,
        Path(settings.backup.directory),
    ]:
        d.mkdir(parents=True, exist_ok=True)
