# Changelog

All notable changes to this project. Versions follow [semantic versioning](https://semver.org/).

## 1.0.1 — 2026-11-03

### Fixed
- A UPI payload that repeats a parameter (`pa`, `am`, `pn`, in any letter case) is reported as
  high risk: the payee or amount is ambiguous.
- A malformed UPI payload or a URL with an invalid port is reported as a high-risk finding
  instead of raising or being trusted.

## 1.0.0 — 2026-11-03

### Added
- A checking API (`qrguard serve`): `POST /v1/check` checks a payload against what was registered,
  `POST /v1/scan` checks a photo sent as the body, and `GET /v1/checks[/{id}]` reads the log
  (`?risk=high` filters). Still offline: payloads are never fetched. Photos and payloads are not
  stored; each check records the input's SHA-256, the risk, the signals and who asked, in SQLite or
  Postgres with numbered migrations (`qrguard migrate`).
- Images over 50 megapixels are refused before decoding (`OPENCV_IO_MAX_IMAGE_PIXELS`, set when
  the package loads, before OpenCV), so a small crafted file can't make the service allocate
  gigabytes.
- Settings from `QRGUARD_*` environment variables, checked at startup; production refuses to start
  without hashed API keys and a database. Roles on keys, rate limit, body cap, security headers,
  JSON logs with request IDs, `/healthz`, `/readyz` and Prometheus `/metrics`.
- `pyproject.toml` 1.0.0 (Python 3.12+), pinned lock files, a container image (slim, non-root,
  health check), CI with ruff, bandit, pip-audit and coverage (it replaces the old test workflow
  and keeps its import-order check and warnings-as-errors).
- `SECURITY.md`, `docs/threat-model.md`, `docs/runbook.md`, MIT licence.

### Unchanged
- The destination checks, image signals and scan reports; the 27 original tests pass unchanged.
- The benchmark: re-run with the pinned OpenCV and NumPy (`qrguard bench --n 60 --seed 1`), all
  403 values in `results/results.json` came out identical.
