"""Rate Limiting Algorithms.

These are intended for use with the ratelimit.middleware.RateLimiter class.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class _Bucket:
    tokens: int
    last_update: datetime


class TokenBucket:
    """Algorithm for controlling the rate of access to some resource.

    Each user of the resource is assigned a bucket, which has a fixed
    capacity. These buckets are filled with tokens at a fixed rate.
    When a user wants to access the resource, this algorithm first
    checks if they have any tokens in their bucket. If the bucket is
    non-empty then they user may use the resouce and their token count
    is decreased by 1. Otherwise, if the user does not have any tokens
    in their bucket, they may not use the resource.
    """

    def __init__(
        self,
        capacity: int = 10,
        rate: int = 1,
        memory_days: Optional[int] = None,
    ):
        """Initialise a set of buckets with the given capacity and refresh rate.

        Args:
            capacity: The maximum number of tokens in a single bucket.
            rate_seconds: The number of seconds to wait before increasing the
                          token count in each bucket.
            memory_days: The number of days to remember each client. Must be greater than zero

        """  # noqa: E501
        if memory_days is None:
            self._memory_days = None
        elif memory_days < 1:
            raise ValueError("memory_days must be greater than zero.")
        else:
            self._memory_days = timedelta(days=memory_days)
        self._capacity = capacity
        self._rate = rate
        self._buckets = dict()
        self._last_cleanup = None

    def __len__(self) -> int:
        """The number of buckets being used."""
        return len(self._buckets)

    def __call__(self, key: bytes, time: datetime) -> bool:
        """Determine if the client has permission to use the resorce.

        Args:
            key: A unique identifier for the client.
            time: The time the user is trying to access the resouce.

        Returns:
            True if the client has permission to access the resource,
            False otherwise.
        """
        bucket = self._get_bucket(key, time)
        top_up = int((time - bucket.last_update).total_seconds() / self._rate)
        tokens = min(bucket.tokens + top_up, self._capacity) - 1
        self._buckets[key] = _Bucket(tokens, time)
        self._clear_old(time)
        return tokens >= 0

    def _get_bucket(self, key, time):
        bucket = self._buckets.get(key)
        if bucket:
            return bucket
        return _Bucket(self._capacity, time)

    def _clear_old(self, time):
        if not self._memory_days:
            return
        if self._last_cleanup is None:
            self._last_cleanup = time
        if time - self._last_cleanup >= self._memory_days:
            self._buckets = {
                k: v
                for k, v in self._buckets.items()
                if time - v.last_update < self._memory_days
            }
            self._last_cleanup = time
