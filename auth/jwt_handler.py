"""
JWT Token Creation & Verification

HOW JWT WORKS (interview deep-dive):
─────────────────────────────────────────────────────────────
A JWT has three parts separated by dots:  HEADER.PAYLOAD.SIGNATURE

1. HEADER (base64):
   {"alg": "HS256", "typ": "JWT"}

2. PAYLOAD (base64) — our data:
   {"sub": "42", "email": "ayush@example.com", "role": "user", "exp": 1700000000}

3. SIGNATURE:
   HMAC-SHA256(base64(header) + "." + base64(payload), SECRET_KEY)

IMPORTANT: The payload is NOT encrypted — it's just base64-encoded.
Anyone can decode it. The signature only proves it wasn't TAMPERED with.

Flow:
  Login → Server creates JWT with user info → sends to client
  Client → stores token (localStorage / cookie)
  Every request → Client sends: Authorization: Bearer <token>
  Server → decodes token, verifies signature, extracts user info

WHY HS256 (symmetric)?
  → One secret key for both signing and verifying.
  → Simple for a monolith. For microservices, use RS256 (asymmetric)
    so only the auth service has the private key, and other services
    verify with the public key.

Interview question: "How do you invalidate a JWT?"
  → "JWTs are stateless — once issued, they're valid until expiry.
     To force invalidation, you can: (a) use short expiry times,
     (b) maintain a token blacklist in Redis, or (c) rotate the
     secret key (invalidates ALL tokens)."
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from ..config import get_settings
from ..schemas.token import TokenData

settings = get_settings()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT token.

    Args:
        data: payload dict, e.g. {"sub": "42", "email": "...", "role": "user"}
        expires_delta: custom expiry time (default: from settings)

    Returns:
        Encoded JWT string.

    The `sub` (subject) claim is a JWT standard — it identifies the
    principal (user). We store the user_id as a string here.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_access_token(token: str) -> TokenData:
    """
    Decode and verify a JWT token.

    Returns:
        TokenData with user_id, email, role extracted from payload.

    Raises:
        JWTError: if token is expired, tampered, or malformed.

    How verification works internally:
      1. Split token into header.payload.signature
      2. Recompute HMAC-SHA256(header.payload, SECRET_KEY)
      3. Compare with the provided signature
      4. If match → token is authentic and untampered
      5. Check `exp` claim → reject if expired
      6. Extract claims and return as TokenData
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id: int = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None:
            raise JWTError("Token payload missing 'sub' claim")

        return TokenData(user_id=int(user_id), email=email, role=role)

    except JWTError:
        raise  # re-raise so the caller (dependency) can handle it
