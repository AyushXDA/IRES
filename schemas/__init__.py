"""
Schemas package — re-exports all Pydantic models for clean imports.

Usage anywhere in the project:
    from railway_app.schemas import UserCreate, TrainResponse, Token
"""

from .user import UserBase, UserCreate, UserResponse, UserLogin, UserUpdate
from .train import TrainBase, TrainCreate, TrainUpdate, TrainResponse
from .booking import BookingCreate, BookingResponse, BookingListItem
from .token import Token, TokenData

__all__ = [
    # User
    "UserBase", "UserCreate", "UserResponse", "UserLogin", "UserUpdate",
    # Train
    "TrainBase", "TrainCreate", "TrainUpdate", "TrainResponse",
    # Booking
    "BookingCreate", "BookingResponse", "BookingListItem",
    # Auth
    "Token", "TokenData",
]
