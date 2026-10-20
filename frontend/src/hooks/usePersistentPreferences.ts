import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useRef, useState } from 'react';
import { BasketLine } from '../types';

const STORAGE_KEY = 'price-check-ke.preferences.v1';

export type AppPreferences = {
  displayName: string;
  basket: BasketLine[];
  watchedIds: string[];
  weeklyBudget: string;
  savedBudget: number;
  shoppingArea: string;
};

const DEFAULT_PREFERENCES: AppPreferences = {
  displayName: '',
  basket: [{ productId: 'bread', quantity: 1, strategy: 'lowest' }],
  watchedIds: ['brookside-milk'],
  weeklyBudget: '700',
  savedBudget: 700,
  shoppingArea: 'Nairobi',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parsePreferences(serialized: string): AppPreferences {
  const value: unknown = JSON.parse(serialized);
  if (!isRecord(value)) throw new Error('Saved preferences are not a valid object.');

  const isBasketLine = (line: unknown): line is BasketLine =>
    isRecord(line) &&
    typeof line.productId === 'string' &&
    typeof line.quantity === 'number' &&
    Number.isInteger(line.quantity) &&
    line.quantity > 0 &&
    (line.strategy === 'lowest' || line.strategy === 'single');

  if (
    !Array.isArray(value.basket) ||
    !value.basket.every(isBasketLine) ||
    !Array.isArray(value.watchedIds) ||
    !value.watchedIds.every((id) => typeof id === 'string') ||
    typeof value.weeklyBudget !== 'string' ||
    typeof value.savedBudget !== 'number' ||
    !Number.isFinite(value.savedBudget) ||
    value.savedBudget <= 0 ||
    typeof value.shoppingArea !== 'string'
  ) {
    throw new Error('Saved preferences do not match the current app format.');
  }

  return {
    displayName: typeof value.displayName === 'string' ? value.displayName : '',
    basket: value.basket,
    watchedIds: value.watchedIds,
    weeklyBudget: value.weeklyBudget,
    savedBudget: value.savedBudget,
    shoppingArea: value.shoppingArea,
  };
}

export function usePersistentPreferences() {
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [isReady, setIsReady] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);
  const [canPersist, setCanPersist] = useState(false);
  const saveQueue = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    let active = true;

    AsyncStorage.getItem(STORAGE_KEY)
      .then((serialized) => {
        if (!active) return;
        if (serialized !== null) setPreferences(parsePreferences(serialized));
        setCanPersist(true);
        setIsReady(true);
      })
      .catch((error: unknown) => {
        console.error('Could not restore saved preferences.', error);
        if (!active) return;
        setStorageError('Saved settings could not be loaded. New changes may be lost when the app closes.');
        setIsReady(true);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!isReady || !canPersist) return;
    let active = true;
    const serialized = JSON.stringify(preferences);
    const timer = setTimeout(() => {
      saveQueue.current = saveQueue.current
        .then(() => AsyncStorage.setItem(STORAGE_KEY, serialized))
        .then(() => {
          if (active) setStorageError(null);
        })
        .catch((error: unknown) => {
          console.error('Could not save preferences.', error);
          if (active) setStorageError('Changes could not be saved on this device. Please try again later.');
        });
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [canPersist, isReady, preferences]);

  return { preferences, setPreferences, isReady, storageError };
}
