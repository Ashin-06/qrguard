# Threat model

What the checking service protects, from whom, and what is still open. Written for the 1.0.0 code;
nobody independent has reviewed it.

## What it protects

| Asset | Where it lives |
|---|---|
| The risk verdict an inspector or payment app acts on | API responses and the `checks` table |
| Photos and payloads | request bodies only; not stored |
| Merchant expectations (registered UPI IDs, domains) | sent per request by the caller; not stored |
| API keys | callers hold the key; the service holds only SHA-256 hashes |

The costly failure is a missed swap: telling a customer or inspector a fraudster's code is fine.

## Trust boundaries

1. **Caller → service.** Photos are taken in the field and may be crafted to break decoders.
2. **Service → network.** None. Payloads are never fetched, resolved or sent anywhere, so a
   malicious link can't be triggered by checking it.

## Threats and what stops them

| Threat | Mitigation | Residual risk |
|---|---|---|
| A crafted image header claims gigapixels | OpenCV refuses to decode more than 50 megapixels; 20 MB body cap | Bugs in OpenCV's image decoders |
| A swapped UPI ID or lookalike domain passes | Exact-payload, payee, name and domain checks; lookalike, punycode, shortener, IP and `user@host` tricks are flagged | A full cover is caught only when the expected destination is supplied |
| A genuine code is flagged (false alarm) | Strict image signals had no false alarms on the synthetic benchmark; the texture lead is low severity | Real-photo rates are unmeasured |
| Checking a link triggers it | The service is offline: no fetch, no DNS, no reputation lookup | — |
| Someone reads the log or runs checks | API keys with roles; no CORS unless listed | Every `viewer` sees every check |
| Errors leak data | Validation errors don't echo input; unhandled errors return only a request ID | — |
| A verdict is disputed later | The log keeps the photo's or payload's SHA-256, the risk and the signals | The log is not signed or hash-chained |

## Not covered

- Real-photo validation (lab tasks L1-L3).
- Reputation data and depth cues for raised sticker edges.
- TLS (terminate it at the ingress).
