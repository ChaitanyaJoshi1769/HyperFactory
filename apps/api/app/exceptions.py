"""Custom exceptions and error handlers"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class HyperFactoryException(Exception):
    """Base exception for HyperFactory"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        self.error_code = error_code or "INTERNAL_SERVER_ERROR"
        super().__init__(self.message)


class ResourceNotFoundError(HyperFactoryException):
    """Raised when a resource is not found"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
        )


class ValidationError(HyperFactoryException):
    """Raised when validation fails"""

    def __init__(self, message: str, field: Optional[str] = None):
        detail = f"Field '{field}': {message}" if field else message
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class ConflictError(HyperFactoryException):
    """Raised when there's a conflict (e.g., resource already exists)"""

    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
        )


class UnauthorizedError(HyperFactoryException):
    """Raised when authentication is required"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(HyperFactoryException):
    """Raised when user lacks permissions"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class InternalServerError(HyperFactoryException):
    """Raised when there's an internal server error"""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
        )


class DatabaseError(HyperFactoryException):
    """Raised when there's a database error"""

    def __init__(self, message: str = "Database operation failed"):
        logger.error(f"Database error: {message}")
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
        )


class ExternalServiceError(HyperFactoryException):
    """Raised when external service fails"""

    def __init__(self, service_name: str, message: str):
        full_message = f"{service_name} error: {message}"
        logger.error(full_message)
        super().__init__(
            message=full_message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
        )


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorResponse:
    """Standard error response format"""

    def __init__(
        self,
        error_code: str,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500,
        timestamp: Optional[str] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.detail = detail or message
        self.status_code = status_code
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "detail": self.detail,
                "status": self.status_code,
                "timestamp": self.timestamp,
            }
        }


# ============================================================================
# Exception Handlers
# ============================================================================

async def hyperfactory_exception_handler(request: Request, exc: HyperFactoryException):
    """Handle HyperFactory custom exceptions"""
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        status_code=exc.status_code,
    )
    logger.error(f"HyperFactory exception: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.to_dict(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "message": error["msg"],
            "type": error["type"],
        })

    error_response = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Validation failed",
        detail=f"{len(errors)} validation error(s)",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

    response = error_response.to_dict()
    response["error"]["validation_errors"] = errors

    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response,
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected exception: {exc}")

    error_response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        detail=str(exc) if str(exc) else "Unknown error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.to_dict(),
    )


def register_exception_handlers(app: FastAPI):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(HyperFactoryException, hyperfactory_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
