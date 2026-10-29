# Project progress

Part 1 — Splash screen: complete (commit `fd4a697`).
Changed: Added the lecture-style splash activity, launcher layout, theme color, and Android documentation.
Tests: Current Android verification: 21 unit tests passed and assembleDebug succeeded; instrumentation was not run (adb unavailable).

Part 2 — Navigation Component: complete (commit `e402e70`).
Changed: Added the fragment navigation graph, toolbar integration, destinations, arguments, and navigation tests.
Tests: Current Android verification: 21 unit tests passed and assembleDebug succeeded; instrumentation was not run (adb unavailable).

Part 3 — Menu polish: complete (commit `4d42d83`).
Changed: Added vector menu icons, an always-visible watchlist action, and About/Exit actions through MenuProvider.
Tests: Current Android verification: 21 unit tests passed and assembleDebug succeeded; instrumentation was not run (adb unavailable).

Part 4 — Synthetic assistant dataset: complete (commit `467e6da`).
Changed: Generated 4,030 synthetic questions with family-based splits; kept the 91-row AI-written held-out file separate.
Tests: Generator reported 2,900/433/697 rows across 48/8/12 families; dataset tests 3 passed; Ruff clean.

Part 5 — Intent model: complete (commit `fa7c0cd`).
Changed: Trained and evaluated word/character TF-IDF intent models and saved ignored model artifacts and metadata.
Tests: Selected calibrated LinearSVC at threshold 0.4200; synthetic test 0.6026 accuracy/0.5652 macro-F1, held-out 0.7912/0.8115.

Part 6 — Entity linking and deterministic answers: complete (commit `4003a84`).
Changed: Added the fitted product linker, store/county resolution, deterministic answers, and unknown/out-of-snapshot handling.
Tests: Entity accuracy 0.7722 validation, 0.9492 synthetic test, 0.6630 AI-written held-out; two unknown held-out entities resolved correctly.

Part 7 — Trained listing matcher: complete (commit `9a0e078`).
Changed: Added synthetic-bootstrap LogisticRegression pair matcher, threshold fallback, evaluation, and regenerated label suggestions.
Tests: Synthetic 77-pair evaluation (63 positive): model P/R/F1 1.0000/1.0000/1.0000; old threshold P/R/F1 0.9844/1.0000/0.9921.

Part 8 — Trained model API: complete (commit `3d99725`).
Changed: Added trained assistant/model-info endpoints and optional predicted listing categories; removed the pretrained-service code, dependency, environment switches, and tool-schema wiring.
Tests: Final backend suite 128 passed; Ruff clean. Tracked active-repository search has only the permitted sentence in AI_REPORT.md.

Part 9 — Android and frontend wiring: complete (commit `cde9cc2`).
Changed: Wired source/intent metadata and predicted listing badges into Android and the existing frontend API client.
Tests: Frontend `npx tsc --noEmit` passed; Android: 21 unit tests passed and assembleDebug succeeded; 5 instrumented tests were not run because adb is unavailable.

Part 10 — Reports and verification: complete.
Changed: Updated PEAS, provenance, metrics, model cards, limitations, READMEs, and this progress log.
Tests: Backend 127 → 128 passed; Android count stayed at 26 annotations (21 unit/5 instrumentation), with 21 unit tests passing. assembleDebug and Ruff succeeded; frontend type-check passed; instrumentation was not run (adb unavailable).

Part 11 — Optional product images: integration code complete; suggestions and approval pending.
Changed: Added a rate-limited Open Food Facts candidate CSV workflow, an empty approved-image registry, backend attribution/licence metadata, and Android image rendering with a placeholder. No images are approved or displayed until a human reviews the candidate metadata and records approval.
Tests: Backend 132 passed and Ruff clean; Android 22 unit tests passed and assembleDebug succeeded. The candidate search was not run because no maintainer contact email was configured; no external image requests were made.

Part 12 — Assistant listing lookup: complete.
Changed: Resolve exact store/product questions by listing name and generic questions through comparable groups or matching listing terms before fuzzy product fallback; add regression coverage for known listings and staple groups.
Tests: Backend 140 passed and Ruff clean; exact Quickmart and cheapest milk lookups returned matching advertised listings and snapshot coverage.

Task 1 — Deterministic store, basket, and unit-price answers updated.
Changed: Resolve ordered store aliases; compare named stores or all snapshot stores, calculate basket totals, show pack sizes, unit prices, URLs, and missing-store/item states.
Verification: Added answer tests using listing data; not run because pytest and required API/ML dependencies are unavailable in the offline Python runtime.

Task 2 — Compare-stores templates and leakage audit updated.
Changed: Appended new compare-stores template families, added normalized held-out overlap checks and per-split intent/family reporting, and marked prior model metrics as needing refresh.
Verification: Ran `python scripts/build_assistant_dataset.py`; family-grouped splits include compare_stores in each split, and the script reported its computed intent counts and highest normalized character-trigram Jaccard similarity.

Task 3 — Assistant request limiter adjusted.
Changed: Default is 60 requests per 60-second window, zero disables throttling, invalid negative limits remain rejected, and docs/tests/message were updated.
Verification: Added default-limit and disabled-limit tests; not run because pytest is unavailable in the offline Python runtime.

Part 13 — Intent-classifier CRISP-DM notebook: implementation in progress; execution and consistency check blocked by this environment.
Changed: Added a Colab-configurable notebook builder with pandas-based dataset inspection, shared word/character TF-IDF features, model comparison, validation-only abstention selection, overfitting diagnostics, provenance-separated evaluation, artifact export, API answer examples, and CLI consistency-check code. Updated model-loader guidance, READMEs, and AI/model-card descriptions. Optional entity-linking section was skipped because it is outside the required training path.
Verification: Recorded pre-change backend suite was 140 passed (Part 12). This environment's Python 3.12 runtime has pandas and NumPy but lacks scikit-learn, matplotlib, pytest, and Ruff; Windows Store Python and WSL execution were unavailable. No dependencies were downloaded. Notebook execution, fresh test count, Ruff, CLI comparison, and resulting model metrics remain unverified.

