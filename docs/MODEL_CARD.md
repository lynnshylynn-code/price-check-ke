# Model cards

## Intent classifier

- **Model:** CalibratedLinearSVC with word and character TF-IDF, trained 2026-10-27.
- **Training data:** 2,900 synthetic rows from 48 template families. Validation used 433 synthetic rows from 8 families; the 697-row synthetic test and 91-row AI-written held-out set were kept separate. Training SHA-256: `3e801bee7212dee46dab9c2279b812ae1bff7c7ebad89135728bd9dddd2f88d3`.
- **Metrics:** synthetic test accuracy 0.6026 / macro-F1 0.5652; AI-written held-out accuracy 0.7912 / macro-F1 0.8115. Dummy baseline macro-F1 0.0511 and 0.0450 respectively.
- **Intended use:** route supported product, listing, market-price and food-inflation questions to deterministic data functions; abstain below validation-selected confidence threshold 0.4200.
- **Limitations:** all questions are synthetic or AI-written; compare_stores was missed in all 53 synthetic test examples. Not a human-validated conversational system.

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
