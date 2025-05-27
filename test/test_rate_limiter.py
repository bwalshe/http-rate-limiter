import logging

import pytest

from ratelimit.middleware import RateLimiter


def make_scope(key, value):
    scope = {"type": "http"}
    scope[key] = value
    return scope


@pytest.mark.asyncio
async def test_rate_limit_pass_through(mocker):
    """If our rate limiting algorithm doesn't block the client, then
    trafic should pass through unchanged
    """

    def allow_all(key, time):
        return True

    app = mocker.AsyncMock(return_val=None)
    limiter = RateLimiter(app, allow_all)
    scope = make_scope("client", ("host", 1))
    receive = mocker.Mock(return_val=None)
    send = mocker.Mock(return_val=None)

    await limiter(scope, receive, send)

    app.assert_called_with(scope, receive, send)
    receive.assert_not_called()
    send.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_blocks(mocker):
    """If our rate limiting algorithm blocks the client, then
    the wrapped appp should not be called
    """

    def allow_none(key, time):
        return False

    app = mocker.AsyncMock(return_val=None)
    limiter = RateLimiter(app, allow_none)
    scope = make_scope("client", ("host", 1))
    receive = mocker.AsyncMock(return_val=None)
    send = mocker.AsyncMock(return_val=None)

    await limiter(scope, receive, send)

    app.assert_not_called()
    send.assert_called()


@pytest.mark.asyncio
async def test_rate_limit_only_blocks_http(mocker):
    """The rate limiter should only affect http traffic, and it does not
    care if the client key is missing from the scope in this case
    """

    def allow_none(key, time):
        return False

    key_fn = mocker.AsyncMock(return_val=None)
    app = mocker.AsyncMock(return_val=None)
    limiter = RateLimiter(app, allow_none, key_fn)
    scope = {"type": "stream"}
    receive = mocker.AsyncMock(return_val=None)
    send = mocker.AsyncMock(return_val=None)

    await limiter(scope, receive, send)

    app.assert_called_with(scope, receive, send)
    key_fn.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_id_fn(mocker):
    """Supplying a key function in the constructor allows us to identify
    clients using that function.
    """

    def is_10(i, _):
        return i == b"10"

    def get_user_id(scope):
        return scope["user_id"]

    app = mocker.AsyncMock(return_val=None)
    limiter = RateLimiter(app, is_10, key_fn=get_user_id)
    receive = mocker.AsyncMock(return_val=None)
    send = mocker.AsyncMock(return_val=None)

    await limiter(make_scope("user_id", b"1"), receive, send)
    app.assert_not_called()

    await limiter(make_scope("user_id", b"10"), receive, send)
    app.assert_called()


@pytest.mark.asyncio
async def test_rate_limit_logs_block(mocker, caplog):
    def always_fail(key, time):
        return False

    app = mocker.AsyncMock(return_val=None)
    limiter = RateLimiter(app, always_fail)
    receive = mocker.AsyncMock(return_val=None)
    send = mocker.AsyncMock(return_val=None)
    scope = make_scope("client", ("localhost", 1))

    with caplog.at_level(logging.INFO):
        await limiter(scope, receive, send)
        assert "blocked" in caplog.text.lower()
