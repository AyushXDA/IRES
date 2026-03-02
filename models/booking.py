"""
Booking ORM Model

DESIGN DECISIONS:
─────────────────────────────────────────────────────────────
1. `user_id` + `train_id` are foreign keys.
   → This creates the classic many-to-many relationship:
     One user → many bookings.
     One train → many bookings.
   → The bookings table is the JOIN/ASSOCIATION table with extra data.

2. `seat_number` is assigned at booking time.
   → Simple approach: seat_number = total_seats - available_seats + 1
   → Unique per train? We add a UniqueConstraint(train_id, seat_number).
     This means the DB itself prevents two bookings for the same seat
     on the same train — defense in depth beyond application logic.

3. `status` tracks booking lifecycle:
   → "confirmed"  → seat is booked
   → "cancelled"  → user cancelled (available_seats incremented back)
   → We don't DELETE bookings — we soft-delete via status.
   → Why? Audit trail. In real systems (banking, railways) you never
     lose transaction history.

4. `booked_at` uses server_default for consistency.

5. `ondelete="CASCADE"`:
   → If a user or train is deleted, their bookings are also removed.
   → In production you'd likely use RESTRICT or soft-delete instead,
     but CASCADE is simpler for learning.

6. Foreign key indexes:
   → SQLAlchemy auto-creates indexes on FKs for MySQL/InnoDB, but
     we're explicit with `index=True` for clarity.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from ..database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    train_id = Column(
        Integer,
        ForeignKey("trains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="confirmed")  # confirmed | cancelled
    booked_at = Column(DateTime, server_default=func.now())

    # ── Relationships ────────────────────────────────
    user = relationship("User", back_populates="bookings")
    train = relationship("Train", back_populates="bookings")

    # ── Table-level constraints ──────────────────────
    __table_args__ = (
        UniqueConstraint("train_id", "seat_number", name="uq_train_seat"),
    )

    def __repr__(self):
        return (
            f"<Booking(id={self.id}, user={self.user_id}, "
            f"train={self.train_id}, seat={self.seat_number}, status='{self.status}')>"
        )
