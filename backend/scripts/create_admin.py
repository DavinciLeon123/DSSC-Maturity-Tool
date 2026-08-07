"""
Idempotent admin seed script.
Run: python scripts/create_admin.py
Called automatically by Docker entrypoint after alembic upgrade head.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


def _seed_admin(session: Session, email: str, password: str) -> None:
    existing = session.exec(select(User).where(User.email == email)).first()
    if not existing:
        admin = User(email=email, hashed_password=hash_password(password), role="ADMIN")
        session.add(admin)
        session.commit()
        print(f"Admin user created: {email}")
    else:
        print(f"Admin user already exists — skipping: {email}")


def create_admin():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        _seed_admin(session, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
        for email, password in settings.additional_admins_list:
            _seed_admin(session, email, password)


if __name__ == "__main__":
    create_admin()
