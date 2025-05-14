from datetime import datetime, timedelta

from ratelimit.algorithm import TokenBucket


def test_token_bucket_construct():
    bucket = TokenBucket(10, 1)
    len(bucket) == 0


def test_token_bucket_call():
    bucket = TokenBucket()
    assert bucket(b"key", datetime(2001, 1, 1, 1))


def test_token_bucket_len():
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
    bucket = TokenBucket(2, 1)
    t = datetime(2001, 1, 1, 1)
    dt = timedelta(seconds=10)
    key = b"A"
    assert bucket(key, t)
    assert bucket(key, t)
    assert not bucket(key, t)
    assert bucket(key, t + dt)
