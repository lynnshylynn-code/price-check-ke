import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';
import { fetchProductCatalog, isProductCatalogResponse } from '../services/marketApi';
import { Product } from '../types';

const CACHE_KEY_PREFIX = 'price-check-ke.verified-product-catalog.v2.';

export function useProductCatalog(area: string) {
  const [products, setProducts] = useState<Product[]>([]);
  const [dataLabel, setDataLabel] = useState('Verified retailer listings');
  const [caveats, setCaveats] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [catalogArea, setCatalogArea] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const cacheKey = `${CACHE_KEY_PREFIX}${area.toLowerCase()}`;

    async function loadCatalog() {
      try {
        const serialized = await AsyncStorage.getItem(cacheKey);
        if (serialized) {
          const cached: unknown = JSON.parse(serialized);
          if (isProductCatalogResponse(cached) && cached.area.toLowerCase() === area.toLowerCase() && active) {
            setProducts(cached.products);
            setDataLabel(cached.data_label);
            setCaveats(cached.caveats);
            setFromCache(true);
            setError(null);
            setCatalogArea(area);
          }
        }
      } catch (cacheError) {
        console.error('Could not read the cached product catalog.', cacheError);
      }

      try {
        const catalog = await fetchProductCatalog(area, controller.signal);
        if (!active) return;
        setProducts(catalog.products);
        setDataLabel(catalog.data_label);
        setCaveats(catalog.caveats);
        setError(null);
        setFromCache(false);
        setCatalogArea(area);
        try {
          await AsyncStorage.setItem(cacheKey, JSON.stringify(catalog));
        } catch (cacheError) {
          console.error('Could not cache the product catalog.', cacheError);
        }
      } catch (requestError) {
        if (requestError instanceof Error && requestError.name === 'AbortError') return;
        if (!active) return;
        setProducts([]);
        setDataLabel('Verified retailer listings');
        setCaveats('');
        setFromCache(false);
        setCatalogArea(area);
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
  }, [area]);

  const catalogMatchesArea = catalogArea.toLowerCase() === area.toLowerCase();
  return {
    products: catalogMatchesArea ? products : [],
    dataLabel: catalogMatchesArea ? dataLabel : 'Verified retailer listings',
    caveats: catalogMatchesArea ? caveats : '',
    loading: !catalogMatchesArea || loading,
    error: catalogMatchesArea ? error : null,
    fromCache: catalogMatchesArea && fromCache,
  };
}
