# Price Check KE

An Android-first Expo app prototype for Kenyan shoppers. It follows the Pricewise
mockup: Home, Search and product comparisons, Basket, Trends, and Profile.

## Run on Android

```powershell
npm install
npm run android
```

Use an Android emulator or a device with Expo Go installed. The project is
configured for Android; iOS is not a target for this app.

## Data and insight boundaries

- The sample supermarket products and retailer prices are illustrative UI demo
  data. They are not live store listings, verified prices, or stock availability.
- The supplied notebook describes the World Bank's Kenya Monthly Food Price
  Estimates by Product and Market (RTFP) dataset and includes a national
  market-average excerpt for January–August 2026. The Trends chart uses those
  eight `inflation_food_price_index` values from the notebook output.
- The notebook does not include the source CSV itself. The full RTFP file is
  not bundled, and the app currently does not import or query it.
- The market insight is a transparent, deterministic summary of that excerpt.
  There is no generative AI service, retailer feed, sign-in, or price-alert
  backend connected yet.

Dataset source: [World Bank Microdata Library — Monthly Food Price Estimates by
Product and Market](https://microdata.worldbank.org/index.php/catalog/6167).
