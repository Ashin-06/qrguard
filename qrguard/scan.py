"""One photo -> one report: image evidence of an overlay plus a destination check for every readable code."""
from qrguard import dest, image

LIMITS = [
    "A sticker that covers the genuine code completely leaves no image trace; only the destination check "
    "catches it, and only if the expected destination (domain, UPI ID or exact payload) is supplied.",
    "The 'module_texture_outside' signal can be triggered by bold signage text about one module thick; "
    "it is a low-severity lead, not evidence on its own.",
    "Offline by design: no reputation lookups, nothing is fetched or sent.",
    "Validated on synthetic photos only so far (see the benchmark); real-photo validation is pending.",
]
STRICT = {"different_payloads", "multiple_codes", "orphan_finders", "undecodable_code"}


def scan_image(img, expect: dict | None = None) -> dict:
    ov = image.overlay_signals(img)
    codes = []
    for c in ov["codes"]:
        entry = {k: c[k] for k in ("payload", "center", "side", "corners")}
        if c["payload"]:
            entry["destination"] = dest.analyse(c["payload"], expect)
        codes.append(entry)
    findings = list(ov["findings"])
    if not any(c["payload"] for c in codes):
        findings.append({"signal": "no_readable_code", "severity": "medium",
                         "detail": "no readable QR code found" + (" (a code is visible but unreadable)" if codes else "")})
    worst = max([dest.SEVERITY[f["severity"]] for f in findings] +
                [dest.SEVERITY[c["destination"]["risk"]] for c in codes if "destination" in c], default=0)
    return {"risk": {3: "high", 2: "medium"}.get(worst, "low"), "image_findings": findings, "codes": codes,
            "expected": expect or {}, "limits": LIMITS}


def scan_file(path: str, expect: dict | None = None) -> dict:
    return {"file": path, **scan_image(image.load(path), expect)}
