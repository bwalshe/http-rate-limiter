"""ASGI middleware for limiting access rates."""

from starlette.types import ASGIApp

from .algorithm import TokenBucket
from .middleware import RateLimiter


def TokenBucketRateLimiter(
    app: ASGIApp, capacity: int = 10, rate: int = 1
) -> ASGIApp:
    """Construct a RateLimiter object that uses the TokenBucket alorithm.

    Args:
        app: The WSGI app the RateLimiter will wrap.
        capacity: The maximum number of tokens in each bucket.
        rate: The number of seconds before adding a token to a bucket.
    """
    return RateLimiter(app, TokenBucket(capacity, rate))
