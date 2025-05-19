"""Fixtures used by multiple tests."""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


@pytest.fixture
def website():
    """A very simple webapp which just returns "Hello" at "/"."""

    def homepage(request):
        return PlainTextResponse("Hello", status_code=200)

    app = Starlette(routes=[Route("/", endpoint=homepage)])

    return app
