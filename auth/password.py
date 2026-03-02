"""
Password Hashing Utilities (bcrypt)

HOW BCRYPT WORKS (interview deep-dive):
─────────────────────────────────────────────────────────────
1. bcrypt is a ONE-WAY hash function — you cannot reverse it.
   → hash("password123") = "$2b$12$LJ3m4..." (always different due to salt)
   → There's no decrypt("$2b$12$LJ3m4...") → "password123"

2. It automatically generates a RANDOM SALT per password.
   → Two users with the same password get different hashes.
   → This defeats rainbow table attacks (pre-computed hash lookups).

3. It has a COST FACTOR (the "12" in $2b$12$...).
   → Higher cost = more iterations = slower hashing.
   → "12" means 2^12 = 4096 iterations (~250ms per hash).
   → This is INTENTIONALLY SLOW to resist brute-force attacks.
   → MD5/SHA256 are fast (millions/sec) — terrible for passwords.

4. The hash string format:  $2b$12$<22-char-salt><31-char-hash>
   → The salt is embedded in the hash itself, so you don't need
     to store it separately.

WHY passlib?
  → It wraps bcrypt with a clean API and handles edge cases
    (encoding, version compat, deprecated hash migration).

Interview question: "Why not use SHA-256 for passwords?"
  → "SHA-256 is a fast hash — an attacker with a GPU can compute
     billions of SHA-256 hashes per second. bcrypt is intentionally
     slow (cost factor), making brute-force attacks impractical."
"""

from passlib.context import CryptContext

# ── Password context ─────────────────────────────────
# schemes=["bcrypt"] → use bcrypt for all new hashes
# deprecated="auto" → if we add a new scheme later, old bcrypt
#   hashes auto-upgrade on next login (zero-downtime migration)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Example:
        hashed = hash_password("Secret123")
        # "$2b$12$LJ3m4x..."  ← different every time (random salt)
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plaintext password against a stored bcrypt hash.
    Returns True if they match, False otherwise.

    How it works internally:
      1. Extract the salt from the stored hash.
      2. Hash the plaintext password with that same salt.
      3. Compare the two hashes. Constant-time comparison
         to prevent timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)
