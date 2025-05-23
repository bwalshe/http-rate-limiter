import logging

import pytest
from starlette.testclient import TestClient

from ratelimit.middleware import RateLimiter


def test_rate_limit_pass_through(website):
    """If our rate limiting algorithm doesn't block the client, then
    trafic should pass through unchanged
    """

    def allow_all(key, time):
        return True

    limiter = RateLimiter(website, allow_all)

    with (
        TestClient(website) as direct_client,
        TestClient(limiter) as limiter_client,
    ):
        url = "/"
        direct_result = direct_client.get(url)
        limiter_result = limiter_client.get(url)
        assert direct_result.status_code == limiter_result.status_code
        assert direct_result.text == limiter_result.text


def test_rate_limit_response_code(website):
    """If the algorithm blocks the client, then they should receive a
    429 code.
    """

    def always_fail(key, time):
        return False

    limiter = RateLimiter(website, always_fail)

    with TestClient(limiter) as client:
        response = client.get("/")
        assert response.status_code == 429


def test_rate_limit_id_fn(website):
    """Supplying a key function in the constructor allows us to identify
    clients using that function.
    """

    def is_10(i, _):
        return i == "10"

    def get_user_id(scope):
        query = scope["query_string"].decode()
        return query.split("=")[1]

    limiter = RateLimiter(website, is_10, get_user_id)
    with TestClient(limiter) as client:
        url = "/"
        with pytest.raises(Exception):
            client.get(url)
        user_1_response = client.get(url, params={"user_id": "1"})
        assert user_1_response.status_code == 429
        user_10_response = client.get(url, params={"user_id": "10"})
        assert user_10_response.status_code == 200


def test_rate_limit_logs_block(website, caplog):
    def always_fail(key, time):
        return False

    limiter = RateLimiter(website, always_fail)
    with caplog.at_level(logging.INFO), TestClient(limiter) as client:
        client.get("/")
        assert "blocked" in caplog.text
