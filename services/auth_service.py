"""
Auth Service Layer — business logic for registration & login.

WHY A SERVICE LAYER?
─────────────────────────────────────────────────────────────
The route handler should ONLY:
  1. Accept the request
  2. Call the service
  3. Return the response

Business logic (hashing, validation, DB queries) lives HERE.

Benefits:
  - Testable: you can test `register_user()` without spinning up
    an HTTP server — just pass a mock DB session.
  - Reusable: if you add a CLI tool or a background job that
    creates users, it calls the same service function.
  - Clean: routes stay thin (5-10 lines), services do the work.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.user import User
from ..schemas.user import UserCreate
from ..auth.password import hash_password, verify_password
from ..auth.jwt_handler import create_access_token


def register_user(db: Session, user_data: UserCreate) -> User:
    """
    Register a new user.

    Steps:
      1. Check if email already exists → 409 Conflict
      2. Check if username already exists → 409 Conflict
      3. Hash the password with bcrypt
      4. Create the ORM object, add to session, commit
      5. Refresh to get auto-generated fields (id, created_at)
      6. Return the user object

    WHY check duplicates in code AND have unique constraints in DB?
      → The code check gives a friendly error message ("Email already
        registered"). The DB constraint is a safety net for race
        conditions — if two requests register the same email
        simultaneously, the DB constraint catches the second one.
    """
    # Check email uniqueness
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Check username uniqueness
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user with hashed password
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="user",  # default role — admin is set manually in DB
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # loads id, created_at from DB

    return new_user


def authenticate_user(db: Session, email: str, password: str) -> dict:
    """
    Authenticate a user and return a JWT token.

    Steps:
      1. Find user by email → 401 if not found
      2. Verify password against stored bcrypt hash → 401 if wrong
      3. Create JWT with user_id, email, role in payload
      4. Return the token dict

    WHY the same error for "user not found" and "wrong password"?
      → Security. If you say "email not found", an attacker can
        enumerate which emails are registered. A generic "Invalid
        credentials" message reveals nothing.

    Interview question: "How do you prevent user enumeration?"
      → "I return the same error for both invalid email and invalid
         password, and I use constant-time comparison for passwords."
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),      # JWT standard: subject = user identifier
            "email": user.email,
            "role": user.role,
        }
    )

    return {"access_token": access_token, "token_type": "bearer"}
