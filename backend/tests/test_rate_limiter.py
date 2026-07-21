from app.services.rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_allows_new_key():
    limiter = SlidingWindowRateLimiter()

    assert limiter.check("session-a") is True
    assert limiter.remaining("session-a") >= 0
