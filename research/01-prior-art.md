# 01 · Prior Art and the Gap

Searched 10 Oct 2026 (web standard + extended, arXiv, GitHub). **Correction to the earlier shortlist:** physical-overlay detection is not untouched; one early prototype exists (below).

## Closest work
| Work | Approach | What it does not do |
|---|---|---|
| [XQR for Merchants](https://github.com/Fio-achsha4/XQR-FOR-MERCHANTS) (GitHub, created 4 Oct 2026, research prototype) | YOLOv8 QR localisation, error-level analysis, quiet-zone violation check, noise variance, MobileNetV3, Flask app; outputs an anomaly score for UPI payment stickers | never checks **where the payment goes**; score is "not a probability of fraud"; no measured detection or false-alarm rates |
| [Trad & Chehab, arXiv:2505.03451](https://arxiv.org/abs/2505.03451) (2025, rev. 2026) | ML (XGBoost, AUC 0.91) on QR **module pixels** to predict phishing without decoding | digital codes; not physical overlays |
| [QRiS, arXiv:2510.17175](https://arxiv.org/pdf/2510.17175) (2025) | structural features of the QR for quishing detection | same |
| [ALFA, arXiv:2601.06768](https://arxiv.org/pdf/2601.06768) | safe-by-design mitigation for "fancy" QR codes | design change, needs new codes |
| Barron & Sharma, *Quashing quishing attacks using self-authenticating dual-modulated QR codes*, IEEE S&P 2025 (cited by ALFA) | codes that authenticate themselves | needs new codes printed; does not help existing ones |
| [Picard et al., Counterfeit detection with QR codes, DocEng 2021](https://www.researchgate.net/publication/353948106_Counterfeit_detection_with_QR_codes) | copy-detection patterns | anti-copying of genuine codes, not overlays |
| Consumer guidance ([QRCodeKIT](https://qrcodekit.com/news/qr-code-sticker-overlay-fraud/), [Hoxhunt](https://hoxhunt.com/blog/quishing), parking-scam reports) | "look for raised, peeling, misaligned stickers"; scan analytics drop-offs for dynamic codes | manual |
| URL-reputation QR scanners | check the decoded URL against threat feeds | blind to UPI payees and to new, unlisted domains |

## The attack in the wild
- **Parking meters / EV chargers (US, UK):** fake "scan to pay" stickers sending users to card-harvesting sites ([Tom's Guide](https://www.tomsguide.com/news/texas-parking-meter-qr-scam), [Carwow](https://www.carwow.co.uk/news/8652/how-to-spot-qr-code-parking-scams), UK parish council warnings).
- **UPI payment stickers (India):** fraudsters paste their own UPI QR over a shop's; customers' payments go to the fraudster. Hyderabad vendor case and ~2,000 complaints/month reported by Hyderabad cyber experts ([Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/hyderabad-cyber-scam-targeting-small-businesses-1812451)); Khajuraho (MP) ring that swapped codes at 10 shops, caught on CCTV ([Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fmadhya-pradesh%2Fqr-code-scam-fraudsters-swap-scanners-overnight-with-fake-ones-in-mps-khajuraho-3352633)). Official advice: check the payee name the app shows ([Bank of Maharashtra](https://bankofmaharashtra.bank.in/blogs/use-qr-upi-safely-cybersecurity-guide)); report on cybercrime.gov.in / 1930.

## Gap
1. No tool combines **image evidence of an overlay** with **verification of the destination** (payee VPA, domain, exact registered payload). The destination is what the attack changes, and it can be checked even when the sticker is visually perfect.
2. No published **measurement** of what image analysis can and cannot catch: a sticker that covers the original completely leaves no trace of the underlying code.

## Contribution
An offline, explainable scanner (overlay-specific image signals + destination checks against what the merchant or operator registered) and a reproducible synthetic benchmark that measures each signal's detection and false-alarm rates.
