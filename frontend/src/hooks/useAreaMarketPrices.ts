import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';
import { fetchPriceSeries } from '../services/marketApi';
import { PriceSeriesResponse } from '../types/market';

const CACHE_PREFIX = 'price-check-ke.market-prices.v1.';

type AreaPrices = {
  area: string;
  beans: PriceSeriesResponse | null;
  maize: PriceSeriesResponse | null;
  loading: boolean;
  error: string | null;
  fromCache: boolean;
};

function isPriceSeries(value: unknown): value is PriceSeriesResponse {
  if (typeof value !== 'object' || value === null) return false;
  const item = value as Partial<PriceSeriesResponse>;
  return (
    typeof item.market === 'string' &&
    (item.commodity === 'beans' || item.commodity === 'maize') &&
    typeof item.unit === 'string' &&
    typeof item.currency === 'string' &&
    typeof item.source_name === 'string' &&
    typeof item.source_url === 'string' &&
    (item.coverage_start === null || typeof item.coverage_start === 'string') &&
    (item.coverage_end === null || typeof item.coverage_end === 'string') &&
    typeof item.source_note === 'string' &&
    Array.isArray(item.observations) &&
    item.observations.every(
      (row) =>
        typeof row === 'object' &&
        row !== null &&
        typeof row.market === 'string' &&
        typeof row.county === 'string' &&
        typeof row.region === 'string' &&
        typeof row.date === 'string' &&
        typeof row.price === 'number' &&
        typeof row.currency === 'string' &&
        typeof row.unit === 'string',
    )
  );
}

function readCachedPrices(serialized: string): Pick<AreaPrices, 'beans' | 'maize'> {
  const parsed: unknown = JSON.parse(serialized);
  if (typeof parsed !== 'object' || parsed === null || !('beans' in parsed) || !('maize' in parsed)) {
    throw new Error('Cached market prices have an invalid format.');
  }
  const prices = parsed as { beans: unknown; maize: unknown };
  if (
    (prices.beans !== null && !isPriceSeries(prices.beans)) ||
    (prices.maize !== null && !isPriceSeries(prices.maize))
  ) {
    throw new Error('Cached market prices do not match the current format.');
  }
  return {
    beans: prices.beans,
    maize: prices.maize,
  };
}

function trimCachedSeries(series: PriceSeriesResponse): PriceSeriesResponse {
  return {
    ...series,
    observations: series.observations.slice(-24),
  };
}

export function useAreaMarketPrices(area: string) {
  const [result, setResult] = useState<AreaPrices>({
    area,
    beans: null,
    maize: null,
    loading: true,
    error: null,
    fromCache: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    async function loadPrices() {
      let cached: Pick<AreaPrices, 'beans' | 'maize'> | null = null;
      try {
        const serialized = await AsyncStorage.getItem(`${CACHE_PREFIX}${area}`);
        if (serialized) {
          cached = readCachedPrices(serialized);
          if (active) setResult({ area, ...cached, loading: true, error: null, fromCache: true });
        }
      } catch (error) {
        console.error('Could not read cached market prices.', error);
      }

      try {
        const [beans, maize] = await Promise.all([
          fetchPriceSeries(area, 'beans', controller.signal),
          fetchPriceSeries(area, 'maize', controller.signal),
        ]);
        if (!active) return;
        setResult({ area, beans, maize, loading: false, error: null, fromCache: false });
        try {
          await AsyncStorage.setItem(
            `${CACHE_PREFIX}${area}`,
            JSON.stringify({
              beans: trimCachedSeries(beans),
              maize: trimCachedSeries(maize),
            }),
          );
        } catch (error) {
          console.error('Could not cache market prices.', error);
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') return;
        if (!active) return;
        setResult({
          area,
          ...(cached ?? { beans: null, maize: null }),
          loading: false,
          error:
            error instanceof Error
              ? error.message
              : 'Market prices could not be loaded from the API.',
          fromCache: cached !== null,
        });
      }
    }

    void loadPrices();
    return () => {
      active = false;
      controller.abort();
    };
  }, [area]);

  return result.area === area
    ? result
    : {
        area,
        beans: null,
        maize: null,
        loading: true,
        error: null,
        fromCache: false,
      };
}
