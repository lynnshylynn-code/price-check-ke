# AI report

A pretrained OpenAI language model was considered and not used; this assistant runs a locally trained intent classifier and deterministic data lookups.

## Task, agent and PEAS

The user enters a natural-language question about advertised listings or Kenya food-market data. A trained intent classifier routes it; deterministic Python functions retrieve and format facts. The agent does not generate unsupported numbers or use forecasts or buying advice.

- **Performance:** exact data grounding, correct intent/entity routing, explicit refusals for unsupported requests, source attribution, and measured classification/linking/matching metrics.
- **Environment:** the 20 Oct 2026 public advertised-listing snapshot, the World Bank RTFP Kenya market dataset through Aug 2026, the synthetic/AI-written question files, and the optional ignored APHRC catalogue workbook.
- **Actuators:** deterministic answers with source, coverage, product URL, entities and model confidence; or a refusal with example questions.
- **Sensors:** question text, trained intent probabilities, listing snapshot, comparable groups, and RTFP market series.

## Stateless task-oriented dialogue

The assistant is a rule-and-model based task-oriented dialogue system, not open chat and not an LLM. The model-based agent receives its internal conversation state as a client-supplied context object on every request; the API stores no conversation state. Context is size-limited, entity values and listing identifiers are checked against current data, and invalid context starts a new turn. The dialogue layer classifies follow-up turns, merges only the changed slot, requests missing entities, and reuses the existing deterministic lookup functions. Context turn count and stored result IDs are capped.

The web and Android clients keep up to 50 messages and the latest context on the device. Clear conversation removes this local history. There is no cross-device or server-side memory. Training examples for follow-up types and scripted dialogue evaluations are AI-written synthetic data; human-written dialogue evaluation is optional. This assistant answers questions about the price data; it is not open chat.

<!-- followup:start -->
- Selected follow-up model: `LogisticRegression`; threshold 0.3249.
- Synthetic follow-up test: rows 634; accuracy 0.7334; macro-F1 0.7372.
- Synthetic test precision / recall / F1 by label:
| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| acknowledge | 1.0000 | 1.0000 | 1.0000 | 60 |
| explain | 1.0000 | 0.6667 | 0.8000 | 72 |
| new_question | 0.6341 | 0.3611 | 0.4602 | 72 |
| refine_store | 0.7500 | 0.5000 | 0.6000 | 72 |
| show_more | 1.0000 | 0.1667 | 0.2857 | 72 |
| swap_county_or_commodity | 1.0000 | 1.0000 | 1.0000 | 72 |
| swap_product | 0.5433 | 0.9583 | 0.6935 | 72 |
| swap_store | 0.6604 | 1.0000 | 0.7955 | 70 |
| swap_year | 1.0000 | 1.0000 | 1.0000 | 72 |
- AI-written dialogues: turn accuracy 0.8913; dialogue success rate 0.7000.
<!-- followup:end -->

Intent routing is a **model-based/goal-based agent**: it uses a trained model to classify the request and deterministic data functions to reach a source-grounded answer. High-precision wording cues preserve explicit unit-price queries and single-store price queries when the classifier confuses them with adjacent intents. In the learning-agent mapping, the **learning element** is the CRISP-DM notebook `notebooks/assistant_intent_crisp_dm.ipynb` and the dataset builder; `train_assistant.py` is its command-line copy. The notebook makes data inspection, feature preparation, model comparison, threshold selection, and held-out evaluation visible. The **performance element** is the API serving path, and the **critic** is the validation/test evaluation in the notebook.

## Data provenance and splits

The supplied templates are AI-written. Expanded rows are **synthetic**, not human-authored. The dataset builder generates family-grouped splits, applies an intent cap, and removes training questions whose normalized character-trigram Jaccard similarity to AI-written or human-reviewed held-out questions is at least 0.85. Additional general-knowledge and future-price examples are explicitly train-only; their held-out counterparts remain separate template families. Current row counts and leakage results are populated from training metadata below. The separate `heldout_test_questions.csv` remains AI-written and was not used to train or select the classifier. `human_test_questions_draft.csv` remains an AI-generated draft; the separate 32-question evaluation set was supplied in human-authored wording and is labeled `human_written`. It was developed after reviewing the draft, so treat its results as a pilot rather than a fully independent user study. The four supermarket price-at-store questions reference observed listings from Naivas Nairobi delivery, Quickmart Westlands, Jaza Nairobi delivery, and the dated Carrefour Westlands snapshot; they do not represent all Nairobi branches. No independent fluent-speaker review is recorded.

## Intent model results

