# aiombenzin

Async Python client for the [mBenzin.cz](https://www.mbenzin.cz) fuel price map (Czech Republic): the prices of
every station for one fuel, as mBenzin.cz publishes them.

> **Unofficial.** This library is not made, endorsed or supported by mBenzin.cz. The price map is not a documented
> public API, and it needs a **personal access key** from mBenzin.cz: e-mail reklama@mbenzin.cz and say what you
> use the prices for. Never publish your key. mBenzin.cz asks that the prices are shown with the source
> **„Ceny: mbenzin.cz“**.

It is used by the Home Assistant integration [Ceny paliv](https://github.com/Vituhlos/ha-ceny-paliv).

## Install

```bash
pip install aiombenzin
```

Python 3.12 or newer, with `aiohttp`.

## Use

```python
import asyncio

import aiohttp

from aiombenzin import CannotConnect, InvalidAuth, RateLimited, async_fetch_markers


async def main() -> None:
    async with aiohttp.ClientSession() as session:  # bring your own session
        try:
            markers = await async_fetch_markers(session, "YOUR-KEY", "n95")
        except RateLimited as err:
            print(f"Too many requests; try again in {err.retry_after} s")
            return
        except InvalidAuth:
            print("mBenzin.cz does not accept the key")
            return
        except CannotConnect as err:
            print(f"mBenzin.cz cannot be reached: {err}")
            return
    cheapest = min(markers, key=lambda m: m["price"])
    print(cheapest["name"], cheapest["addr"], cheapest["price"])


asyncio.run(main())
```

- **Fuels** (`aiombenzin.FUELS`): `n95` (Natural 95), `benzinplus` (Natural 98), `diesel`, `dieselplus`, `lpg`, `cng`
  (per kg), `adblue`.
- **Markers** are returned as mBenzin.cz sends them, not validated. A marker usually has `id`, `url` (the station's
  page), `name`, `chain`, `addr` (for example `Selbská 15/2732, Aš`), `price` (CZK), `fresh` (when the price was
  updated: `Dnes`, `Včera` or a date such as `12.11.2026`), `lat`, `lng` and `ccs`.
- **The key** is sent in a header, never in the URL.
- **Errors**: `RateLimited` (HTTP 429, with `retry_after` in seconds from the Retry-After header, at most 24 hours),
  `InvalidAuth` (HTTP 401/403 with `definite=True`, or an answer without markers, which is how mBenzin.cz answers a
  key it does not accept), `CannotConnect` (anything else). All derive from `MBenzinError`.
- Options of `async_fetch_markers`: `user_agent`, `timeout` (seconds, default 60), `clock` (the current time, for an
  HTTP-date Retry-After) and `url`.

Be gentle: one request per fuel downloads the whole country, so a few requests a day are enough.

## Development

```bash
pip install -e ".[test]"
pytest
ruff check . && ruff format --check .
mypy
```

The tests run against a local server; no key is needed and no request reaches mBenzin.cz.

## Releasing

Releases are published to PyPI by `.github/workflows/release.yml` with trusted publishing (no token): push a tag
`vX.Y.Z` that matches the version in `pyproject.toml`. The PyPI project trusts the workflow `release.yml` of this
repository in the environment `pypi`.

## License

MIT — see [LICENSE](LICENSE).
