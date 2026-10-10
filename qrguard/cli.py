"""qrguard command line. Offline: payloads are never fetched or sent anywhere."""
import argparse
import json
import sys
from pathlib import Path

from qrguard import bench, dest, scan


def _expect(a) -> dict:
    return {"payload": a.expect_payload, "domains": a.expect_domain or [], "vpa": a.expect_vpa,
            "name": a.expect_name}


def _expect_args(p):
    p.add_argument("--expect-domain", action="append", help="domain the code should point to (repeatable)")
    p.add_argument("--expect-vpa", help="UPI ID the payment should go to")
    p.add_argument("--expect-name", help="payee name the UPI code should show")
    p.add_argument("--expect-payload", help="exact registered payload (strongest check)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="qrguard", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a payload string (URL, upi://pay, ...)")
    c.add_argument("payload")
    _expect_args(c)
    sc = sub.add_parser("scan", help="scan a photo: overlay evidence + destination check of every code")
    sc.add_argument("photo", nargs="+")
    _expect_args(sc)
    b = sub.add_parser("bench", help="run the synthetic benchmark")
    b.add_argument("--n", type=int, default=40, help="photos per row (default 40)")
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--out", help="folder for results.json and results.md")
    a = p.parse_args(argv)
    try:
        if a.cmd == "check":
            print(json.dumps(dest.analyse(a.payload, _expect(a)), indent=2, ensure_ascii=False))
        elif a.cmd == "scan":
            reps = [scan.scan_file(f, _expect(a)) for f in a.photo]
            print(json.dumps(reps[0] if len(reps) == 1 else reps, indent=2, ensure_ascii=False))
        elif a.cmd == "bench":
            res = bench.run(a.n, a.seed)
            md = bench.to_markdown(res)
            if a.out:
                Path(a.out).mkdir(parents=True, exist_ok=True)
                (Path(a.out) / "results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
                (Path(a.out) / "results.md").write_text(md, encoding="utf-8")
            print(md)
    except (OSError, ValueError) as e:
        p.error(f"{a.cmd}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(main())
