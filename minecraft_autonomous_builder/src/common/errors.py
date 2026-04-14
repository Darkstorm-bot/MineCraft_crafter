from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class ValidationError(AppError):
    """Raised when schema or data validation fails."""


class NotFoundError(AppError):
    """Raised when requested resource does not exist."""


class CollisionError(AppError):
    """Raised when coordinate reservations collide."""


class ExecutionError(AppError):
    """Raised when world execution fails."""
