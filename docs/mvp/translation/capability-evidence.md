# Translation capability evidence

Domain tests prove Transcript Manifest fingerprint validation, language normalization, source text/timing preservation, exact language-major coverage, one active adapter call, item failure isolation, retry reuse, replay/conflict, atomic JSON/SRT output, lazy NLLB language mapping and the public CLI.

Adjacent Graph Studio tests prove six ordered owner steps, multi-language command admission, policy rejection, production adapter registration and Translation Manifest verification. A deterministic adapter is a composition substitute only; it does not prove linguistic quality or NLLB availability.

Live evidence on 2026-08-02 used the public PowerShell launcher, the offline-cached `facebook/nllb-200-distilled-600M` model and CPU execution. One two-segment English Transcript Manifest produced Russian and Kazakh translation JSON/SRT artifacts, exact manifest coverage and a receipt with terminal class `COMPLETED` in 97.7 seconds. The identical command replayed as `DUPLICATE_COMPLETED` in 0.56 seconds without loading the model again.

A separate browser-admitted Graph Studio run `7e50a83f-2f81-4c97-9d3b-505161c51aa8` completed all six steps and produced RU+KK Translation Manifest SHA-256 `829c7f1508ac2fb5b0fbab4ca6b15d0c0014b0bf3acb724d4c8bb1b4f2145e5e`.

The source ASR had already misrecognized `trunks` as `prompts`; NLLB faithfully translated that wrong source. This proves why transcript review remains a separate quality gate and why executable completion is not linguistic certification.