The main training path is `notebooks/assistant_intent_crisp_dm.ipynb`, generated and executed by `backend/scripts/build_assistant_notebook.py`. It compares a majority-class baseline with Multinomial Naive Bayes, kNN, a decision tree, logistic regression, calibrated linear SVM, random forest, and a small MLP neural network. Every candidate uses the same word and character TF-IDF feature union. Validation-only macro-F1 with abstentions selects the model and global confidence threshold; accepted accuracy and coverage break ties. A separate `compare_stores` cutoff is selected on validation data to meet a minimum precision target while preserving overall coverage. Test and held-out results are reported only after these choices. Tree-depth, neighbour-count, and regularization sweeps demonstrate train/validation gaps. The CLI script remains available as a consistency check and writes the same metadata and model format. Re-run the notebook builder to refresh the executed comparison table when training data or dependencies change.


Two supplemental out-of-scope families are training-only; the existing validation and test question files are unchanged. Scores are not directly comparable to earlier versions because training examples and the selection metric changed. Evaluation remains template-based; the synthetic validation and test splits each cover only two `compare_stores` template families.

<!-- metrics:start -->
- Selected model: `CalibratedLinearSVC`.
- Abstain threshold: 0.4014; validation coverage: 0.9989.
- Intent-specific cutoff: `compare_stores` 0.8076; validation precision 0.7538, recall 0.8991, coverage 0.9651 (target 0.7500).
- Rows: training 4440, validation 887, synthetic test 920.
- Synthetic test: accuracy 0.8707, macro-F1 0.8904, coverage 0.9391, abstained 56.
- Synthetic test per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.8023 | 0.6765 | 0.7340 | 102 |
| cheapest_item | 0.9277 | 0.7064 | 0.8021 | 109 |
| compare_stores | 0.8145 | 0.9439 | 0.8745 | 107 |
| food_inflation | 1.0000 | 1.0000 | 1.0000 | 111 |
| market_price | 1.0000 | 0.9806 | 0.9902 | 103 |
| out_of_scope | 1.0000 | 0.9045 | 0.9499 | 178 |
| price_at_store | 0.8509 | 0.9798 | 0.9108 | 99 |
| unit_price | 1.0000 | 0.7568 | 0.8615 | 111 |
- AI-written held-out: rows 91; accuracy 0.8462; macro-F1 0.8757; coverage 0.9341; abstained 6.
- AI-written held-out per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.9091 | 1.0000 | 0.9524 | 10 |
| cheapest_item | 0.8889 | 0.8000 | 0.8421 | 10 |
| compare_stores | 0.9000 | 0.9000 | 0.9000 | 10 |
| food_inflation | 1.0000 | 0.8000 | 0.8889 | 10 |
| market_price | 0.9000 | 0.9000 | 0.9000 | 10 |
| out_of_scope | 0.8947 | 0.8500 | 0.8718 | 20 |
| price_at_store | 0.8000 | 0.7273 | 0.7619 | 11 |
| unit_price | 1.0000 | 0.8000 | 0.8889 | 10 |
- Human-written held-out: rows 32; accuracy 0.8438; macro-F1 0.8576; coverage 0.9375; abstained 2.
- Human-written held-out per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.8000 | 1.0000 | 0.8889 | 4 |
| cheapest_item | 0.8000 | 1.0000 | 0.8889 | 4 |
| compare_stores | 1.0000 | 1.0000 | 1.0000 | 4 |
| food_inflation | 1.0000 | 1.0000 | 1.0000 | 4 |
| market_price | 1.0000 | 1.0000 | 1.0000 | 4 |
| out_of_scope | 1.0000 | 0.5000 | 0.6667 | 4 |
| price_at_store | 1.0000 | 0.5000 | 0.6667 | 4 |
| unit_price | 0.7500 | 0.7500 | 0.7500 | 4 |
- Leakage check: training questions dropped at or above 0.85 similarity 0; highest retained similarity 0.7500 (AI-written held-out).
- Training date: 2026-11-17.
<!-- metrics:end -->

## ROC-AUC and cross-validation robustness

The five folds are stratified by intent and grouped by template family. These training-only results are a robustness check; validation-only macro-F1 continues to select the model. Some intents have few distinct training families, so these CV scores are not an independent real-world generalization estimate. One-vs-rest ROC-AUC scores use class probabilities without the deployed abstention threshold.

