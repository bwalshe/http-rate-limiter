from datetime import datetime


class TokenBucket:
    def __init__(self, capacity=10, rate=1):
        self._capacity = capacity
        self._rate = rate
        self._buckets = dict()

    def __len__(self) -> int:
        return len(self._buckets)

    def __call__(self, key: bytes, time: datetime) -> bool:
        capacity, last_update = self._buckets.get(key, (self._capacity, time))
        top_up = int((time - last_update).total_seconds() / self._rate)
        capacity = min(capacity + top_up, self._capacity) - 1
        last_update = time if top_up > 0 else last_update
        self._buckets[key] = (capacity, last_update)
        return capacity >= 0
