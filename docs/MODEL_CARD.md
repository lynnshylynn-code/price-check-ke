# Model cards

## Intent classifier

- **Training path:** `notebooks/assistant_intent_crisp_dm.ipynb` is the main training path. It compares a majority baseline, Multinomial Naive Bayes, kNN, decision tree, logistic regression, calibrated linear SVM, random forest, and MLP over shared word/character TF-IDF features. Validation macro-F1 with abstentions selects the model and global cutoff; the precision-targeted `compare_stores` cutoff is also validation-only. `backend/scripts/train_assistant.py` is the command-line copy.
- **Evaluation note:** two supplemental out-of-scope families are training-only, and the existing validation and test question files are unchanged. Scores are not directly comparable to earlier versions because training examples and the selection metric changed. The synthetic validation and test splits each cover only two `compare_stores` template families.

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

## Cross-validation and ROC-AUC robustness

The CV is stratified by intent and grouped by template family; it is a training-only robustness check and does not select the shipped model. Some intents have few template families, so the scores are not an independent real-world generalization estimate. ROC-AUC is one-vs-rest probability ranking and does not measure deployed-threshold calibration.

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

## Sustainability, ethics and governance

- Training runtime is measured locally in seconds; no electrical energy or kWh is claimed without power measurements.
- Food-price transparency may support SDG 2 and SDG 12, but the prototype has no measured social or environmental impact.
- Sample bias: current Nairobi observations have limited Naivas/Quickmart location coverage. The audit of the dated public listing file counted 239 rows (Naivas 176, Carrefour 25, Quickmart 38, no Jaza); 214 rows do not explicitly identify a county. Counts describe this file only.
- Prejudicial bias risk: synthetic, limited language coverage can reduce performance on Swahili/Sheng, dialects, typos, and unseen product names.
- Measurement bias: advertised prices are not verified checkout prices, promotion eligibility, stock, or purchase records.
- Basket, budget, watchlist, shopping area, and assistant chat stay in on-device AsyncStorage/DataStore. The API receives assistant questions plus client context per request without saving conversation state.
- Prototype orders send retailer, listing IDs/quantities, phone, delivery address, and optional coordinates to backend SQLite. Phone is masked in responses; use the order delete action / `DELETE /api/v1/orders/{id}` to remove an order. Chat history has a local clear action; there is no all-preferences erase control.
- Orders are not forwarded to a supermarket; the prototype sends no real payment. The optional Daraja path is sandbox-only.

Measured training runtime:

<!-- compute:start -->
Measured local training wall-clock time: 396.216 seconds. This is elapsed time, not measured electrical energy.
<!-- compute:end -->

## Pretrained model comparison

- No hosted LLM or transformer fine-tuning is used. Small synthetic training data, local CPU latency, no per-query service cost, offline operation, and deterministic data-grounded answers favor TF-IDF with linear classifiers.
- An optional sentence-transformer embedding comparison is available; no result is reported unless it is actually run.

## Follow-up classifier and dialogue system

- **Architecture:** deterministic task-oriented dialogue, with a client-supplied and validated context object; the API is stateless. A follow-up classifier identifies store/product/county/commodity/year changes, more-results requests, filters, explanations, acknowledgements, or a new question. Slot merging and clarification route into the existing deterministic answer functions.
- **Model candidates:** word and character TF-IDF with entity-type indicators; logistic regression, calibrated linear SVM, and random forest compared against a majority dummy baseline. The validation set selects the model and abstention threshold.
- **Training data:** `backend/data/assistant/followup_templates.csv` is AI-written synthetic data, split by family ID. `dialogues_eval.json` is AI-written scripted evaluation. Human-written dialogue evaluation is optional and reported separately.
- **Use and limits:** not open chat, not a hosted LLM, and cannot provide forecasts or advice. Follow-up wording remains synthetic; no memory is stored on the server or shared across devices. Client history is stored on device only and can be cleared.

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
## Listing pair matcher

- **Model:** LogisticRegression over product-pair text, size, unit, brand and unit-price features, trained 2026-10-27 with scikit-learn 1.9.1.
- **Training data:** 231 synthetic bootstrap pairs because no human `label` values were filled. Data SHA-256: `561b63b33425d521f473b8714c8c0f61abf183dcef8f37ccfa5500f6c4744228`.
- **Metrics:** synthetic 77-pair evaluation, 63 positives: model precision/recall/F1 1.0000/1.0000/1.0000; 0.70 threshold baseline 0.9844/1.0000/0.9921.
- **Intended use:** suggest comparable cross-store listings in the dated snapshot.
- **Limitations:** metrics are synthetic and the test set is small. Human review is required before treating groups as reliable.

## Entity linker

- **Model:** character n-gram TF-IDF nearest-neighbour index over listing names and product aliases, plus slot-based store/county/commodity matching.
- **Training/evaluation data:** trained 2026-10-27 with scikit-learn 1.9.1 from slot aliases and the actual RTFP county/market directory. Data SHA-256: `c977019e18f5b0e9c731bd55332ccc919756f6b3df0914f949b3dbeb4b2676fe`. Product threshold 0.05 and store threshold 0.875 were selected on synthetic validation examples. Synthetic validation accuracy 0.7722 (711 entities), synthetic test accuracy 0.9492 (433 entities), AI-written held-out accuracy 0.6630 (92 entities). Two deliberately unknown entities in the held-out set were both rejected correctly; no unknown entities occurred in the synthetic test split.
- **Intended use:** map a question’s explicit entities to observed records or return a clear not-in-snapshot result.
- **Limitations:** unseen paraphrases and misspellings can still be linked incorrectly; validation thresholds and human review remain necessary.

## Optional food-group and NOVA labeler

- **Model:** character n-gram TF-IDF nearest-neighbour lookup, run 2026-10-27 on public listing names against the APHRC `unique_items` catalogue.
- **Data:** 6,041 catalogue rows with `description`, `food_group` and `nova`; the workbook is licence-restricted and is not committed. Generated listing predictions remain local and gitignored.
- **Metrics:** no independent labelled evaluation was run, so accuracy is unknown. Returned values are explicitly marked `predicted` with similarity confidence.
- **Intended use:** optional badges to help users interpret listing categories.
- **Limitations:** nearest text match can attach the wrong category; confidence is similarity, not calibrated probability. Human spot-check is required before relying on these labels.
