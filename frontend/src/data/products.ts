import { Category, Product } from '../types';

export const PRODUCTS: Product[] = [
  {
    id: 'bread',
    name: 'Supa Loaf Bread',
    size: '400g',
    description: 'White sandwich loaf',
    category: 'Bakery',
    prices: [
      { store: 'Naivas', price: 65, stock: 'In stock' },
      { store: 'Carrefour', price: 69, stock: 'In stock' },
      { store: 'Jaza', price: 70, stock: 'In stock' },
      { store: 'Quickmart', price: 72, stock: 'In stock' },
    ],
  },
  {
    id: 'yoghurt',
    name: 'KCC Yoghurt',
    size: '500ml',
    description: 'Natural probiotic yoghurt',
    category: 'Dairy',
    prices: [
      { store: 'Jaza', price: 110, stock: 'In stock' },
      { store: 'Naivas', price: 115, stock: 'In stock' },
      { store: 'Carrefour', price: 119, stock: 'In stock' },
    ],
  },
  {
    id: 'brookside-milk',
    name: 'Brookside Milk',
    size: '1L',
    description: 'Long life full cream',
    category: 'Dairy',
    prices: [
      { store: 'Carrefour', price: 139, stock: 'In stock' },
      { store: 'Naivas', price: 145, stock: 'Low stock' },
      { store: 'Jaza', price: 147, stock: 'In stock' },
      { store: 'Quickmart', price: 150, stock: 'In stock' },
    ],
  },
  {
    id: 'fresha-milk',
    name: 'Fresha Milk',
    size: '1L',
    description: 'Fresh whole milk',
    category: 'Dairy',
    prices: [
      { store: 'Naivas', price: 145, stock: 'In stock' },
      { store: 'Jaza', price: 149, stock: 'In stock' },
      { store: 'Quickmart', price: 152, stock: 'In stock' },
    ],
  },
  {
    id: 'cooking-oil',
    name: 'Fresh Fri Cooking Oil',
    size: '1L',
    description: 'Pure vegetable oil',
    category: 'Pantry',
    prices: [
      { store: 'Carrefour', price: 245, stock: 'In stock' },
      { store: 'Naivas', price: 252, stock: 'In stock' },
      { store: 'Jaza', price: 256, stock: 'In stock' },
      { store: 'Quickmart', price: 259, stock: 'In stock' },
    ],
  },
  {
    id: 'sugar',
    name: 'Kabras Sugar',
    size: '2kg',
    description: 'Fine white sugar',
    category: 'Pantry',
    prices: [
      { store: 'Quickmart', price: 280, stock: 'In stock' },
      { store: 'Naivas', price: 289, stock: 'In stock' },
      { store: 'Jaza', price: 292, stock: 'In stock' },
      { store: 'Carrefour', price: 295, stock: 'In stock' },
    ],
  },
  {
    id: 'tomatoes',
    name: 'Fresh Tomatoes',
    size: '1kg',
    description: 'Fresh market tomatoes',
    category: 'Produce',
    prices: [
      { store: 'Naivas', price: 120, stock: 'In stock' },
      { store: 'Carrefour', price: 135, stock: 'In stock' },
      { store: 'Jaza', price: 125, stock: 'In stock' },
      { store: 'Quickmart', price: 130, stock: 'In stock' },
    ],
  },
  {
    id: 'onions',
    name: 'Red Onions',
    size: '1kg',
    description: 'Fresh red onions',
    category: 'Produce',
    prices: [
      { store: 'Naivas', price: 150, stock: 'In stock' },
      { store: 'Carrefour', price: 160, stock: 'In stock' },
      { store: 'Jaza', price: 145, stock: 'In stock' },
      { store: 'Quickmart', price: 155, stock: 'In stock' },
    ],
  },
  {
    id: 'maize-flour',
    name: 'Soko Maize Flour',
    size: '2kg',
    description: 'Fortified sifted maize flour',
    category: 'Pantry',
    prices: [
      { store: 'Naivas', price: 165, stock: 'In stock' },
      { store: 'Carrefour', price: 172, stock: 'In stock' },
      { store: 'Jaza', price: 168, stock: 'In stock' },
      { store: 'Quickmart', price: 170, stock: 'In stock' },
    ],
  },
  {
    id: 'eggs',
    name: 'Farm Fresh Eggs',
    size: 'Tray of 15',
    description: 'Medium-size eggs',
    category: 'Dairy',
    prices: [
      { store: 'Naivas', price: 330, stock: 'In stock' },
      { store: 'Carrefour', price: 345, stock: 'In stock' },
      { store: 'Jaza', price: 325, stock: 'In stock' },
      { store: 'Quickmart', price: 335, stock: 'In stock' },
    ],
  },
];

export const CATEGORIES: Category[] = ['All', 'Dairy', 'Bakery', 'Pantry', 'Produce'];

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
};
