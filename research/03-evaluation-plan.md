# 03 · Evaluation Plan

## Synthetic benchmark (built into the tool, reproducible from a seed) — run 10 Oct 2026, results in [04](04-results.md)
- Background: random coloured panel with texture and noise ("meter/shop board").
- Genuine code: random payload (URL or UPI), white quiet zone, random size and position.
- Tampered images: an attacker code with its own white margin pasted over the genuine one at a random **coverage** (fraction of the genuine code hidden, 30% to 100%), offset, small rotation and scale.
- Camera effects: Gaussian blur, noise, brightness, mild perspective.
- Labels: genuine / tampered, coverage, both payloads.

## Metrics
- Per signal and overall: detection rate (tampered flagged) and false-alarm rate (genuine flagged), with 95% Wilson intervals.
- Detection rate **by coverage band**, to show where image evidence runs out.
- Destination checks: rate of attacker payloads caught when the expected destination is known (should be ~100%; any miss is a bug).

## Real-world lab tasks (pending)
| ID | Task |
|---|---|
| L1 | Print genuine codes, print attacker stickers, photograph with 3 phones at 3 distances/angles, partial and full overlays |
| L2 | Photograph genuine public signage (no overlays) for the false-alarm rate in the wild |
| L3 | Compare with XQR for Merchants on the same photos |
| L4 | Phone app prototype adding parallax/LiDAR depth (a raised sticker edge) as a further signal |

## Ethics
Lab stickers are only placed on the project's own printed codes, never on public signage or real merchants' codes.
