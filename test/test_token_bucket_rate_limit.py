import time

from starlette.testclient import TestClient

from ratelimit import TokenBucketRateLimiter


def test_token_bucket_rate_limit(website):
    limiter = TokenBucketRateLimiter(website, capacity=2, rate=1)
    with TestClient(limiter) as client:
        assert client.get("/").status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/").status_code == 429
        time.sleep(2)
        assert client.get("/").status_code == 200
