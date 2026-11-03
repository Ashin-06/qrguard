"""Reproducible synthetic benchmark (research/03): what image evidence and destination checks catch."""
import math
from urllib.parse import parse_qs, urlsplit

import numpy as np

from qrguard import dest, image, synth

BANDS = (0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0)
STRICT = {"different_payloads", "multiple_codes", "orphan_finders", "undecodable_code"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def _expect(genuine: str) -> dict:
    """What the operator or merchant would have registered for this code."""
    if genuine.startswith("upi://"):
        return {"vpa": parse_qs(urlsplit(genuine).query)["pa"][0]}
    return {"domains": [urlsplit(genuine).hostname]}


def _evaluate(img, meta) -> dict:
    ov = image.overlay_signals(img)
    sig = {f["signal"] for f in ov["findings"]}
    exp = _expect(meta["genuine"])
    risks = [dest.analyse(c["payload"], exp)["risk"] for c in ov["codes"] if c["payload"]]
    return {"strict": bool(sig & STRICT), "sensitive": bool(sig), "destination": "high" in risks,
            "unreadable": not risks}


def run(n: int = 40, seed: int = 1, kinds=("url", "upi"), bands=BANDS) -> dict:
    rng = np.random.default_rng(seed)
    rows = []
    for kind in kinds:
        cases = [("genuine", False, 0.0)] + [(f"{b:.2f}", True, b) for b in bands]
        for label, tampered, cov in cases:
            counts = {"strict": 0, "sensitive": 0, "destination": 0, "unreadable": 0, "either": 0}
            hidden = []
            for _ in range(n):
                img, meta = synth.make_case(rng, tampered, cov, kind)
                r = _evaluate(img, meta)
                for k in ("strict", "sensitive", "destination", "unreadable"):
                    counts[k] += r[k]
                counts["either"] += r["strict"] or r["destination"]
                hidden.append(meta["code_hidden"])
            rows.append({"kind": kind, "case": label, "tampered": tampered, "n": n,
                         "code_hidden_mean": round(float(np.mean(hidden)), 3),
                         **{k: {"k": v, "rate": round(v / n, 3), "ci95": wilson(v, n)} for k, v in counts.items()}})
    return {"seed": seed, "n_per_case": n, "rows": rows,
            "note": "genuine rows give false-alarm rates; tampered rows give detection rates"}


def to_markdown(res: dict) -> str:
    out = [f"Seed {res['seed']}, {res['n_per_case']} synthetic photos per row. Rates with 95% Wilson intervals.", "",
           "| Code | Case | Code hidden | Strict image | Sensitive image | Destination check | Strict OR destination | Unreadable |",
           "|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        cell = lambda k, r=r: f"{r[k]['rate']:.2f} ({r[k]['ci95'][0]:.2f}-{r[k]['ci95'][1]:.2f})"
        out.append(f"| {r['kind']} | {r['case']} | {r['code_hidden_mean']:.2f} | {cell('strict')} | {cell('sensitive')} | "
                   f"{cell('destination')} | {cell('either')} | {cell('unreadable')} |")
    return "\n".join(out) + "\n"
