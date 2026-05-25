"""Rate Limiting - API usage quotas and abuse prevention"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from enum import Enum
import time
import logging

# Configuration
DEFAULT_REQUESTS_PER_MINUTE = 60
DEFAULT_REQUESTS_PER_HOUR = 1000
DEFAULT_REQUESTS_PER_DAY = 10000


class RateLimitStrategy(str, Enum):
    """Available rate limiting strategies"""

    FIXED_WINDOW = "fixed_window"          # Simple: requests in time window
    SLIDING_WINDOW = "sliding_window"      # Accurate: rolling time window
    TOKEN_BUCKET = "token_bucket"          # Fair: tokens replenish over time


class RateLimitPeriod(str, Enum):
    """Time periods for rate limiting"""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class RateLimitConfig:
    """Configuration for rate limiting"""

    def __init__(
        self,
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
        requests_per_hour: int = DEFAULT_REQUESTS_PER_HOUR,
        requests_per_day: int = DEFAULT_REQUESTS_PER_DAY,
        strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW,
        burst_allowance: float = 1.5,  # Allow 50% burst above limit
    ):
        """
        Initialize rate limit configuration.

        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            requests_per_day: Max requests per day
            strategy: Rate limiting strategy
            burst_allowance: Burst multiplier (1.5 = 50% above limit allowed)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.strategy = strategy
        self.burst_allowance = burst_allowance

    def get_limit(self, period: RateLimitPeriod) -> int:
        """Get request limit for period"""
        if period == RateLimitPeriod.MINUTE:
            return self.requests_per_minute
        elif period == RateLimitPeriod.HOUR:
            return self.requests_per_hour
        elif period == RateLimitPeriod.DAY:
            return self.requests_per_day
        return self.requests_per_minute


