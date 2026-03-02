"""
Booking Service — the MOST interview-critical module.

This file demonstrates:
  1. Database transactions (BEGIN → operations → COMMIT/ROLLBACK)
  2. Row-level locking (SELECT ... FOR UPDATE)
  3. Race condition prevention
  4. Atomic seat assignment

THE DOUBLE-BOOKING PROBLEM:
─────────────────────────────────────────────────────────────
Imagine 2 users try to book the LAST seat at the same time:

  WITHOUT locking (BROKEN):
  ┌─────────────── Time ─────────────────┐
  │ User A: SELECT available_seats → 1   │
  │ User B: SELECT available_seats → 1   │  ← both see 1 seat
  │ User A: UPDATE SET seats = 0, INSERT │
  │ User B: UPDATE SET seats = -1, INSERT│  ← DOUBLE BOOKED!
  └──────────────────────────────────────┘

  WITH SELECT ... FOR UPDATE (CORRECT):
  ┌─────────────── Time ─────────────────┐
  │ User A: SELECT ... FOR UPDATE → 1   │  ← locks the row
  │ User B: SELECT ... FOR UPDATE → ⏳   │  ← BLOCKED, waits
  │ User A: UPDATE SET seats = 0, INSERT │
  │ User A: COMMIT                       │  ← releases lock
  │ User B: SELECT ... FOR UPDATE → 0   │  ← now sees 0
  │ User B: → "No seats available" (409) │  ← correctly rejected
  └──────────────────────────────────────┘

HOW SELECT ... FOR UPDATE WORKS:
  1. It acquires a ROW-LEVEL EXCLUSIVE LOCK on the selected rows.
  2. Other transactions that try to read the SAME rows with
     FOR UPDATE will BLOCK until the lock is released.
  3. The lock is released when the transaction COMMITs or ROLLBACKs.
  4. This is a PESSIMISTIC locking strategy.

  In SQLAlchemy: db.query(Train).filter(...).with_for_update().first()

  The SQL generated:
    SELECT * FROM trains WHERE id = 1 FOR UPDATE;

ALTERNATIVE: Optimistic Locking
  Instead of locking, you add a `version` column:
    UPDATE trains SET seats = seats - 1, version = version + 1
    WHERE id = 1 AND version = 5;
  If another transaction already incremented the version,
  this UPDATE affects 0 rows → retry.
  Better for high-read, low-write scenarios.

  We use PESSIMISTIC locking here because bookings are
  high-write during peak hours (like IRCTC on Tatkal day).

Interview question: "How do you handle concurrent bookings?"
  → "I use SELECT ... FOR UPDATE inside a transaction. This acquires
     a row-level lock on the train row, so only one transaction can
     read-and-modify the seat count at a time. Other concurrent
     requests wait until the lock is released. This guarantees
     atomic seat assignment with zero double-bookings."
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from ..models.train import Train
from ..models.booking import Booking


def book_seat(db: Session, user_id: int, train_id: int) -> Booking:
    """
    Book a seat on a train with concurrency-safe locking.

    TRANSACTION FLOW:
    ─────────────────────────────────────────────────────
    1. BEGIN TRANSACTION (implicit — autocommit=False)
    2. SELECT train FOR UPDATE    → locks the row
    3. Check available_seats > 0  → reject if full
    4. Check duplicate booking    → prevent same user rebooking
    5. Calculate seat_number      → total - available + 1
    6. Decrement available_seats  → atomic within lock
    7. INSERT booking record
    8. COMMIT                     → releases lock
    9. On ANY error → ROLLBACK   → releases lock, undoes all changes

    The try/except/finally ensures the lock is ALWAYS released,
    even if an unexpected error occurs.
    """
    try:
        # ── Step 1: Lock the train row ────────────────
        # with_for_update() generates: SELECT ... FOR UPDATE
        # This BLOCKS other transactions from reading this row
        # until we COMMIT or ROLLBACK.
        train = (
            db.query(Train)
            .filter(Train.id == train_id)
            .with_for_update()          # ← THE CRITICAL LINE
            .first()
        )

        if not train:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Train with ID {train_id} not found",
            )

        # ── Step 2: Check seat availability ───────────
        if train.available_seats <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No seats available on this train",
            )

        # ── Step 3: Prevent duplicate booking ─────────
        # Same user can't book the same train twice (confirmed)
        existing_booking = (
            db.query(Booking)
            .filter(
                and_(
                    Booking.user_id == user_id,
                    Booking.train_id == train_id,
                    Booking.status == "confirmed",
                )
            )
            .first()
        )

        if existing_booking:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a confirmed booking on this train",
            )

        # ── Step 4: Calculate seat number ─────────────
        # Seat assignment: next sequential number
        # If 200 total, 198 available → 2 booked → next seat = 3
        seat_number = train.total_seats - train.available_seats + 1

        # ── Step 5: Decrement available seats ─────────
        train.available_seats -= 1

        # ── Step 6: Create booking record ─────────────
        new_booking = Booking(
            user_id=user_id,
            train_id=train_id,
            seat_number=seat_number,
            status="confirmed",
        )

        db.add(new_booking)

        # ── Step 7: Commit transaction ────────────────
        # This releases the FOR UPDATE lock.
        # Both the seat decrement AND the booking insert are
        # committed ATOMICALLY — either both succeed or neither does.
        db.commit()
        db.refresh(new_booking)

        return new_booking

    except HTTPException:
        db.rollback()       # release lock on business errors
        raise               # re-raise the HTTP error as-is

    except Exception as e:
        db.rollback()       # release lock on unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Booking failed: {str(e)}",
        )


def cancel_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    """
    Cancel a booking and restore the seat.

    WHY soft-delete (status = "cancelled") instead of DELETE?
      → Audit trail. Every transaction is preserved.
      → Analytics: "How many cancellations per train?"
      → Customer support: "Show me all bookings including cancelled"

    TRANSACTION FLOW:
      1. Find booking by ID (must belong to this user)
      2. Lock the train row (FOR UPDATE)
      3. Increment available_seats
      4. Set booking status = "cancelled"
      5. Commit atomically
    """
    try:
        # Find the booking — must belong to the requesting user
        booking = (
            db.query(Booking)
            .filter(
                and_(
                    Booking.id == booking_id,
                    Booking.user_id == user_id,
                )
            )
            .first()
        )

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found or doesn't belong to you",
            )

        if booking.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled",
            )

        # Lock the train row to safely increment seats
        train = (
            db.query(Train)
            .filter(Train.id == booking.train_id)
            .with_for_update()
            .first()
        )

        if train:
            train.available_seats += 1

        booking.status = "cancelled"

        db.commit()
        db.refresh(booking)

        return booking

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cancellation failed: {str(e)}",
        )


def get_user_bookings(db: Session, user_id: int) -> list[dict]:
    """
    Get all bookings for a user (booking history).

    Returns a list of dicts with booking + train details joined.
    This uses a JOIN query to avoid N+1 problem:
      BAD:  for booking in bookings: booking.train.train_name  ← N+1 queries
      GOOD: join bookings with trains in a single query

    Interview question: "What is the N+1 query problem?"
      → "If you load 10 bookings, then access booking.train for each,
         SQLAlchemy fires 1 query for bookings + 10 queries for trains
         = 11 queries total. A JOIN does it in 1 query."
    """
    bookings = (
        db.query(Booking, Train)
        .join(Train, Booking.train_id == Train.id)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.booked_at.desc())
        .all()
    )

    # Transform the joined rows into structured dicts
    result = []
    for booking, train in bookings:
        result.append({
            "id": booking.id,
            "train_number": train.train_number,
            "train_name": train.train_name,
            "source": train.source,
            "destination": train.destination,
            "seat_number": booking.seat_number,
            "status": booking.status,
            "booked_at": booking.booked_at,
        })

    return result
