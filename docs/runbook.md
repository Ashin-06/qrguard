# Runbook

How to deploy and operate the checking service. Commands assume the repository root.

## Deploy

```bash
docker build -t qrguard:1.0.0 .
python -m qrguard.ops keygen            # one API key per inspector app, viewer and monitor
docker run -d --name qrguard -p 8105:8105 -v qrguard-data:/data \
  -e QRGUARD_KEYS_FILE=/run/secrets/qrguard-keys.json \
  qrguard:1.0.0
curl -fsS http://127.0.0.1:8105/readyz
```

The image runs in production mode as a non-root user with its log in SQLite under `/data`. It
refuses to start, and logs why, without hashed API keys or a database URL. It needs no outbound
network access.

## Use

The caller supplies what the code should point to: the merchant's registered UPI ID, the operator's
domain, or the exact registered payload (strongest).

```bash
curl -fsS -H "x-api-key: $KEY" --data-binary @sticker.jpg \
  "http://127.0.0.1:8105/v1/scan?expect_vpa=sharma.store@okaxis&expect_name=Sharma%20Store&label=shop%2012"
curl -fsS -H "x-api-key: $KEY" -H "content-type: application/json" \
  -d '{"payload": "https://parkmobi1e.io/zone/9", "expect": {"domains": ["parkmobile.io"]}}' \
  http://127.0.0.1:8105/v1/check
```

Act on `risk`: `high` means a swapped destination or strong overlay evidence; `medium` is worth a
second look; `low` with no expectation supplied is not an all-clear for a full cover.

## Configure

| Variable | Required in production | Meaning |
|---|---|---|
| `QRGUARD_ENV` | — | `development` (default) or `production` |
| `QRGUARD_API_KEYS` / `QRGUARD_KEYS_FILE` | yes | JSON `{"sha256:<hex>": {"user": "...", "role": "..."}}`. Roles: `inspector` (check, read), `viewer`, `monitor`, `admin` |
| `QRGUARD_DATABASE_URL` | yes | the check log: `sqlite:////data/qrguard.db` or `postgresql://...` |
| `QRGUARD_HOST`, `QRGUARD_PORT` | — | default `127.0.0.1:8105`; any other address needs API keys |
| `QRGUARD_RATE_LIMIT`, `QRGUARD_MAX_BODY_BYTES` | — | default 120/min per client, 20,000,000 bytes |
| `QRGUARD_CORS_ORIGINS` | — | comma-separated origins allowed to call the API from a browser |
| `OPENCV_IO_MAX_IMAGE_PIXELS` | — | decode limit, default 50,000,000 pixels |

## Watch

- `GET /healthz`; `GET /readyz` (database); `GET /metrics` (role `monitor`): requests, latency,
  errors, `qrguard_decisions_total{decision="risk_low|risk_medium|risk_high"}`.
- `GET /v1/checks?risk=high` lists the sites to visit first.

## Rotate keys

Add the new API key hash, restart, hand over the key, remove the old hash, restart.

## Back up and restore

Back up the log like any SQLite or Postgres database (`python -m qrguard migrate` creates the
schema on a fresh one).

## Incidents

1. **Leaked API key.** Remove its hash and restart; list that user's entries.
2. **A swap was missed.** Find the check by ID, confirm whether an expectation was supplied, and
   add the photo to the benchmark cases once it is safe to keep.
