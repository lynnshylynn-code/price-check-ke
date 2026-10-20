export const SHOPPING_AREAS = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru'] as const;
export type ShoppingArea = (typeof SHOPPING_AREAS)[number];
