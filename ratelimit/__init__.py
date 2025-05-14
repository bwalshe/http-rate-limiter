from starlette.types import ASGIApp

from .middleware import RateLimiter
from .algorithm import TokenBucket


def TokenBucketRateLimiter(app: ASGIApp,
                           capacity: int = 10,
                           rate: int = 1) -> ASGIApp:
    return RateLimiter(app, TokenBucket(capacity, rate))
