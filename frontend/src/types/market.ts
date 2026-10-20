export type FoodInflationObservation = {
  year: number;
  month: string;
  month_number: number;
  value: number;
};

export type FoodInflationResponse = {
  series: {
    country: string;
    market_scope: string;
    market_id: string;
    indicator: string;
    unit: string;
    year: number;
    source_name: string;
    source_url: string;
    source_note: string;
    coverage_start: string;
    coverage_end: string;
  };
  observations: FoodInflationObservation[];
  summary: {
    observation_count: number;
    missing_month_count: number;
    mean_value: number;
    minimum_month: string;
    minimum_value: number;
    latest_month: string;
    latest_value: number;
    previous_month: string;
    previous_value: number;
    change_from_previous: number;
    peak_month: string;
    peak_value: number;
    direction: string;
    narrative: string;
  };
};

export type PriceCommodity = 'beans' | 'maize' | 'goat';

export type PriceObservation = {
  market: string;
  county: string;
  region: string;
  date: string;
  commodity: PriceCommodity;
  price: number;
  currency: string;
  unit: string;
};

export type PriceSeriesResponse = {
  market: string;
  commodity: PriceCommodity;
  unit: string;
  currency: string;
  source_name: string;
  source_url: string;
  coverage_start: string | null;
  coverage_end: string | null;
  source_note: string;
  observations: PriceObservation[];
};

export type ProductCatalogResponse = {
  is_demo_data: true;
  disclaimer: string;
  products: import('./index').Product[];
};

export type BasketPricingResponse = {
  is_demo_data: true;
  disclaimer: string;
  strategy: 'lowest' | 'single';
  best_single_store: string | null;
  store_totals: { store: string; total: number }[];
  total: number;
  lines: {
    product_id: string;
    product_name: string;
    quantity: number;
    store: string;
    unit_price: number;
    total: number;
  }[];
};
