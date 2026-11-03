# QRGuard: Catching Overlay QR Stickers (Quishing and UPI Swaps)

**Project 5 of 5** · Status: research complete, tool and checking API built and tested (39 tests), synthetic benchmark run, real-photo lab work pending
Research cut-off: 10 Oct 2026

## What this is

Fraudsters stick their own QR code over a genuine one: parking meters and EV chargers send people to card-stealing sites; shop UPI codes send payments to the fraudster. Hyderabad cyber experts report around 2,000 such complaints a month from vendors alone.

QRGuard checks a photo of a QR code in two independent ways:
1. **Image evidence of an overlay**: two codes stacked, the leftover corner squares of a covered code, a detected but unreadable code.
2. **The destination itself**: does the payload match what the operator or merchant registered (exact payload, UPI payee ID, domain)? Is the domain a lookalike, a shortener, an IP address, a `user@host` trick?

It runs offline and never sends the payload anywhere. It reports every signal with its reason.

## How it differs from existing work
An early prototype, *XQR for Merchants* (Oct 2026), looks for image anomalies around UPI stickers but never checks where the payment goes and publishes no accuracy figures. Academic quishing detectors classify the QR pattern of digital codes, not physical overlays. QRGuard adds destination verification and a reproducible benchmark that measures what image analysis can and cannot catch. Details in [research/01](research/01-prior-art.md).

## Repository layout
```
05-qr-overlay-detector/
├── README.md
├── research/
│   ├── 01-prior-art.md         prior work (incl. XQR), the attack in the wild, the gap
│   ├── 02-method.md            threat model, image signals, destination checks, limits
│   ├── 03-evaluation-plan.md   synthetic benchmark, metrics, lab tasks
│   ├── 04-results.md           benchmark results, what they show, threats to validity
│   └── sources.md
├── qrguard/
│   ├── dest.py                 destination checks: registered payload, domains, lookalikes, UPI payee
│   ├── image.py                every QR in a photo + overlay signals
│   ├── scan.py                 photo -> one report (image evidence + destination per code)
│   ├── synth.py                synthetic genuine/overlay photos with camera effects
│   ├── bench.py                reproducible benchmark, Wilson intervals
│   ├── api.py                  checking API with a log of every check
│   ├── ops.py, db.py           settings, API keys, limits, logs, metrics; database and migrations
│   └── cli.py                  `qrguard` command
├── docs/                       threat model, runbook
├── results/                    benchmark output (results.md, results.json)
├── tests/                      39 tests
└── pyproject.toml
```

## Tool
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.lock -e .   # Linux/macOS: .venv/bin/pip
pytest -q
```
Offline: nothing is fetched or sent.
```bash
qrguard scan  photo.jpg --expect-vpa sharma.store@okaxis --expect-name "Sharma Store"   # shop UPI sticker
qrguard scan  meter.jpg --expect-domain parkmobile.io                                   # parking meter
qrguard scan  photo.jpg --expect-payload "upi://pay?pa=sharma.store@okaxis&pn=Sharma%20Store"  # strongest
qrguard check "https://parkmobi1e.io/zone/9" --expect-domain parkmobile.io              # a payload string
qrguard bench --n 60 --seed 1 --out results                                             # re-run the benchmark
```
Who supplies the expectation: the merchant (their UPI ID), the parking or charging operator (their domain), or a payment app that already knows which merchant the customer is standing at.

## Results (synthetic benchmark, 960 photos)
| Share of genuine code hidden | Strict image signals | Destination check | Both combined |
|---|---|---|---|
| genuine photos (false alarms) | 0% | 0% | **0%** |
| ~50-65% | 98-100% | 97-100% | **100%** |
| ~80% | 12-33% | 100% | **100%** |
| 86-100% (incl. full cover) | 0% | 100% | **100%** |

Image evidence alone fades once most of the code is hidden; the destination check (given the expected payee or domain) catches full covers; together they caught every tampered photo with no false alarms. The low-severity texture lead adds range but fires on 8-15% of genuine photos with bold signage text. Details, intervals and threats to validity: [research/04](research/04-results.md), [results/results.md](results/results.md).

| Feature | Checked against | Status |
|---|---|---|
| Destination checks (payload, URL tricks, lookalikes, UPI payee/name/amount, trailing-dot hosts) | 14 targeted cases | ✅ tests |
| Code finding (2 detectors x 2 scales), overlay signals | synthetic photos; side-by-side and stacked codes | ✅ tests |
| Scan report, CLI, bad-input handling | synthetic photos | ✅ tests |
| Benchmark reproducibility (fixed seed) | repeated runs | ✅ tests |
| Real photos (printed codes and stickers, phones, angles) | - | ⏳ lab tasks L1-L3 |

### Known gaps
- **Synthetic only so far**: real stickers (gloss, curvature, shadows) and real signage may change the rates.
- **The expectation must come from somewhere** (merchant registry, operator domain list, payment-app context); without it a clean full cover is not caught.
- **No reputation lookups or depth cues** (parallax/LiDAR for a raised sticker edge) yet: research/03 L4.
- **Approximate public-suffix list**: registrable-domain logic uses a small built-in suffix list.

## Checking API

`qrguard serve` (or the container image, `docker build -t qrguard .`, see [docs/runbook.md](docs/runbook.md)) puts the payload and photo checks behind an API, for an inspector's app or a payment app.

| Endpoint | Purpose |
|---|---|
| `POST /v1/check` | a decoded payload against what was registered (`expect`: payload, domains, UPI ID, name) |
| `POST /v1/scan` | a photo sent as the body; expectations as `expect_vpa`, `expect_name`, `expect_domain`, `expect_payload` query parameters |
| `GET /v1/checks`, `/v1/checks/{id}` | the log: who checked which input (by SHA-256), the risk and signals; `?risk=high` filters |
| `GET /healthz`, `/readyz`, `/metrics` | health, readiness and Prometheus metrics |

Still offline: payloads are never fetched or sent. Photos and payloads are not stored, and images over 50 megapixels are refused before decoding. API keys carry a role: `inspector`, `viewer`, `monitor`. Create one with `python -m qrguard.ops keygen`.

| Variable | Purpose |
|---|---|
| `QRGUARD_ENV=production` | refuse to start without hashed API keys and a database |
| `QRGUARD_API_KEYS` / `QRGUARD_KEYS_FILE` | hashed API keys with roles |
| `QRGUARD_DATABASE_URL` | the check log: `sqlite:///...` or `postgresql://...` |

## Limitations

- Validated on synthetic photos only; real stickers and signage may change the rates.
- Without an expected destination a clean full cover is not caught.
- The check log records input hashes but is not signed or hash-chained.
- The code has not had an independent security review.

See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## Ethics in one line
Test stickers go only on the project's own printed codes, never on public signs or real merchants' codes.

## License

MIT. See [LICENSE](LICENSE).
