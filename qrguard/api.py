"""Checking service: payload and photo checks behind an API, with a log of every check.

    POST /v1/check            a decoded payload (URL, upi://pay, ...) against what was registered [check]
    POST /v1/scan             a photo of a QR code (body = the image): overlay evidence + destination [check]
    GET  /v1/checks[/{id}]    the check log: who checked which input (by SHA-256), the risk found [read]
    GET  /healthz, /readyz, /metrics

Offline by design: payloads are never fetched, resolved or sent anywhere. Photos and payloads are
not stored; each check keeps the SHA-256 of its input, the risk, the signals raised and who asked.
Callers send an API key whose role decides the permissions in brackets; settings come from
QRGUARD_* variables (see ops.py and docs/runbook.md).

    python -m qrguard serve
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import cv2  # the decode limit is set in qrguard/__init__.py, before OpenCV first loads
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from . import db, dest, ops, scan

settings = ops.load_settings()
ops.setup_logging(settings.log_level)
engine = db.connect(settings.database_url)
_lock = threading.Lock()

app = FastAPI(title="QRGuard checking service", version="1.0.0")
ops.install(app, settings, {"database": lambda: engine.connect().close()})


class Expectation(BaseModel):
    payload: Optional[str] = Field(None, max_length=4096, description="the exact registered payload (strongest check)")
    domains: List[str] = Field(default_factory=list, max_length=50, description="domains the code should point to")
    vpa: Optional[str] = Field(None, max_length=255, description="the UPI ID payments should go to")
    name: Optional[str] = Field(None, max_length=200, description="the payee name the UPI code should show")


class CheckRequest(BaseModel):
    payload: str = Field(..., min_length=1, max_length=4096)
    expect: Expectation = Field(default_factory=Expectation)
    label: str = Field("", max_length=200, description="site, meter or merchant reference, for the log")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _log(ident: dict, kind: str, label: str, sha: str, risk: str, signals: List[str]) -> str:
    cid = uuid.uuid4().hex
    with _lock, engine.begin() as c:
        c.execute(text("INSERT INTO checks VALUES (:i, :t, :u, :k, :l, :h, :r, :s)"),
                  {"i": cid, "t": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                   "u": ident["user"] or "demo", "k": kind, "l": label, "h": sha, "r": risk,
                   "s": json.dumps(sorted(set(signals)))})
    ops.DECISIONS.labels(decision=f"risk_{risk}").inc()
    return cid


@app.post("/v1/check")
def check(req: CheckRequest, ident: dict = Depends(ops.require("check"))) -> Dict[str, Any]:
    res = dest.analyse(req.payload, req.expect.model_dump())
    signals = [f["signal"] for f in res["findings"] if f["severity"] != "info"]
    sha = _sha(req.payload.encode())
    return {"check_id": _log(ident, "payload", req.label, sha, res["risk"], signals), "input_sha256": sha, **res}


@app.post("/v1/scan")
async def scan_photo(request: Request, label: str = Query("", max_length=200),
                     expect_payload: Optional[str] = Query(None, max_length=4096),
                     expect_domain: List[str] = Query([], max_length=50),
                     expect_vpa: Optional[str] = Query(None, max_length=255),
                     expect_name: Optional[str] = Query(None, max_length=200),
                     ident: dict = Depends(ops.require("check"))) -> Dict[str, Any]:
    data = await request.body()
    try:
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) if data else None
    except cv2.error:  # OpenCV raises, rather than returning None, for images over the pixel limit
        img = None
    if img is None:
        raise HTTPException(422, "send a photo (JPEG, PNG or WebP, at most 50 megapixels) as the request body")
    expect = {"payload": expect_payload, "domains": expect_domain, "vpa": expect_vpa, "name": expect_name}
    res = scan.scan_image(img, expect)
    signals = [f["signal"] for f in res["image_findings"] if f["severity"] != "info"]
    signals += [f["signal"] for c in res["codes"] for f in c.get("destination", {}).get("findings", [])
                if f["severity"] != "info"]
    sha = _sha(data)
    return {"check_id": _log(ident, "photo", label, sha, res["risk"], signals), "input_sha256": sha, **res}


def _row(r) -> Dict[str, Any]:
    d = dict(r)
    if "signals" in d:
        d["signals"] = json.loads(d["signals"])
    return d


@app.get("/v1/checks", dependencies=[Depends(ops.require("read"))])
def list_checks(limit: int = Query(50, ge=1, le=1000), risk: Optional[str] = Query(None, pattern="^(low|medium|high)$")
                ) -> Dict[str, Any]:
    sql, args = "SELECT * FROM checks", {"n": limit}
    if risk:
        sql, args["r"] = sql + " WHERE risk = :r", risk
    with engine.connect() as c:
        rows = c.execute(text(sql + " ORDER BY created_at DESC LIMIT :n"), args).mappings().all()
    return {"checks": [_row(r) for r in rows]}


@app.get("/v1/checks/{check_id}", dependencies=[Depends(ops.require("read"))])
def get_check(check_id: str) -> Dict[str, Any]:
    with engine.connect() as c:
        r = c.execute(text("SELECT * FROM checks WHERE id = :i"), {"i": check_id[:64]}).mappings().first()
    if r is None:
        raise HTTPException(404, "check not found")
    return _row(r)
