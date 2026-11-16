export type Tab = 'Home' | 'Search' | 'Basket' | 'Trends' | 'Profile';
export type Category =
  | 'All'
  | 'Dairy'
  | 'Bakery'
  | 'Pantry'
  | 'Produce'
  | 'Household'
  | 'Non-food';
export type StorePrice = {
  store: string;
  location_id: string;
  location_name: string;
  location_context: string;
  item_name: string;
  price: number;
  regular_price: number | null;
  product_url: string;
  observed_at: string;
};
export type Product = {
  id: string;
  name: string;
  size: string;
  description: string;
  category: Exclude<Category, 'All'>;
  comparison_note: string | null;
  missing_at_stores: string[];
  prices: StorePrice[];
};
export type BasketLine = { productId: string; quantity: number; strategy: 'lowest' | 'single' };
export type BasketStoreTotal = {
  store: string;
  location_id: string;
  total: number;
};
