"""
Railway Reservation System — Application Entry Point

HOW FastAPI STARTS:
───────────────────────────────────────────────────────
1. Uvicorn (ASGI server) imports this file.
2. It finds the `app` object (FastAPI instance).
3. On startup, `lifespan` runs → creates DB tables.
4. Uvicorn starts accepting HTTP requests and routes
   them to the correct path operation function.

WHY lifespan instead of @app.on_event("startup")?
  @app.on_event is deprecated since FastAPI 0.103.
  `lifespan` is the modern async context-manager approach.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .config import get_settings

# Import models so Base.metadata knows about all tables
from .models import User, Train, Booking  # noqa: F401

settings = get_settings()


# ── Lifespan: runs on startup & shutdown ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:  Create all tables that don't exist yet.
    Shutdown: (nothing for now — engine pool auto-cleans)
    """
    print("🚂 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables ready.")
    except Exception as e:
        print(f"⚠️  DB table creation skipped: {e}")
        print("   → Update DATABASE_URL in .env and restart.")
    yield                       # ← app runs between startup and shutdown
    print("🛑 Shutting down...")


# ── FastAPI Application ──────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="A production-style backend for railway seat reservation.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve Static Frontend ───────────────────────────
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")


# ── Health Check ─────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """Simple endpoint to verify the server is alive."""
    return {"status": "healthy", "service": settings.APP_NAME}


# ── Route Registration ───────────────────────────────
from .routes.auth import router as auth_router
from .routes.trains import admin_router as train_admin_router
from .routes.trains import public_router as train_public_router
from .routes.bookings import router as booking_router

app.include_router(auth_router)
app.include_router(train_admin_router)
app.include_router(train_public_router)
app.include_router(booking_router)
