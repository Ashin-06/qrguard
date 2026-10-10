"""Synthetic photos of genuine codes and overlay stickers, for tests and the benchmark (research/03)."""
import cv2
import numpy as np


def qr_image(payload: str, module_px: int = 8, quiet: int = 4) -> np.ndarray:
    m = cv2.QRCodeEncoder.create().encode(payload)
    m = cv2.resize(m, None, fx=module_px, fy=module_px, interpolation=cv2.INTER_NEAREST)
    m = cv2.copyMakeBorder(m, quiet * module_px, quiet * module_px, quiet * module_px, quiet * module_px,
                           cv2.BORDER_CONSTANT, value=255)
    return cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)


def background(rng, h=900, w=900) -> np.ndarray:
    base = rng.integers(40, 220, 3)
    img = np.ones((h, w, 3), np.uint8) * base.astype(np.uint8)
    for _ in range(rng.integers(2, 6)):  # signage blocks and text-like lines
        x, y = rng.integers(0, w - 50), rng.integers(0, h - 30)
        col = tuple(int(v) for v in rng.integers(0, 255, 3))
        cv2.rectangle(img, (int(x), int(y)), (int(x + rng.integers(40, 300)), int(y + rng.integers(10, 60))), col, -1)
    noise = rng.normal(0, 4, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)


def paste(dst: np.ndarray, src: np.ndarray, x: int, y: int, size: int, angle: float = 0.0) -> None:
    """Paste `src` resized to size x size with its top-left near (x, y), rotated about its centre."""
    s = cv2.resize(src, (size, size), interpolation=cv2.INTER_AREA)
    pad = size  # room for rotation
    canvas = cv2.copyMakeBorder(s, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    mask = cv2.copyMakeBorder(np.full((size, size), 255, np.uint8), pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    M = cv2.getRotationMatrix2D((canvas.shape[1] / 2, canvas.shape[0] / 2), angle, 1.0)
    canvas = cv2.warpAffine(canvas, M, canvas.shape[1::-1], flags=cv2.INTER_LINEAR)
    mask = cv2.warpAffine(mask, M, mask.shape[1::-1], flags=cv2.INTER_NEAREST)
    x0, y0 = x - pad, y - pad
    h, w = dst.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(w, x0 + canvas.shape[1]), min(h, y0 + canvas.shape[0])
    if dx1 <= dx0 or dy1 <= dy0:
        return
    region = mask[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0] > 0
    dst[dy0:dy1, dx0:dx1][region] = canvas[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0][region]


def camera(rng, img: np.ndarray, strength: float = 1.0) -> np.ndarray:
    h, w = img.shape[:2]
    j = 0.03 * strength * min(h, w)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + rng.uniform(-j, j, src.shape).astype(np.float32)
    img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderMode=cv2.BORDER_REPLICATE)
    k = int(rng.choice([1, 3, 5])) if strength else 1
    if k > 1:
        img = cv2.GaussianBlur(img, (k, k), 0)
    img = np.clip(img.astype(float) * rng.uniform(0.85, 1.15) + rng.normal(0, 3 * strength, img.shape), 0, 255)
    ok, enc = cv2.imencode(".jpg", img.astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(70, 96))])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def payloads(rng, kind: str, n: int) -> tuple[str, str]:
    """(genuine, attacker) payload pair."""
    if kind == "upi":
        return (f"upi://pay?pa=store{n}@okaxis&pn=Store%20{n}",
                f"upi://pay?pa=98{rng.integers(10**7, 10**8)}@ybl&pn=Store%20{n}")
    return f"https://parkmobile.io/zone/{n}", f"https://parkmobi1e.io/zone/{n}"


def make_case(rng, tampered: bool, coverage: float = 1.0, kind: str = "url", strength: float = 1.0):
    """One synthetic photo. coverage = nominal fraction of the genuine code hidden by the sticker."""
    n = int(rng.integers(100, 9999))
    good, bad = payloads(rng, kind, n)
    img = background(rng)
    side = int(rng.integers(260, 360))
    x, y = int(rng.integers(150, 900 - side - 150)), int(rng.integers(150, 900 - side - 150))
    genuine = qr_image(good)
    total = genuine.shape[0] // 8            # modules incl. margins (qr_image uses 8 px modules)
    margin = (total - (cv2.QRCodeEncoder.create().encode(good).shape[0] - 4)) / 2
    paste(img, genuine, x, y, side, float(rng.uniform(-4, 4)))
    # Printed text around the code, as on real signage; bold variants are a deliberate false-alarm test.
    for label, ty in (("SCAN TO PAY", y + side + 30), (f"ZONE {n}", y - 20)):
        thick = int(rng.integers(2, 7))
        cv2.putText(img, label, (x + int(rng.integers(0, 40)), int(ty)), cv2.FONT_HERSHEY_SIMPLEX,
                    float(rng.uniform(0.8, 1.6)), (20, 20, 20), thick, cv2.LINE_AA)
    meta = {"tampered": tampered, "coverage": coverage if tampered else 0.0, "code_hidden": 0.0, "genuine": good,
            "attacker": bad if tampered else None, "kind": kind}
    if tampered:
        scale = 1.06 if coverage >= 1.0 else float(rng.uniform(0.95, 1.1))
        size = int(side * scale)
        shift = int(round((1 - coverage) * side))
        code_px, margin_px = side * (total - 2 * margin) / total, side * margin / total
        meta["code_hidden"] = round(1 - max(0.0, min(code_px, shift - margin_px)) / code_px, 3)
        dx, dy = [(shift, 0), (-shift, 0), (0, shift), (0, -shift)][int(rng.integers(0, 4))]
        cx, cy = x + side / 2 + dx, y + side / 2 + dy
        paste(img, qr_image(bad), int(cx - size / 2), int(cy - size / 2), size, float(rng.uniform(-6, 6)))
    return camera(rng, img, strength), meta
