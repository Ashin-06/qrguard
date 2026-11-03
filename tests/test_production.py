"""The checking API: settings, auth, limits, headers, metrics, health, the check log and migrations."""
import hashlib
import importlib
import json
import os
import struct
import subprocess
import sys
import zlib

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from qrguard import db, ops, synth

KEY = "qrguard_" + "x" * 40
HASHED = {f"sha256:{hashlib.sha256(KEY.encode()).hexdigest()}": {"user": "inspector-1", "role": "inspector"}}
GENUINE = "upi://pay?pa=sharmastores@okhdfcbank&pn=Sharma%20Stores&cu=INR"
SWAPPED = "upi://pay?pa=sharma.st0res@ybl&pn=Sharma%20Stores&cu=INR"


def boot(monkeypatch, **env):
    for k in [k for k in os.environ if k.startswith("QRGUARD_")]:
        monkeypatch.delenv(k)
    for k, v in env.items():
        monkeypatch.setenv(f"QRGUARD_{k}", v)
    import qrguard.api as api

    return importlib.reload(api)


def png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def huge_png(w: int, h: int) -> bytes:
    """A small but valid greyscale PNG of w x h pixels (zeros compress about 1000:1)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    rows = (b"\0" * (w + 1)) * h  # each row: filter byte + w grey pixels
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


@pytest.mark.parametrize("change, message", [
    ({"QRGUARD_API_KEYS": None}, "API keys"),
    ({"QRGUARD_DATABASE_URL": None}, "DATABASE_URL"),
    ({"QRGUARD_API_KEYS": json.dumps({KEY: {"user": "x", "role": "inspector"}})}, "sha256"),
    ({"QRGUARD_API_KEYS": json.dumps({"sha256:" + "0" * 64: {"user": "x", "role": "root"}})}, "roles"),
    ({"QRGUARD_CORS_ORIGINS": "*"}, "CORS"),
])
def test_production_settings_refused(change, message):
    env = {"QRGUARD_ENV": "production", "QRGUARD_API_KEYS": json.dumps(HASHED), "QRGUARD_DATABASE_URL": "sqlite://"}
    assert ops.load_settings(env).production
    env.update(change)
    with pytest.raises(ops.ConfigError, match=message):
        ops.load_settings({k: v for k, v in env.items() if v is not None})


def test_no_public_bind_and_readable_exit():
    with pytest.raises(ops.ConfigError, match="without API keys"):
        ops.load_settings({"QRGUARD_HOST": "0.0.0.0"})
    env = {k: v for k, v in os.environ.items() if not k.startswith("QRGUARD_")}
    r = subprocess.run([sys.executable, "-m", "qrguard", "serve", "--host", "0.0.0.0"], env=env,
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode != 0 and "without API keys" in r.stderr


def test_checks_are_logged_across_a_restart(monkeypatch, tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'checks.db'}"
    c = TestClient(boot(monkeypatch, DATABASE_URL=url).app)
    expect = {"vpa": "sharmastores@okhdfcbank", "name": "Sharma Stores"}
    good = c.post("/v1/check", json={"payload": GENUINE, "expect": expect, "label": "shop 12"}).json()
    bad = c.post("/v1/check", json={"payload": SWAPPED, "expect": expect, "label": "shop 12"}).json()
    assert good["risk"] == "low" and bad["risk"] == "high"
    assert any(f["signal"] == "upi_payee_mismatch" for f in bad["findings"])
    phish = c.post("/v1/check", json={"payload": "https://parkmobi1e.io/pay", "expect": {"domains": ["parkmobile.io"]}})
    assert phish.json()["risk"] == "high"

    photo = png(synth.qr_image(SWAPPED))
    r = c.post("/v1/scan", content=photo, params={"expect_vpa": "sharmastores@okhdfcbank", "label": "meter 7"})
    s = r.json()
    assert r.status_code == 200 and s["risk"] == "high" and s["input_sha256"] == hashlib.sha256(photo).hexdigest()
    assert s["codes"][0]["payload"] == SWAPPED

    c = TestClient(boot(monkeypatch, DATABASE_URL=url).app)  # restart
    got = c.get(f"/v1/checks/{s['check_id']}").json()
    assert got["kind"] == "photo" and got["risk"] == "high" and "upi_payee_mismatch" in got["signals"]
    assert "sharma.st0res" not in json.dumps(got)  # payloads are not stored
    assert len(c.get("/v1/checks").json()["checks"]) == 4
    assert {x["risk"] for x in c.get("/v1/checks", params={"risk": "high"}).json()["checks"]} == {"high"}
    assert c.get("/v1/checks/nope").status_code == 404


def test_bad_photos_are_refused(monkeypatch):
    c = TestClient(boot(monkeypatch).app)
    assert c.post("/v1/scan", content=b"").status_code == 422
    assert c.post("/v1/scan", content=b"not an image").status_code == 422
    big = huge_png(8000, 7500)  # a valid 60-megapixel image in under 100 KB
    assert len(big) < 100_000
    r = c.post("/v1/scan", content=big)
    assert r.status_code == 422 and "megapixels" in r.text
    blank = c.post("/v1/scan", content=png(np.full((200, 200, 3), 255, np.uint8))).json()
    assert any(f["signal"] == "no_readable_code" for f in blank["image_findings"])


def test_roles_and_metrics(monkeypatch):
    keys = {"k-in": {"user": "asha", "role": "inspector"}, "k-view": {"user": "vic", "role": "viewer"},
            "k-mon": {"user": "prom", "role": "monitor"}}
    c = TestClient(boot(monkeypatch, API_KEYS=json.dumps(keys)).app)
    body = {"payload": GENUINE}
    assert c.post("/v1/check", json=body).status_code == 401
    assert c.post("/v1/check", json=body, headers={"x-api-key": "wrong"}).status_code == 401
    assert c.post("/v1/check", json=body, headers={"x-api-key": "k-view"}).status_code == 403
    assert c.post("/v1/check", json=body, headers={"x-api-key": "k-in"}).status_code == 200
    log = c.get("/v1/checks", headers={"authorization": "Bearer k-view"}).json()["checks"]
    assert log[0]["requested_by"] == "asha"
    assert c.get("/metrics", headers={"x-api-key": "k-in"}).status_code == 403
    m = c.get("/metrics", headers={"x-api-key": "k-mon"})
    assert m.status_code == 200 and "qrguard_decisions_total{decision=" in m.text


def test_limits_headers_errors_and_health(monkeypatch):
    c = TestClient(boot(monkeypatch, RATE_LIMIT="3").app)
    codes = [c.get("/v1/checks").status_code for _ in range(5)]
    assert codes[:3] == [200] * 3 and codes[3:] == [429, 429]
    api = boot(monkeypatch, MAX_BODY_BYTES="500")

    @api.app.get("/boom")
    def boom():
        raise RuntimeError("secret detail: merchant key 0xdeadbeef")

    c = TestClient(api.app)
    assert c.post("/v1/check", json={"payload": "x" * 600}).status_code == 413

    def chunks():
        for _ in range(10):
            yield b"a" * 100

    assert c.post("/v1/scan", content=chunks()).status_code == 413
    crash = c.get("/boom")
    assert crash.status_code == 500 and "deadbeef" not in crash.text and crash.json()["request_id"]
    bad = c.post("/v1/check", json={"payload": ["SECRETVPA"]})
    assert bad.status_code == 422 and "SECRETVPA" not in bad.text
    r = c.get("/v1/checks", headers={"x-request-id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123" and r.headers["content-security-policy"] == ops.API_CSP
    assert c.get("/healthz").json() == {"status": "ok"}
    assert c.get("/readyz").json()["checks"] == {"database": True}
    monkeypatch.setattr(api.engine, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert c.get("/readyz").status_code == 503


def test_json_logs_carry_request_ids(capsys):
    ops.setup_logging("INFO")
    token = ops.request_id.set("rid-1")
    ops.log.info("hello")
    ops.request_id.reset(token)
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["request_id"] == "rid-1"


def test_migrations_apply_once(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    eng = db.engine(url)
    assert db.migrate(eng) == ["001_init.sql"] and db.migrate(eng) == []
    with eng.connect() as c:
        tables = {r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))}
    assert {"checks", "schema_migrations"} <= tables
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("QRGUARD_")}, "QRGUARD_DATABASE_URL": url}
    out = subprocess.run([sys.executable, "-m", "qrguard", "migrate"], env=env, capture_output=True, text=True,
                         timeout=120, check=False)
    assert out.returncode == 0 and "up to date" in out.stdout


def test_decode_limit_in_a_fresh_process(tmp_path):
    """The import order `qrguard serve` uses: the CLI loads image.py (and OpenCV) before the API."""
    (tmp_path / "big.png").write_bytes(huge_png(8000, 7500))
    (tmp_path / "ok.png").write_bytes(huge_png(4000, 3000))
    code = ("import sys, numpy as np; import qrguard.cli; import cv2\n"
            "for f in sys.argv[1:]:\n"
            "    try:\n"
            "        im = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)\n"
            "    except cv2.error:\n"
            "        im = None\n"
            "    print('decoded' if im is not None else 'refused')\n")
    env = {k: v for k, v in os.environ.items() if k != "OPENCV_IO_MAX_IMAGE_PIXELS"}
    out = subprocess.run([sys.executable, "-c", code, str(tmp_path / "big.png"), str(tmp_path / "ok.png")],
                         env=env, capture_output=True, text=True, timeout=120, check=False)
    assert out.stdout.split() == ["refused", "decoded"], out.stderr
