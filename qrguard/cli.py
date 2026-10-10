"""qrguard command line. Offline: payloads are never fetched or sent anywhere."""
import argparse
import json
import sys

from qrguard import dest


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
    a = p.parse_args(argv)
    if a.cmd == "check":
        print(json.dumps(dest.analyse(a.payload, _expect(a)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
