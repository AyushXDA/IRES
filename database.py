"""
Database engine, session, and Base setup using SQLAlchemy.

ARCHITECTURE NOTES:
─────────────────────────────────────────────────────────────
1. Engine    → the "connection pool" to MySQL. Created ONCE.
2. SessionLocal → a factory that produces database sessions.
3. Base      → all ORM models inherit from this.
4. get_db()  → FastAPI dependency that yields a session per request
               and guarantees cleanup via `finally`.

WHY `yield` in get_db()?
  FastAPI dependencies that use `yield` act like context managers.
  Everything before `yield` runs BEFORE the route handler.
  Everything after `yield` runs AFTER the response is sent.
  This guarantees the session is always closed, even on exceptions.

Interview question: "How do you manage DB connections in FastAPI?"
  → "I use a dependency with yield that provides a scoped session
     and closes it in a finally block."
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import get_settings

settings = get_settings()

# ── Engine ─────────────────────────────────────────────────────
# pool_pre_ping=True → tests connection health before reuse (avoids stale connections)
# echo=True in debug → prints raw SQL to console (great for learning & debugging)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# ── Session Factory ────────────────────────────────────────────
# autocommit=False → we control when to commit (explicit transactions)
# autoflush=False  → we control when to flush (avoids surprise SQL during reads)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ── Declarative Base ──────────────────────────────────────────
Base = declarative_base()


# ── Dependency ────────────────────────────────────────────────
def get_db():
    """
    Yields a SQLAlchemy session for a single request lifecycle.
    Used as:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
