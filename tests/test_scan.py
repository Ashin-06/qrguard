import json

import cv2
import numpy as np
import pytest

from qrguard import bench, cli, scan, synth


def test_full_overlay_caught_only_by_destination():
    rng = np.random.default_rng(21)
    img, meta = synth.make_case(rng, tampered=True, coverage=1.0, kind="upi")
    vpa = meta["genuine"].split("pa=")[1].split("&")[0]
    blind = scan.scan_image(img)                       # no expectation given
    told = scan.scan_image(img, {"vpa": vpa})          # merchant's registered UPI ID
    assert told["risk"] == "high"
    assert any(f["signal"] == "upi_payee_mismatch" for c in told["codes"] for f in c["destination"]["findings"])
    assert blind["risk"] != "high"                     # without an expectation a clean full cover is not caught
    assert told["limits"] == scan.LIMITS


def test_genuine_with_expectation_is_low():
    rng = np.random.default_rng(22)
    img, meta = synth.make_case(rng, tampered=False, kind="url")
    r = scan.scan_image(img, {"domains": ["parkmobile.io"]})
    assert r["risk"] == "low"  # only the low-severity texture lead may appear on a genuine photo
    assert {f["signal"] for f in r["image_findings"]} <= {"module_texture_outside"}
    assert r["codes"][0]["destination"]["risk"] == "low"


def test_no_code_in_photo():
    r = scan.scan_image(np.full((300, 300, 3), 127, np.uint8))
    assert r["risk"] == "medium" and r["image_findings"][0]["signal"] == "no_readable_code"


def test_wilson_interval():
    assert bench.wilson(0, 0) == (0.0, 1.0)
    lo, hi = bench.wilson(50, 100)
    assert lo < 0.5 < hi and 0.39 < lo < 0.41
    assert bench.wilson(10, 10)[1] == 1.0


def test_bench_is_reproducible():
    a = bench.run(n=2, seed=5, kinds=("url",), bands=(0.5,))
    b = bench.run(n=2, seed=5, kinds=("url",), bands=(0.5,))
    assert a == b and len(a["rows"]) == 2 and "| url | genuine |" in bench.to_markdown(a)


def test_cli_scan_and_errors(tmp_path, capsys):
    img = synth.qr_image("upi://pay?pa=9876543210@ybl&pn=Shop")
    p = tmp_path / "photo.png"
    cv2.imwrite(str(p), img)
    cli.main(["scan", str(p), "--expect-vpa", "shop@okaxis"])
    out = json.loads(capsys.readouterr().out)
    assert out["risk"] == "high" and out["file"] == str(p)
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"nope")
    with pytest.raises(SystemExit) as e:
        cli.main(["scan", str(bad)])
    assert e.value.code == 2 and "not a readable image" in capsys.readouterr().err
