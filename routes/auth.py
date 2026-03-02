"""
Auth Routes — HTTP endpoints for registration and login.

ROUTE DESIGN PRINCIPLES:
─────────────────────────────────────────────────────────────
1. Routes are THIN — they only:
   a. Accept the request (FastAPI auto-validates via Pydantic schema)
   b. Call the service function
   c. Return the response (FastAPI auto-serializes via response_model)

2. All business logic is in `services/auth_service.py`.

3. `response_model` controls EXACTLY what fields are returned.
   Even if the service returns a full User ORM object with
   `hashed_password`, the response_model filters it out.

4. `status_code` should match REST conventions:
   - 201 Created → new resource created (registration)
   - 200 OK      → successful operation (login)
   - 401         → authentication failed
   - 409         → conflict (duplicate email/username)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import UserCreate, UserResponse, UserLogin
from ..schemas.token import Token
from ..services.auth_service import register_user, authenticate_user
from ..auth.dependencies import get_current_user
from ..models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],   # groups endpoints in Swagger UI
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    user_data: UserCreate,           # auto-validated by Pydantic
    db: Session = Depends(get_db),   # auto-injected DB session
):
    """
    Create a new user account.

    - Validates input (username length, email format, password length)
    - Checks for duplicate email/username → 409
    - Hashes password with bcrypt
    - Returns the created user (without password)
    """
    new_user = register_user(db, user_data)
    return new_user
    # FastAPI sees response_model=UserResponse, so it:
    #   1. Calls UserResponse.model_validate(new_user)  (ORM → Pydantic)
    #   2. Serializes to JSON (excluding hashed_password)
    #   3. Returns with status 201


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get JWT token",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email + password.

    - Returns JWT access token on success
    - Returns 401 on invalid credentials
    - Token expires after configured minutes (default: 30)

    Usage: Include the token in subsequent requests:
    `Authorization: Bearer <token>`
    """
    token = authenticate_user(db, credentials.email, credentials.password)
    return token


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the profile of the currently authenticated user.
    Requires a valid JWT token in the Authorization header.

    This endpoint demonstrates the `get_current_user` dependency:
    - Extracts token from header
    - Verifies JWT signature and expiry
    - Loads user from DB
    - Injects user object into this function
    """
    return current_user
