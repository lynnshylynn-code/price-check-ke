import { useEffect, useState } from 'react';
import { fetchFoodInflation } from '../services/marketApi';
import { FoodInflationResponse } from '../types/market';

export function useFoodInflation() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    attempt: number;
    data: FoodInflationResponse | null;
    error: string | null;
  }>({ attempt: 0, data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    fetchFoodInflation(controller.signal)
      .then((data) => setResult({ attempt, data, error: null }))
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name === 'AbortError') return;
        setResult({
          attempt,
          data: null,
          error:
            requestError instanceof Error
              ? requestError.message
              : 'Market data could not be loaded.',
        });
      });

    return () => controller.abort();
  }, [attempt]);

  const isCurrentAttempt = result.attempt === attempt;
  return {
    data: isCurrentAttempt ? result.data : null,
    error: isCurrentAttempt ? result.error : null,
    isLoading: !isCurrentAttempt || (result.data === null && result.error === null),
    retry: () => setAttempt((current) => current + 1),
  };
}
