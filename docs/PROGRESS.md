# Progress

Parts 1 and 2 were already implemented on this checkout before this continuation. I am preserving those commits and continuing with Part 3 next.

Part 1 — Splash screen: complete in commit `8722025`.
Changed: Added lecture-style splash activity, vector-derived logo layout, theme color, Android documentation, and launch test.
Tests: Prior run count not captured in commit history; re-run attempted during this continuation but Gradle did not return output.

Part 2 — Navigation Component: complete in commit `c5196f0`.
Changed: Added NavHost graph, navigation actions/arguments, toolbar integration, and navigation instrumentation tests.
Tests: Prior run count not captured in commit history; re-run attempted during this continuation but Gradle did not return output.

Part 3 — Menu polish: complete; local commit pending.
Changed: Added vector menu icons, watchlist layout action, and MainActivity About/Exit actions via MenuProvider.
Tests: 0 tests run in this pass; prior local report lists 16 unit test cases but is stale/unverified. XML resources parsed successfully.

Parts 4–11 — Not started or audited yet.

Part 4 — Synthetic assistant dataset: complete; local commit pending.
Changed: Added seeded 15–20 fillings/template generation, 20% character noise, canonical-distinct paired slots, family-only splits, saved family lists/counts, and kept the 91-row AI-written held-out file separate.
Tests: Dataset generator printed 4,030 rows (48 train / 8 validation / 12 test families); `pytest tests/test_assistant_dataset.py` — 3 passed; Ruff — clean.
