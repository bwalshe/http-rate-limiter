"""Rate limiting ASGI middleware."""

from collections.abc import Callable
from datetime import datetime

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


def _default_get_key(scope):
    return scope["client"]


class RateLimiter:
    """Controlis the rate of traffic sent to an ASGI app.

    The RateLimiter wraps an ASGI app and uses a supplied rate limiting
    algorithm (such as Token Bucket) to contorl how often clients can
    access the app. Clients which are below the rate limit are have their
    request passed through to the app unaffected. Clients that go over
    the limit will receive a HTTP 429 (Too Many Requests) error.
    """

    def __init__(
        self,
        app: ASGIApp,
        algorithm: Callable[[bytes, datetime], bool],
        key_fn: Callable[[Scope], bytes] = _default_get_key,
    ):
        """Initialise a RateLimiter with the supplied rate limiting algorithm.

        The rate limiting algorithm must take a bytes arguement
        representing a key and a datetime representing when the
        client with this key tried to access the service and
        return True if the client has permission to access the service.

        Args:
            app: The app which is being limited.
            algorithm: A function which returns True if the client has
                       permnission to access the wrapped app.
            key_fn: A function which genrates a key for the client,
                    based on the scope supplied in the request.
                    Defaults to client IP.

        """
        self._app = app
        self._algorithm = algorithm
        self._key_fn = key_fn
        self._limit_response = Response("Limit Exceded", status_code=429)

    def _get_key(self, scope):
        return self._key_fn(scope)

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """ASGI interface function.

        If the client is below the rate limit then this will proxy
        through to the wrapped app. If they are over the limit they
        will receive a http 429 instead.
        """
        if scope["type"] == "http":
            key = self._get_key(scope)
            if not self._algorithm(key, datetime.now()):
                await self._limit_response(scope, receive, send)
                return
        await self._app(scope, receive, send)
