"""Rate Limiting Algorithms.

These are intended for use with the ratelimit.middleware.RateLimiter class.
"""

from datetime import datetime


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

    def __init__(self, capacity=10, rate=1):
        """Initialise a set of buckets with the given capacity and refresh rate.

        Args:
            capacity: The maximum number of tokens in a single bucket.
            rate: The number of seconds to wait before increasing the
                  token count in each bucket.
        """  # noqa: E501
        self._capacity = capacity
        self._rate = rate
        self._buckets = dict()

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
        capacity, last_update = self._buckets.get(key, (self._capacity, time))
        top_up = int((time - last_update).total_seconds() / self._rate)
        capacity = min(capacity + top_up, self._capacity) - 1
        last_update = time if top_up > 0 else last_update
        self._buckets[key] = (capacity, last_update)
        return capacity >= 0
