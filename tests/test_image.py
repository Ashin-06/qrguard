import cv2
import numpy as np

from qrguard import image, synth

STRICT = {"different_payloads", "multiple_codes", "orphan_finders", "undecodable_code"}


def signals(img):
    return {f["signal"] for f in image.overlay_signals(img)["findings"]}


def test_clean_code_decodes_without_strict_signals():
    rng = np.random.default_rng(11)
    for _ in range(8):
        img, meta = synth.make_case(rng, tampered=False)
        codes = image.find_codes(img)
        assert [c["payload"] for c in codes] == [meta["genuine"]]
        assert codes[0]["modules"] and codes[0]["modules"] >= 21
        assert not signals(img) & STRICT


def test_half_covered_code_is_flagged():
    rng = np.random.default_rng(12)
    flagged = 0
    for _ in range(8):
        img, meta = synth.make_case(rng, tampered=True, coverage=0.5)
        flagged += bool(signals(img) & STRICT)
    assert flagged >= 7


def test_full_overlay_leaves_attacker_payload_only():
    # The limit the benchmark quantifies: a full cover leaves only the attacker's code to read.
    rng = np.random.default_rng(13)
    img, meta = synth.make_case(rng, tampered=True, coverage=1.0)
    assert [c["payload"] for c in image.find_codes(img)] == [meta["attacker"]]


def test_two_different_codes_side_by_side():
    canvas = np.full((500, 1000, 3), 200, np.uint8)
    synth.paste(canvas, synth.qr_image("https://parkmobile.io/zone/1"), 60, 60, 300)
    synth.paste(canvas, synth.qr_image("https://evil.example/zone/1"), 330, 60, 300)  # margins touching
    s = signals(canvas)
    assert "different_payloads" in s and "multiple_codes" in s
    far = np.full((500, 1300, 3), 200, np.uint8)  # far apart (a poster with two codes): different, not "close"
    synth.paste(far, synth.qr_image("https://parkmobile.io/zone/1"), 60, 60, 300)
    synth.paste(far, synth.qr_image("https://evil.example/zone/1"), 900, 60, 300)
    assert signals(far) == {"different_payloads"}


def test_rectilinear_blob_test():
    square = np.zeros((40, 40), np.uint8)
    square[5:35, 5:35] = 1
    disc = np.zeros((40, 40), np.uint8)
    cv2.circle(disc, (20, 20), 15, 1, -1)
    assert image._rectilinear(square) and not image._rectilinear(disc)


def test_load_rejects_non_image(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(b"not an image")
    try:
        image.load(str(p))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_rgba_and_degenerate_corners_do_not_crash():
    rgba = cv2.cvtColor(synth.qr_image("https://parkmobile.io/zone/7"), cv2.COLOR_BGR2BGRA)
    assert [c["payload"] for c in image.find_codes(rgba)] == ["https://parkmobile.io/zone/7"]
    assert image.overlay_signals(rgba)["findings"] == []
    flat = {"payload": "x", "modules": 25, "corners": [[10, 10], [20, 20], [30, 30], [40, 40]],
            "center": [25, 25], "side": 14.0}
    assert image.module_texture(rgba, flat) == []
