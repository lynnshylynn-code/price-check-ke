# Price Check KE: AI course design report

## Agent definition

| PEAS component | Price Check KE |
|---|---|
| Performance measure | Grounded, correctly dated/unit-labelled answers; valid basket assignments; clear missing-data handling; responsive requests. |
| Environment | Kenyan market observations in the supplied RTFP dataset, illustrative supermarket catalog, user questions, and backend service. |
| Actuators | Text answer, source and coverage metadata, basket comparison, HTTP response, prototype order record/status, local cancel/delete, and payment sandbox request. |
| Sensors | User question, validated tool arguments, RTFP CSV observations, advertised listing snapshot, basket/address/phone form fields, and sandbox payment callback. |

### Environment properties

- **Partially observable:** the dataset contains only sampled market observations, not every market, transaction, or current retail price.
- **Stochastic:** actual prices and survey observations vary over time; a fixed dataset snapshot makes individual tool reads repeatable.
- **Episodic:** each question is answered independently; user questions are not retained as conversational state.
- **Static during a request:** the CSV snapshot and catalog do not change while a request is being processed.
- **Single-agent:** one backend agent answers each request; no other autonomous agent competes or coordinates in this environment.

## Agent structures in the code

- `offline_answers.py` is a **simple reflex agent**: condition-action rules inspect words and return a response based on matching patterns and market data.
- `ai_insights.py` with `market_tools.py` is a **goal-based agent**: it seeks a grounded answer, uses `get_series` and `compare_markets` as sensors/actions, validates tool arguments with strict schemas, and caps the tool-call loop at four rounds.
- `basket_search.py` is a **problem-solving agent**: it searches a finite state space of product-to-store assignments. BFS, DFS, iterative deepening, and greedy best-first return the first goal in their traversal order and can be non-optimal with unequal prices; UCS and A* optimize the stated basket plus optional fixed visit cost. `POST /api/v1/basket/optimize` exposes BFS, UCS, and A* for a small selected basket and marks all catalog prices as demo data.
- `fuzzy_price.py` is a transparent historical description: p10/p50/p90 thresholds define low, typical, and high memberships; min implication, max aggregation, and centroid defuzzification produce a 0–100 position score. `/api/v1/market/price-position` reports the source and coverage, and returns no score for missing history. This position is not a forecast or recommendation.
- A **utility-based** version could balance basket cost against trip count, travel burden, stock confidence, and user preferences. The optional fixed store visit cost in the search model illustrates only one such trade-off.

### Learning-agent components

The **performance element** is the rule/model-driven answer and search behavior. A **learning element** that retrains from feedback is absent. A **critic** that scores answer quality exists only as offline golden fixtures and the opt-in evaluation scripts, not as continuous user feedback. A **problem generator** is also absent: the service does not autonomously seek new data or experiments. The CRISP-DM notebook is an offline educational analysis, not an online model update loop.

### Pretrained model and grounding

The model is selected by `OPENAI_MODEL`, defaulting to `gpt-4.1-mini` in `ai_insights.py`. A pretrained language model is used for natural-language interpretation rather than training a language model from the limited project dataset. The system prompt restricts claims to RTFP evidence and defines units, gaps, and prohibited forecasts. Strict tool schemas constrain calls to known market/commodity/date fields, while the backend tools retrieve the actual rows. The prompt and schemas reduce errors; they do not guarantee that every generated explanation is correct, so source and coverage accompany answers.

## Evaluation

The 17 committed pytest golden cases use a fake OpenAI client and fixture tool outputs. They verify request/tool plumbing and expected answer facts without calling the live model. `scripts/run_live_eval.py` is an opt-in model evaluation: it calls the configured model for all fixture questions plus at least eight questions whose expected numbers are derived from the CSV at runtime. It reports pass rate and failures and skips when `OPENAI_API_KEY` is absent. The live evaluation is not part of CI and can incur API usage.

The executed CRISP-DM notebook read 55,224 rows from `rtfp_kenya_market_2007_2026-08.csv`; after filtering, 7,345 observed price rows remained and 191 IQR flags were retained for inspection. County profile clustering selected k=6 (silhouette 0.573; elbow candidate k=4). For the chronological trend-class holdout, which starts in April 2020, the most-frequent baseline accuracy was 0.4712, selected kNN (k=3) was 0.5833, and the selected depth-2 decision tree was 0.5096. These are single-snapshot descriptive results; the small improvement over baseline does not establish robust predictive value. The notebook saved its local cluster-label artifact under the ignored `notebooks/output/` directory.

The AI rate limiter is in-memory and keyed by `request.client.host`; all users behind the same proxy therefore share a bucket. `X-Forwarded-For` is trusted only if the deployment sets `PRICE_CHECK_TRUST_PROXY=1` and the proxy overwrites that header. The limiter is process-local and is not a distributed quota.

### Live model evaluation status

Live evaluation has **not yet been run** as of 2026-10-20. `OPENAI_API_KEY` was not available in the environment, so there are no live pass-rate or failure results to report. After configuring the key, run `python scripts/run_live_eval.py` from `backend/`. The configured model defaults to `gpt-4.1-mini` (override with `OPENAI_MODEL`). Record the date, model, and printed result here after the command completes; the committed pytest golden tests are not a substitute for a live model run.

