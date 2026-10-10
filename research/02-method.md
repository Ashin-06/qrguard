# 02 · Method

## Threat model
An attacker prints a QR code that encodes their own destination (phishing URL, or their UPI VPA) and sticks it over, or next to, a genuine code. They may match colours and labels. They cannot change what the genuine operator registered (domain, VPA, payload) and usually cannot hide every trace of the code underneath when the sticker does not cover it fully.

## Two independent kinds of evidence

### A. Image signals (overlay-specific)
| Signal | Meaning | Strength |
|---|---|---|
| `different_payloads` | two decodable codes in one view encode different destinations | strong |
| `multiple_codes` | two or more codes detected close together | strong-medium (some posters legitimately carry two codes) |
| `orphan_finders` | finder squares (the three big corner squares) that belong to no decoded code: the uncovered corner of a code underneath | medium |
| `undecodable_code` | a code is detected but cannot be read: often a partially covered one | medium-weak |

Finder-pattern detection: contours with at least two nested child levels, roughly square, compared against the decoded codes' corners (expanded by a margin). Explainable: each finding carries image coordinates.

### B. Destination checks (on every decoded payload)
| Payload | Checks |
|---|---|
| any | equals the **registered payload** if one is given (strongest possible check) |
| URL | not https; host is an IP address; `user@host` trick; punycode / non-ASCII host; known URL shortener; deep subdomain stacking; **registrable domain not in the expected list**; **lookalike** of an expected domain (edit distance ≤ 2 after a homoglyph skeleton: 0→o, 1→l, 5→s, rn→m, vv→w...); expected brand appearing as a subdomain of a different domain (`parkmobile.com.evil.net`) |
| UPI (`upi://pay?pa=...`) | payee VPA ≠ expected VPA; payee name ≠ expected name; VPA format; amount pre-filled (the "scan to receive" trap pairs a pay request with an amount) |
| other schemes | reported as-is (Wi-Fi config, tel, crypto addresses) |

## Risk level
`high` if any strong signal or a destination mismatch/lookalike; `medium` for medium signals or risky URL properties; `low` otherwise. The report always lists every signal with its reason, never only a score.

## Limits (stated in every report)
- A sticker that covers the genuine code completely and cleanly leaves **no image trace**; only destination checks catch it, and only if the expected destination is known.
- Image signals depend on resolution, blur and angle.
- No reputation lookups: the scanner is offline by design (no payload is sent anywhere).
