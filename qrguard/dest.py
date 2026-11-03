"""Check where a QR payload actually sends the user (method: research/02, part B).

Offline and deterministic: nothing is fetched or resolved. Each finding is
{"signal", "severity", "detail"}; severity is info < low < medium < high.
"""
import ipaddress
import re
import unicodedata
from urllib.parse import parse_qsl, unquote, urlsplit

SEVERITY = {"info": 0, "low": 1, "medium": 2, "high": 3}

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly", "rebrand.ly", "cutt.ly",
              "shorturl.at", "tiny.cc", "rb.gy", "t.ly", "bl.ink", "lnkd.in", "s.id", "v.gd", "qrco.de", "short.io"}
# ponytail: tiny public-suffix subset; use the full Public Suffix List if registrable-domain errors show up.
MULTI_SUFFIXES = {"co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au", "gov.au", "co.in", "net.in",
                  "org.in", "gov.in", "ac.in", "co.jp", "co.nz", "com.br", "com.mx", "co.za", "com.sg", "com.cn",
                  "co.kr", "com.tr", "com.ar"}
# Characters and pairs attackers swap for lookalikes; applied to both sides before comparing.
_SKELETON = [("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"), ("7", "t"), ("-", "")]
_VPA = re.compile(r"^[A-Za-z0-9._-]{2,256}@[A-Za-z][A-Za-z0-9.-]{1,64}$")


def _f(signal, severity, detail):
    return {"signal": signal, "severity": severity, "detail": detail}


def registrable(host: str) -> str:
    labels = host.rstrip(".").split(".")
    n = 3 if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_SUFFIXES else 2
    return ".".join(labels[-n:])


def skeleton(s: str) -> str:
    s = unicodedata.normalize("NFKC", s.lower())
    for a, b in _SKELETON:
        s = s.replace(a, b)
    return s


def osa_distance(a: str, b: str) -> int:
    """Edit distance counting adjacent transpositions as one edit (optimal string alignment)."""
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def _unicode_host(host: str) -> str:
    try:
        return host.encode("ascii").decode("idna")
    except (UnicodeError, ValueError):
        return host


def check_url(url: str, expected_domains=()) -> list[dict]:
    out = []
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower().rstrip(".")  # "example.com." is the same host
        _ = parts.port  # Access validates numeric syntax and the port range.
    except ValueError as e:
        return [_f("malformed_url", "high", f"URL cannot be parsed: {e}")]
    if not host:
        return [_f("malformed_url", "high", "URL has no host")]
    if parts.scheme != "https":
        out.append(_f("not_https", "medium", f"scheme is {parts.scheme!r}, not https"))
    if parts.username is not None or "@" in parts.netloc:
        shown = unquote(parts.netloc.rsplit("@", 1)[0])
        out.append(_f("userinfo_trick", "high", f"URL shows {shown!r} before '@' but opens {host}"))
    try:
        ipaddress.ip_address(host.strip("[]"))
        out.append(_f("ip_address_host", "high", f"host is a raw IP address ({host})"))
        return out
    except ValueError:
        pass
    shown = _unicode_host(host)
    if any(label.startswith("xn--") for label in host.split(".")) or not host.isascii():
        out.append(_f("internationalised_domain", "high" if expected_domains else "medium",
                      f"domain uses non-ASCII characters: {shown} (can imitate a familiar name)"))
    reg = registrable(host)
    if reg in SHORTENERS or host in SHORTENERS:
        out.append(_f("redirect_service", "medium", f"{reg} is a link shortener/redirect: the real destination is hidden"))
    if host.count(".") >= 4:
        out.append(_f("deep_subdomain", "low", f"{host} has {host.count('.') + 1} labels"))
    exp = [e.lower().strip(".") for e in expected_domains]
    if exp:
        if any(host == e or host.endswith("." + e) for e in exp):
            out.append(_f("expected_domain", "info", f"{host} is within an expected domain"))
        else:
            reg_s = skeleton(_unicode_host(reg))
            look = [e for e in exp if skeleton(e) == reg_s or osa_distance(reg_s, skeleton(e)) <= 2]
            brand = [e for e in exp if e.split(".")[0] in host.split(".")[:-2] or e in host]
            if look:
                out.append(_f("lookalike_domain", "high", f"{reg} looks like expected {look[0]} but is a different domain"))
            elif brand:
                out.append(_f("brand_in_subdomain", "high",
                              f"{host} contains {brand[0]!r} but the real domain is {reg}"))
            else:
                out.append(_f("unexpected_domain", "high", f"{reg} is not one of the expected domains {exp}"))
    return out


