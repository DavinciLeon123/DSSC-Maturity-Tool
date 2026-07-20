"""
Idempotent admin seed script.
Run: python scripts/create_admin.py
Called automatically by Docker entrypoint after alembic upgrade head.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, create_engine
from app.models.user import User
from app.core.security import hash_password
from app.core.config import settings


def create_admin():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        ).first()
        if not existing:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="ADMIN",
            )
            session.add(admin)
            session.commit()
            print(f"Admin user created: {settings.ADMIN_EMAIL}")
        else:
            print(f"Admin user already exists — skipping: {settings.ADMIN_EMAIL}")


if __name__ == "__main__":
    create_admin()
