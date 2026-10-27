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

Part 8 — Model API and OpenAI removal: complete (commit `3d99725`).
Changed: Added trained assistant/model-info endpoints and optional predicted listing categories; removed OpenAI code, dependency, environment switches, and LLM tool wiring.
Tests: Final backend suite 128 passed; Ruff clean. Tracked active-repository search has only the permitted sentence in AI_REPORT.md.

Part 9 — Android and frontend wiring: complete (local commit pending).
Changed: Wired source/intent metadata and predicted listing badges into Android and the existing frontend API client.
Tests: Frontend `npx tsc --noEmit` passed; Android: 21 unit tests passed and assembleDebug succeeded; 5 instrumented tests were not run because adb is unavailable.

Part 10 — Reports and verification: complete (local commit pending).
Changed: Updated PEAS, provenance, metrics, model cards, limitations, READMEs, and this progress log.
Tests: Backend 127 passed before the CSV-derived golden test; final backend suite 128 passed and Ruff clean. Android: 21 unit tests passed and assembleDebug succeeded; instrumentation was not run (adb unavailable).

Part 11 — Optional product images: skipped.
Changed: Not started because the prior parts' Android build verification and human review remain incomplete.
Tests: No image suggestions or image integration tests were run.

