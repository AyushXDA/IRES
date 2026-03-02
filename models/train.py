"""
Train ORM Model

DESIGN DECISIONS:
─────────────────────────────────────────────────────────────
1. `train_number` is unique + indexed.
   → Real-world trains have an official number (e.g., 12301 Rajdhani).
   → This is the "business key" — users search by it.
   → We keep a separate `id` as the technical primary key so that
     foreign keys reference a stable integer, not a string.

2. `source` and `destination` are indexed.
   → The most common query is: "trains from A to B"
   → Without indexes this is a full table scan — unacceptable at scale.

3. `total_seats` vs `available_seats`:
   → `total_seats`     = the physical capacity (set once by admin).
   → `available_seats`  = decremented on each booking, incremented on cancel.
   → WHY separate columns?
     Interview answer: "total_seats is an invariant. available_seats is
     a mutable counter that changes with every booking. Keeping them
     separate lets us validate: available_seats can never exceed total_seats."

4. `available_seats` is the HOT column for concurrency.
   → This is the column we'll protect with SELECT ... FOR UPDATE
     to prevent double-booking. More on this in the booking step.

5. Relationship `bookings` links to booking records for this train.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, func
)
from sqlalchemy.orm import relationship
from ..database import Base


class Train(Base):
    __tablename__ = "trains"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    train_number = Column(String(20), unique=True, nullable=False, index=True)
    train_name = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False, index=True)
    destination = Column(String(100), nullable=False, index=True)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    departure_time = Column(String(10), nullable=True)   # e.g. "14:30"
    arrival_time = Column(String(10), nullable=True)      # e.g. "22:15"
    created_at = Column(DateTime, server_default=func.now())

    # ── Relationships ────────────────────────────────
    bookings = relationship("Booking", back_populates="train", lazy="select")

    def __repr__(self):
        return (
            f"<Train(id={self.id}, number='{self.train_number}', "
            f"name='{self.train_name}', seats={self.available_seats}/{self.total_seats})>"
        )
