"""Rate Limiting tests - API usage quotas and abuse prevention"""

import pytest
from datetime import datetime, timedelta
from app.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitPeriod,
    RateLimitStatus,
    rate_limiter,
)


# ============================================================================
# RateLimitConfig Tests
# ============================================================================

def test_rate_limit_config_defaults():
    """Test default rate limit configuration"""
    config = RateLimitConfig()

    assert config.requests_per_minute == 60
    assert config.requests_per_hour == 1000
    assert config.requests_per_day == 10000
    assert config.strategy == RateLimitStrategy.FIXED_WINDOW
    assert config.burst_allowance == 1.5


def test_rate_limit_config_custom():
    """Test custom rate limit configuration"""
    config = RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=5000,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_allowance=2.0,
    )

    assert config.requests_per_minute == 30
    assert config.requests_per_hour == 500
    assert config.requests_per_day == 5000
    assert config.strategy == RateLimitStrategy.TOKEN_BUCKET
    assert config.burst_allowance == 2.0


def test_get_limit_minute():
    """Test getting minute limit"""
    config = RateLimitConfig(requests_per_minute=60)
    assert config.get_limit(RateLimitPeriod.MINUTE) == 60


def test_get_limit_hour():
    """Test getting hour limit"""
    config = RateLimitConfig(requests_per_hour=1000)
    assert config.get_limit(RateLimitPeriod.HOUR) == 1000


def test_get_limit_day():
    """Test getting day limit"""
    config = RateLimitConfig(requests_per_day=10000)
    assert config.get_limit(RateLimitPeriod.DAY) == 10000


# ============================================================================
# RateLimitStatus Tests
# ============================================================================

def test_rate_limit_status_allowed():
    """Test allowed status"""
    reset_at = datetime.utcnow() + timedelta(minutes=1)
    status = RateLimitStatus(allowed=True, requests_remaining=10, reset_at=reset_at)

    assert status.allowed is True
    assert status.requests_remaining == 10
    assert status.reset_at == reset_at
    assert status.retry_after_seconds is None


def test_rate_limit_status_denied():
    """Test denied status"""
    reset_at = datetime.utcnow() + timedelta(minutes=1)
    status = RateLimitStatus(
        allowed=False, requests_remaining=0, reset_at=reset_at, retry_after_seconds=60
    )

    assert status.allowed is False
    assert status.requests_remaining == 0
    assert status.retry_after_seconds == 60


def test_rate_limit_status_to_headers():
    """Test converting status to HTTP headers"""
    reset_at = datetime.utcnow() + timedelta(minutes=1)
    status = RateLimitStatus(
        allowed=True, requests_remaining=10, reset_at=reset_at, retry_after_seconds=60
    )

    headers = status.to_headers()

    assert "X-RateLimit-Remaining" in headers
    assert headers["X-RateLimit-Remaining"] == "10"
    assert "X-RateLimit-Reset" in headers
    assert "Retry-After" in headers
    assert headers["Retry-After"] == "60"


# ============================================================================
# Fixed Window Strategy Tests
# ============================================================================

def test_fixed_window_within_limit():
    """Test fixed window strategy within limit"""
    limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    config = RateLimitConfig(requests_per_minute=5)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make 5 requests
    for i in range(5):
        status = limiter.check_limit("user1", config, now)
        assert status.allowed is True

    # 6th request should be denied
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False


def test_fixed_window_after_reset():
    """Test fixed window resets after time window"""
    limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    config = RateLimitConfig(requests_per_minute=2)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make 2 requests
    limiter.check_limit("user1", config, now)
    limiter.check_limit("user1", config, now)

    # 3rd request denied
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False

    # Advance time by 1 minute
    later = now + timedelta(minutes=1)

    # Should be allowed again
    status = limiter.check_limit("user1", config, later)
    assert status.allowed is True


def test_fixed_window_multiple_users():
    """Test fixed window with multiple users"""
    limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    config = RateLimitConfig(requests_per_minute=2)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # User1: 2 requests
    limiter.check_limit("user1", config, now)
    limiter.check_limit("user1", config, now)

    # User1: 3rd request denied
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False

    # User2: should be fine
    status = limiter.check_limit("user2", config, now)
    assert status.allowed is True


# ============================================================================
# Sliding Window Strategy Tests
# ============================================================================

def test_sliding_window_within_limit():
    """Test sliding window strategy within limit"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(requests_per_minute=5)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make 5 requests
    for i in range(5):
        status = limiter.check_limit("user1", config, now)
        assert status.allowed is True

    # 6th request should be denied
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False


def test_sliding_window_rolling_reset():
    """Test sliding window rolling reset"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(requests_per_minute=3)
    start = datetime(2024, 1, 15, 10, 30, 0)

    # Make 3 requests at start
    for i in range(3):
        limiter.check_limit("user1", config, start)

    # Try request at same time - denied
    status = limiter.check_limit("user1", config, start)
    assert status.allowed is False

    # 30 seconds later, try again - still denied (3 requests in window)
    mid = start + timedelta(seconds=30)
    status = limiter.check_limit("user1", config, mid)
    assert status.allowed is False

    # After 60+ seconds, should be allowed (original requests expire)
    later = start + timedelta(minutes=1, seconds=1)
    status = limiter.check_limit("user1", config, later)
    assert status.allowed is True


