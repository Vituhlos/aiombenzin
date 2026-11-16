"""Errors raised by aiombenzin."""

from __future__ import annotations


class MBenzinError(Exception):
    """Base class of every aiombenzin error."""


class CannotConnect(MBenzinError):
    """mBenzin.cz cannot be reached or answered with an unexpected HTTP status."""


class InvalidAuth(MBenzinError):
    """The access key is missing, wrong or not accepted.

    `definite` is True for HTTP 401/403. mBenzin.cz also answers a key it does not accept with an HTML page, but
    such a page can come from an outage too: callers may want to trust it only when it repeats.
    """

    def __init__(self, *args: object, definite: bool = False) -> None:
        super().__init__(*args)
        self.definite = definite


class RateLimited(MBenzinError):
    """HTTP 429: mBenzin.cz is temporarily limiting requests.

    `retry_after` is the delay in seconds from the Retry-After header (at most 24 hours), or None without one.
    """

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__()
        self.retry_after = retry_after
