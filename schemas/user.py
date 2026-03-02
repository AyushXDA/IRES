"""
User Pydantic Schemas (DTOs — Data Transfer Objects)

WHY SEPARATE SCHEMAS FROM ORM MODELS?
─────────────────────────────────────────────────────────────
ORM Model (SQLAlchemy)  = how data is STORED in the database.
Pydantic Schema         = how data ENTERS and LEAVES the API.

They look similar but serve completely different purposes:

  1. Security: The User ORM model has `hashed_password`. You NEVER
     want that in an API response. The response schema excludes it.

  2. Validation: When a user registers, we need `password` (plaintext)
     to hash it. But the ORM model only has `hashed_password`. The
     request schema captures the raw password before we hash it.

  3. Flexibility: You can change the DB schema without breaking the
     API contract, and vice versa. This is the "anti-corruption layer"
     pattern.

Interview tip: "I never expose ORM models directly in API responses.
I use Pydantic schemas as a serialization boundary to control exactly
what data enters and leaves the system."

NAMING CONVENTION:
  - XxxCreate  → request body for creating a resource
  - XxxUpdate  → request body for updating (partial fields)
  - XxxResponse → what the API returns to the client
  - XxxBase    → shared fields (DRY — Don't Repeat Yourself)
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


# ── Base: shared fields ──────────────────────────────
class UserBase(BaseModel):
    username: str = Field(
        ...,                          # required
        min_length=3,
        max_length=50,
        examples=["ayush_dev"],
        description="Unique username, 3-50 characters",
    )
    email: EmailStr = Field(
        ...,
        examples=["ayush@example.com"],
        description="Valid email address",
    )


# ── Create: registration request ─────────────────────
class UserCreate(UserBase):
    """What the client sends to POST /auth/register"""
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        examples=["StrongP@ss123"],
        description="Plaintext password (will be hashed server-side)",
    )


# ── Response: what the API returns ───────────────────
class UserResponse(UserBase):
    """What the API sends back — NO password field."""
    id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2: read data from ORM objects
        # This allows: UserResponse.model_validate(user_orm_object)
        # Without this, Pydantic can't read SQLAlchemy model attributes.


# ── Login: authentication request ────────────────────
class UserLogin(BaseModel):
    """What the client sends to POST /auth/login"""
    email: EmailStr = Field(..., examples=["ayush@example.com"])
    password: str = Field(..., examples=["StrongP@ss123"])


# ── Update: partial profile update ───────────────────
class UserUpdate(BaseModel):
    """Optional fields for PATCH /users/me"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
