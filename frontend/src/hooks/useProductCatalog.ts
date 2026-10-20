import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';
import { PRODUCTS } from '../data/products';
import { fetchProductCatalog, isProductCatalogResponse } from '../services/marketApi';
import { Product } from '../types';

const CACHE_KEY = 'price-check-ke.product-catalog.v1';

export function useProductCatalog() {
  const [products, setProducts] = useState<Product[]>(PRODUCTS);
  const [disclaimer, setDisclaimer] = useState(
    'Illustrative supermarket prices for demonstration only; not live retailer quotes.',
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    async function loadCatalog() {
      try {
        const serialized = await AsyncStorage.getItem(CACHE_KEY);
        if (serialized) {
          const cached: unknown = JSON.parse(serialized);
          if (isProductCatalogResponse(cached) && active) {
            setProducts(cached.products);
            setDisclaimer(cached.disclaimer);
            setFromCache(true);
          }
        }
      } catch (cacheError) {
        console.error('Could not read the cached product catalog.', cacheError);
      }

      try {
        const catalog = await fetchProductCatalog(controller.signal);
        if (!active) return;
        setProducts(catalog.products);
        setDisclaimer(catalog.disclaimer);
        setError(null);
        setFromCache(false);
        try {
          await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(catalog));
        } catch (cacheError) {
          console.error('Could not cache the product catalog.', cacheError);
        }
      } catch (requestError) {
        if (requestError instanceof Error && requestError.name === 'AbortError') return;
        if (!active) return;
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'The product catalog could not be loaded.',
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadCatalog();
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  return { products, disclaimer, loading, error, fromCache };
}
