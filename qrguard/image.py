"""Find every QR code in a photo and the image signals of an overlay (method: research/02, part A)."""
import cv2
import numpy as np


def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)


def load(path: str) -> np.ndarray:
    """Read an image (works with non-ASCII Windows paths, unlike cv2.imread)."""
    img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"{path}: not a readable image")
    return img


def _codes_from(detector, gray, scale):
    try:
        ok, datas, points, straight = detector.detectAndDecodeMulti(gray)
    except cv2.error:
        return []
    if not ok or points is None:
        return []
    out = []
    straight = list(straight) if straight is not None else []
    for i, (data, pts) in enumerate(zip(datas, points)):
        st = straight[i] if i < len(straight) else None
        modules = int(st.shape[0]) if st is not None and getattr(st, "ndim", 0) == 2 and st.shape[0] >= 21 else None
        pts = np.asarray(pts, float).reshape(4, 2) / scale
        side = float(np.mean([np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)]))
        out.append({"payload": data or None, "corners": pts.round(1).tolist(), "center": pts.mean(0).round(1).tolist(),
                    "side": round(side, 1), "modules": modules if data else None})
    return out


def find_codes(img: np.ndarray) -> list[dict]:
    """All QR codes, from two detectors and two scales, merged; decoded payload or None."""
    gray = _gray(img)
    found = []
    for scale in (1.0, 2.0) if max(gray.shape) < 1200 else (1.0,):
        g = gray if scale == 1.0 else cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        for det in (cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco()):
            found += _codes_from(det, g, scale)
    merged = []
    for c in sorted(found, key=lambda c: c["payload"] is None):  # decoded ones first
        same = next((m for m in merged if np.hypot(*np.subtract(m["center"], c["center"])) < 0.3 * max(m["side"], c["side"])), None)
        if same is None:
            merged.append(c)
        elif same["payload"] is None and c["payload"]:
            same.update(c)
    return merged


