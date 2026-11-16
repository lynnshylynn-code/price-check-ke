# Model cards

## Intent classifier

- **Training path:** `notebooks/assistant_intent_crisp_dm.ipynb` is the main training path. It compares a majority baseline, Multinomial Naive Bayes, kNN, decision tree, logistic regression, calibrated linear SVM, random forest, and MLP over shared word/character TF-IDF features. Model selection, global abstention, and the precision-targeted `compare_stores` cutoff use validation data only. `backend/scripts/train_assistant.py` is the command-line copy.
- **Evaluation note:** the dataset splits changed in this version, so older results are not directly comparable. The synthetic validation and test splits each cover only two `compare_stores` template families.

<!-- metrics:start -->
- Selected model: `CalibratedLinearSVC`.
- Abstain threshold: 0.5283; validation coverage: 0.8963.
- Intent-specific cutoff: `compare_stores` 0.8039; validation precision 0.7581, recall 0.8624, coverage 0.8568 (target 0.7500).
- Rows: training 4286, validation 887, synthetic test 920.
- Synthetic test: accuracy 0.7717, macro-F1 0.8410, coverage 0.8370, abstained 150.
- Synthetic test per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.8333 | 0.6373 | 0.7222 | 102 |
| cheapest_item | 0.9146 | 0.6881 | 0.7853 | 109 |
| compare_stores | 0.8145 | 0.9439 | 0.8745 | 107 |
| food_inflation | 1.0000 | 1.0000 | 1.0000 | 111 |
| market_price | 1.0000 | 0.9806 | 0.9902 | 103 |
| out_of_scope | 1.0000 | 0.5056 | 0.6716 | 178 |
| price_at_store | 0.8509 | 0.9798 | 0.9108 | 99 |
| unit_price | 1.0000 | 0.6306 | 0.7735 | 111 |
- AI-written held-out: rows 91; accuracy 0.8242; macro-F1 0.8711; coverage 0.9011; abstained 9.
- AI-written held-out per-intent precision/recall:
| Intent | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| biggest_discount | 0.9091 | 1.0000 | 0.9524 | 10 |
| cheapest_item | 0.8889 | 0.8000 | 0.8421 | 10 |
| compare_stores | 0.9000 | 0.9000 | 0.9000 | 10 |
| food_inflation | 0.9000 | 0.9000 | 0.9000 | 10 |
| market_price | 0.9000 | 0.9000 | 0.9000 | 10 |
| out_of_scope | 1.0000 | 0.7000 | 0.8235 | 20 |
| price_at_store | 0.8000 | 0.7273 | 0.7619 | 11 |
| unit_price | 1.0000 | 0.8000 | 0.8889 | 10 |
- Leakage check: training questions dropped at or above 0.85 similarity 0; highest retained similarity 0.7500 (AI-written held-out).
- Training date: 2026-11-16.
<!-- metrics:end -->

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
