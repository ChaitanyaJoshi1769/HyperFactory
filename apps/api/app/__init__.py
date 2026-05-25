"""HyperFactory API application package"""

__version__ = "0.2.0"
__author__ = "HyperFactory Team"

from .db import Base, get_db, SessionLocal, engine
from .exceptions import (
    HyperFactoryException,
    ResourceNotFoundError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    DatabaseError,
    ExternalServiceError,
    register_exception_handlers,
)

__all__ = [
    "Base",
    "get_db",
    "SessionLocal",
    "engine",
    "HyperFactoryException",
    "ResourceNotFoundError",
    "ValidationError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "DatabaseError",
    "ExternalServiceError",
    "register_exception_handlers",
]
