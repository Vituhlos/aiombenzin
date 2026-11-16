"""aiombenzin against a local test server: no request ever reaches mBenzin.cz."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from aiombenzin import (
    DEFAULT_USER_AGENT,
    FUELS,
    URL,
    CannotConnect,
    InvalidAuth,
    MBenzinError,
    RateLimited,
    async_fetch_markers,
    retry_after_seconds,
)

KEY = "test-key"
MARKER = {
    "id": "17266",
    "url": "/Ceny-benzinu-a-nafty/As/F1-Gas-Selbska-152732/17266",
    "name": "F1 Gas",
    "chain": "F1 Gas",
    "addr": "Selbská 15/2732, Aš",
    "price": 39.7,
    "fresh": "12.11.2026",
    "lat": 50.21787,
    "lng": 12.176793,
    "ccs": True,
}

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


@pytest.fixture
async def serve() -> AsyncIterator[Callable[[Handler], Awaitable[str]]]:
    """Start a local server answering with `handler`; return the URL to fetch."""
    servers: list[TestServer] = []

    async def start(handler: Handler) -> str:
        app = web.Application()
        app.router.add_get("/Mapa-cen/data", handler)
        server = TestServer(app)
        await server.start_server()
        servers.append(server)
        return str(server.make_url("/Mapa-cen/data"))

    yield start
    for server in servers:
        await server.close()


async def test_markers_are_returned_and_the_key_stays_out_of_the_url(
    serve: Callable[[Handler], Awaitable[str]],
) -> None:
    seen: list[web.Request] = []

    async def handler(request: web.Request) -> web.StreamResponse:
        seen.append(request)
        return web.json_response({"markers": [MARKER]})

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        markers = await async_fetch_markers(session, KEY, "n95", url=url)
    assert markers == [MARKER]
    request = seen[0]
    assert request.headers["X-Mbenzin-Klic"] == KEY
    assert request.headers["User-Agent"] == DEFAULT_USER_AGENT
    assert dict(request.query) == {"fuel": "n95", "ccs": "0"}
    assert KEY not in str(request.url)


async def test_a_custom_user_agent_is_sent(serve: Callable[[Handler], Awaitable[str]]) -> None:
    agents: list[str] = []

    async def handler(request: web.Request) -> web.StreamResponse:
        agents.append(request.headers["User-Agent"])
        return web.json_response({"markers": []})

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        assert await async_fetch_markers(session, KEY, "lpg", url=url, user_agent="HomeAssistant-ceny-paliv") == []
    assert agents == ["HomeAssistant-ceny-paliv"]


@pytest.mark.parametrize("status", [401, 403])
async def test_a_refused_key_is_definite(serve: Callable[[Handler], Awaitable[str]], status: int) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        return web.Response(status=status)

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(InvalidAuth) as err:
            await async_fetch_markers(session, KEY, "n95", url=url)
    assert err.value.definite is True


@pytest.mark.parametrize(
    "body",
    [
        "<html><body>Browser check</body></html>",  # what mBenzin.cz answers a key it does not accept
        '{"error": "no markers"}',
        '{"markers": "not a list"}',
        "[]",
    ],
)
async def test_an_answer_without_markers_is_an_unaccepted_key(
    serve: Callable[[Handler], Awaitable[str]], body: str
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        return web.Response(text=body, content_type="text/html")

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(InvalidAuth) as err:
            await async_fetch_markers(session, KEY, "n95", url=url)
    assert err.value.definite is False


async def test_a_key_that_cannot_be_sent_is_refused_without_a_request(
    serve: Callable[[Handler], Awaitable[str]],
) -> None:
    calls: list[web.Request] = []

    async def handler(request: web.Request) -> web.StreamResponse:
        calls.append(request)
        return web.json_response({"markers": []})

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(InvalidAuth):
            await async_fetch_markers(session, "key\nwith a line break", "n95", url=url)
    assert calls == []


@pytest.mark.parametrize(
    ("header", "expected"),
    [("120", 120.0), ("999999", 86400.0), ("Sat, 14 Nov 2026 10:05:00 GMT", 300.0), ("soon", None), (None, None)],
)
async def test_rate_limiting_tells_how_long_to_wait(
    serve: Callable[[Handler], Awaitable[str]], header: str | None, expected: float | None
) -> None:
    async def handler(request: web.Request) -> web.StreamResponse:
        return web.Response(status=429, headers={"Retry-After": header} if header else {})

    url = await serve(handler)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(RateLimited) as err:
            await async_fetch_markers(
                session, KEY, "diesel", url=url, clock=lambda: datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
            )
    assert err.value.retry_after == expected


async def test_other_answers_and_failures_cannot_connect(serve: Callable[[Handler], Awaitable[str]]) -> None:
    async def broken(request: web.Request) -> web.StreamResponse:
        return web.Response(status=503)

    async def slow(request: web.Request) -> web.StreamResponse:
        await asyncio.sleep(1)
        return web.json_response({"markers": []})

    async with aiohttp.ClientSession() as session:
        with pytest.raises(CannotConnect, match="HTTP 503"):
            await async_fetch_markers(session, KEY, "n95", url=await serve(broken))
        with pytest.raises(CannotConnect, match="TimeoutError"):
            await async_fetch_markers(session, KEY, "n95", url=await serve(slow), timeout=0.05)
        # nothing listens on this port
        with pytest.raises(CannotConnect, match="ClientConnectorError"):
            await async_fetch_markers(session, KEY, "n95", url="http://127.0.0.1:9/Mapa-cen/data")


def test_retry_after_parsing() -> None:
    now = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
    assert retry_after_seconds("  60 ", now) == 60.0
    assert retry_after_seconds("Sat, 14 Nov 2026 09:00:00 GMT", now) == 0.0  # already past
    assert retry_after_seconds("Sat, 14 Nov 2026 10:01:00", now) == 60.0  # no zone: UTC
    assert retry_after_seconds("Sat, 14 Nov 2026 10:01:00 GMT", datetime(2026, 11, 14, 10, 0)) == 60.0
    assert retry_after_seconds("", now) is None
    assert retry_after_seconds("9" * 400, now) is None  # too large for a float


def test_public_names() -> None:
    assert URL == "https://www.mbenzin.cz/Mapa-cen/data"
    assert FUELS == ("n95", "benzinplus", "diesel", "dieselplus", "lpg", "cng", "adblue")
    assert issubclass(CannotConnect, MBenzinError)
    assert issubclass(InvalidAuth, MBenzinError)
    assert issubclass(RateLimited, MBenzinError)


def test_the_version_matches_the_package_metadata() -> None:
    import tomllib
    from pathlib import Path

    import aiombenzin

    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text("utf-8"))
    assert aiombenzin.__version__ == pyproject["project"]["version"]
