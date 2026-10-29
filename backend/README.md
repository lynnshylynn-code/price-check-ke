# Price Check KE API

FastAPI service for the supplied Kenya RTFP market dataset, a public supermarket listing snapshot, and a locally trained assistant. Advertised listings are a dated snapshot and may differ in store. Missing observations are never estimated.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ml]"
python scripts/build_assistant_dataset.py
python scripts/build_assistant_notebook.py  # generates, executes, and saves outputs to notebooks/assistant_intent_crisp_dm.ipynb
python scripts/train_entity_linker.py
python scripts/train_matcher.py
python scripts/predict_listing_categories.py  # optional; ignored output when APHRC workbook is present
.\start-local.ps1
```

The trained artifacts are written to the ignored `backend/models/` directory. The API starts at `http://127.0.0.1:8000`; interactive docs are at `/docs`. No model service key is required. Secrets for the optional Daraja sandbox remain environment variables.

`PRICE_CHECK_CORS_ORIGINS` controls allowed browser origins. Assistant requests are limited by default to 60 per IP per 60-second window. `PRICE_CHECK_AI_RATE_LIMIT` and `PRICE_CHECK_AI_RATE_WINDOW_SECONDS` override those defaults; set the limit to `0` to disable throttling. Set `PRICE_CHECK_TRUST_PROXY=1` only behind a proxy that overwrites forwarded headers. `PRICE_CHECK_ORDERS_DB` selects the prototype SQLite path. `PRICE_CHECK_APHRC_XLSX` may point to the ignored workbook; the default stays inside `data/listings/private/`. Optional Daraja configuration uses `PRICE_CHECK_PAYMENTS`, `PRICE_CHECK_CALLBACK_SECRET`, `DARAJA_BASE_URL`, `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`, `DARAJA_SHORTCODE`, `DARAJA_PASSKEY`, `DARAJA_CALLBACK_URL`, `DARAJA_PARTY_B`, and `DARAJA_TRANSACTION_TYPE`.

## Assistant and data endpoints

- `POST /api/v1/assistant/ask` — trained intent model with deterministic data lookups, intent, confidence, entities, source and coverage metadata.
- `POST /api/v1/ai/market-question` — compatibility route backed by the same trained assistant.
- `POST /api/v1/ai/market-question/simulate` — deterministic historic market-data answer.
- `GET /api/v1/models/info` — model availability, training date, data hash and metrics.
- `GET /api/markets` and `GET /api/prices` — World Bank RTFP market price data.
- `GET /api/v1/listings` and `/api/v1/listing-groups` — dated advertised listing snapshot.
- Order and basket endpoints remain prototype-only.

## Dataset and model provenance

The main assistant training path is the CRISP-DM notebook at `../notebooks/assistant_intent_crisp_dm.ipynb`. Run `python scripts/build_assistant_notebook.py` to regenerate and execute it with the installed local dependencies. In Colab, clone the repository (or upload `backend/data/assistant` and the training script) and configure `ASSISTANT_DATA_DIR` / `ASSISTANT_MODEL_DIR` as needed. The notebook compares a majority baseline, Naive Bayes, kNN, decision tree, logistic regression, calibrated linear SVM, random forest, and MLP using the same word/character TF-IDF features. It selects the model and abstention threshold on validation only, then reports test and held-out sources separately. `python scripts/train_assistant.py` is the command-line copy of that pipeline and writes the same artifact format for compatibility.

Question templates are AI-written and generated questions are synthetic. The separate `heldout_test_questions.csv` set is AI-written held-out data and is never used for training or tuning. The matcher uses human labels only when `label` is filled; otherwise it bootstraps synthetic noisy-copy positives and same-brand different-size negatives. Report these metrics as synthetic. The APHRC workbook is optional and excluded from Git; every endpoint must work when it is absent.

Run backend checks with `python -m pytest` and `ruff check`. See `../docs/AI_REPORT.md` and `../docs/MODEL_CARD.md` for design, metrics and limitations.

## Optional product image suggestions

`python scripts/suggest_images_off.py --limit 15` writes local suggestions to
`data/images/candidates.csv`; it never downloads images or fills the `approved` column. Set
`PRICE_CHECK_OFF_CONTACT_EMAIL` first so requests identify the app as
`PriceCheckKE/1.0 (contact-email)`. The script waits at least 6.2 seconds between at most 15
searches and leaves uploader attribution blank when the API does not provide it. A maintainer must
verify attribution and image-specific rights, then copy only approved complete entries into
`data/images/product_images.json`. The default image registry is empty; listing responses expose only
entries explicitly marked approved. Open Food Facts documents a 10-search-requests/minute limit, the
required app-identifying User-Agent, and CC BY-SA product images; some images may have separate
rights restrictions. The script uses their documented legacy full-text CGI search endpoint because
the current v2 API supports structured search rather than plain-text search. Do not use
supermarket-site images.