def check_upi(payload: str, expected_vpa: str | None = None, expected_name: str | None = None) -> list[dict]:
    try:
        parts = urlsplit(payload.strip())
    except ValueError as e:
        return [_f("malformed_upi", "high", f"UPI payload cannot be parsed: {e}")]
    q, duplicates = {}, set()
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key = key.lower()
        if key in q:
            duplicates.add(key)
        q[key] = value
    if duplicates:
        return [_f("upi_duplicate_parameter", "high",
                   f"UPI parameter {key!r} occurs more than once; payment details are ambiguous")
                for key in sorted(duplicates)]
    out, pa = [], q.get("pa", "").strip()
    if not pa:
        return [_f("upi_no_payee", "high", "UPI payload has no payee address (pa)")]
    if not _VPA.match(pa):
        out.append(_f("upi_bad_vpa", "high", f"payee address {pa!r} is not a valid UPI ID"))
    if expected_vpa:
        if pa.lower() == expected_vpa.lower().strip():
            out.append(_f("upi_expected_payee", "info", f"payee {pa} is the expected UPI ID"))
        else:
            out.append(_f("upi_payee_mismatch", "high", f"payee {pa} is not the expected {expected_vpa}"))
    pn = q.get("pn", "")
    if expected_name and pn and _norm_name(pn) != _norm_name(expected_name):
        out.append(_f("upi_name_mismatch", "medium", f"payee name {pn!r} differs from expected {expected_name!r}"))
    if q.get("am"):
        out.append(_f("upi_amount_prefilled", "medium",
                      f"amount {q['am']} is pre-filled: scanning pays it (a 'scan to receive money' trap uses this)"))
    return out


def _norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", s).lower())


def classify(payload: str) -> str:
    p = payload.strip().lower()
    if p.startswith(("http://", "https://")):
        return "url"
    if p.startswith("upi://"):
        return "upi"
    if re.match(r"^[a-z][a-z0-9+.-]*:", p):
        return "other_scheme"
    return "text"


def analyse(payload: str, expect: dict | None = None) -> dict:
    """expect: {"payload": exact string, "domains": [...], "vpa": str, "name": str} (all optional)."""
    expect = expect or {}
    kind, findings = classify(payload), []
    if expect.get("payload") is not None:
        same = payload == expect["payload"]
        findings.append(_f("registered_payload", "info" if same else "high",
                           "matches the registered payload exactly" if same else "differs from the registered payload"))
    if kind == "url":
        findings += check_url(payload, expect.get("domains") or ())
    elif kind == "upi":
        findings += check_upi(payload, expect.get("vpa"), expect.get("name"))
    else:
        findings.append(_f(kind, "info", f"payload is {kind.replace('_', ' ')}: {payload[:60]!r}"))
        if (expect.get("domains") or expect.get("vpa")) and expect.get("payload") is None:
            findings.append(_f("unexpected_type", "high", f"expected a link or UPI payment, got {kind.replace('_', ' ')}"))
    return {"type": kind, "payload": payload, "findings": findings, "risk": risk(findings)}


def risk(findings: list[dict]) -> str:
    worst = max((SEVERITY[f["severity"]] for f in findings), default=0)
    return {3: "high", 2: "medium"}.get(worst, "low")
