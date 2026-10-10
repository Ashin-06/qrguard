# QRGuard: Catching Overlay QR Stickers (Quishing and UPI Swaps)

**Project 5 of 5** · Status: research complete, tool in progress
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
│   └── sources.md
```

## Ethics in one line
Test stickers go only on the project's own printed codes, never on public signs or real merchants' codes.
