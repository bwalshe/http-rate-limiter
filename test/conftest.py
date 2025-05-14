import pytest

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import PlainTextResponse


@pytest.fixture
def website():
    def homepage(request):
        return PlainTextResponse("Hello", status_code=200)

    app = Starlette(
        routes=[Route("/", endpoint=homepage)]
    )

    return app
