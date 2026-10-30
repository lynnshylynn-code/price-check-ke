# Model cards

## Intent classifier

- **Training path:** `notebooks/assistant_intent_crisp_dm.ipynb` is the main training path. It compares a majority baseline, Multinomial Naive Bayes, kNN, decision tree, logistic regression, calibrated linear SVM, random forest, and MLP over shared word/character TF-IDF features. Selection and abstention use validation data only. `backend/scripts/train_assistant.py` is the command-line copy.
- **Evaluation note:** the dataset splits changed in this version, so older results are not directly comparable. The compare_stores score rests on a small number of template families.

<!-- metrics:start -->
Run `python scripts/refresh_docs_metrics.py` after training to fill in this section.
<!-- metrics:end -->
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
