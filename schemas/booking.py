"""
Booking Pydantic Schemas

DESIGN NOTES:
─────────────────────────────────────────────────────────────
1. BookingCreate only needs `train_id`.
   → The `user_id` comes from the JWT token (the logged-in user).
   → NEVER let the client specify user_id — that would let someone
     book on behalf of another user. Security rule: identity comes
     from the auth token, not from the request body.

2. BookingResponse includes nested user and train info.
   → The client shouldn't need a second API call to see who booked
     what train. We embed the relevant details.

3. `seat_number` is assigned server-side.
   → The client doesn't choose their seat in this system.
   → Calculated as: total_seats - available_seats + 1 (before decrement)
     or simply the next available number.

4. Status is read-only in the response.
   → Clients can't set status directly. They call:
     POST /bookings → creates with status="confirmed"
     DELETE /bookings/{id} → changes status to "cancelled"
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Create ──────────────────────────────────────────
class BookingCreate(BaseModel):
    """POST /bookings — user books a seat on a train."""
    train_id: int = Field(
        ...,
        ge=1,
        examples=[1],
        description="ID of the train to book",
    )


# ── Response ────────────────────────────────────────
class BookingResponse(BaseModel):
    """Full booking details returned to the client."""
    id: int
    user_id: int
    train_id: int
    seat_number: int
    status: str
    booked_at: datetime

    # Nested info so client doesn't need extra API calls
    train_name: Optional[str] = None
    train_number: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None

    class Config:
        from_attributes = True


# ── Booking list response (simpler) ─────────────────
class BookingListItem(BaseModel):
    """Compact booking info for listing booking history."""
    id: int
    train_number: str
    train_name: str
    source: str
    destination: str
    seat_number: int
    status: str
    booked_at: datetime

    class Config:
        from_attributes = True
