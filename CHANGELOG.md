# Changelog

## 0.1.0

- First version: `async_fetch_markers()` downloads the markers of one fuel with the caller's `aiohttp` session and
  access key; `CannotConnect`, `InvalidAuth` and `RateLimited` (with the Retry-After delay) report failures;
  `retry_after_seconds()`; the fuel codes in `FUELS`. Typed (`py.typed`), checked with `mypy --strict`. The code
  comes from the Home Assistant integration Ceny paliv 0.6.2.
