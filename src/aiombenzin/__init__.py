"""Async client for the mBenzin.cz fuel price map (Czech Republic). Unofficial; needs your own access key."""

from .client import DEFAULT_USER_AGENT, FUELS, MAX_RETRY_AFTER, URL, async_fetch_markers, retry_after_seconds
from .exceptions import CannotConnect, InvalidAuth, MBenzinError, RateLimited

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_USER_AGENT",
    "FUELS",
    "MAX_RETRY_AFTER",
    "URL",
    "CannotConnect",
    "InvalidAuth",
    "MBenzinError",
    "RateLimited",
    "async_fetch_markers",
    "retry_after_seconds",
]