## Supermarket listing study and ordering prototype

`notebooks/supermarket_listings_crisp_dm.ipynb` is generated by
`backend/scripts/build_listings_notebook.py` and executed against the supplied
239-row CSV (20 Oct 2026). GroupShuffleSplit APHRC food-group results:
majority Dummy accuracy 0.1275, MultinomialNB 0.8849 (macro F1 0.70,
weighted F1 0.87), and decision tree accuracy 0.6026 (macro F1 0.51,
weighted F1 0.65). These are catalogue-text holdout metrics, not measured
accuracy on retailer descriptions. The APHRC catalogue has no prices. The
category label CSV remains blank, so retailer category accuracy is unavailable.
The pair-label CSV also remains blank, so no threshold, precision, recall, or
F1 is reported for matching. Both human-label samples have 60 rows.

The snapshot is partial and offer-skewed: 185 rows have regular prices, with
mean displayed discount 0.2492. Prices vary by store, location, session, and
promotion; stock and checkout prices were not verified. The data has no sales
history, and no dataset licence was obtained or asserted. Carrefour location
context says Westlands/Nairobi by site default; Quickmart's store view is
unverified; most rows have no location context. Selection bias comes from the
three stores and advertised homepage offers. Measurement bias arises because
advertised prices can differ from checkout prices. The tiny human-labelled
samples create evaluation bias, and APHRC till-style wording creates domain
shift from retailer names and abbreviations.

The ordering API is a prototype actuator: it stores an order request locally,
opens no supermarket order channel, and transfers no real money. The payment
mock can produce a `paid_sandbox` demonstration state. The optional Daraja
provider uses the sandbox OAuth and STK Push requests, persists merchant and
checkout request IDs, authenticates callbacks with a path token, checks the
callback amount against the server-computed subtotal, and handles duplicate
callbacks idempotently. It is restricted to the sandbox host and requires
server environment credentials plus a public HTTPS callback URL. `GET order`
can be polled for callback-updated state; without a reachable callback, state
remains `payment_pending` because an STK Query fallback is not implemented.
Daraja sandbox payment has not been verified with live credentials. Delivery
fee remains unknown. Order deletion removes the local record. Android ordering
screens and this interface are not production checkout.

## Updated supermarket notebook results

The executed listings notebook trains food-group and NOVA classifiers with
GroupShuffleSplit by normalized catalogue description (4,833 train rows,
1,208 holdout rows). For food group, majority Dummy accuracy is 0.1275,
MultinomialNB accuracy is 0.8849 (macro F1 0.70; weighted F1 0.87), and the
decision tree accuracy is 0.6026 (macro F1 0.51; weighted F1 0.65). For NOVA,
the majority baseline accuracy is 0.6142 (macro F1 0.19; weighted F1 0.47),
MultinomialNB accuracy is 0.9321 (macro F1 0.87; weighted F1 0.93), and the
decision tree accuracy is 0.8510 (macro F1 0.78; weighted F1 0.85). The
notebook contains the per-class precision, recall, F1, and confusion matrices.
Retailer predictions are saved per store in the ignored output directory, but
should be read as shifted catalogue predictions, not verified product labels.

Matching was measured on a controlled synthetic test only: 47 held-out pairs,
31 positive pairs, threshold 0.59, precision 1.0000, recall 0.9677, and F1
0.9836. This tests noisy copies and deliberately distinct product pairs; it is
not an estimate of real-world matching quality. The canonical sheets
`backend/data/labels/match_pairs.csv` and
`backend/data/labels/category_sample.csv` each have 60 rows and currently 0
human-reviewed labels. `label_status.py` therefore reports no agreement or
kappa yet. Suggestions are separate heuristic AI suggestions with evidence;
they are not training or evaluation labels. The APHRC-to-retailer prediction
has domain shift from till-style catalogue wording to retailer listing names.

## Ethics, coverage, and bias

Using the bias categories of Suresh and Guttag:

- **Historical bias:** RTFP records reflect historical market and survey conditions; they cannot be treated as today's retail prices.
- **Representation bias:** only 21 counties in this supplied file have any beans, maize, or goat price records. Coverage is concentrated in arid and semi-arid areas. Kisumu and Nakuru have no observations; Nairobi beans coverage ends in January 2022 and Mombasa beans in November 2021. Answers for these places must show the gap, not infer a price.
- **Measurement bias:** these are survey-based market estimates, not supermarket shelf prices or household transaction records. Beans and `maize_fao` are KES/kg, `livestock_goat_s_fao` is KES/unit. Inflation and `*_price_index` columns are index values, not product prices.
- **Aggregation bias:** county selections return observed market rows; county prices are not silently averaged by the API. Any county-month aggregation in the notebook is analytical and explicitly identified as such.
- **Evaluation bias:** earlier golden questions concentrated on a few counties. Part 4 broadens coverage with CSV-derived cases across Turkana, Kilifi, Makueni, Marsabit, Mandera, North Imenti, Lamu West, and Voi, and covers all three commodities wherever the source has records. This is a more varied check, not proof of national representativeness.

The app makes no future-price forecast or purchase recommendation. Supermarket catalog prices are synthetic demo examples, not verified retailer prices. The OpenAI call uses `store=False`; user questions are not persisted by this application. The service does not require personal identity or household financial details for these market queries.
