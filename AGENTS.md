# AI agent instructions — aiombenzin

These instructions apply to every coding agent working in this repository.

- **aiombenzin** is the async client for the mBenzin.cz price map used by the Home Assistant integration
  [Ceny paliv](https://github.com/Vituhlos/ha-ceny-paliv). Keep it small: downloading and errors here; caching,
  processing and Home Assistant concerns stay in the integration.
- The mBenzin access key is personal. Never include a real key, token, Home Assistant configuration or other
  personal data in code, tests, logs, issues or pull requests. Tests use a local server and a fake key.
- Keep the public API typed (`py.typed`, `mypy --strict`) and covered by tests; report which checks actually ran and
  never claim validation against the live mBenzin.cz service from tests or CI.
- Do not merge, release (push a version tag), publish or delete branches without the maintainer's (@Vituhlos)
  explicit authorization. Releases go to PyPI only through `.github/workflows/release.yml`.
- Pull requests and agent-written GitHub comments are in English and disclose AI authorship, naming the actual agent
  and model (or `not exposed`), as in the integration's `AGENTS.md`.
