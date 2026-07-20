from sqlmodel import Session, create_engine
from app.core.config import settings

# Railway: ensure service has 512MB+ memory (verified via Railway dashboard)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=15,        # Maintained connections (sleeping between requests)
    max_overflow=25,     # Extra connections during peak (total max = 40)
    pool_pre_ping=True,  # Validate connections before use (catches stale/dropped)
    pool_recycle=1800,   # Recycle connections after 30 min (prevents idle timeout)
)


def get_session():
    with Session(engine) as session:
        yield session