<!-- robustness:start -->
Stratified, family-grouped five-fold CV is a training-only robustness check; it does not select the deployed model.
| Candidate | Mean macro-F1 | Std. dev. |
|---|---:|---:|
| CalibratedLinearSVC | 0.6910 | 0.0890 |
| DecisionTree | 0.5623 | 0.0584 |
| DummyMostFrequent | 0.0355 | 0.0054 |
| KNeighbors | 0.5416 | 0.0581 |
| LogisticRegression | 0.6919 | 0.0842 |
| MLP | 0.6873 | 0.0804 |
| MultinomialNB | 0.6537 | 0.0764 |
| RandomForest | 0.6863 | 0.0760 |
Synthetic test macro one-vs-rest ROC-AUC: 0.9760.
- Synthetic test `biggest_discount` ROC-AUC: 0.9038.
- Synthetic test `cheapest_item` ROC-AUC: 0.9645.
- Synthetic test `compare_stores` ROC-AUC: 0.9880.
- Synthetic test `food_inflation` ROC-AUC: 1.0000.
- Synthetic test `market_price` ROC-AUC: 1.0000.
- Synthetic test `out_of_scope` ROC-AUC: 0.9999.
- Synthetic test `price_at_store` ROC-AUC: 0.9946.
- Synthetic test `unit_price` ROC-AUC: 0.9574.
AI-written held-out macro one-vs-rest ROC-AUC: 0.9884.
- AI-written held-out `biggest_discount` ROC-AUC: 0.9975.
- AI-written held-out `cheapest_item` ROC-AUC: 0.9778.
- AI-written held-out `compare_stores` ROC-AUC: 0.9963.
- AI-written held-out `food_inflation` ROC-AUC: 1.0000.
- AI-written held-out `market_price` ROC-AUC: 0.9864.
- AI-written held-out `out_of_scope` ROC-AUC: 0.9585.
- AI-written held-out `price_at_store` ROC-AUC: 0.9909.
- AI-written held-out `unit_price` ROC-AUC: 1.0000.
<!-- robustness:end -->

## Course-topic reasoning demonstrations

- **Propositional logic and knowledge-based reasoning:** `logic_rules.py` derives snapshot facts such as a recorded discount and relative unit-price position, then uses Horn clauses, forward chaining, backward chaining, and truth-table entailment. `GET /api/v1/listings/{listing_id}/reasoning` returns base facts, derived facts, fired rules, and a proof. Missing stock evidence is represented as unknown, never as in-stock.
- **Constraint satisfaction:** `basket_csp.py` treats each selected Nairobi catalog product as a variable and observed retailer prices as its domain. MRV backtracking and forward checking apply a maximum-store limit, minimum spend for each used store, optional budget cap, and optional requirement to use a named retailer. `POST /api/v1/basket/constraints` returns the least-cost satisfying assignment found, expanded-node count, or an explicit unsatisfied constraint. A public listing is an observed offer, not verified stock.
- **Association rules:** `association_rules.py` implements Apriori support, confidence, and lift over `backend/data/baskets/synthetic_baskets.csv`. The baskets are seeded teaching examples based on staple groups, not transactions or evidence of actual shopper behavior. `GET /api/v1/basket/suggestions?items=...` repeats that synthetic-data warning.
- **Local and adversarial search:** `local_search.py` demonstrates hill climbing with random restarts and seeded simulated annealing over store assignments, alongside the A* basket search. The minimax/alpha-beta pricing game in `search_demo.py` has arbitrary illustrative payoffs and is not an economic or retailer-behavior model.

## Entity linking and listing matching

Entity linking uses a character n-gram TF-IDF nearest-neighbour index over observed listing names and supplied product surface forms. Store, county and commodity resolution uses the supplied slot lexicon, with county/commodity names also checked against the RTFP directory. The product and store thresholds were selected on synthetic validation data: 0.05 product similarity (159 product cases, 0.9937 accuracy) and 0.875 store similarity (validation accuracy 1.0000). These high validation figures are synthetic and should not be read as real-world performance.

The final `python scripts/evaluate_entity_linking.py` run linked 549/711 synthetic validation entities (0.7722), 411/433 synthetic test entities (0.9492), and 61/92 entities in the AI-written held-out set (0.6630). Two deliberately unknown entities occurred in the held-out set; both resolved to “not in the snapshot” (2/2). No deliberately unknown product/store entities occurred in the synthetic validation or test split, so those splits do not measure unknown handling.

The listing matcher is `LogisticRegression` over token overlap, word/character cosine, normalized size/unit, brand token, length difference, unit-price ratio, and name similarity. No human `label` entries were filled in `match_pairs.csv`, so the model and its metrics are **synthetic bootstrap** only. It trained on 231 pairs and evaluated on 77 pairs (63 positives): model precision/recall/F1 1.0000/1.0000/1.0000; old 0.70 threshold precision/recall/F1 0.9844/1.0000/0.9921. The model confusion matrix was `[[14, 0], [0, 63]]`; baseline was `[[13, 1], [0, 63]]`. These small synthetic scores do not establish production matching quality.

