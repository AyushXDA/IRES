"""
FastAPI Auth Dependencies

WHAT IS A DEPENDENCY IN FASTAPI?
─────────────────────────────────────────────────────────────
A dependency is a function that runs BEFORE your route handler.
FastAPI calls it automatically, injects its return value, and
handles errors.

Think of it as MIDDLEWARE for a specific route, not the whole app.

Flow for a protected route:
  1. Client sends: Authorization: Bearer <token>
  2. FastAPI sees `Depends(get_current_user)` on the route
  3. It calls `get_current_user()` BEFORE the route handler
  4. `get_current_user` extracts the token, verifies it, loads the user
  5. If valid → user object is injected into the route handler
  6. If invalid → 401 Unauthorized is returned (route never executes)

DEPENDENCY CHAIN:
  oauth2_scheme → extracts raw token string from header
       ↓
  get_current_user → verifies JWT, loads user from DB
       ↓
  get_current_admin → checks user.role == "admin"
       ↓
  Route handler receives the validated user object

Interview question: "How do you implement RBAC in FastAPI?"
  → "I chain dependencies. `get_current_user` verifies the JWT.
     `get_current_admin` depends on `get_current_user` and adds
     a role check. Routes that need admin access use
     `Depends(get_current_admin)`."
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from ..database import get_db
from ..models.user import User
from .jwt_handler import verify_access_token

# ── OAuth2 scheme ─────────────────────────────────────
# tokenUrl tells Swagger UI where to send login requests.
# It extracts the token from: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Get Current User ─────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that:
      1. Extracts Bearer token from the Authorization header
      2. Decodes & verifies the JWT
      3. Loads the user from the database
      4. Returns the User ORM object

    If anything fails → raises 401 Unauthorized.

    WHY load from DB every time?
      → The user might have been deleted or deactivated since the
        token was issued. If we only trusted the token payload,
        a deleted user could still access the system.
      → Trade-off: extra DB query per request. In high-scale systems,
        you'd cache user data in Redis with short TTL.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_data = verify_access_token(token)
    except JWTError:
        raise credentials_exception

    # Load user from DB to ensure they still exist
    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise credentials_exception

    return user


# ── Get Current Admin ────────────────────────────────
def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the logged-in user has admin role.
    Chains on top of get_current_user — so JWT is already verified.

    Usage:
        @router.post("/admin/trains")
        def add_train(admin: User = Depends(get_current_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