def test_sliding_window_hourly_limit():
    """Test sliding window respects hourly limit"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(
        requests_per_minute=100, requests_per_hour=10, requests_per_day=100
    )
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make 10 requests
    for _ in range(10):
        status = limiter.check_limit("user1", config, now)
        assert status.allowed is True

    # 11th should be denied (hour limit)
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False


# ============================================================================
# Token Bucket Strategy Tests
# ============================================================================

def test_token_bucket_within_limit():
    """Test token bucket strategy within limit"""
    limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
    config = RateLimitConfig(requests_per_minute=5, burst_allowance=1.0)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Can make up to 5 requests initially
    for i in range(5):
        status = limiter.check_limit("user1", config, now)
        assert status.allowed is True

    # 6th request denied (no time elapsed for replenishment)
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False


def test_token_bucket_replenishment():
    """Test token bucket replenishment over time"""
    limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
    config = RateLimitConfig(requests_per_minute=60, burst_allowance=1.0)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make a request
    limiter.check_limit("user1", config, now)

    # Advance 1 second (1 token should replenish)
    later = now + timedelta(seconds=1)
    status = limiter.check_limit("user1", config, later)
    assert status.allowed is True


def test_token_bucket_burst():
    """Test token bucket burst allowance"""
    limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
    config = RateLimitConfig(requests_per_minute=10, burst_allowance=2.0)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # With 2x burst allowance, should allow 20 tokens initially
    for i in range(15):
        status = limiter.check_limit("user1", config, now)
        assert status.allowed is True


# ============================================================================
# Reset Tests
# ============================================================================

def test_reset_identifier():
    """Test resetting rate limit for identifier"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(requests_per_minute=2)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Max out limit
    limiter.check_limit("user1", config, now)
    limiter.check_limit("user1", config, now)

    # Verify limit exceeded
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is False

    # Reset
    limiter.reset("user1")

    # Should be allowed again
    status = limiter.check_limit("user1", config, now)
    assert status.allowed is True


def test_reset_all():
    """Test resetting all rate limits"""
    limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    config = RateLimitConfig(requests_per_minute=2)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Max out limits for multiple users
    for user in ["user1", "user2", "user3"]:
        limiter.check_limit(user, config, now)
        limiter.check_limit(user, config, now)

    # Reset all
    limiter.reset_all()

    # All should be allowed
    for user in ["user1", "user2", "user3"]:
        status = limiter.check_limit(user, config, now)
        assert status.allowed is True


# ============================================================================
# Usage Statistics Tests
# ============================================================================

def test_get_usage_sliding_window():
    """Test getting usage statistics for sliding window"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    config = RateLimitConfig(requests_per_minute=100)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make requests
    for _ in range(5):
        limiter.check_limit("user1", config, now)

    # Get usage (pass same time for consistency)
    usage = limiter.get_usage("user1", now)
    assert usage["requests_last_minute"] == 5
    assert usage["requests_last_hour"] == 5
    assert usage["requests_last_day"] == 5


def test_get_usage_token_bucket():
    """Test getting usage statistics for token bucket"""
    limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)
    config = RateLimitConfig(requests_per_minute=100)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Make requests
    for _ in range(5):
        limiter.check_limit("user1", config, now)

    # Get usage
    usage = limiter.get_usage("user1")
    assert "tokens_available" in usage
    assert "last_refill" in usage


def test_get_usage_nonexistent():
    """Test getting usage for nonexistent identifier"""
    limiter = RateLimiter()
    usage = limiter.get_usage("nonexistent")

    assert usage["requests_last_minute"] == 0
    assert usage["requests_last_hour"] == 0
    assert usage["requests_last_day"] == 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_rate_limiter_instance_exists():
    """Test that global rate limiter instance exists"""
    assert rate_limiter is not None
    assert isinstance(rate_limiter, RateLimiter)


def test_typical_api_workflow():
    """Test typical API rate limiting workflow"""
    limiter = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    config = RateLimitConfig(requests_per_minute=10)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Simulate 10 API requests
    for i in range(10):
        status = limiter.check_limit("api_key_123", config, now)
        assert status.allowed is True
        headers = status.to_headers()
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

    # 11th request hits limit
    status = limiter.check_limit("api_key_123", config, now)
    assert status.allowed is False
    assert status.retry_after_seconds == 60


def test_multiple_strategies_same_limiter():
    """Test using different strategies with different limiters"""
    fixed = RateLimiter(strategy=RateLimitStrategy.FIXED_WINDOW)
    sliding = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    token = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)

    config = RateLimitConfig(requests_per_minute=5)
    # Token bucket with no burst allowance for this test
    token_config = RateLimitConfig(requests_per_minute=5, burst_allowance=1.0)
    now = datetime(2024, 1, 15, 10, 30, 0)

    # Each should track independently
    for _ in range(5):
        assert fixed.check_limit("user", config, now).allowed is True
        assert sliding.check_limit("user", config, now).allowed is True
        assert token.check_limit("user", token_config, now).allowed is True

    # Next request on each
    assert fixed.check_limit("user", config, now).allowed is False
    assert sliding.check_limit("user", config, now).allowed is False
    assert token.check_limit("user", token_config, now).allowed is False


def test_realistic_api_scenario():
    """Test realistic API rate limiting scenario"""
    limiter = RateLimiter(strategy=RateLimitStrategy.SLIDING_WINDOW)
    
    # Different limits for different API key tiers
    basic_config = RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=1000,
    )
    premium_config = RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=1000,
        requests_per_day=10000,
    )

    now = datetime(2024, 1, 15, 10, 30, 0)

    # Basic user hits minute limit
    for i in range(10):
        status = limiter.check_limit("basic_user", basic_config, now)
        assert status.allowed is True

    status = limiter.check_limit("basic_user", basic_config, now)
    assert status.allowed is False

    # Premium user can do more
    for i in range(50):
        status = limiter.check_limit("premium_user", premium_config, now)
        assert status.allowed is True

    status = limiter.check_limit("premium_user", premium_config, now)
    assert status.allowed is True
