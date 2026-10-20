import { BasketLine, BasketStoreTotal, Product } from '../types';

export const money = (value: number) => `KSh ${Math.round(value).toLocaleString('en-KE')}`;
export const bestPrice = (product: Product) =>
  product.prices.reduce((best, item) => (item.price < best.price ? item : best));
export const basketPrice = (
  product: Product,
  strategy: 'lowest' | 'single',
  singleStore?: string | null,
) =>
  strategy === 'single'
    ? product.prices.find((item) => item.store === singleStore) ?? bestPrice(product)
    : bestPrice(product);

export function compareBasketStores(
  basket: BasketLine[],
  products: Product[],
): BasketStoreTotal[] {
  if (basket.length === 0) return [];

  const storeNames = new Set<string>();
  for (const line of basket) {
    const product = products.find((item) => item.id === line.productId);
    if (!product) return [];
    for (const price of product.prices) storeNames.add(price.store);
  }

  return [...storeNames]
    .map((store) => {
      let total = 0;
      for (const line of basket) {
        const product = products.find((item) => item.id === line.productId);
        const price = product?.prices.find((item) => item.store === store);
        if (!price) return null;
        total += price.price * line.quantity;
      }
      return { store, total };
    })
    .filter((item): item is BasketStoreTotal => item !== null)
    .sort((a, b) => a.total - b.total || a.store.localeCompare(b.store));
}
