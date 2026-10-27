# Price Check KE — Native Android app

This is the native Android client, implemented in Kotlin and Jetpack Compose to
match the mobile-development lecture topics. The existing Expo client remains
the web application in `../frontend/`.

## Splash screen

- `SplashActivity` is the launcher activity (lecture-style delayed hand-off to
  `MainActivity` with a `Handler` on the main looper). The delay is a named
  constant in `SplashActivity`; pending callbacks are removed in `onDestroy`,
  and Back cancels the timer and finishes the splash.
- On Android 12 and later, the system shows its own splash screen before any
  activity layout. `Theme.PriceCheck` sets `android:windowSplashScreenBackground`
  so that system splash matches the in-app splash background colour.
- Google discourages artificial splash delays in production apps; the
  recommended approach is [`androidx.core:core-splashscreen`](https://developer.android.com/develop/ui/views/launch/splash-screen)
  to keep the system splash visible only until the app is ready, without an
  extra timed screen.

## Architecture

- After the splash, `MainActivity` hosts a `NavHostFragment` (`nav_graph.xml`)
  starting at `PriceCheckFragment`, with a Material toolbar wired through
  `setupActionBarWithNavController` (hidden on the home destination). Activity
  lifecycle callbacks, including `onRestart`, log under the `PriceCheckLifecycle`
  Logcat tag.
- `PriceCheckFragment` hosts the Compose shopping screens and navigates to
  `WatchlistFragment`, the store hand-off / checkout / order-status demo flow,
  and `AboutActivity` through the Navigation Component. Fragment arguments use
  `Bundle` keys in `NavArgs` instead of the Safe Args Gradle plugin so this
  project stays compatible with the current AGP/Kotlin toolchain without an
  extra code-generation plugin.
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
  market observations, and answers from the locally trained assistant with source, intent confidence, and coverage.
  User preferences, shopping area, and basket data are saved locally with
  DataStore.

## Lecture topics demonstrated

- Kotlin classes, data classes, collections, and coroutines for network and
  persistence work off the main thread.
- Jetpack Compose and Material 3 shopping screens, including light/dark color
  schemes, typography, shapes, animations, and previews.
- Compose `LazyColumn` / `LazyRow` for Compose content and View-system
  `RecyclerView` specifically for the watchlist.
- A top-bar Compose options menu, XML watchlist sort and layout menu, persistent
  list/grid view using `LinearLayoutManager` and `GridLayoutManager`, and a true
  long-press context menu for watchlist actions.
- An XML `AboutActivity` layout with an Up button connected to its declared
  `MainActivity` parent and lifecycle logging for the Android activity callbacks.
- Separate UI, application/state-holder, and data/repository layers.
- Resource-backed UI strings and a mipmap adaptive launcher icon.
- The Home screen area picker is populated from `GET /api/markets` and includes
  only counties with at least one market that has available commodities. Kitui
  is the default when no saved selection is valid; saved legacy enum names are
  matched case-insensitively and normalized to the API county name.
- Market data shows the latest observation date for each market and commodity.
  Missing county/commodity observations are displayed explicitly rather than
  estimated.
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

## Retailer listings and prototype ordering

The app loads `/api/v1/listings` from the backend and groups exact normalized
item-name and pack-size matches for comparison. If the API is unavailable, the
bundled `snapshot 20 Oct 2026` JSON asset is used. Demo catalog prices are a
last-resort fallback and remain visibly labelled as demo data. Retailer values
are advertised snapshot prices; stock and checkout prices are not verified.

The checkout flow is a prototype. It creates a local backend order record and
uses the mock payment provider by default; it does not submit an order to a
supermarket or move real money. Listing hand-off buttons open the retailer URL
in a browser. Delivery fee is set by the retailer at its own checkout and is
not estimated here. Address and phone data are sent to the local backend for
the prototype order and can be erased from the status screen.

### Lecture topics mapped to code

| Topic | Code location | Demonstration |
| --- | --- | --- |
| Fragments and back stack | `PriceCheckFragment`, `StoreHandoffFragment`, `CheckoutFragment`, `OrderStatusFragment` | Each step replaces the content fragment and is added to the back stack; checkout state is shared with `activityViewModels`. |
| Implicit intents | `StoreHandoffFragment` | `ACTION_VIEW` opens each listing URL; `ACTION_SEND` shares the basket as plain text. Missing browser apps are handled. |
| Runtime permissions | `CheckoutFragment`, `OrderStatusFragment` | Optional coarse location and Android 13+ notification permission are requested at runtime; denial leaves the main flow available. |
| Notifications | `OrderStatusFragment` | Creates a notification channel and notifies when the order reaches `paid_sandbox`, subject to notification permission. |
| Forms and validation | `CheckoutScreen`, `CheckoutViewModel` | Address and Kenyan phone fields show inline validation before the order request. |
| Offline data | `ListingsRepository`, `generate_android_listings_snapshot.py` | The backend snapshot asset supplies listings when the API cannot be reached. |

Generate the bundled snapshot after changing the source CSV:

```powershell
cd backend
python scripts/generate_android_listings_snapshot.py
```

For the optional Daraja sandbox, configure the backend-only environment
variables documented in `../backend/README.md` and expose a public HTTPS
callback URL. No Daraja credentials are stored in this Android app.

## Verify

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```
