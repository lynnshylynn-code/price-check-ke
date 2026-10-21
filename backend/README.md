# Price Check KE API

FastAPI service for the supplied Kenya RTFP dataset. It exposes observed
market-level commodity prices and the national Market Average
`inflation_food_price_index` series. It does not contain live supermarket
prices.

## Run locally

From the repository root, in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\start-local.ps1
```

The startup script asks for the OpenAI API key using hidden terminal input,
then starts the backend with the key available only to that process and its
children. It does not save the key to a file. Set `OPENAI_MODEL` in the
environment before starting to override the default `gpt-4.1-mini`. Never put
the key in the Expo app or a public client environment variable. Without a key,
the AI endpoint returns HTTP 503 and the app displays the configuration error.

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is at
`http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /health` — service health
- `GET /api/v1/market/food-inflation` — national food-price index and summary
- `GET /api/markets` — source markets, counties, and commodity coverage
- `GET /api/prices?market=Garissa&commodity=maize&from=2026-01-01&to=2026-08-31`
  — observed prices for an exact county or market, with optional inclusive dates
- `GET /api/v1/products` — centralized illustrative supermarket demo catalog
- `POST /api/v1/basket/pricing` — centralized basket calculation for demo
  products; results remain labelled as demo data
- `POST /api/v1/ai/market-question` — tool-based OpenAI answer with source
  citation; request JSON is `{"question": "..."}` (3–500 characters)
- `POST /api/v1/ai/market-question/simulate` — deterministic no-key answer
  using the same backend data and source metadata

## Test

```powershell
pytest
ruff check
```

The browser development origins on ports 8081 through 8084 are allowed by
default. Set `PRICE_CHECK_CORS_ORIGINS` to a comma-separated list of exact
origins when using other browser origins.
AI requests are limited to 8 per client IP per 60 seconds by default. Override
with `PRICE_CHECK_AI_RATE_LIMIT` and `PRICE_CHECK_AI_RATE_WINDOW_SECONDS`. The
limiter is process-local; use a shared store in a multi-worker deployment. It
uses `request.client.host` and does not trust caller-supplied
`X-Forwarded-For`. Configure trusted proxy handling before deploying behind a
reverse proxy.

For an Android emulator, set
`EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000` in the frontend terminal. For a
physical device, use the computer's LAN IP and start Uvicorn with
`--host 0.0.0.0`.

## Data scope and retailer-price requirements

`data/rtfp_kenya_market_2007_2026-08.csv` is the supplied Kenya RTFP market-level
CSV. The [World Bank file dictionary](https://microdata.worldbank.org/catalog/6167/data-dictionary)
and CSV `components` field identify `beans (1 KG, Index Weight = 1)`,
`maize_fao (1 Kg, Index Weight = 1)`, and
`livestock_goat_s_fao (1 unit, Index Weight = 0)`. Their raw columns are nominal
prices in KES. The `o_`, `h_`, `l_`, and `c_` columns are open/high/low/close
estimates; `inflation_*` and `*_price_index` are derived index measures, not
unit prices. The price API reads only the three raw commodity columns, returns
one row per market/month, does not interpolate missing values, and does not
aggregate county markets.

The national `Market Average` row has 236 months; the first 12 food-inflation
values are blank, leaving 224 observations from Jan 2008 through Aug 2026. In
the supplied file, Nairobi and Mombasa have some historical beans observations
but no maize observations; Kisumu and Nakuru have no beans or maize
observations. The clients must show those gaps instead of estimating or
substituting prices.

The AI endpoint uses `get_series` and `compare_markets` function tools rather
than placing the entire CSV in each prompt. Its instructions restrict answers
to tool output, require source-grounded facts, and prohibit forecasts, causal
claims, fabricated current prices, and purchase guarantees. The deterministic
simulation is available without an OpenAI key and is not a generated answer.
Sixteen golden cases in `tests/evals/market_qa.json` exercise mocked tool output,
including missing data and prompt-injection examples.

Before adding real retailer comparisons, provide an approved price source and
preserve, for each observation: product/brand, package size, store, shopping
area, currency, price, observation timestamp, source/reference, and stock
status when available. Keep missing prices missing; don't infer them from the
national RTFP index or silently substitute another store's price. Expose the
observation period and source to shoppers, and agree a review/expiry policy
with the data provider.

## Container deployment

`Dockerfile` packages the API and supports the `PORT` environment variable.
Build and smoke-test it locally before choosing a hosting provider:

```powershell
docker build -t price-check-ke-api ./backend
docker run --rm -p 8000:8000 price-check-ke-api
```

No hosting target, credentials, production origin, or deployment has been
configured. Set `PRICE_CHECK_CORS_ORIGINS` to the deployed frontend's exact
origin before publishing the API.

## Supermarket listings and prototype ordering

The separate `/api/v1/listings` endpoints read the supplied 239-row advertised
listing snapshot, collected 20 Oct 2026. It is partial, offer-skewed, and does
not verify stock or checkout prices. Locations are missing or unverified for
most rows. No dataset licence was obtained or asserted. The optional APHRC
workbook remains ignored in `data/listings/private/`. Unit prices are returned
only for unambiguous parsed pack sizes. These listings are not a sales dataset
or price history.

`POST /api/v1/orders` is a local prototype: it does not submit orders to a
supermarket and does not move money. Delivery fees are unknown and returned as
null. SQLite records are under `data/runtime/`; set `PRICE_CHECK_ORDERS_DB` to
change the path. Delete prototype records with `DELETE /api/v1/orders/{id}`.
Delete demo records after demonstrations; no production retention policy or
checkout is configured.

The payment default is a deterministic local mock. Daraja configuration uses
`PRICE_CHECK_PAYMENTS=daraja_sandbox`, `DARAJA_BASE_URL` (must be
`https://sandbox.safaricom.co.ke`), `DARAJA_CONSUMER_KEY`,
`DARAJA_CONSUMER_SECRET`, `DARAJA_SHORTCODE`, `DARAJA_PASSKEY`, and
`DARAJA_CALLBACK_URL`. Credentials are server-only and production URLs are
rejected. Daraja sandbox calls have not been verified without merchant
credentials and a reachable callback URL.
