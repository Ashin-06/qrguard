# 04 · Results: Synthetic Benchmark (10 Oct 2026)

`qrguard bench --n 60 --seed 1 --out results` · 960 photos (URL and UPI codes; 60 genuine + 60 per coverage level each) · 7 min on a laptop. Full table with 95% Wilson intervals: [`results/results.md`](../results/results.md); raw counts: `results/results.json`.

## Summary
| Share of the genuine code hidden | Strict image signals | Sensitive (+ texture) | Destination check* | Strict OR destination |
|---|---|---|---|---|
| none: false-alarm rate on genuine photos | **0%** (0-6%) | 8% URL, 15% UPI | **0%** | **0%** |
| ~50% | 100% | 100% | 97-100% | **100%** |
| ~65% | 98-100% | 100% | 98-100% | **100%** |
| ~80% | 12% URL, 33% UPI | 93-98% | 100% | **100%** |
| ~86% | 0% | 52% URL, 92% UPI | 100% | **100%** |
| ~93% | 0% | 22% URL, 47% UPI | 100% | **100%** |
| 100% (full cover) | 0% | 10-23% (= its false-alarm level) | 100% | **100%** |

\* The destination check assumes the expected destination (merchant UPI ID, operator domain) is supplied.

## What this shows
1. **Image evidence fades with coverage.** Strict signals (stacked codes, leftover corner squares, unreadable code, different payloads) are reliable up to about two-thirds of the genuine code hidden, with no false alarms. Beyond ~80% hidden they see nothing, because nothing of the genuine code's structure remains visible.
2. **The texture lead extends the range but costs false alarms.** It still flags most stickers hiding 80-86% of the code, but it fires on 8-15% of genuine photos with bold signage text next to the code. At full cover its hit rate equals its false-alarm rate: no real signal. Hence it is a low-severity lead only.
3. **The destination check carries the full-cover case.** A clean full cover is invisible to image analysis; checking the payee or domain catches it every time. Together, strict image signals and the destination check caught every tampered photo, with no false alarms on genuine ones.
4. **Neither is enough alone.** Image signals alone miss most heavy covers. The destination check alone misses the 2-3% of partial overlays where no code is readable (the image signals caught those).

## Threats to validity
- **Synthetic photos**: real stickers add gloss, curvature, shadows, wear and different printers; real signage has more varied text and logos. Real-photo validation is lab task L1/L2.
- **The destination result is nearly tautological here**: the synthetic attacker always encodes a different payee or a lookalike domain. In the field, the hard part is having the expected destination at scan time (merchant registry, operator domain list, payment-app context), not the check itself.
- One attacker style (same-size printed sticker); attackers who replace the whole plate or print on a matching background are out of scope for image signals.
- Coverage is applied along one axis; diagonal offsets and partial rotations differ.
