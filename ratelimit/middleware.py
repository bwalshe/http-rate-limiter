from datetime import datetime
from typing import Callable

from starlette.responses import Response
from starlette.types import ASGIApp, Scope, Receive, Send


class RateLimiter:
    def __init__(self,
                 app: ASGIApp,
                 algorithm: Callable[[bytes, datetime], bool],
                 key_fn: Callable[[Scope], bytes] = None):
        self._app = app
        self._algorithm = algorithm
        self._key_fn = key_fn
        self._limit_response = Response("Limit Exceded", status_code=429)

    def _get_key(self, scope):
        if self._key_fn:
            return self._key_fn(scope)
        return scope["client"]

    async def __call__(self, scope: Scope,
                       receive: Receive,
                       send: Send) -> None:
        if scope["type"] in ("http", "webstocket"):
            key = self._get_key(scope)
            if not self._algorithm(key, datetime.now()):
                await self._limit_response(scope, receive, send)
                return
        await self._app(scope, receive, send)
