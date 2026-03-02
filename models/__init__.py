"""
Model package — all ORM models are imported here so that
Base.metadata.create_all() can discover every table.

WHY this file matters:
  SQLAlchemy's declarative Base only knows about models that have
  been *imported* before create_all() is called. If you define a
  model but never import it, the table simply won't be created.

  By importing all models here, and then importing this package
  in main.py, we guarantee every table is registered.
"""

from .user import User
from .train import Train
from .booking import Booking

__all__ = ["User", "Train", "Booking"]
