import {
  BasketPricingResponse,
  FoodInflationResponse,
  PriceCommodity,
  ProductCatalogResponse,
  PriceSeriesResponse,
} from '../types/market';
import { BasketLine } from '../types';

export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(
  /\/$/,
  '',
);

function isFoodInflationResponse(value: unknown): value is FoodInflationResponse {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<FoodInflationResponse>;
  return (
    typeof payload.series?.country === 'string' &&
    typeof payload.series.market_scope === 'string' &&
    typeof payload.series.market_id === 'string' &&
    typeof payload.series.indicator === 'string' &&
    typeof payload.series.unit === 'string' &&
    typeof payload.series.year === 'number' &&
    typeof payload.series.source_name === 'string' &&
    typeof payload.series.source_url === 'string' &&
    typeof payload.series.source_note === 'string' &&
    typeof payload.series.coverage_start === 'string' &&
    typeof payload.series.coverage_end === 'string' &&
    Array.isArray(payload.observations) &&
    payload.observations.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        typeof item.year === 'number' &&
        typeof item.month === 'string' &&
        typeof item.month_number === 'number' &&
        typeof item.value === 'number',
    ) &&
    typeof payload.summary?.latest_month === 'string' &&
    typeof payload.summary.observation_count === 'number' &&
    typeof payload.summary.missing_month_count === 'number' &&
    typeof payload.summary.mean_value === 'number' &&
    typeof payload.summary.minimum_month === 'string' &&
    typeof payload.summary.minimum_value === 'number' &&
    typeof payload.summary.latest_value === 'number' &&
    typeof payload.summary.previous_month === 'string' &&
    typeof payload.summary.previous_value === 'number' &&
    typeof payload.summary.change_from_previous === 'number' &&
    typeof payload.summary.peak_month === 'string' &&
    typeof payload.summary.peak_value === 'number' &&
    typeof payload.summary.direction === 'string' &&
    typeof payload.summary.narrative === 'string'
  );
}

export async function fetchFoodInflation(
  signal?: AbortSignal,
): Promise<FoodInflationResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/market/food-inflation`, { signal });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(
      `Could not reach the Price Check KE API at ${API_BASE_URL}. Check that the backend is running and that EXPO_PUBLIC_API_BASE_URL points to it.`,
    );
  }

  if (!response.ok) {
    throw new Error(`Market data request failed with HTTP ${response.status}.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Market data API returned invalid JSON.');
  }
  if (!isFoodInflationResponse(payload)) {
    throw new Error('Market data API returned an unexpected response.');
  }
  return payload;
}

function isPriceSeriesResponse(value: unknown): value is PriceSeriesResponse {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<PriceSeriesResponse>;
  return (
    typeof payload.market === 'string' &&
    (payload.commodity === 'beans' || payload.commodity === 'maize' || payload.commodity === 'goat') &&
    typeof payload.unit === 'string' &&
    typeof payload.currency === 'string' &&
    typeof payload.source_name === 'string' &&
    typeof payload.source_url === 'string' &&
    (payload.coverage_start === null || typeof payload.coverage_start === 'string') &&
    (payload.coverage_end === null || typeof payload.coverage_end === 'string') &&
    typeof payload.source_note === 'string' &&
    Array.isArray(payload.observations) &&
    payload.observations.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        typeof item.market === 'string' &&
        typeof item.county === 'string' &&
        typeof item.region === 'string' &&
        typeof item.date === 'string' &&
        typeof item.price === 'number' &&
        typeof item.currency === 'string' &&
        typeof item.unit === 'string',
    )
  );
}

export async function fetchPriceSeries(
  market: string,
  commodity: PriceCommodity,
  signal?: AbortSignal,
): Promise<PriceSeriesResponse> {
  const query = new URLSearchParams({ market, commodity });
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/prices?${query.toString()}`, { signal });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(`Could not reach the market data API at ${API_BASE_URL}.`);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Market price API returned invalid JSON.');
  }
  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `Market price request failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }
  if (!isPriceSeriesResponse(payload)) {
    throw new Error('Market price API returned an unexpected response.');
  }
  return payload;
}