## Bias and limitations

Question generation comes from AI-written templates and does not represent real user language. Synthetic noise and the AI-written held-out questions are not independent human evaluation. Current synthetic results are uneven: `biggest_discount`, `cheapest_item`, and `market_price` remain weak on the synthetic test split, and `unit_price` recall is lower in the AI-written held-out set. The 32-question human-written intent set is an initial pilot; a larger independently authored sample and human dialogue evaluation are needed before drawing conclusions about real user queries. Some product, store and county names are absent from the snapshot; fuzzy matches can still be wrong. Listing prices are a dated advertised snapshot, not checkout prices, stock, or price history. RTFP covers only recorded markets and periods; missing observations are not filled in. APHRC-derived categories are predictions and inherit the catalogue’s coverage and label limitations.

## Sustainability, ethics and governance

- **Training compute:** the training script records measured Python wall-clock duration below. It is elapsed runtime, not a power or energy measurement. No kWh figure is claimed because hardware power draw was not measured. If later estimated, use `energy_kWh = average_power_W × elapsed_seconds / 3,600,000` and state the measured or assumed average power.
- **AI for sustainability:** clearer access to dated food prices can support SDG 2 (Zero Hunger) by helping users inspect price information, and SDG 12 (Responsible Consumption and Production) by supporting comparisons. This prototype does not measure hunger, affordability outcomes, waste reduction, or SDG impact.
- **Bias — sample:** listing coverage is sparse and uneven across retailers and locations. The audit of the dated public-listings file reports 239 rows: Naivas 176, Carrefour 25, Quickmart 38, and no Jaza rows. Only 25 rows explicitly name Nairobi as county; 214 location contexts do not identify a county. These are counts in that file, not proof of complete branch coverage or stock. `python scripts/audit_coverage.py` reproduces the counts.
- **Bias — prejudicial:** intent routing may work less well for Swahili/Sheng, dialects, spelling variation, or unfamiliar product names because the training examples are mostly synthetic and language coverage is limited. Do not treat confidence as proof of equal performance; expand and independently review language-specific evaluations.
- **Bias — measurement:** advertised prices can differ from checkout prices, promotion eligibility, and stock. The listing snapshot is not a transaction dataset or a history of price changes.
- **Governance and privacy:** basket, budget, watched items, shopping area, basket strategy, optional display name, and assistant conversation are stored locally by the web client (AsyncStorage) or Android app (DataStore); Android also stores the last order ID. The assistant API receives a question and client-supplied context for that request and does not persist conversation state. Prototype order creation sends store, listing IDs/quantities, delivery address, phone number, and optional coordinates to the backend’s SQLite order store; it does not transmit the order to a supermarket. The API masks phone numbers in returned order records, but the prototype retains the stored order until deleted. The order-status delete control calls `DELETE /api/v1/orders/{id}`; chat can be cleared locally. There is no single in-app erase-all control for local preferences.

Measured training runtime:

<!-- compute:start -->
Measured local training wall-clock time: 396.216 seconds. This is elapsed time, not measured electrical energy.
<!-- compute:end -->

## Pretrained models and transfer learning

This project uses a small local word/character TF-IDF representation with linear classifiers rather than fine-tuning a transformer or calling a hosted LLM. Available labelled question data is small and synthetic; a transformer would add more parameters and training complexity without evidence of a matching data scale. The local pipeline has predictable CPU latency, no per-query API charge, works offline after model artifacts are installed, and routes requests to deterministic answers grounded in the local snapshots. A hosted generative model could produce fluent prose, but would add network dependence, privacy and governance concerns, recurring inference cost, and a risk of unsupported prices unless tightly grounded.

`python scripts/compare_pretrained_embeddings.py` is an optional local comparison using sentence-transformer embeddings with logistic regression. It was not run unless the optional package and model are available; no comparison metric is claimed here.

## Not yet done / unverified

- Independent fluent-speaker review of the approved Swahili/Sheng questions; human review of the match-pair labels.
- Human-written dialogue evaluation set (`human_dialogues.json`, 10 conversations of 3–6 turns) and its separate evaluation run.
- Device/emulator instrumentation tests (no `adb` executable/device was available); the Android unit tests and debug build did pass.
- Daraja sandbox transaction and callback with merchant credentials and a reachable HTTPS callback.
- Human spot-check of the predicted food-group/NOVA badges; the output is local and ignored by Git.
- Open Food Facts image candidate queries and human approval. The candidate script requires a maintainer contact email; the approved-image registry remains empty.
