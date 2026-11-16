import { BasketLine, BasketStoreTotal, Product } from '../types';

export const money = (value: number) => `KSh ${Math.round(value).toLocaleString('en-KE')}`;
export const bestPrice = (product: Product) =>
  product.prices.reduce((best, item) => (item.price < best.price ? item : best));
export const storeLocationLabel = (price: Product['prices'][number]) =>
  `${price.store} - ${price.location_name}`;
export const basketPrice = (
  product: Product,
  strategy: 'lowest' | 'single',
  singleStore?: string | null,
) =>
  strategy === 'single'
    ? product.prices.find((item) => item.location_id === singleStore) ?? bestPrice(product)
    : bestPrice(product);

export function compareBasketStores(
  basket: BasketLine[],
  products: Product[],
): BasketStoreTotal[] {
  if (basket.length === 0) return [];

  const locationIds = new Set<string>();
  for (const line of basket) {
    const product = products.find((item) => item.id === line.productId);
    if (!product) return [];
    for (const price of product.prices) locationIds.add(price.location_id);
  }

  return [...locationIds]
    .map((locationId) => {
      let total = 0;
      let label = '';
      for (const line of basket) {
        const product = products.find((item) => item.id === line.productId);
        const price = product?.prices.find((item) => item.location_id === locationId);
        if (!price) return null;
        label = storeLocationLabel(price);
        total += price.price * line.quantity;
      }
      return { store: label, location_id: locationId, total };
    })
    .filter((item): item is BasketStoreTotal => item !== null)
    .sort((a, b) => a.total - b.total || a.store.localeCompare(b.store));
}
