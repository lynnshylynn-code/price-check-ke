# Price Check KE — Native Android app

This is the native Android client, implemented in Kotlin and Jetpack Compose to
match the mobile-development lecture topics. The existing Expo client remains
the web application in `../frontend/`.

## Architecture

- `MainActivity` is the Android entry Activity; it hosts `PriceCheckFragment`.
  Activity lifecycle callbacks, including `onRestart`, log under the
  `PriceCheckLifecycle` Logcat tag.
- `PriceCheckFragment` hosts the Compose shopping screens and opens
  `WatchlistFragment` through a `FragmentManager` transaction on the back stack.
  Both fragments share the Activity-scoped `PriceCheckViewModel`.
- `WatchlistFragment` uses a View-system `RecyclerView`, `LinearLayoutManager`,
  `ListAdapter`, `DiffUtil`, and a `ViewHolder`. It inflates its XML sorting
  menu through `MenuProvider` / `MenuInflater`; product long-press actions use
  `PopupMenu`.
- `AboutActivity` is launched with an explicit Intent. Basket sharing uses
  `ACTION_SEND` with plain text.
- Fragment lifecycle callbacks are logged under
  `PriceCheckFragmentLifecycle`.
- `ui/` contains Compose screens and a `PriceCheckViewModel` state holder.
  Screens receive state and event callbacks; the ViewModel handles app logic.
- `data/` contains an in-memory `ProductRepository`, the FastAPI market-data
  repository, and the Preferences DataStore repository.
- `domain/` contains pure basket-pricing functions and the local
  dataset-question response rules.
- The backend supplies the RTFP historical index, available beans and maize
  market observations, and optional OpenAI answers with source and coverage.
  User preferences, shopping area, and basket data are saved locally with
  DataStore.

## Lecture topics demonstrated

- Kotlin classes, data classes, collections, and coroutines for network and
  persistence work off the main thread.
- Jetpack Compose and Material 3 shopping screens, including light/dark color
  schemes, typography, shapes, animations, and previews.
- Compose `LazyColumn` / `LazyRow` for Compose content and View-system
  `RecyclerView` specifically for the watchlist.
- A top-bar Compose options menu and product contextual menu, plus the
  watchlist XML sort menu and View-system context `PopupMenu`.
- Separate UI, application/state-holder, and data/repository layers.
- Resource-backed UI strings and a mipmap adaptive launcher icon.
- The Home screen area picker selects the matching Nairobi, Mombasa, Kisumu,
  or Nakuru county in the backend market dataset. Some county/commodity pairs
  have no recorded prices; the app displays that gap instead of estimating.
- Supermarket product prices are labelled demo data and do not vary with the
  selected area. Market observations come from the World Bank RTFP dataset.

## Run on an Android emulator

Start the API in another terminal from `../backend`:

```powershell
.\start-local.ps1
```

Then from this folder, with Android Studio's SDK installed:

```powershell
.\gradlew.bat installDebug
```

The default API URL `http://10.0.2.2:8000` reaches the host computer's
`127.0.0.1:8000` from the Android emulator. For a physical device, use the
computer's LAN address and start Uvicorn with `--host 0.0.0.0`:

```powershell
.\gradlew.bat installDebug -PAPI_BASE_URL="http://192.168.1.10:8000"
```

Replace the sample LAN address with the computer's actual address. Use HTTPS
for a deployed API. Cleartext traffic is enabled only when the configured
development API URL uses HTTP.

## Verify

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```
