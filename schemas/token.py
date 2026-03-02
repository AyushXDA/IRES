"""
Token / Auth Pydantic Schemas

DESIGN NOTES:
─────────────────────────────────────────────────────────────
1. Token is the response from POST /auth/login.
   → Contains the JWT access_token and its type ("bearer").
   → The client stores this token and sends it in the
     Authorization header: `Bearer <token>` on every request.

2. TokenData is the DECODED payload inside the JWT.
   → We embed `user_id`, `email`, and `role` in the JWT payload.
   → When a request comes in, we decode the token and build
     a TokenData object — this becomes the "current user" context.

   Interview tip: "The JWT payload should contain just enough to
   identify the user and their permissions. Don't put sensitive data
   like passwords or PII in the token — JWTs are base64-encoded,
   not encrypted. Anyone can decode and read them."
"""

from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Response from POST /auth/login"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT payload — used internally, never sent to client."""
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
