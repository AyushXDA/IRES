"""
Booking Routes — Book seats, cancel, view history.

ALL routes here require authentication (get_current_user).
Users can only manage THEIR OWN bookings — user_id comes
from the JWT token, never from the request body.

ROUTE DESIGN:
  POST   /bookings          → Book a seat (user sends only train_id)
  DELETE /bookings/{id}     → Cancel a booking (soft-delete)
  GET    /bookings/my       → User's booking history

WHY /bookings/my instead of /users/{id}/bookings?
  → Simpler: the user doesn't need to know their own ID.
  → Safer: there's no way to accidentally view another user's bookings.
  → The identity comes from the JWT token.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.booking import BookingCreate, BookingResponse, BookingListItem
from ..services.booking_service import book_seat, cancel_booking, get_user_bookings
from ..auth.dependencies import get_current_user
from ..models.user import User

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a seat on a train",
)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a seat on the specified train.

    - User ID is extracted from the JWT token (not from request body)
    - Seat number is assigned automatically
    - Uses row-level locking to prevent double-booking
    - Prevents duplicate confirmed bookings on the same train

    **Concurrency safe**: If two users try to book the last seat
    simultaneously, only one succeeds. The other gets 409 Conflict.
    """
    booking = book_seat(db, current_user.id, booking_data.train_id)

    # Enrich response with train details
    # (the ORM relationship loads train lazily)
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        train_id=booking.train_id,
        seat_number=booking.seat_number,
        status=booking.status,
        booked_at=booking.booked_at,
        train_name=booking.train.train_name,
        train_number=booking.train.train_number,
        source=booking.train.source,
        destination=booking.train.destination,
    )


@router.delete(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Cancel a booking",
)
def cancel(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a confirmed booking.

    - Only the booking owner can cancel (enforced by user_id from JWT)
    - Seat is returned to the available pool
    - Booking status changes to "cancelled" (not deleted)
    - Uses row-level locking for atomic seat restoration
    """
    booking = cancel_booking(db, booking_id, current_user.id)

    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        train_id=booking.train_id,
        seat_number=booking.seat_number,
        status=booking.status,
        booked_at=booking.booked_at,
        train_name=booking.train.train_name if booking.train else None,
        train_number=booking.train.train_number if booking.train else None,
        source=booking.train.source if booking.train else None,
        destination=booking.train.destination if booking.train else None,
    )


@router.get(
    "/my",
    response_model=list[BookingListItem],
    summary="Get my booking history",
)
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all bookings (confirmed + cancelled) for the current user.

    - Ordered by most recent first
    - Includes train details (joined query — avoids N+1 problem)
    - Returns empty list if no bookings exist
    """
    return get_user_bookings(db, current_user.id)
