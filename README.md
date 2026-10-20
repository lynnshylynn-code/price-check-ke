# Price Check KE

Price Check KE is a Kenyan shopping-comparison prototype with a native Kotlin
and Jetpack Compose Android app and an Expo web client. It follows the
Pricewise mockup: Home, Search and product comparisons, Basket, Trends, and
Profile. A FastAPI backend serves the Kenya food-market dataset and optional
OpenAI-backed dataset Q&A.
Supermarket-price feeds are not integrated.

## Project structure

```text
price-check-ke/
├── backend/              # FastAPI food-market data and AI API
│   ├── data/              # Supplied 20.4 MB RTFP Kenya dataset
│   ├── src/price_check_api/
│   │   ├── main.py        # API routes and CORS
│   │   ├── ai_insights.py # OpenAI-backed, dataset-grounded answers
│   │   ├── market_data.py # Dataset loading and summary
│   │   └── schemas.py     # Validated API response models
│   ├── tests/
│   └── pyproject.toml
├── frontend/             # Expo web client
│   ├── assets/            # App icons and splash images
│   ├── src/
│   │   ├── components/    # Shared UI and bottom navigation
│   │   ├── constants/     # Theme tokens and shared styles
│   │   ├── data/          # Illustrative supermarket product catalog
│   │   ├── hooks/         # Market data and local preference persistence
│   │   ├── services/      # Backend API client
│   │   ├── screens/       # Home, Search, Basket, Trends, Profile
│   │   ├── types/         # Shared TypeScript models
│   │   ├── utils/         # Pricing helpers
│   │   ├── App.tsx        # App state and screen orchestration
│   │   └── index.ts       # Expo app entry point
│   ├── app.json
│   └── package.json
├── android-native/       # Native Kotlin and Jetpack Compose Android app
│   ├── app/src/main/
│   │   ├── AndroidManifest.xml
│   │   └── java/ke/pricecheck/app/
│   │       ├── MainActivity.kt
│   │       ├── data/     # Product catalog, API and DataStore repositories
│   │       ├── domain/   # Dataset-based Q&A rules
│   │       └── ui/       # Compose screens and ViewModel
│   └── README.md
├── .gitignore
├── LICENSE
└── README.md
```

## Run the backend

In a PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\start-local.ps1
```

The API runs at `http://127.0.0.1:8000`; interactive docs are at
`http://127.0.0.1:8000/docs`. The startup script prompts for the OpenAI key
using hidden input; press Enter to start without live AI access. `OPENAI_MODEL`
is optional and defaults to `gpt-4.1-mini`. Never put this key in the Expo app.
Without a configured key, live AI is unavailable, but Trends still supports
dataset summaries and clearly labelled offline answers.

## Run the frontend

In a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run web
```

Open the local URL printed by Expo (usually `http://localhost:8081`). To run
Android instead, use `npm run android`. In an Android emulator, set
`$env:EXPO_PUBLIC_API_BASE_URL="http://10.0.2.2:8000"` in that terminal before
starting Expo. A physical Android device needs the computer's LAN IP and a
backend listening on `0.0.0.0`.

## Run the native Android app

The lecture-aligned native Android client is in `android-native/`; the Expo app
in `frontend/` is web-only. Start the backend, then run these commands from `android-native`
with Android Studio's Android SDK installed:

```powershell
.\gradlew.bat installDebug
```

The emulator API URL defaults to `http://10.0.2.2:8000`. For a physical device,
configure the computer's LAN IP with `-PAPI_BASE_URL="http://<computer-ip>:8000"`.
See [android-native/README.md](./android-native/README.md) for architecture,
lecture topic mapping, and build instructions.

## Test

```powershell
cd backend
python -m pytest
```

## Data and insight boundaries

- Supermarket products and prices are illustrative UI demo data. They are not
  live store listings, verified prices, or stock availability.
- The backend uses the supplied 55,224-row World Bank Kenya RTFP market CSV.
  Its national Market Average row has 236 months; the first 12 inflation
  values are blank, leaving 224 reported values from Jan 2008–Aug 2026.
- Trends provides year-by-year descriptive exploration and optional
  OpenAI-powered Q&A grounded in the historical RTFP data. AI answers are not
  forecasts or supermarket prices. The deterministic summary works without an
  OpenAI key.
- For a presentation without a working OpenAI key, Trends has a clearly
  labelled demo simulation. It uses fixed response rules and the loaded
  historical figures; it does not call an AI model and must not be presented as
  a live AI answer.
- If a live OpenAI question fails, Trends shows the service error and a clearly
  labelled offline answer calculated from the loaded dataset. This makes
  supported historical questions usable without API availability, but it is
  not a generated AI answer and cannot explain causes or forecast prices.
- RTFP's national food-price index cannot substantiate product-specific
  supermarket comparisons. Real price comparisons need an approved retailer or
  user-verified feed with source, location, package size, and observation time.
- Basket, budget, shopping area, and watchlist are persisted locally on this
  device. There is no account sync. The alert preference is saved, but live
  retailer feeds and push notifications are not connected.
- A backend Dockerfile is provided for deployment preparation. No hosting
  provider, production URL, or deployment has been configured.
- Before exposing the AI endpoint publicly, configure authentication and
  request-rate/cost limits. It currently validates question length and is
  intended for local development until those protections are added.

Dataset source: [World Bank Microdata Library — Monthly Food Price Estimates by
Product and Market](https://microdata.worldbank.org/index.php/catalog/6167).

See [backend/README.md](./backend/README.md) for data requirements and deployment
setup.
