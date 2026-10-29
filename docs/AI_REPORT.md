# AI report

A pretrained OpenAI language model was considered and not used; this assistant runs a locally trained intent classifier and deterministic data lookups.

## Task, agent and PEAS

The user enters a natural-language question about advertised listings or Kenya food-market data. A trained intent classifier routes it; deterministic Python functions retrieve and format facts. The agent does not generate unsupported numbers or use forecasts or buying advice.

- **Performance:** exact data grounding, correct intent/entity routing, explicit refusals for unsupported requests, source attribution, and measured classification/linking/matching metrics.
- **Environment:** the 20 Oct 2026 public advertised-listing snapshot, the World Bank RTFP Kenya market dataset through Aug 2026, the synthetic/AI-written question files, and the optional ignored APHRC catalogue workbook.
- **Actuators:** deterministic answers with source, coverage, product URL, entities and model confidence; or a refusal with example questions.
- **Sensors:** question text, trained intent probabilities, listing snapshot, comparable groups, and RTFP market series.

Intent routing is a **model-based/goal-based agent**: it uses a trained model to classify the request and deterministic data functions to reach a source-grounded answer. In the learning-agent mapping, the **learning element** is the CRISP-DM notebook `notebooks/assistant_intent_crisp_dm.ipynb` and the dataset builder; `train_assistant.py` is its command-line copy. The notebook makes data inspection, feature preparation, model comparison, threshold selection, and held-out evaluation visible. The **performance element** is the API serving path, and the **critic** is the validation/test evaluation in the notebook.

## Data provenance and splits

The 228 supplied templates are AI-written. Expanded rows are **synthetic**, not human-authored. The generator wrote 4,030 rows and split whole families: 2,900 training rows from 48 families, 433 validation rows from 8 families, and 697 synthetic test rows from 12 families. All eight intents occur in every split. The separate 91-row `heldout_test_questions.csv` is an **AI-written held-out set**; it was not used to train or select the classifier. There are no human-authored question metrics.

## Intent model results

The main training path is `notebooks/assistant_intent_crisp_dm.ipynb`, generated and executed by `backend/scripts/build_assistant_notebook.py`. It compares a majority-class baseline with Multinomial Naive Bayes, kNN, a decision tree, logistic regression, calibrated linear SVM, random forest, and a small MLP neural network. Every candidate uses the same word and character TF-IDF feature union. Validation-only macro-F1 with abstentions, accepted accuracy, and coverage determine model and threshold selection; the synthetic test and provenance-labelled held-out sources are reported afterward. Tree-depth, neighbour-count, and regularization sweeps demonstrate train/validation gaps. The CLI script remains available as a consistency check and writes the same metadata and model format. Re-run the notebook builder to refresh the executed comparison table when training data or dependencies change.

The result table below is the previously recorded command-line training run. The new notebook was not executable in the current offline environment because its installed Python runtime lacks scikit-learn and matplotlib; therefore these existing metrics are not presented as a fresh notebook-versus-CLI consistency result.

The compare-stores template families have since been expanded. **Needs refresh after retraining:** the metrics below describe the prior dataset and must not be used to assess the expanded compare-stores intent.

Training ran 2026-10-27 with scikit-learn 1.9.1. The selected model was `CalibratedLinearSVC`, using word and character TF-IDF features and a confidence threshold of 0.4200 selected on the synthetic validation split. Its training data SHA-256 is `3e801bee7212dee46dab9c2279b812ae1bff7c7ebad89135728bd9dddd2f88d3`.

| Evaluation data | Model accuracy | Model macro-F1 | Dummy accuracy | Dummy macro-F1 | Rows |
|---|---:|---:|---:|---:|---:|
| Synthetic test split | 0.6026 | 0.5652 | 0.2568 | 0.0511 | 697 |
| AI-written held-out set | 0.7912 | 0.8115 | 0.2198 | 0.0450 | 91 |

The test reports below include abstention as `__abstain__`. Order is `biggest_discount`, `cheapest_item`, `compare_stores`, `food_inflation`, `market_price`, `out_of_scope`, `price_at_store`, `unit_price`, `__abstain__`.

**Synthetic test per-intent precision / recall / F1 (support):**

| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.9796 | 0.4706 | 0.6358 | 102 |
| cheapest_item | 0.8333 | 0.5000 | 0.6250 | 50 |
| compare_stores | 0.0000 | 0.0000 | 0.0000 | 53 |
| food_inflation | 1.0000 | 0.3824 | 0.5532 | 102 |
| market_price | 0.5233 | 0.9783 | 0.6818 | 46 |
| out_of_scope | 0.7898 | 0.7765 | 0.7831 | 179 |
| price_at_store | 0.2500 | 0.6981 | 0.3682 | 53 |
| unit_price | 1.0000 | 0.7768 | 0.8744 | 112 |

**Synthetic test confusion matrix:**

```text
[[48, 3, 0, 0, 0, 19, 15, 0, 17],
 [0, 25, 0, 0, 6, 0, 8, 0, 11],
 [0, 0, 0, 0, 0, 0, 50, 0, 3],
 [0, 0, 0, 39, 17, 18, 13, 0, 15],
 [0, 0, 0, 0, 45, 0, 0, 0, 1],
 [1, 1, 17, 0, 18, 139, 0, 0, 3],
 [0, 1, 15, 0, 0, 0, 37, 0, 0],
 [0, 0, 0, 0, 0, 0, 25, 87, 0],
 [0, 0, 0, 0, 0, 0, 0, 0, 0]]
```

The Dummy baseline predicts only `out_of_scope`: precision/recall/F1 are 0/0/0 for the other seven intents and 0.2568/1.0000/0.4087 for `out_of_scope`. Its synthetic confusion matrix has 102, 50, 53, 102, 46, 179, 53 and 112 examples in the `out_of_scope` prediction column, respectively, and zero in other columns.

**AI-written held-out per-intent precision / recall / F1 (support):**

| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.8750 | 0.7000 | 0.7778 | 10 |
| cheapest_item | 0.8750 | 0.7000 | 0.7778 | 10 |
| compare_stores | 0.6364 | 0.7000 | 0.6667 | 10 |
| food_inflation | 1.0000 | 0.9000 | 0.9474 | 10 |
| market_price | 0.7143 | 1.0000 | 0.8333 | 10 |
| out_of_scope | 0.9333 | 0.7000 | 0.8000 | 20 |
| price_at_store | 0.7143 | 0.9091 | 0.8000 | 11 |
| unit_price | 1.0000 | 0.8000 | 0.8889 | 10 |

**AI-written held-out confusion matrix:**

```text
[[7, 0, 1, 0, 1, 0, 0, 0, 1],
 [1, 7, 0, 0, 0, 1, 0, 0, 1],
 [0, 0, 7, 0, 0, 0, 2, 0, 1],
 [0, 0, 0, 9, 1, 0, 0, 0, 0],
 [0, 0, 0, 0, 10, 0, 0, 0, 0],
 [0, 1, 2, 0, 2, 14, 1, 0, 0],
 [0, 0, 1, 0, 0, 0, 10, 0, 0],
 [0, 0, 0, 0, 0, 0, 1, 8, 1],
 [0, 0, 0, 0, 0, 0, 0, 0, 0]]
```

Its Dummy baseline again predicts only `out_of_scope`, giving that class precision/recall/F1 0.2198/1.0000/0.3604 and zero scores for the other classes. Its confusion matrix has 10, 10, 10, 10, 10, 20, 11 and 10 examples in the `out_of_scope` column in the same intent order.

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
