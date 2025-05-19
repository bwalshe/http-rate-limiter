from datetime import datetime, timedelta

from ratelimit.algorithm import TokenBucket


def test_token_bucket_construct():
    bucket = TokenBucket(10, 1)
    assert len(bucket) == 0


def test_token_bucket_call():
    """Checks that the TokenBucket call method conforms to the expected
    standard"""
    bucket = TokenBucket()
    assert bucket(b"key", datetime(2001, 1, 1, 1))


def test_token_bucket_len():
    """Observing a new client key should increase the size of the set
    of buckets."""
    bucket = TokenBucket()
    assert len(bucket) == 0

    t = datetime(2001, 1, 1, 1)
    dt = timedelta(seconds=1)
    bucket(b"A", t)
    assert len(bucket) == 1
    bucket(b"A", t + dt)
    assert len(bucket) == 1
    bucket(b"B", t + 2 * dt)
    assert len(bucket) == 2


def test_token_bucket_limits_rate():
    """Construct a bucket with an inital capaicity of 2, send in
    3 accesses, all with the same time. The first two accesses
    should be allowed and the third should be blocked. Waiting
    a few seconds should allow access to return.
    """
    bucket = TokenBucket(2, 1)
    t = datetime(2001, 1, 1, 1)
    dt = timedelta(seconds=10)
    key = b"A"
    assert bucket(key, t)
    assert bucket(key, t)
    assert not bucket(key, t)
    assert bucket(key, t + dt)
