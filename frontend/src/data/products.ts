import { Category } from '../types';

export const CATEGORIES: Category[] = [
  'All',
  'Dairy',
  'Bakery',
  'Pantry',
  'Produce',
  'Household',
  'Non-food',
];

export const MONTHLY_FOOD_INFLATION = [
  { month: 'Jan', value: -1.53 },
  { month: 'Feb', value: 4.61 },
  { month: 'Mar', value: 5.14 },
  { month: 'Apr', value: 8.13 },
  { month: 'May', value: 13.12 },
  { month: 'Jun', value: 8.63 },
  { month: 'Jul', value: 9.3 },
  { month: 'Aug', value: 10.46 },
];

export const categoryCode: Record<Exclude<Category, 'All'>, string> = {
  Dairy: 'DAIRY',
  Bakery: 'BREAD',
  Pantry: 'PANTRY',
  Produce: 'FRESH',
  Household: 'HOME',
  'Non-food': 'OTHER',
};
