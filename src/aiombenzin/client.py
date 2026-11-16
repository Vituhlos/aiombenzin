"""Download the price-map markers of mBenzin.cz."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp

from .exceptions import CannotConnect, InvalidAuth, RateLimited

URL = "https://www.mbenzin.cz/Mapa-cen/data"
DEFAULT_USER_AGENT = "aiombenzin"
# The fuel codes of the price map: Natural 95, Natural 98, Diesel, Diesel Plus, LPG, CNG (per kg), AdBlue.
FUELS: tuple[str, ...] = ("n95", "benzinplus", "diesel", "dieselplus", "lpg", "cng", "adblue")
# A broken or hostile Retry-After header must not block a key for longer than this.
MAX_RETRY_AFTER = timedelta(hours=24)


def retry_after_seconds(value: str | None, now: datetime | None = None) -> float | None:
    """The delay a Retry-After header asks for, in seconds (0 to 24 hours), or None when it is missing or invalid.

    Both forms are understood: a number of seconds, and an HTTP date (compared with `now`, default the current
    time in UTC).
    """
    if not value:
        return None
    value = value.strip()
    if value.isdecimal():
        try:
            delay = float(int(value))
        except (OverflowError, ValueError):
            return None
        return min(delay, MAX_RETRY_AFTER.total_seconds()) if math.isfinite(delay) else None
    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        delay = (retry_at - current.astimezone(UTC)).total_seconds()
        return min(max(0.0, delay), MAX_RETRY_AFTER.total_seconds())
    except (TypeError, ValueError, OverflowError):
        return None


async def async_fetch_markers(
    session: aiohttp.ClientSession,
    key: str,
    fuel: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 60,
    clock: Callable[[], datetime] | None = None,
    url: str = URL,
) -> list[dict[str, Any]]:
    """Download the markers of one fuel for the whole Czech Republic.

    The caller owns `session` (Home Assistant passes its shared one) and its own access `key`, which is sent in a
    header, never in the URL. The markers are returned as mBenzin.cz sends them, not validated: each usually has
    `id`, `url`, `name`, `chain`, `addr`, `price`, `fresh`, `lat`, `lng` and `ccs`. `clock` gives the current
    time for an HTTP-date Retry-After header.

    Raises RateLimited (HTTP 429), InvalidAuth (HTTP 401/403, a key that cannot be sent, or an answer without
    markers, which is what mBenzin.cz gives a key it does not accept) and CannotConnect (any other failure).
    """
    try:
        async with session.get(
            url,
            params={"fuel": fuel, "ccs": "0"},
            headers={"User-Agent": user_agent, "X-Mbenzin-Klic": key},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status == 429:
                raise RateLimited(retry_after_seconds(resp.headers.get("Retry-After"), clock() if clock else None))
            if resp.status in (401, 403):
                raise InvalidAuth(definite=True)
            if resp.status != 200:
                raise CannotConnect(f"HTTP {resp.status}")
            try:
                data = await resp.json(content_type=None)
            except ValueError:  # an HTML "browser check" page: the key is not accepted
                data = None
    except (aiohttp.ClientError, TimeoutError) as err:
        raise CannotConnect(type(err).__name__) from None
    except ValueError:  # aiohttp refuses a header value with control characters: not a usable key
        raise InvalidAuth from None
    markers = data.get("markers") if isinstance(data, dict) else None
    if not isinstance(markers, list):
        raise InvalidAuth
    return markers
