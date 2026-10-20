export type Tab = 'Home' | 'Search' | 'Basket' | 'Trends' | 'Profile';
export type Category = 'All' | 'Dairy' | 'Bakery' | 'Pantry' | 'Produce';
export type StorePrice = { store: string; price: number; stock: string };
export type Product = {
  id: string;
  name: string;
  size: string;
  description: string;
  category: Exclude<Category, 'All'>;
  prices: StorePrice[];
};
export type BasketLine = { productId: string; quantity: number; strategy: 'lowest' | 'single' };
export type BasketStoreTotal = {
  store: string;
  total: number;
};
