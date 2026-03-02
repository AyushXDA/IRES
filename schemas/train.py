"""
Train Pydantic Schemas

DESIGN NOTES:
─────────────────────────────────────────────────────────────
1. TrainCreate does NOT include `available_seats`.
   → When an admin adds a train, they set `total_seats`.
   → `available_seats` is auto-set to equal `total_seats` by the
     service layer. The admin shouldn't manually set it — that
     would be error-prone and could lead to inconsistency.

2. TrainUpdate uses Optional fields.
   → PATCH semantics: only send the fields you want to change.
   → The service layer will merge provided fields with existing data.

3. TrainResponse includes `available_seats` for users to see.

4. TrainSearch is a schema for query parameters, not a request body.
   → FastAPI reads these from the URL: /trains/search?source=Delhi&destination=Mumbai

5. Field validators:
   → `ge=1` on total_seats ensures you can't create a train with 0 seats.
   → `min_length=1` on source/destination prevents empty strings.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Base ─────────────────────────────────────────────
class TrainBase(BaseModel):
    train_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        examples=["12301"],
        description="Official train number",
    )
    train_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Rajdhani Express"],
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["New Delhi"],
    )
    destination: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Mumbai Central"],
    )


# ── Create (Admin) ──────────────────────────────────
class TrainCreate(TrainBase):
    """POST /admin/trains — admin adds a new train."""
    total_seats: int = Field(
        ...,
        ge=1,                        # must be ≥ 1
        examples=[200],
        description="Total seat capacity",
    )
    departure_time: Optional[str] = Field(
        None,
        examples=["14:30"],
        description="Departure time (HH:MM)",
    )
    arrival_time: Optional[str] = Field(
        None,
        examples=["22:15"],
        description="Arrival time (HH:MM)",
    )


# ── Update (Admin) ──────────────────────────────────
class TrainUpdate(BaseModel):
    """PATCH /admin/trains/{id} — partial update."""
    train_name: Optional[str] = Field(None, min_length=1, max_length=100)
    source: Optional[str] = Field(None, min_length=1, max_length=100)
    destination: Optional[str] = Field(None, min_length=1, max_length=100)
    total_seats: Optional[int] = Field(None, ge=1)
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None


# ── Response ────────────────────────────────────────
class TrainResponse(TrainBase):
    """What the API returns for a train."""
    id: int
    total_seats: int
    available_seats: int
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
