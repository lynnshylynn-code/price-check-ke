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

The supplied templates are AI-written. Expanded rows are **synthetic**, not human-authored. The dataset builder generates family-grouped splits, applies an intent cap, and removes training questions whose normalized character-trigram Jaccard similarity to AI-written or human-written held-out questions is at least 0.85. Current row counts and leakage results are populated from training metadata below. The separate `heldout_test_questions.csv` remains AI-written and was not used to train or select the classifier. No human-written held-out file is present.

## Intent model results

The main training path is `notebooks/assistant_intent_crisp_dm.ipynb`, generated and executed by `backend/scripts/build_assistant_notebook.py`. It compares a majority-class baseline with Multinomial Naive Bayes, kNN, a decision tree, logistic regression, calibrated linear SVM, random forest, and a small MLP neural network. Every candidate uses the same word and character TF-IDF feature union. Validation-only macro-F1 with abstentions, accepted accuracy, and coverage determine model and threshold selection; the synthetic test and provenance-labelled held-out sources are reported afterward. Tree-depth, neighbour-count, and regularization sweeps demonstrate train/validation gaps. The CLI script remains available as a consistency check and writes the same metadata and model format. Re-run the notebook builder to refresh the executed comparison table when training data or dependencies change.


The dataset splits changed in this version, so older scores are not directly comparable. The compare_stores score rests on a small number of template families.

<!-- metrics:start -->
Run `python scripts/refresh_docs_metrics.py` after training to fill in this section.
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
