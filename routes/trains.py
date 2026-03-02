"""
Train Routes — Admin CRUD + Public Search

ROUTE ORGANIZATION:
─────────────────────────────────────────────────────────────
We use TWO routers in one file to separate concerns:

  admin_router (prefix: /admin/trains)
    → All endpoints require `Depends(get_current_admin)`
    → POST, PATCH, DELETE operations

  public_router (prefix: /trains)
    → No auth required (anyone can search)
    → GET operations only

WHY two routers?
  → Clean Swagger UI grouping (Admin vs Public tags)
  → Admin routes can get a different rate limiter or middleware later
  → Makes it visually obvious which routes are protected

REST CONVENTIONS:
  POST   /admin/trains          → Create (201)
  PATCH  /admin/trains/{id}     → Partial update (200)
  DELETE /admin/trains/{id}     → Delete (200)
  GET    /trains                → List all (200)
  GET    /trains/{id}           → Get one (200)
  GET    /trains/search         → Search with query params (200)
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..schemas.train import TrainCreate, TrainUpdate, TrainResponse
from ..services.train_service import (
    add_train,
    update_train,
    delete_train,
    get_train_by_id,
    search_trains,
    list_all_trains,
)
from ..auth.dependencies import get_current_admin
from ..models.user import User


# ═══════════════════════════════════════════════════════
#  ADMIN ROUTES — require admin JWT
# ═══════════════════════════════════════════════════════

admin_router = APIRouter(
    prefix="/admin/trains",
    tags=["Admin: Train Management"],
)


@admin_router.post(
    "",
    response_model=TrainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new train",
)
def create_train(
    train_data: TrainCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),     # ← protected
):
    """
    Admin-only: Add a new train to the system.

    - `available_seats` is auto-set to `total_seats`
    - `train_number` must be unique
    """
    return add_train(db, train_data)


@admin_router.patch(
    "/{train_id}",
    response_model=TrainResponse,
    summary="Update train details",
)
def modify_train(
    train_id: int,
    update_data: TrainUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin-only: Partially update a train.

    Send only the fields you want to change.
    If `total_seats` is reduced, it validates that enough seats aren't
    already booked.
    """
    return update_train(db, train_id, update_data)


@admin_router.delete(
    "/{train_id}",
    summary="Delete a train",
)
def remove_train(
    train_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Admin-only: Delete a train and its bookings (CASCADE).

    Returns a confirmation message.
    """
    return delete_train(db, train_id)


# ═══════════════════════════════════════════════════════
#  PUBLIC ROUTES — no auth required
# ═══════════════════════════════════════════════════════

public_router = APIRouter(
    prefix="/trains",
    tags=["Trains: Search & Availability"],
)


@public_router.get(
    "",
    response_model=list[TrainResponse],
    summary="List all trains",
)
def get_all_trains(
    db: Session = Depends(get_db),
):
    """
    Returns all trains in the system.
    No authentication required.
    """
    return list_all_trains(db)


@public_router.get(
    "/search",
    response_model=list[TrainResponse],
    summary="Search trains by route",
)
def search(
    source: Optional[str] = Query(
        None,
        min_length=1,
        description="Departure station (case-insensitive, partial match)",
        examples=["Delhi"],
    ),
    destination: Optional[str] = Query(
        None,
        min_length=1,
        description="Arrival station (case-insensitive, partial match)",
        examples=["Mumbai"],
    ),
    only_available: bool = Query(
        True,
        description="If true, only return trains with available seats",
    ),
    db: Session = Depends(get_db),
):
    """
    Search trains by source and/or destination.

    - Both params are optional — supply one or both
    - Case-insensitive partial matching (e.g., "del" matches "New Delhi")
    - Optionally filter for only trains with available seats
    - Returns empty list if no matches (not 404)

    Example: `/trains/search?source=Delhi&destination=Mumbai`
    """
    return search_trains(db, source, destination, only_available)


@public_router.get(
    "/stations",
    response_model=list[str],
    summary="List all unique station names",
)
def get_stations(db: Session = Depends(get_db)):
    """
    Returns a sorted list of unique station names (sources + destinations).
    Used for autocomplete / suggestions in the frontend.
    """
    from ..models.train import Train as TrainModel
    sources = db.query(TrainModel.source).distinct().all()
    destinations = db.query(TrainModel.destination).distinct().all()
    stations = sorted({s[0] for s in sources} | {d[0] for d in destinations})
    return stations


@public_router.get(
    "/{train_id}",
    response_model=TrainResponse,
    summary="Get train details by ID",
)
def get_train(
    train_id: int,
    db: Session = Depends(get_db),
):
    """
    Get details of a specific train including seat availability.
    Returns 404 if train doesn't exist.
    """
    return get_train_by_id(db, train_id)
