# Follow-up dialogue data

`followup_templates.csv` contains AI-written synthetic follow-up templates; the expanded questions are synthetic too. They are not real conversations or a substitute for human evaluation.

`dialogues_eval.json` is an AI-written scripted evaluation set. To contribute human evaluation, create `human_dialogues.json` with the same `{ "source": "human_written", "dialogues": [...] }` structure. Write 10 conversations of 3–6 turns each. Every turn has a `user` string and a `CHECKS` array using supported check types from `scripts/evaluate_dialogues.py` (`response_shape`, `no_advice_or_forecast`, `listing_sources_in_snapshot`, `cited_listing_prices_match_snapshot`, `named_store_mentioned`, `unknown_store_declared`). Do not include personal information or hard-coded prices; checks should refer to the supplied data. Run `python scripts/evaluate_dialogues.py` to report the human set separately.