class RateLimitStatus:
    """Status of rate limit check"""

    def __init__(
        self,
        allowed: bool,
        requests_remaining: int,
        reset_at: datetime,
        retry_after_seconds: Optional[int] = None,
    ):
        self.allowed = allowed
        self.requests_remaining = requests_remaining
        self.reset_at = reset_at
        self.retry_after_seconds = retry_after_seconds

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP rate limit headers"""
        headers = {
            "X-RateLimit-Remaining": str(self.requests_remaining),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if self.retry_after_seconds is not None:
            headers["Retry-After"] = str(self.retry_after_seconds)
        return headers


class RateLimiter:
    """Rate limiting engine with multiple strategies"""

    def __init__(
        self,
        strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW,
    ):
        """
        Initialize rate limiter.

        Args:
            strategy: Rate limiting strategy to use
        """
        self.strategy = strategy
        self.logger = logging.getLogger("rate_limiter")
        # In-memory storage (for production, use Redis)
        self._request_history: Dict[str, list] = {}
        self._token_buckets: Dict[str, dict] = {}

    def check_limit(
        self,
        identifier: str,
        config: RateLimitConfig,
        current_time: Optional[datetime] = None,
    ) -> RateLimitStatus:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (api_key_id, user_id, ip_address)
            config: Rate limit configuration
            current_time: Override current time (for testing)

        Returns:
            RateLimitStatus with decision and headers
        """
        if current_time is None:
            current_time = datetime.utcnow()

        if self.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._check_fixed_window(identifier, config, current_time)
        elif self.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._check_sliding_window(identifier, config, current_time)
        elif self.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._check_token_bucket(identifier, config, current_time)

        return RateLimitStatus(
            allowed=True,
            requests_remaining=config.requests_per_minute,
            reset_at=current_time + timedelta(minutes=1),
        )

    def _check_fixed_window(
        self,
        identifier: str,
        config: RateLimitConfig,
        current_time: datetime,
    ) -> RateLimitStatus:
        """
        Check rate limit using fixed window strategy.

        Simple: count requests in current minute/hour/day windows
        """
        # Check all periods (minute is strictest)
        for period in [RateLimitPeriod.MINUTE, RateLimitPeriod.HOUR, RateLimitPeriod.DAY]:
            key = f"{identifier}:{period.value}:{current_time.timestamp() // self._period_seconds(period)}"

            if key not in self._request_history:
                self._request_history[key] = []

            # Count requests in this window
            count = len(self._request_history[key])
            limit = config.get_limit(period)

            if count >= limit:
                # Limit exceeded
                window_seconds = self._period_seconds(period)
                reset_at = current_time + timedelta(seconds=window_seconds)
                retry_after = window_seconds

                self.logger.warning(
                    f"Rate limit exceeded for {identifier} ({period.value}): {count}/{limit}"
                )

                return RateLimitStatus(
                    allowed=False,
                    requests_remaining=0,
                    reset_at=reset_at,
                    retry_after_seconds=retry_after,
                )

        # Within all limits, record request
        minute_key = f"{identifier}:minute:{current_time.timestamp() // 60}"
        if minute_key not in self._request_history:
            self._request_history[minute_key] = []
        self._request_history[minute_key].append(current_time)

        # Return status
        minute_limit = config.requests_per_minute
        minute_count = len(self._request_history[minute_key])

        reset_at = current_time + timedelta(minutes=1)

        return RateLimitStatus(
            allowed=True,
            requests_remaining=max(0, minute_limit - minute_count),
            reset_at=reset_at,
        )

    def _check_sliding_window(
        self,
        identifier: str,
        config: RateLimitConfig,
        current_time: datetime,
    ) -> RateLimitStatus:
        """
        Check rate limit using sliding window strategy.

        More accurate: count requests in rolling time window
        """
        if identifier not in self._request_history:
            self._request_history[identifier] = []

        history = self._request_history[identifier]

        # Remove old requests outside minute window
        minute_ago = current_time - timedelta(minutes=1)
        hour_ago = current_time - timedelta(hours=1)
        day_ago = current_time - timedelta(days=1)

        # Clean up old requests
        history[:] = [ts for ts in history if ts > day_ago]

        # Count requests in each window
        minute_count = sum(1 for ts in history if ts > minute_ago)
        hour_count = sum(1 for ts in history if ts > hour_ago)
        day_count = len(history)

        # Check against limits
        if minute_count >= config.requests_per_minute:
            oldest_in_window = min((ts for ts in history if ts > minute_ago), default=None)
            if oldest_in_window:
                reset_at = oldest_in_window + timedelta(minutes=1)
                retry_after = int((reset_at - current_time).total_seconds())
            else:
                reset_at = current_time + timedelta(minutes=1)
                retry_after = 60

            self.logger.warning(
                f"Rate limit exceeded for {identifier} (minute): {minute_count}/{config.requests_per_minute}"
            )

            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
            )

        if hour_count >= config.requests_per_hour:
            self.logger.warning(
                f"Rate limit exceeded for {identifier} (hour): {hour_count}/{config.requests_per_hour}"
            )

            oldest_in_window = min((ts for ts in history if ts > hour_ago), default=None)
            if oldest_in_window:
                reset_at = oldest_in_window + timedelta(hours=1)
            else:
                reset_at = current_time + timedelta(hours=1)

            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_at=reset_at,
                retry_after_seconds=3600,
            )

        if day_count >= config.requests_per_day:
            self.logger.warning(
                f"Rate limit exceeded for {identifier} (day): {day_count}/{config.requests_per_day}"
            )

            oldest_in_window = min((ts for ts in history if ts > day_ago), default=None)
            if oldest_in_window:
                reset_at = oldest_in_window + timedelta(days=1)
            else:
                reset_at = current_time + timedelta(days=1)

            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_at=reset_at,
                retry_after_seconds=86400,
            )

        # Record request
        history.append(current_time)

        # Return status
        return RateLimitStatus(
            allowed=True,
            requests_remaining=max(0, config.requests_per_minute - minute_count),
            reset_at=current_time + timedelta(minutes=1),
        )

    def _check_token_bucket(
        self,
        identifier: str,
        config: RateLimitConfig,
        current_time: datetime,
    ) -> RateLimitStatus:
        """
        Check rate limit using token bucket strategy.

        Fair: tokens replenish over time, allows bursts up to bucket size
        """
        if identifier not in self._token_buckets:
            self._token_buckets[identifier] = {
                "tokens": config.requests_per_minute * config.burst_allowance,
                "last_update": current_time,
            }

        bucket = self._token_buckets[identifier]
        last_update = bucket["last_update"]
        tokens = bucket["tokens"]

        # Calculate elapsed time and replenish tokens
        elapsed = (current_time - last_update).total_seconds()
        refill_rate = config.requests_per_minute / 60  # tokens per second

        tokens = min(
            config.requests_per_minute * config.burst_allowance,
            tokens + (elapsed * refill_rate),
        )

        # Check if request allowed
        if tokens >= 1:
            tokens -= 1
            bucket["tokens"] = tokens
            bucket["last_update"] = current_time

            return RateLimitStatus(
                allowed=True,
                requests_remaining=int(tokens),
                reset_at=current_time + timedelta(seconds=60),
            )
        else:
            # Calculate time until next token available
            time_until_token = (1 - tokens) / refill_rate
            reset_at = current_time + timedelta(seconds=time_until_token)

            self.logger.warning(
                f"Rate limit exceeded for {identifier} (token bucket): {tokens:.2f} tokens remaining"
            )

            return RateLimitStatus(
                allowed=False,
                requests_remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, int(time_until_token)),
            )

    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier"""
        if identifier in self._request_history:
            del self._request_history[identifier]
        if identifier in self._token_buckets:
            del self._token_buckets[identifier]

    def reset_all(self) -> None:
        """Reset all rate limits"""
        self._request_history.clear()
        self._token_buckets.clear()

    @staticmethod
    def _period_seconds(period: RateLimitPeriod) -> int:
        """Convert period to seconds"""
        if period == RateLimitPeriod.MINUTE:
            return 60
        elif period == RateLimitPeriod.HOUR:
            return 3600
        elif period == RateLimitPeriod.DAY:
            return 86400
        return 60

    def get_usage(self, identifier: str, current_time: Optional[datetime] = None) -> Dict[str, int]:
        """Get current usage statistics for identifier"""
        if current_time is None:
            current_time = datetime.utcnow()

        if identifier in self._request_history:
            history = self._request_history[identifier]
            minute_ago = current_time - timedelta(minutes=1)
            hour_ago = current_time - timedelta(hours=1)
            day_ago = current_time - timedelta(days=1)

            return {
                "requests_last_minute": sum(1 for ts in history if ts > minute_ago),
                "requests_last_hour": sum(1 for ts in history if ts > hour_ago),
                "requests_last_day": sum(1 for ts in history if ts > day_ago),
                "total_requests": len(history),
            }
        elif identifier in self._token_buckets:
            bucket = self._token_buckets[identifier]
            return {
                "tokens_available": int(bucket["tokens"]),
                "last_refill": bucket["last_update"].isoformat(),
            }

        return {"requests_last_minute": 0, "requests_last_hour": 0, "requests_last_day": 0}


# Global rate limiter instance
rate_limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)


# ============================================================================
# Helper Functions for Auth Integration
# ============================================================================

def get_client_identifier(request) -> str:
    """
    Get unique client identifier for rate limiting.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Unique identifier (IP address or user-agent hash)
    """
    # Prefer X-Forwarded-For for load balancer scenarios
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Fall back to client IP
    if request.client:
        return request.client.host
    
    return "unknown"


# Pre-configured rate limiters for auth endpoints
login_limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
register_limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)

# Configuration for auth endpoints
LOGIN_RATE_LIMIT_CONFIG = RateLimitConfig(
    requests_per_minute=5,      # 5 login attempts per minute
    requests_per_hour=20,       # 20 per hour
    requests_per_day=100,       # 100 per day
)

REGISTER_RATE_LIMIT_CONFIG = RateLimitConfig(
    requests_per_minute=2,      # 2 registrations per minute
    requests_per_hour=10,       # 10 per hour
    requests_per_day=50,        # 50 per day
)


def check_login_rate_limit(client_identifier: str) -> Tuple[bool, Optional[str]]:
    """
    Check if login attempt is within rate limit.
    
    Args:
        client_identifier: Client IP or identifier
        
    Returns:
        Tuple of (allowed, error_message)
    """
    status = login_limiter.check_limit(client_identifier, LOGIN_RATE_LIMIT_CONFIG)
    
    if not status.allowed:
        retry_after = status.retry_after_seconds or 60
        return False, f"Too many login attempts. Please try again in {retry_after} seconds."
    
    return True, None


def check_register_rate_limit(client_identifier: str) -> Tuple[bool, Optional[str]]:
    """
    Check if registration attempt is within rate limit.
    
    Args:
        client_identifier: Client IP or identifier
        
    Returns:
        Tuple of (allowed, error_message)
    """
    status = register_limiter.check_limit(client_identifier, REGISTER_RATE_LIMIT_CONFIG)
    
    if not status.allowed:
        retry_after = status.retry_after_seconds or 60
        return False, f"Too many registration attempts. Please try again in {retry_after} seconds."
    
    return True, None
