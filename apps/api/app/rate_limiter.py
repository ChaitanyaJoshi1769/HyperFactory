"""Rate limiting for authentication endpoints"""

from fastapi import HTTPException, Request
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time


class RateLimiter:
    """Simple in-memory rate limiter for authentication endpoints"""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        """
        Initialize rate limiter.

        Args:
            max_attempts: Maximum number of attempts allowed in the window
            window_seconds: Time window in seconds for rate limiting (default 5 minutes)
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Track attempts: {identifier: [(timestamp, request_data), ...]}
        self.attempts: Dict[str, list] = {}

    def _cleanup_old_attempts(self, identifier: str) -> None:
        """Remove attempts outside the time window"""
        if identifier not in self.attempts:
            return

        current_time = time.time()
        self.attempts[identifier] = [
            (ts, data) for ts, data in self.attempts[identifier]
            if current_time - ts < self.window_seconds
        ]

        # Clean up empty entries
        if not self.attempts[identifier]:
            del self.attempts[identifier]

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed.

        Args:
            identifier: Unique identifier (e.g., username, IP address, or combination)

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        self._cleanup_old_attempts(identifier)

        if identifier not in self.attempts:
            self.attempts[identifier] = []

        current_attempts = len(self.attempts[identifier])
        return current_attempts < self.max_attempts

    def add_attempt(self, identifier: str, request_data: dict = None) -> None:
        """
        Record an attempt.

        Args:
            identifier: Unique identifier
            request_data: Optional request data to log (e.g., {"username": "user1"})
        """
        self._cleanup_old_attempts(identifier)

        if identifier not in self.attempts:
            self.attempts[identifier] = []

        self.attempts[identifier].append((time.time(), request_data or {}))

    def get_remaining_attempts(self, identifier: str) -> int:
        """Get remaining attempts for an identifier"""
        self._cleanup_old_attempts(identifier)

        if identifier not in self.attempts:
            return self.max_attempts

        return max(0, self.max_attempts - len(self.attempts[identifier]))

    def get_reset_time(self, identifier: str) -> datetime:
        """Get when the rate limit resets"""
        if identifier not in self.attempts or not self.attempts[identifier]:
            return datetime.utcnow()

        oldest_attempt_time = self.attempts[identifier][0][0]
        reset_time = datetime.utcfromtimestamp(
            oldest_attempt_time + self.window_seconds
        )
        return reset_time


# Global rate limiters
login_limiter = RateLimiter(max_attempts=5, window_seconds=300)  # 5 attempts per 5 min
register_limiter = RateLimiter(max_attempts=3, window_seconds=600)  # 3 attempts per 10 min
password_reset_limiter = RateLimiter(max_attempts=3, window_seconds=3600)  # 3 per hour


def get_client_identifier(request: Request) -> str:
    """
    Extract client identifier from request.
    Uses IP address for unauthenticated requests.
    """
    # Try to get X-Forwarded-For header (for proxied requests)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def check_rate_limit(limiter: RateLimiter, identifier: str) -> None:
    """
    Check rate limit and raise HTTPException if exceeded.

    Args:
        limiter: RateLimiter instance
        identifier: Unique identifier for rate limiting

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    if not limiter.is_allowed(identifier):
        reset_time = limiter.get_reset_time(identifier)
        time_remaining = (reset_time - datetime.utcnow()).total_seconds()

        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {int(time_remaining)} seconds.",
            headers={"Retry-After": str(int(time_remaining))},
        )

    # Record this attempt
    limiter.add_attempt(identifier)


def check_login_rate_limit(username: str, client_ip: str) -> None:
    """Check rate limit for login attempts using username"""
    identifier = f"login:{username}"
    check_rate_limit(login_limiter, identifier)


def check_register_rate_limit(email: str, client_ip: str) -> None:
    """Check rate limit for registration attempts using email"""
    identifier = f"register:{email}"
    check_rate_limit(register_limiter, identifier)


def check_password_reset_rate_limit(email: str, client_ip: str) -> None:
    """Check rate limit for password reset attempts using email"""
    identifier = f"reset:{email}"
    check_rate_limit(password_reset_limiter, identifier)
