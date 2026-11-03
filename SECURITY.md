# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately, through GitHub's private vulnerability
reporting on this repository (Security → Report a vulnerability) or by contacting the
maintainer, [@Ashin-06](https://github.com/Ashin-06), directly. Do not open a public issue.

Include what you found, how to reproduce it and what an attacker could do with it. You should
get an acknowledgement within 5 working days. Please give us 90 days to fix an issue before
disclosing it, and don't test against anyone else's deployment.

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | yes |
| < 1.0 | no (research prototype releases) |

## Scope

In scope: the destination checks (payloads, URLs, lookalike domains, UPI payee and name), code
finding and overlay signals, the scan report, the checking API and its log, the container image
and the CI configuration. A crafted photo or payload that crashes the service, exhausts memory or
CPU, or hides a swapped destination that the README says is caught is in scope.

Out of scope: full covers checked without an expected destination (the README says these can't
be caught), real-photo accuracy (not validated yet), and findings that need an already-compromised
host or a leaked API key.

This project has **not** had an independent security review or penetration test, and its
methods have not been validated in court.