export async function fetchProductCatalog(
  area: string,
  signal?: AbortSignal,
): Promise<ProductCatalogResponse> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/products?area=${encodeURIComponent(area)}`,
      { signal },
    );
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(`Could not reach the product catalog API at ${API_BASE_URL}.`);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Product catalog API returned invalid JSON.');
  }
  if (!response.ok) throw new Error(`Product catalog request failed with HTTP ${response.status}.`);
  if (!isProductCatalogResponse(payload)) {
    throw new Error('Product catalog API returned an unexpected response.');
  }
  return payload;
}

export function isProductCatalogResponse(value: unknown): value is ProductCatalogResponse {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<ProductCatalogResponse>;
  const categories = ['Dairy', 'Bakery', 'Pantry', 'Produce', 'Household', 'Non-food'];
  return (
    payload.is_demo_data === false &&
    typeof payload.area === 'string' &&
    typeof payload.data_label === 'string' &&
    typeof payload.caveats === 'string' &&
    Array.isArray(payload.products) &&
    payload.products.every(
      (product) =>
        typeof product === 'object' &&
        product !== null &&
        typeof product.id === 'string' &&
        typeof product.name === 'string' &&
        typeof product.size === 'string' &&
        typeof product.description === 'string' &&
        typeof product.category === 'string' &&
        categories.includes(product.category) &&
        (typeof product.comparison_note === 'string' || product.comparison_note === null) &&
        Array.isArray(product.missing_at_stores) &&
        product.missing_at_stores.every((store) => typeof store === 'string') &&
        Array.isArray(product.prices) &&
        product.prices.every(
          (price) =>
            typeof price.store === 'string' &&
            typeof price.location_id === 'string' &&
            typeof price.location_name === 'string' &&
            typeof price.location_context === 'string' &&
            typeof price.item_name === 'string' &&
            typeof price.price === 'number' &&
            (typeof price.regular_price === 'number' || price.regular_price === null) &&
            typeof price.product_url === 'string' &&
            price.product_url.startsWith('https://') &&
            typeof price.observed_at === 'string' &&
            Number.isFinite(Date.parse(price.observed_at)),
        ),
    )
  );
}

export function isBasketPricingResponse(value: unknown): value is BasketPricingResponse {
  if (typeof value !== 'object' || value === null) return false;
  const payload = value as Partial<BasketPricingResponse>;
  return (
    payload.is_demo_data === false &&
    typeof payload.disclaimer === 'string' &&
    (payload.strategy === 'lowest' || payload.strategy === 'single') &&
    (payload.best_single_store === null || typeof payload.best_single_store === 'string') &&
    (payload.best_single_location_id === null ||
      typeof payload.best_single_location_id === 'string') &&
    typeof payload.total === 'number' &&
    Array.isArray(payload.store_totals) &&
    payload.store_totals.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        typeof item.store === 'string' &&
        typeof item.location_id === 'string' &&
        typeof item.total === 'number',
    ) &&
    Array.isArray(payload.lines) &&
    payload.lines.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        typeof item.product_id === 'string' &&
        typeof item.store === 'string' &&
        typeof item.location_id === 'string' &&
        typeof item.unit_price === 'number' &&
        typeof item.total === 'number',
    )
  );
}

export async function fetchBasketPricing(
  items: BasketLine[],
  strategy: 'lowest' | 'single',
  area: string,
  signal?: AbortSignal,
): Promise<BasketPricingResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/basket/pricing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: items.map(({ productId, quantity }) => ({ product_id: productId, quantity })),
        strategy,
        area,
      }),
      signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(`Could not reach the basket pricing API at ${API_BASE_URL}.`);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Basket pricing API returned invalid JSON.');
  }
  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `Basket pricing request failed with HTTP ${response.status}.`;
    throw new Error(detail);
  }
  if (!isBasketPricingResponse(payload)) {
    throw new Error('Basket pricing API returned an unexpected response.');
  }
  return payload;
}
