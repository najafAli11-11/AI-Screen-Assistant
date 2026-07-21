from app.services.rate_limiter import SlidingWindowRateLimiter, rate_limiter

RateLimiter = SlidingWindowRateLimiter

__all__ = ["RateLimiter", "SlidingWindowRateLimiter", "rate_limiter"]