def finder_patterns(img: np.ndarray) -> list[dict]:
    """Candidate finder squares: a dark square ring around a dark square (contour nesting depth 2, area ratio ~49:9)."""
    gray = _gray(img)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, hier = cv2.findContours(bw, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return []
    hier, out = hier[0], []
    for i, c in enumerate(contours):
        child = hier[i][2]
        grand = hier[child][2] if child >= 0 else -1
        if grand < 0:
            continue
        a_out, a_in = cv2.contourArea(c), cv2.contourArea(contours[grand])
        if a_out < 64 or a_in <= 0 or not 3.0 <= a_out / a_in <= 9.0:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if not 0.75 <= w / h <= 1.33 or len(cv2.approxPolyDP(c, 0.06 * cv2.arcLength(c, True), True)) != 4:
            continue
        cx, cy = x + w / 2, y + h / 2
        if any(abs(cx - f["center"][0]) < w / 3 and abs(cy - f["center"][1]) < h / 3 for f in out):
            continue  # same square found twice
        out.append({"center": [round(cx, 1), round(cy, 1)], "size": round((w + h) / 2, 1)})
    return out


def _rectilinear(mask: np.ndarray, tol_deg: float = 12.0) -> bool:
    """True if a blob's outline is almost all horizontal/vertical segments (QR modules), not curves/diagonals (text)."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return False
    poly = cv2.approxPolyDP(max(cnts, key=cv2.contourArea), 2.0, True).reshape(-1, 2).astype(float)
    total = aligned = 0.0
    for p, q in zip(poly, np.roll(poly, -1, axis=0)):
        dx, dy = abs(q[0] - p[0]), abs(q[1] - p[1])
        length = float(np.hypot(dx, dy))
        ang = np.degrees(np.arctan2(dy, dx))
        total += length
        aligned += length if ang <= tol_deg or ang >= 90 - tol_deg else 0.0
    return total > 0 and aligned / total >= 0.85


def module_texture(img: np.ndarray, code: dict, near: int = 5, far: int = 12) -> list[dict]:
    """Sides of a decoded code where QR-like block texture sits just beyond its quiet zone.

    The code is rectified to 10 px per module; bands `near`..`far` modules outside each edge are
    thresholded with the code's own Otsu level and opened with a 0.7-module kernel, which removes
    text strokes; only solid blobs with axis-aligned outlines are counted (letters have curves and
    diagonals). Many module-sized dark blobs there suggest another code peeking out from under
    a sticker. Bold signage can also trigger it: the benchmark measures that false-alarm rate.
    """
    m, M, pad = code.get("modules"), 10, far + 1
    if not m:
        return []
    gray = _gray(img)
    size = (m + 2 * pad) * M
    dst = np.float32([[pad, pad], [pad + m, pad], [pad + m, pad + m], [pad, pad + m]]) * M
    try:
        H = cv2.getPerspectiveTransform(np.float32(code["corners"]), dst)
        if not np.all(np.isfinite(H)):
            return []
        rect = cv2.warpPerspective(gray, H, (size, size), borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    except cv2.error:  # degenerate corners from a bad detection: no texture verdict, not a crash
        return []
    thr, _ = cv2.threshold(rect[pad * M:(pad + m) * M, pad * M:(pad + m) * M], 0, 255,
                           cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = cv2.morphologyEx((rect < thr).astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    lo, hi = (pad - near) * M, (pad + m + near) * M
    bands = {"top": dark[(pad - far) * M:lo, lo:hi], "bottom": dark[hi:(pad + m + far) * M, lo:hi],
             "left": dark[lo:hi, (pad - far) * M:lo], "right": dark[lo:hi, hi:(pad + m + far) * M]}
    out = []
    for side, band in bands.items():
        n, labels, stats, _ = cv2.connectedComponentsWithStats(band, connectivity=4)
        # QR modules merge into solid, axis-aligned rectilinear blocks at least a module wide; letters are not.
        blobs = 0
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if 60 <= area <= 3000 and min(w, h) >= 8 and area >= 0.55 * w * h:
                blobs += _rectilinear((labels[y:y + h, x:x + w] == i).astype(np.uint8))
        frac = float(band.mean())
        if blobs >= 4 and 0.1 <= frac <= 0.85:
            out.append({"side": side, "blobs": blobs, "dark_fraction": round(frac, 2)})
    return out


def _inside(pt, corners, margin):
    poly = np.asarray(corners, np.float32)
    return cv2.pointPolygonTest(poly, tuple(map(float, pt)), True) >= -margin


def overlay_signals(img: np.ndarray, codes: list[dict] | None = None) -> dict:
    codes = find_codes(img) if codes is None else codes
    findings = []
    decoded = [c for c in codes if c["payload"]]
    payloads = sorted({c["payload"] for c in decoded})
    if len(payloads) >= 2:
        findings.append({"signal": "different_payloads", "severity": "high",
                         "detail": f"{len(payloads)} codes in view encode different destinations"})
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if np.hypot(*np.subtract(a["center"], b["center"])) < 1.5 * max(a["side"], b["side"]):
                findings.append({"signal": "multiple_codes", "severity": "medium",
                                 "detail": f"two codes close together at {a['center']} and {b['center']}"})
    for c in codes:
        if not c["payload"]:
            findings.append({"signal": "undecodable_code", "severity": "medium",
                             "detail": f"a code at {c['center']} is detected but cannot be read (partly covered?)"})
    orphans = []
    if codes:
        for f in finder_patterns(img):
            if any(_inside(f["center"], c["corners"], 0.15 * c["side"]) for c in codes):
                continue
            near = min(np.hypot(*np.subtract(f["center"], c["center"])) / c["side"] for c in codes)
            if near <= 2.0 and f["size"] >= 0.08 * max(c["side"] for c in codes):
                orphans.append(f)
    for c in decoded:
        tex = module_texture(img, c)
        if tex:
            findings.append({"signal": "module_texture_outside", "severity": "low",  # bold signage text can mimic it
                             "detail": f"QR-like blocks just outside the code's margin ({', '.join(t['side'] for t in tex)}"
                                       f" side): possibly a covered code underneath", "sides": tex})
    if orphans:
        findings.append({"signal": "orphan_finders", "severity": "medium",
                         "detail": f"{len(orphans)} corner square(s) belonging to no readable code, e.g. at "
                                   f"{orphans[0]['center']}: possibly a covered code underneath",
                         "points": [o["center"] for o in orphans]})
    return {"codes": codes, "findings": findings}
