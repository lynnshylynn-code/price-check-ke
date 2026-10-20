import { useEffect, useState } from 'react';
import { fetchBasketPricing } from '../services/marketApi';
import { BasketLine } from '../types';
import { BasketPricingResponse } from '../types/market';

type PricingState = {
  key: string;
  pricing: BasketPricingResponse | null;
  error: string | null;
  loading: boolean;
};

export function useBasketPricing(items: BasketLine[]) {
  const key = JSON.stringify(items);
  const [state, setState] = useState<PricingState>({
    key: '',
    pricing: null,
    error: null,
    loading: false,
  });

  useEffect(() => {
    if (items.length === 0) return;

    const controller = new AbortController();
    let active = true;
    const strategy = items[0]?.strategy ?? 'lowest';

    fetchBasketPricing(items, strategy, controller.signal)
      .then((result) => {
        if (active) setState({ key, pricing: result, error: null, loading: false });
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name === 'AbortError') return;
        if (!active) return;
        setState({
          key,
          pricing: null,
          error:
            requestError instanceof Error
              ? requestError.message
              : 'Basket pricing could not be loaded from the API.',
          loading: false,
        });
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [items, key]);

  const stateMatchesBasket = state.key === key;
  return {
    pricing: stateMatchesBasket ? state.pricing : null,
    error: stateMatchesBasket ? state.error : null,
    loading: items.length > 0 && (!stateMatchesBasket || state.loading),
  };
}
