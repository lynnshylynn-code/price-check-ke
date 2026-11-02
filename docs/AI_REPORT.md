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

Intent routing is a **model-based/goal-based agent**: it uses a trained model to classify the request and deterministic data functions to reach a source-grounded answer. In the learning-agent mapping, the **learning element** is the CRISP-DM notebook `notebooks/assistant_intent_crisp_dm.ipynb` and the dataset builder; `train_assistant.py` is its command-line copy. The notebook makes data inspection, feature preparation, model comparison, threshold selection, and held-out evaluation visible. The **performance element** is the API serving path, and the **critic** is the validation/test evaluation in the notebook.

## Data provenance and splits

The supplied templates are AI-written. Expanded rows are **synthetic**, not human-authored. The dataset builder generates family-grouped splits, applies an intent cap, and removes training questions whose normalized character-trigram Jaccard similarity to AI-written or human-written held-out questions is at least 0.85. Current row counts and leakage results are populated from training metadata below. The separate `heldout_test_questions.csv` remains AI-written and was not used to train or select the classifier. No human-written held-out file is present.

## Intent model results

The main training path is `notebooks/assistant_intent_crisp_dm.ipynb`, generated and executed by `backend/scripts/build_assistant_notebook.py`. It compares a majority-class baseline with Multinomial Naive Bayes, kNN, a decision tree, logistic regression, calibrated linear SVM, random forest, and a small MLP neural network. Every candidate uses the same word and character TF-IDF feature union. Validation-only macro-F1 with abstentions, accepted accuracy, and coverage determine model and threshold selection; the synthetic test and provenance-labelled held-out sources are reported afterward. Tree-depth, neighbour-count, and regularization sweeps demonstrate train/validation gaps. The CLI script remains available as a consistency check and writes the same metadata and model format. Re-run the notebook builder to refresh the executed comparison table when training data or dependencies change.


The dataset splits changed in this version, so older scores are not directly comparable. The compare_stores score rests on a small number of template families.

<!-- metrics:start -->
- Selected model: `RandomForest`.
- Abstain threshold: 0.3625; validation coverage: 0.8625.
- Rows: training 3346, validation 887, synthetic test 920.
- Synthetic test: accuracy 0.8359, macro-F1 0.8458, coverage 0.9380, abstained 57.
- Synthetic test per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.9880 | 0.8039 | 0.8865 | 102 |
| cheapest_item | 1.0000 | 0.5413 | 0.7024 | 109 |
| compare_stores | 0.7664 | 0.9813 | 0.8607 | 107 |
| food_inflation | 1.0000 | 1.0000 | 1.0000 | 111 |
| market_price | 0.9630 | 0.7573 | 0.8478 | 103 |
| out_of_scope | 0.9834 | 1.0000 | 0.9916 | 178 |
| price_at_store | 0.6284 | 0.9394 | 0.7530 | 99 |
| unit_price | 1.0000 | 0.5676 | 0.7241 | 111 |
- AI-written held-out: rows 91; accuracy 0.7802; macro-F1 0.8116; coverage 0.9231; abstained 7.
- AI-written held-out per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.7000 | 0.7000 | 0.7000 | 10 |
| cheapest_item | 0.7500 | 0.6000 | 0.6667 | 10 |
| compare_stores | 1.0000 | 0.9000 | 0.9474 | 10 |
| food_inflation | 1.0000 | 1.0000 | 1.0000 | 10 |
| market_price | 0.7273 | 0.8000 | 0.7619 | 10 |
| out_of_scope | 0.8824 | 0.7500 | 0.8108 | 20 |
| price_at_store | 0.7500 | 0.8182 | 0.7826 | 11 |
| unit_price | 1.0000 | 0.7000 | 0.8235 | 10 |
- Leakage check: training questions dropped at or above 0.85 similarity 0; highest retained similarity 0.7368 (AI-written held-out).
- Training date: 2026-11-02.
<!-- metrics:end -->
## Entity linking and listing matching

Entity linking uses a character n-gram TF-IDF nearest-neighbour index over observed listing names and supplied product surface forms. Store, county and commodity resolution uses the supplied slot lexicon, with county/commodity names also checked against the RTFP directory. The product and store thresholds were selected on synthetic validation data: 0.05 product similarity (159 product cases, 0.9937 accuracy) and 0.875 store similarity (validation accuracy 1.0000). These high validation figures are synthetic and should not be read as real-world performance.

The final `python scripts/evaluate_entity_linking.py` run linked 549/711 synthetic validation entities (0.7722), 411/433 synthetic test entities (0.9492), and 61/92 entities in the AI-written held-out set (0.6630). Two deliberately unknown entities occurred in the held-out set; both resolved to “not in the snapshot” (2/2). No deliberately unknown product/store entities occurred in the synthetic validation or test split, so those splits do not measure unknown handling.

The listing matcher is `LogisticRegression` over token overlap, word/character cosine, normalized size/unit, brand token, length difference, unit-price ratio, and name similarity. No human `label` entries were filled in `match_pairs.csv`, so the model and its metrics are **synthetic bootstrap** only. It trained on 231 pairs and evaluated on 77 pairs (63 positives): model precision/recall/F1 1.0000/1.0000/1.0000; old 0.70 threshold precision/recall/F1 0.9844/1.0000/0.9921. The model confusion matrix was `[[14, 0], [0, 63]]`; baseline was `[[13, 1], [0, 63]]`. These small synthetic scores do not establish production matching quality.

## Bias and limitations

Question generation comes from AI-written templates and does not represent real user language. Synthetic noise and the AI-written held-out questions are not independent human evaluation. The classifier’s synthetic test missed every `compare_stores` case, so store comparisons need more varied examples and human review. Some product, store and county names are absent from the snapshot; fuzzy matches can still be wrong. Listing prices are a dated advertised snapshot, not checkout prices, stock, or price history. RTFP covers only recorded markets and periods; missing observations are not filled in. APHRC-derived categories are predictions and inherit the catalogue’s coverage and label limitations.

## Not yet done / unverified

- Human-authored assistant test questions and human review of the match-pair labels.
- Device/emulator instrumentation tests (no `adb` executable/device was available); the Android unit tests and debug build did pass.
- Daraja sandbox transaction and callback with merchant credentials and a reachable HTTPS callback.
- Human spot-check of the predicted food-group/NOVA badges; the output is local and ignored by Git.
- Swahili/sheng wording review by a fluent speaker.
- Open Food Facts image candidate queries and human approval. The candidate script requires a maintainer contact email; the approved-image registry remains empty.
