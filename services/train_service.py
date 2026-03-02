"""
Train Service Layer — business logic for train CRUD and search.

DESIGN NOTES:
─────────────────────────────────────────────────────────────
1. Admin operations (add, update, delete) live alongside
   public operations (search, get) in the SAME service.
   Authorization is handled at the ROUTE level via dependencies,
   not here. The service doesn't know about HTTP or roles.

2. `add_train` sets available_seats = total_seats automatically.
   The admin never manually sets available_seats — that's derived.

3. `update_train` uses `model_dump(exclude_unset=True)` — a Pydantic
   v2 method that returns ONLY the fields the client actually sent.
   This enables true PATCH semantics:
     {"train_name": "New Name"}  → only updates the name
     {}                          → changes nothing

4. `search_trains` filters by source AND destination.
   Both are case-insensitive via `.ilike()` — "delhi" matches "Delhi".
   We also filter for available_seats > 0 by default.

5. `get_train_by_id` is a utility used by both admin routes and
   the booking service (to check seat availability).
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.train import Train
from ..schemas.train import TrainCreate, TrainUpdate


# ── Admin: Add Train ────────────────────────────────
def add_train(db: Session, train_data: TrainCreate) -> Train:
    """
    Create a new train.

    Steps:
      1. Check if train_number already exists → 409
      2. Create ORM object with available_seats = total_seats
      3. Commit and return

    WHY check duplicates in code?
      → Friendly error: "Train number 12301 already exists"
      → The DB unique constraint is a safety net for race conditions.
    """
    existing = db.query(Train).filter(
        Train.train_number == train_data.train_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Train number '{train_data.train_number}' already exists",
        )

    new_train = Train(
        train_number=train_data.train_number,
        train_name=train_data.train_name,
        source=train_data.source,
        destination=train_data.destination,
        total_seats=train_data.total_seats,
        available_seats=train_data.total_seats,  # ← all seats start available
        departure_time=train_data.departure_time,
        arrival_time=train_data.arrival_time,
    )

    db.add(new_train)
    db.commit()
    db.refresh(new_train)

    return new_train


# ── Admin: Update Train ─────────────────────────────
def update_train(db: Session, train_id: int, update_data: TrainUpdate) -> Train:
    """
    Partially update a train (PATCH semantics).

    Steps:
      1. Find train by ID → 404 if not found
      2. Extract only the fields the client sent (exclude_unset)
      3. If total_seats changed, adjust available_seats proportionally
      4. Apply changes and commit

    WHY exclude_unset=True?
      Without it, Optional fields default to None, and you'd
      accidentally overwrite existing data with None.

    Example:
      Client sends: {"train_name": "Shatabdi Express"}
      model_dump(exclude_unset=True) → {"train_name": "Shatabdi Express"}
      Only train_name is updated. Everything else stays.
    """
    train = get_train_by_id(db, train_id)

    update_dict = update_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    # Handle total_seats change: adjust available_seats accordingly
    if "total_seats" in update_dict:
        new_total = update_dict["total_seats"]
        old_total = train.total_seats
        booked_seats = old_total - train.available_seats

        if new_total < booked_seats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce total seats to {new_total}. "
                    f"Already {booked_seats} seats booked."
                ),
            )

        # Recalculate: new_available = new_total - already_booked
        update_dict["available_seats"] = new_total - booked_seats

    # Apply all updates to the ORM object
    for field, value in update_dict.items():
        setattr(train, field, value)

    db.commit()
    db.refresh(train)

    return train


# ── Admin: Delete Train ─────────────────────────────
def delete_train(db: Session, train_id: int) -> dict:
    """
    Delete a train by ID.

    Returns a confirmation message.
    In production, you might soft-delete (is_active = False)
    to preserve booking history. CASCADE on the FK will
    auto-delete related bookings.
    """
    train = get_train_by_id(db, train_id)

    db.delete(train)
    db.commit()

    return {"detail": f"Train '{train.train_name}' (ID: {train_id}) deleted"}


# ── Public: Get Train by ID ─────────────────────────
def get_train_by_id(db: Session, train_id: int) -> Train:
    """
    Fetch a single train by its primary key.
    Raises 404 if not found.

    Used by:
      - Admin update/delete routes
      - Booking service (to check availability)
    """
    train = db.query(Train).filter(Train.id == train_id).first()

    if not train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Train with ID {train_id} not found",
        )

    return train


# ── Public: Search Trains ────────────────────────────
def search_trains(
    db: Session,
    source: str | None = None,
    destination: str | None = None,
    only_available: bool = True,
) -> list[Train]:
    """
    Search trains by source and/or destination.

    Features:
      - Both params are optional — provide one or both
      - Case-insensitive matching via ILIKE (SQL LIKE with ignore case)
      - Optional filter for only trains with available seats
      - Returns empty list (not 404) if no trains found
        → 404 means "this URL doesn't exist"
        → Empty list means "query succeeded, no results"
        This is a common REST design mistake in interviews.

    SQL generated (both supplied):
      SELECT * FROM trains
      WHERE LOWER(source) LIKE LOWER('%delhi%')
        AND LOWER(destination) LIKE LOWER('%mumbai%')
        AND available_seats > 0;

    WHY ILIKE (case-insensitive)?
      Users might type "delhi", "Delhi", or "DELHI". All should match.
    """
    query = db.query(Train)

    if source:
        query = query.filter(Train.source.ilike(f"%{source}%"))
    if destination:
        query = query.filter(Train.destination.ilike(f"%{destination}%"))

    if only_available:
        query = query.filter(Train.available_seats > 0)

    return query.all()


# ── Public: List All Trains ──────────────────────────
def list_all_trains(db: Session) -> list[Train]:
    """Return all trains. Useful for admin dashboard or browsing."""
    return db.query(Train).all()
