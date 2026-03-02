"""
User ORM Model

DESIGN DECISIONS:
─────────────────────────────────────────────────────────────
1. `id` is an auto-incrementing integer primary key.
   → Simple, fast joins, works perfectly for a monolith.
   → In microservices you'd use UUID — but for this system, int is ideal.

2. `email` is unique + indexed.
   → Login lookups hit this column — index makes it O(log n) not O(n).
   → `unique=True` enforces at the DB level, not just app level.
     Interview tip: "Never rely only on application-level validation
     for uniqueness — always enforce it at the database level too."

3. `role` defaults to "user".
   → Two roles: "user" and "admin".
   → We use a simple string column (not an enum table) because
     there are only 2 roles and they won't change often.

4. `hashed_password` — we NEVER store plaintext passwords.
   → bcrypt is slow by design (cost factor) to resist brute-force.

5. `created_at` uses server_default with `func.now()`.
   → The DB server sets the timestamp, not Python.
   → Why? If your app servers have clock skew, DB time is consistent.

6. Relationship `bookings` with back_populates creates a bidirectional
   link: user.bookings ↔ booking.user
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, func
)
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default="user")  # "user" | "admin"
    created_at = Column(DateTime, server_default=func.now())

    # ── Relationships ────────────────────────────────
    bookings = relationship("Booking", back_populates="user", lazy="select")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
