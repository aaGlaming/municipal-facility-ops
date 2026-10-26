from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db


def get_settings_dependency() -> Settings:
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()
