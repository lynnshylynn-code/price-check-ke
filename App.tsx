import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import React, { useMemo, useState } from 'react';
import {
  Keyboard,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

type Tab = 'Home' | 'Search' | 'Basket' | 'Trends' | 'Profile';
type Category = 'All' | 'Dairy' | 'Bakery' | 'Pantry' | 'Produce';
type StorePrice = { store: string; price: number; stock: string };
type Product = {
  id: string;
  name: string;
  size: string;
  description: string;
  category: Exclude<Category, 'All'>;
  prices: StorePrice[];
};
type BasketLine = { productId: string; quantity: number; strategy: 'lowest' | 'single' };

const COLORS = {
  background: '#F3F6F1',
  surface: '#FFFFFF',
  green: '#07583E',
  deepGreen: '#064A36',
  mint: '#96F1C1',
  text: '#17231D',
  muted: '#768078',
  border: '#E3E9E2',
  paleGreen: '#E2F7EA',
  orange: '#F27E5E',
};

const PRODUCTS: Product[] = [
  {
    id: 'bread',
    name: 'Supa Loaf Bread',
    size: '400g',
    description: 'White sandwich loaf',
    category: 'Bakery',
    prices: [
      { store: 'Naivas', price: 65, stock: 'In stock' },
      { store: 'Carrefour', price: 69, stock: 'In stock' },
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
      { store: 'Carrefour', price: 295, stock: 'In stock' },
    ],
  },
];

const CATEGORIES: Category[] = ['All', 'Dairy', 'Bakery', 'Pantry', 'Produce'];
const STORES = ['Carrefour', 'Naivas', 'Jaza', 'Quickmart'];
const MONTHLY_FOOD_INFLATION = [
  { month: 'Jan', value: -1.53 },
  { month: 'Feb', value: 4.61 },
  { month: 'Mar', value: 5.14 },
  { month: 'Apr', value: 8.13 },
  { month: 'May', value: 13.12 },
  { month: 'Jun', value: 8.63 },
  { month: 'Jul', value: 9.3 },
  { month: 'Aug', value: 10.46 },
];

const money = (value: number) => `KSh ${Math.round(value).toLocaleString('en-KE')}`;
const bestPrice = (product: Product) =>
  product.prices.reduce((best, item) => (item.price < best.price ? item : best));
const basketPrice = (product: Product, strategy: 'lowest' | 'single') =>
  strategy === 'single'
    ? product.prices.find((item) => item.store === 'Naivas') ?? bestPrice(product)
    : bestPrice(product);
const categoryCode: Record<Exclude<Category, 'All'>, string> = {
  Dairy: 'DAIRY',
  Bakery: 'BREAD',
  Pantry: 'PANTRY',
  Produce: 'FRESH',
};

export default function App() {
  return (
    <SafeAreaProvider>
      <PriceCheckApp />
    </SafeAreaProvider>
  );
}

function PriceCheckApp() {
  const insets = useSafeAreaInsets();
  const [tab, setTab] = useState<Tab>('Home');
  const [category, setCategory] = useState<Category>('All');
  const [search, setSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [basket, setBasket] = useState<BasketLine[]>([
    { productId: 'bread', quantity: 1, strategy: 'lowest' },
  ]);
  const [watchedIds, setWatchedIds] = useState<string[]>(['brookside-milk']);
  const [weeklyBudget, setWeeklyBudget] = useState('700');
  const [savedBudget, setSavedBudget] = useState(700);
  const [budgetError, setBudgetError] = useState('');
  const [shoppingArea, setShoppingArea] = useState('Nairobi');
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [savedNotice, setSavedNotice] = useState(false);

  const filteredProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return PRODUCTS.filter((product) => {
      const matchesCategory = category === 'All' || product.category === category;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        `${product.name} ${product.description} ${product.category}`.toLowerCase().includes(normalizedSearch);
      return matchesCategory && matchesSearch;
    }).sort((a, b) => bestPrice(a).price - bestPrice(b).price);
  }, [category, search]);

  const basketTotal = basket.reduce((total, line) => {
    const product = PRODUCTS.find((item) => item.id === line.productId);
    if (!product) return total;
    return total + basketPrice(product, line.strategy).price * line.quantity;
  }, 0);

  const navigateToSearch = (query = '') => {
    setSearch(query);
    setCategory('All');
    setTab('Search');
  };

  const addToBasket = (product: Product) => {
    setBasket((current) => {
      const existing = current.find((line) => line.productId === product.id);
      if (existing) {
        return current.map((line) =>
          line.productId === product.id ? { ...line, quantity: line.quantity + 1 } : line,
        );
      }
      return [...current, { productId: product.id, quantity: 1, strategy: 'lowest' }];
    });
    setSelectedProduct(null);
  };

  const toggleWatch = (productId: string) => {
    setWatchedIds((current) =>
      current.includes(productId)
        ? current.filter((id) => id !== productId)
        : [...current, productId],
    );
  };

  const updateQuantity = (productId: string, change: number) => {
    setBasket((current) =>
      current
        .map((line) =>
          line.productId === productId
            ? { ...line, quantity: Math.max(0, line.quantity + change) }
            : line,
        )
        .filter((line) => line.quantity > 0),
    );
  };

  const setBasketStrategy = (strategy: 'lowest' | 'single') => {
    setBasket((current) => current.map((line) => ({ ...line, strategy })));
  };

  const saveBudget = () => {
    const amount = Number(weeklyBudget);
    if (!Number.isFinite(amount) || amount <= 0) {
      setBudgetError('Enter a budget greater than KSh 0.');
      return;
    }
    setSavedBudget(amount);
    setBudgetError('');
    setSavedNotice(true);
    Keyboard.dismiss();
  };

  const basketCount = basket.reduce((total, line) => total + line.quantity, 0);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="dark" />
      <View style={styles.app}>
        {tab === 'Home' && (
          <HomeScreen
            shoppingArea={shoppingArea}
            basketCount={basketCount}
            onSearch={() => navigateToSearch()}
            onCategory={(nextCategory) => {
              setCategory(nextCategory);
              setSearch('');
              setTab('Search');
            }}
            onOpenProduct={setSelectedProduct}
            onAddProduct={addToBasket}
            onTrends={() => setTab('Trends')}
          />
        )}
        {tab === 'Search' && (
          <SearchScreen
            shoppingArea={shoppingArea}
            search={search}
            category={category}
            products={filteredProducts}
            onChangeSearch={setSearch}
            onChangeCategory={setCategory}
            onOpenProduct={setSelectedProduct}
            onAddProduct={addToBasket}
          />
        )}
        {tab === 'Basket' && (
          <BasketScreen
            basket={basket}
            total={basketTotal}
            budget={savedBudget}
            onChangeQuantity={updateQuantity}
            onSetStrategy={setBasketStrategy}
            onSearch={() => navigateToSearch()}
          />
        )}
        {tab === 'Trends' && (
          <TrendsScreen
            watchedIds={watchedIds}
            onOpenProduct={setSelectedProduct}
            onBrowse={() => navigateToSearch()}
          />
        )}
        {tab === 'Profile' && (
          <ProfileScreen
            shoppingArea={shoppingArea}
            onChangeArea={setShoppingArea}
            weeklyBudget={weeklyBudget}
            onChangeBudget={(value) => {
              setWeeklyBudget(value.replace(/[^0-9]/g, ''));
              setSavedNotice(false);
              setBudgetError('');
            }}
            onSaveBudget={saveBudget}
            budgetError={budgetError}
            alertsEnabled={alertsEnabled}
            onToggleAlerts={setAlertsEnabled}
            savedNotice={savedNotice}
            savedBudget={savedBudget}
          />
        )}
        <BottomNavigation
          activeTab={tab}
          basketCount={basketCount}
          bottomInset={insets.bottom}
          onChange={setTab}
        />
      </View>
      <ProductModal
        product={selectedProduct}
        watched={selectedProduct ? watchedIds.includes(selectedProduct.id) : false}
        onClose={() => setSelectedProduct(null)}
        onToggleWatch={() => selectedProduct && toggleWatch(selectedProduct.id)}
        onAdd={() => selectedProduct && addToBasket(selectedProduct)}
      />
    </SafeAreaView>
  );
}

function ScreenHeader({
  title,
  shoppingArea,
}: {
  title: string;
  shoppingArea: string;
}) {
  return (
    <View style={styles.header}>
      <View style={styles.brandRow}>
        <View style={styles.brandMark}>
          <Ionicons name="pricetag" size={21} color="#FFFFFF" />
        </View>
        <Text style={styles.brandName}>Price Check KE</Text>
        <View style={styles.headerSpacer} />
        <View style={styles.areaPill}>
          <Text style={styles.areaPillText}>{shoppingArea}</Text>
          <Ionicons name="chevron-down" size={15} color={COLORS.muted} />
        </View>
      </View>
      <Text style={styles.pageTitle}>{title}</Text>
      <Text style={styles.headerSubtitle}>Make every shilling count today.</Text>
    </View>
  );
}

function HomeScreen({
  shoppingArea,
  basketCount,
  onSearch,
  onCategory,
  onOpenProduct,
  onAddProduct,
  onTrends,
}: {
  shoppingArea: string;
  basketCount: number;
  onSearch: () => void;
  onCategory: (category: Category) => void;
  onOpenProduct: (product: Product) => void;
  onAddProduct: (product: Product) => void;
  onTrends: () => void;
}) {
  const featured = [PRODUCTS[2], PRODUCTS[0], PRODUCTS[4]];
  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader title="Good evening, Amina" shoppingArea={shoppingArea} />
      <SavingsCard />
      <SearchBar
        value=""
        placeholder="Search milk, bread, cooking oil..."
        onChangeText={() => undefined}
        onPress={onSearch}
        editable={false}
      />
      <SectionHeading eyebrow="Browse the aisles" title="Popular categories" />
      <View style={styles.categoryGrid}>
        {CATEGORIES.filter((item) => item !== 'All').map((item) => (
          <CategoryTile key={item} category={item} onPress={() => onCategory(item)} />
        ))}
      </View>
      <View style={styles.sectionHeadingRow}>
        <SectionHeading eyebrow="Updated this morning" title="Today’s price drops" />
        <Pressable onPress={() => onCategory('All')} accessibilityRole="button">
          <Text style={styles.linkText}>See all</Text>
        </Pressable>
      </View>
      <DemoLabel />
      <View style={styles.productList}>
        {featured.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            onOpen={() => onOpenProduct(product)}
            onAdd={() => onAddProduct(product)}
            compact
          />
        ))}
      </View>
      <Pressable style={styles.insightCard} onPress={onTrends} accessibilityRole="button">
        <View style={styles.insightIcon}>
          <Ionicons name="sparkles" size={19} color={COLORS.green} />
        </View>
        <View style={styles.insightText}>
          <Text style={styles.insightEyebrow}>Smart market insight</Text>
          <Text style={styles.insightTitle}>See what Kenya’s food-price data is telling you</Text>
          <Text style={styles.insightCaption}>World Bank RTFP · national market average</Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color={COLORS.green} />
      </Pressable>
      <Text style={styles.demoFootnote}>
        {basketCount} {basketCount === 1 ? 'item' : 'items'} in your basket · Store prices are illustrative demo data.
      </Text>
    </ScrollView>
  );
}

function SavingsCard() {
  return (
    <View style={styles.savingsCard}>
      <View style={styles.savingsIcon}>
        <Ionicons name="sparkles" size={19} color={COLORS.deepGreen} />
      </View>
      <Text style={styles.savingsLabel}>This week’s savings</Text>
      <Text style={styles.savingsAmount}>KSh 486</Text>
      <Text style={styles.savingsDetail}>Across 7 compared items</Text>
      <View style={styles.progressTrack}>
        <View style={styles.progressFill} />
      </View>
      <Text style={styles.savingsGoal}>KSh 14 away from your weekly goal</Text>
    </View>
  );
}

function SearchBar({
  value,
  placeholder,
  onChangeText,
  onPress,
  editable = true,
}: {
  value: string;
  placeholder: string;
  onChangeText: (value: string) => void;
  onPress?: () => void;
  editable?: boolean;
}) {
  return (
    <Pressable
      style={styles.searchBar}
      onPress={onPress}
      accessibilityRole={editable ? undefined : 'button'}
    >
      <Ionicons name="search-outline" size={21} color={COLORS.green} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#89918A"
        style={styles.searchInput}
        editable={editable}
        returnKeyType="search"
        accessibilityLabel="Search products"
      />
      {value.length > 0 && (
        <Pressable onPress={() => onChangeText('')} accessibilityLabel="Clear search">
          <Ionicons name="close-circle" size={20} color={COLORS.muted} />
        </Pressable>
      )}
    </Pressable>
  );
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <View style={styles.sectionHeading}>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
    </View>
  );
}

function CategoryTile({ category, onPress }: { category: Exclude<Category, 'All'>; onPress: () => void }) {
  const icons: Record<Exclude<Category, 'All'>, keyof typeof Ionicons.glyphMap> = {
    Dairy: 'water-outline',
    Bakery: 'cafe-outline',
    Pantry: 'basket-outline',
    Produce: 'leaf-outline',
  };
  return (
    <Pressable style={styles.categoryTile} onPress={onPress} accessibilityRole="button">
      <View style={styles.categoryIcon}>
        <Ionicons name={icons[category]} size={20} color={COLORS.green} />
      </View>
      <Text style={styles.categoryText}>{category}</Text>
      <Ionicons name="chevron-forward" size={15} color={COLORS.muted} />
    </Pressable>
  );
}

function DemoLabel() {
  return (
    <View style={styles.demoLabel}>
      <Ionicons name="information-circle-outline" size={14} color={COLORS.muted} />
      <Text style={styles.demoLabelText}>Illustrative supermarket prices</Text>
    </View>
  );
}

function ProductCard({
  product,
  onOpen,
  onAdd,
  compact = false,
}: {
  product: Product;
  onOpen: () => void;
  onAdd: () => void;
  compact?: boolean;
}) {
  const best = bestPrice(product);
  return (
    <View style={[styles.productCard, compact && styles.productCardCompact]}>
      <Pressable style={styles.productInfo} onPress={onOpen} accessibilityRole="button">
        <View style={styles.productBadge}>
          <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
        </View>
        <View style={styles.productDetails}>
          <Text style={styles.productName}>
            {product.name} <Text style={styles.productSize}>{product.size}</Text>
          </Text>
          <Text style={styles.productDescription}>{product.description}</Text>
          <View style={styles.storeLine}>
            <Ionicons name="storefront-outline" size={14} color={COLORS.muted} />
            <Text style={styles.storeName}>{best.store}</Text>
          </View>
        </View>
      </Pressable>
      <View style={styles.productPriceBlock}>
        <Text style={styles.bestPriceCaption}>Best price</Text>
        <Text style={styles.productPrice}>{money(best.price)}</Text>
        <Pressable style={styles.addButton} onPress={onAdd} accessibilityRole="button">
          <Ionicons name="add" size={17} color="#FFFFFF" />
          <Text style={styles.addButtonText}>Add</Text>
        </Pressable>
      </View>
    </View>
  );
}

function SearchScreen({
  shoppingArea,
  search,
  category,
  products,
  onChangeSearch,
  onChangeCategory,
  onOpenProduct,
  onAddProduct,
}: {
  shoppingArea: string;
  search: string;
  category: Category;
  products: Product[];
  onChangeSearch: (value: string) => void;
  onChangeCategory: (category: Category) => void;
  onOpenProduct: (product: Product) => void;
  onAddProduct: (product: Product) => void;
}) {
  return (
    <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
      <ScreenHeader title="Find the best price" shoppingArea={shoppingArea} />
      <SearchBar
        value={search}
        placeholder="Search milk, bread, cooking oil..."
        onChangeText={onChangeSearch}
      />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
        {CATEGORIES.map((item) => (
          <Pressable
            key={item}
            style={[styles.filterChip, category === item && styles.filterChipActive]}
            onPress={() => onChangeCategory(item)}
            accessibilityRole="button"
            accessibilityState={{ selected: category === item }}
          >
            <Text style={[styles.filterChipText, category === item && styles.filterChipTextActive]}>
              {item}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
      <View style={styles.resultsHeader}>
        <View>
          <Text style={styles.eyebrow}>Prices near you</Text>
          <Text style={styles.sectionTitle}>{products.length} products</Text>
        </View>
        <View style={styles.sortPill}>
          <Ionicons name="swap-vertical" size={15} color={COLORS.green} />
          <Text style={styles.sortText}>Lowest price</Text>
        </View>
      </View>
      <DemoLabel />
      {products.length > 0 ? (
        <View style={styles.productList}>
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onOpen={() => onOpenProduct(product)}
              onAdd={() => onAddProduct(product)}
            />
          ))}
        </View>
      ) : (
        <View style={styles.emptyState}>
          <Ionicons name="search-outline" size={28} color={COLORS.green} />
          <Text style={styles.emptyTitle}>No matching products</Text>
          <Text style={styles.emptyBody}>Try another search or browse a different category.</Text>
        </View>
      )}
      <View style={styles.infoNote}>
        <Ionicons name="information-circle-outline" size={18} color={COLORS.green} />
        <Text style={styles.infoNoteText}>
          These sample supermarket prices are illustrative, not a live retailer feed.
        </Text>
      </View>
    </ScrollView>
  );
}

function ProductModal({
  product,
  watched,
  onClose,
  onToggleWatch,
  onAdd,
}: {
  product: Product | null;
  watched: boolean;
  onClose: () => void;
  onToggleWatch: () => void;
  onAdd: () => void;
}) {
  if (!product) return null;
  const lowest = bestPrice(product);
  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <Pressable style={styles.modalDismissArea} onPress={onClose} accessibilityLabel="Close product details" />
        <View style={styles.modalSheet}>
          <View style={styles.modalHandle} />
          <View style={styles.modalTopRow}>
            <View style={styles.productBadge}>
              <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
            </View>
            <View style={styles.headerSpacer} />
            <Pressable onPress={onClose} style={styles.closeButton} accessibilityLabel="Close">
              <Ionicons name="close" size={21} color={COLORS.text} />
            </Pressable>
          </View>
          <Text style={styles.eyebrow}>{product.category}</Text>
          <Text style={styles.modalProductTitle}>{product.name}</Text>
          <Text style={styles.productDescription}>
            {product.description} · {product.size}
          </Text>
          <View style={styles.currentPriceCard}>
            <Text style={styles.bestPriceCaption}>Current lowest demo price</Text>
            <Text style={styles.modalLowestPrice}>{money(lowest.price)}</Text>
            <Text style={styles.productDescription}>at {lowest.store}</Text>
          </View>
          <Text style={styles.compareTitle}>Compare supermarkets</Text>
          {product.prices.map((item) => (
            <View style={styles.compareRow} key={item.store}>
              <View style={styles.storeAvatar}>
                <Text style={styles.storeInitial}>{item.store.charAt(0)}</Text>
              </View>
              <View style={styles.compareStore}>
                <Text style={styles.compareStoreName}>{item.store}</Text>
                <Text style={styles.compareStock}>{item.stock}</Text>
              </View>
              {item.store === lowest.store && <Text style={styles.lowestTag}>Lowest</Text>}
              <Text style={styles.comparePrice}>{money(item.price)}</Text>
            </View>
          ))}
          <Text style={styles.modalDisclaimer}>Illustrative prices · availability not verified</Text>
          <View style={styles.modalActions}>
            <Pressable style={styles.watchButton} onPress={onToggleWatch} accessibilityRole="button">
              <Ionicons name={watched ? 'notifications' : 'notifications-outline'} size={18} color={COLORS.green} />
              <Text style={styles.watchButtonText}>{watched ? 'Watching price' : 'Watch price'}</Text>
            </Pressable>
            <Pressable style={styles.primaryButton} onPress={onAdd} accessibilityRole="button">
              <Ionicons name="basket-outline" size={18} color="#FFFFFF" />
              <Text style={styles.primaryButtonText}>Add to basket</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

function BasketScreen({
  basket,
  total,
  budget,
  onChangeQuantity,
  onSetStrategy,
  onSearch,
}: {
  basket: BasketLine[];
  total: number;
  budget: number;
  onChangeQuantity: (productId: string, change: number) => void;
  onSetStrategy: (strategy: 'lowest' | 'single') => void;
  onSearch: () => void;
}) {
  const selectedStrategy = basket[0]?.strategy ?? 'lowest';
  const storeCount =
    selectedStrategy === 'single'
      ? basket.length > 0
        ? 1
        : 0
      : new Set(
          basket
            .map((line) => {
              const product = PRODUCTS.find((item) => item.id === line.productId);
              return product ? bestPrice(product).store : null;
            })
            .filter(Boolean),
        ).size;
  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader title="Your smart basket" shoppingArea="Nairobi" />
      <View style={styles.strategyPanel}>
        <Text style={styles.eyebrow}>Basket strategy</Text>
        <View style={styles.strategyRow}>
          <StrategyButton
            active={selectedStrategy === 'lowest'}
            title="Lowest prices"
            subtitle="Across multiple stores"
            icon="pricetag-outline"
            onPress={() => onSetStrategy('lowest')}
          />
          <StrategyButton
            active={selectedStrategy === 'single'}
            title="One supermarket"
            subtitle="Fewer stops"
            icon="storefront-outline"
            onPress={() => onSetStrategy('single')}
          />
        </View>
      </View>
      <View style={styles.resultsHeader}>
        <View>
          <Text style={styles.eyebrow}>Shopping list</Text>
          <Text style={styles.sectionTitle}>
            {basket.reduce((sum, line) => sum + line.quantity, 0)}{' '}
            {basket.reduce((sum, line) => sum + line.quantity, 0) === 1 ? 'product' : 'products'}
          </Text>
        </View>
        <View style={styles.basketHint}>
          <Ionicons name="checkmark-circle" size={16} color={COLORS.green} />
          <Text style={styles.basketHintText}>Demo prices</Text>
        </View>
      </View>
      {basket.length > 0 ? (
        basket.map((line) => {
          const product = PRODUCTS.find((item) => item.id === line.productId);
          if (!product) return null;
          const selectedPrice = basketPrice(product, line.strategy);
          const price = selectedPrice.price;
          return (
            <View style={styles.basketProduct} key={line.productId}>
              <View style={styles.productBadge}>
                <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
              </View>
              <View style={styles.basketProductDetails}>
                <Text style={styles.productName}>{product.name}</Text>
                <Text style={styles.productDescription}>
                  {product.size} · {selectedPrice.store} · {money(price)} each
                </Text>
                <View style={styles.quantityControl}>
                  <Pressable
                    style={styles.quantityButton}
                    onPress={() => onChangeQuantity(product.id, -1)}
                    accessibilityLabel={`Decrease ${product.name} quantity`}
                  >
                    <Ionicons name="remove" size={17} color={COLORS.green} />
                  </Pressable>
                  <Text style={styles.quantityText}>{line.quantity}</Text>
                  <Pressable
                    style={styles.quantityButton}
                    onPress={() => onChangeQuantity(product.id, 1)}
                    accessibilityLabel={`Increase ${product.name} quantity`}
                  >
                    <Ionicons name="add" size={17} color={COLORS.green} />
                  </Pressable>
                </View>
              </View>
              <Text style={styles.basketLineTotal}>{money(price * line.quantity)}</Text>
            </View>
          );
        })
      ) : (
        <View style={styles.emptyState}>
          <Ionicons name="basket-outline" size={30} color={COLORS.green} />
          <Text style={styles.emptyTitle}>Your basket is empty</Text>
          <Text style={styles.emptyBody}>Find products and add them to plan your shopping.</Text>
          <Pressable style={styles.primaryButton} onPress={onSearch}>
            <Text style={styles.primaryButtonText}>Browse products</Text>
          </Pressable>
        </View>
      )}
      <View style={styles.summaryCard}>
        <Text style={styles.eyebrow}>Estimated total</Text>
        <Text style={styles.summaryTotal}>{money(total)}</Text>
        <SummaryRow label="Products" value={String(basket.reduce((sum, line) => sum + line.quantity, 0))} />
        <SummaryRow label="Stores" value={String(storeCount)} />
        <SummaryRow label="Budget left" value={money(Math.max(0, budget - total))} />
        <SummaryRow label="Budget status" value={total <= budget ? 'Within budget' : 'Over budget'} />
        <Pressable style={[styles.primaryButton, styles.planButton]} onPress={onSearch}>
          <Text style={styles.primaryButtonText}>Continue shopping</Text>
          <Ionicons name="arrow-forward" size={17} color="#FFFFFF" />
        </Pressable>
        <Text style={styles.modalDisclaimer}>Demo estimates only · retailer prices may vary</Text>
      </View>
    </ScrollView>
  );
}

function StrategyButton({
  active,
  title,
  subtitle,
  icon,
  onPress,
}: {
  active: boolean;
  title: string;
  subtitle: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.strategyButton, active && styles.strategyButtonActive]}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
    >
      <Ionicons name={icon} size={20} color={active ? COLORS.green : COLORS.muted} />
      <View style={styles.strategyText}>
        <Text style={styles.strategyTitle}>{title}</Text>
        <Text style={styles.strategySubtitle}>{subtitle}</Text>
      </View>
    </Pressable>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryRow}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
    </View>
  );
}

function TrendsScreen({
  watchedIds,
  onOpenProduct,
  onBrowse,
}: {
  watchedIds: string[];
  onOpenProduct: (product: Product) => void;
  onBrowse: () => void;
}) {
  const latest = MONTHLY_FOOD_INFLATION[MONTHLY_FOOD_INFLATION.length - 1];
  const peak = MONTHLY_FOOD_INFLATION.reduce((best, item) => (item.value > best.value ? item : best));
  const watchedProducts = PRODUCTS.filter((product) => watchedIds.includes(product.id));
  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader title="Your price trends" shoppingArea="Nairobi" />
      <View style={styles.metricGrid}>
        <MetricCard icon="analytics-outline" label="Latest signal" value={`+${latest.value}%`} hint="Food index · Aug 2026" />
        <MetricCard icon="eye-outline" label="Prices watched" value={String(watchedIds.length)} hint="Retail alerts are demo-only" />
        <MetricCard icon="calendar-outline" label="Data coverage" value="2007–2026" hint="Monthly market estimates" />
      </View>
      <View style={styles.chartCard}>
        <View style={styles.chartHeader}>
          <View>
            <Text style={styles.eyebrow}>National market average · 2026</Text>
            <Text style={styles.sectionTitle}>Food-price inflation signal</Text>
          </View>
          <View style={styles.chartValuePill}>
            <Text style={styles.chartValueText}>+{latest.value}%</Text>
          </View>
        </View>
        <View style={styles.chart}>
          {MONTHLY_FOOD_INFLATION.map((item) => {
            const height = Math.max(8, (Math.abs(item.value) / Math.abs(peak.value)) * 102);
            const negative = item.value < 0;
            return (
              <View style={styles.chartColumn} key={item.month}>
                <Text style={[styles.chartBarValue, negative && styles.chartNegative]}>
                  {item.value > 0 ? '+' : ''}{item.value.toFixed(1)}
                </Text>
                <View style={styles.chartBarTrack}>
                  <View
                    style={[
                      styles.chartBar,
                      { height },
                      negative && styles.chartBarNegative,
                      item.month === latest.month && styles.chartBarLatest,
                    ]}
                  />
                </View>
                <Text style={styles.chartMonth}>{item.month}</Text>
              </View>
            );
          })}
        </View>
        <Text style={styles.chartFootnote}>
          Reported inflation field (%) · RTFP market-average row · values copied from the supplied notebook.
        </Text>
      </View>
      <View style={styles.aiCard}>
        <View style={styles.aiCardHeader}>
          <View style={styles.aiIcon}>
            <Ionicons name="sparkles" size={18} color={COLORS.green} />
          </View>
          <Text style={styles.aiLabel}>Smart market insight</Text>
          <View style={styles.ruleBasedTag}>
            <Text style={styles.ruleBasedTagText}>DATA-BASED</Text>
          </View>
        </View>
        <Text style={styles.aiHeadline}>The latest food-price signal is elevated.</Text>
        <Text style={styles.aiBody}>
          The RTFP national market-average row reports {latest.value.toFixed(2)}% for the food price index in
          August 2026. The highest monthly signal in the displayed January–August series was {peak.value.toFixed(2)}%
          in {peak.month}. This is a historical market indicator, not a forecast or a supermarket price.
        </Text>
        <View style={styles.aiSource}>
          <Ionicons name="document-text-outline" size={15} color={COLORS.green} />
          <Text style={styles.aiSourceText}>World Bank RTFP · Kenya · monthly food-price estimates</Text>
        </View>
        <Text style={styles.aiFootnote}>
          Insight is calculated on-device from the notebook’s data excerpt. No generative AI service is connected yet.
        </Text>
      </View>
      <View style={styles.watchedSection}>
        <View style={styles.sectionHeadingRow}>
          <SectionHeading eyebrow="Price alerts" title="Watched products" />
          <Pressable onPress={onBrowse} accessibilityRole="button">
            <Text style={styles.linkText}>Browse</Text>
          </Pressable>
        </View>
        {watchedProducts.length > 0 ? (
          watchedProducts.map((product) => (
            <Pressable
              key={product.id}
              style={styles.watchedRow}
              onPress={() => onOpenProduct(product)}
              accessibilityRole="button"
            >
              <View style={styles.productBadge}>
                <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
              </View>
              <View style={styles.watchedDetails}>
                <Text style={styles.productName}>{product.name}</Text>
                <Text style={styles.productDescription}>Illustrative price · not a live alert</Text>
              </View>
              <Text style={styles.watchedPrice}>{money(bestPrice(product).price)}</Text>
            </Pressable>
          ))
        ) : (
          <Text style={styles.emptyBody}>Watch a product from Search to see it here.</Text>
        )}
      </View>
    </ScrollView>
  );
}

function MetricCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <View style={styles.metricCard}>
      <Ionicons name={icon} size={18} color={COLORS.green} />
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricHint}>{hint}</Text>
    </View>
  );
}

function ProfileScreen({
  shoppingArea,
  onChangeArea,
  weeklyBudget,
  onChangeBudget,
  onSaveBudget,
  budgetError,
  alertsEnabled,
  onToggleAlerts,
  savedNotice,
  savedBudget,
}: {
  shoppingArea: string;
  onChangeArea: (area: string) => void;
  weeklyBudget: string;
  onChangeBudget: (value: string) => void;
  onSaveBudget: () => void;
  budgetError: string;
  alertsEnabled: boolean;
  onToggleAlerts: (enabled: boolean) => void;
  savedNotice: boolean;
  savedBudget: number;
}) {
  const areas = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru'];
  const nextArea = () => {
    const index = areas.indexOf(shoppingArea);
    onChangeArea(areas[(index + 1) % areas.length]);
  };
  return (
    <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
      <ScreenHeader title="Your Pricewise profile" shoppingArea={shoppingArea} />
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>AM</Text>
        </View>
        <View style={styles.profileIdentity}>
          <Text style={styles.profileName}>Amina Mwangi</Text>
          <Text style={styles.profileSubtext}>Smart shopper since 2026</Text>
        </View>
        <View style={styles.profileStats}>
          <View style={styles.profileStat}>
            <Text style={styles.profileStatValue}>KSh 1,840</Text>
            <Text style={styles.profileSubtext}>Total saved · demo</Text>
          </View>
          <View style={styles.profileStat}>
            <Text style={styles.profileStatValue}>36</Text>
            <Text style={styles.profileSubtext}>Items compared · demo</Text>
          </View>
        </View>
      </View>
      <SectionHeading eyebrow="Preferences" title="Shopping settings" />
      <View style={styles.settingsCard}>
        <SettingRow
          icon="wallet-outline"
          title="Weekly budget"
          subtitle="Used for basket warnings and suggestions"
        >
          <View style={styles.budgetControl}>
            <Text style={styles.currencyPrefix}>KSh</Text>
            <TextInput
              value={weeklyBudget}
              onChangeText={onChangeBudget}
              keyboardType="number-pad"
              style={styles.budgetInput}
              accessibilityLabel="Weekly budget"
            />
            <Pressable style={styles.saveButton} onPress={onSaveBudget} accessibilityRole="button">
              <Text style={styles.saveButtonText}>Save</Text>
            </Pressable>
          </View>
        </SettingRow>
        {savedNotice && (
          <Text style={styles.savedNotice}>Weekly budget saved: {money(savedBudget)}</Text>
        )}
        {budgetError.length > 0 && <Text style={styles.budgetError}>{budgetError}</Text>}
        <SettingRow
          icon="location-outline"
          title="Shopping area"
          subtitle="Used for nearby price discovery"
        >
          <Pressable style={styles.areaSelect} onPress={nextArea} accessibilityRole="button">
            <Text style={styles.areaSelectText}>{shoppingArea}</Text>
            <Ionicons name="chevron-down" size={16} color={COLORS.green} />
          </Pressable>
        </SettingRow>
        <SettingRow
          icon="notifications-outline"
          title="Price-drop alerts"
          subtitle="Receive updates for watched products"
        >
          <Switch
            value={alertsEnabled}
            onValueChange={onToggleAlerts}
            trackColor={{ false: '#CBD3CC', true: '#9FE9BE' }}
            thumbColor={alertsEnabled ? COLORS.green : '#FFFFFF'}
            accessibilityLabel="Price-drop alerts"
          />
        </SettingRow>
      </View>
      <View style={styles.privacyNote}>
        <Ionicons name="phone-portrait-outline" size={20} color={COLORS.green} />
        <View style={styles.privacyText}>
          <Text style={styles.privacyTitle}>Your preferences stay in this session</Text>
          <Text style={styles.privacyBody}>
            Account sync and retailer connections are not set up in this prototype.
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

function SettingRow({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.settingRow}>
      <View style={styles.settingIcon}>
        <Ionicons name={icon} size={19} color={COLORS.green} />
      </View>
      <View style={styles.settingCopy}>
        <Text style={styles.settingTitle}>{title}</Text>
        <Text style={styles.settingSubtitle}>{subtitle}</Text>
      </View>
      {children}
    </View>
  );
}

function BottomNavigation({
  activeTab,
  basketCount,
  bottomInset,
  onChange,
}: {
  activeTab: Tab;
  basketCount: number;
  bottomInset: number;
  onChange: (tab: Tab) => void;
}) {
  const tabs: { name: Tab; icon: keyof typeof Ionicons.glyphMap; activeIcon: keyof typeof Ionicons.glyphMap }[] = [
    { name: 'Home', icon: 'home-outline', activeIcon: 'home' },
    { name: 'Search', icon: 'search-outline', activeIcon: 'search' },
    { name: 'Basket', icon: 'basket-outline', activeIcon: 'basket' },
    { name: 'Trends', icon: 'trending-up-outline', activeIcon: 'trending-up' },
    { name: 'Profile', icon: 'person-outline', activeIcon: 'person' },
  ];
  return (
    <View style={[styles.bottomNav, { paddingBottom: Math.max(bottomInset, 8) }]}>
      {tabs.map((item) => {
        const selected = activeTab === item.name;
        return (
          <Pressable
            key={item.name}
            style={[styles.navItem, selected && styles.navItemActive]}
            onPress={() => onChange(item.name)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
          >
            <View style={styles.navIconWrap}>
              <Ionicons
                name={selected ? item.activeIcon : item.icon}
                size={21}
                color={selected ? COLORS.green : COLORS.muted}
              />
              {item.name === 'Basket' && basketCount > 0 && (
                <View style={styles.navBadge}>
                  <Text style={styles.navBadgeText}>{basketCount > 9 ? '9+' : basketCount}</Text>
                </View>
              )}
            </View>
            <Text style={[styles.navLabel, selected && styles.navLabelActive]}>{item.name}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: COLORS.background },
  app: { flex: 1, backgroundColor: COLORS.background },
  screenContent: { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 26, gap: 16 },
  header: { gap: 7, marginBottom: 2 },
  brandRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 13 },
  brandMark: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: COLORS.green,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  brandName: { color: COLORS.text, fontSize: 18, fontWeight: '800', letterSpacing: -0.4 },
  headerSpacer: { flex: 1 },
  areaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  areaPillText: { color: COLORS.text, fontSize: 13, fontWeight: '500' },
  pageTitle: { color: COLORS.text, fontSize: 27, lineHeight: 33, fontWeight: '800', letterSpacing: -0.8 },
  headerSubtitle: { color: COLORS.muted, fontSize: 15 },
  savingsCard: {
    backgroundColor: COLORS.deepGreen,
    borderRadius: 27,
    padding: 23,
    minHeight: 214,
    overflow: 'hidden',
  },
  savingsIcon: {
    height: 48,
    width: 48,
    borderRadius: 15,
    backgroundColor: COLORS.mint,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 17,
  },
  savingsLabel: { color: '#C8E8D8', fontSize: 14, marginBottom: 4 },
  savingsAmount: { color: '#FFFFFF', fontWeight: '800', fontSize: 35, letterSpacing: -1 },
  savingsDetail: { color: '#E0F1E8', fontSize: 14, marginTop: 1 },
  progressTrack: { height: 9, borderRadius: 9, backgroundColor: '#23634D', marginTop: 20 },
  progressFill: { width: '83%', height: '100%', borderRadius: 9, backgroundColor: COLORS.mint },
  savingsGoal: { color: '#C8E8D8', fontSize: 13, marginTop: 10 },
  searchBar: {
    minHeight: 54,
    backgroundColor: COLORS.surface,
    borderColor: '#DAE2DA',
    borderWidth: 1,
    borderRadius: 17,
    paddingHorizontal: 15,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  searchInput: { flex: 1, color: COLORS.text, fontSize: 15, paddingVertical: 12 },
  sectionHeading: { gap: 3 },
  eyebrow: { color: COLORS.muted, fontSize: 12, fontWeight: '500' },
  sectionTitle: { color: COLORS.text, fontWeight: '700', fontSize: 18 },
  categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 9 },
  categoryTile: {
    width: '48%',
    minHeight: 55,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    borderRadius: 15,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  categoryIcon: {
    height: 32,
    width: 32,
    borderRadius: 11,
    backgroundColor: COLORS.paleGreen,
    alignItems: 'center',
    justifyContent: 'center',
  },
  categoryText: { flex: 1, color: COLORS.text, fontSize: 14, fontWeight: '600' },
  sectionHeadingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  linkText: { color: COLORS.green, fontSize: 13, fontWeight: '700' },
  demoLabel: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: -7 },
  demoLabelText: { color: COLORS.muted, fontSize: 11 },
  productList: { gap: 10 },
  productCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 12,
    gap: 8,
  },
  productCardCompact: { padding: 10 },
  productInfo: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 10 },
  productBadge: {
    width: 44,
    height: 48,
    borderRadius: 13,
    backgroundColor: '#F0F5EE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  productBadgeText: { color: COLORS.green, fontWeight: '800', fontSize: 9, letterSpacing: 0.3 },
  productDetails: { flex: 1, gap: 3 },
  productName: { color: COLORS.text, fontWeight: '700', fontSize: 13 },
  productSize: { color: COLORS.muted, fontWeight: '500' },
  productDescription: { color: COLORS.muted, fontSize: 11 },
  storeLine: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  storeName: { color: COLORS.muted, fontSize: 11 },
  productPriceBlock: { alignItems: 'flex-end', minWidth: 81, gap: 2 },
  bestPriceCaption: { color: COLORS.muted, fontSize: 10 },
  productPrice: { color: COLORS.text, fontSize: 16, fontWeight: '800' },
  addButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginTop: 3,
    borderRadius: 10,
    backgroundColor: COLORS.green,
  },
  addButtonText: { color: '#FFFFFF', fontSize: 11, fontWeight: '700' },
  insightCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E5F8EC',
    padding: 13,
    borderRadius: 16,
    gap: 10,
  },
  insightIcon: {
    width: 37,
    height: 37,
    borderRadius: 12,
    backgroundColor: '#C7F3D9',
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightText: { flex: 1, gap: 2 },
  insightEyebrow: { color: COLORS.green, fontSize: 11, fontWeight: '700' },
  insightTitle: { color: COLORS.text, fontSize: 13, fontWeight: '700' },
  insightCaption: { color: COLORS.muted, fontSize: 10 },
  demoFootnote: { textAlign: 'center', color: COLORS.muted, fontSize: 11, marginBottom: 4 },
  bottomNav: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    backgroundColor: COLORS.surface,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: 7,
    paddingHorizontal: 5,
  },
  navItem: {
    minWidth: 56,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    paddingVertical: 7,
    paddingHorizontal: 10,
    borderRadius: 16,
  },
  navItemActive: { backgroundColor: '#DCF6E7' },
  navIconWrap: { position: 'relative' },
  navLabel: { color: COLORS.muted, fontSize: 10, fontWeight: '500' },
  navLabelActive: { color: COLORS.green, fontWeight: '700' },
  navBadge: {
    position: 'absolute',
    right: -11,
    top: -5,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    paddingHorizontal: 3,
    backgroundColor: COLORS.orange,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navBadgeText: { color: '#FFFFFF', fontSize: 9, fontWeight: '800' },
  chipRow: { gap: 8, paddingVertical: 2 },
  filterChip: {
    paddingHorizontal: 15,
    paddingVertical: 9,
    borderRadius: 20,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  filterChipActive: { backgroundColor: COLORS.green, borderColor: COLORS.green },
  filterChipText: { color: COLORS.text, fontSize: 12, fontWeight: '600' },
  filterChipTextActive: { color: '#FFFFFF' },
  resultsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sortPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderWidth: 1,
    borderColor: COLORS.border,
    backgroundColor: COLORS.surface,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 14,
  },
  sortText: { color: COLORS.text, fontSize: 11, fontWeight: '600' },
  emptyState: {
    minHeight: 185,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 20,
    backgroundColor: COLORS.surface,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 8,
  },
  emptyTitle: { color: COLORS.text, fontSize: 16, fontWeight: '700' },
  emptyBody: { color: COLORS.muted, fontSize: 13, textAlign: 'center', lineHeight: 19 },
  infoNote: { flexDirection: 'row', alignItems: 'flex-start', gap: 7, paddingHorizontal: 2 },
  infoNoteText: { color: COLORS.muted, fontSize: 11, flex: 1, lineHeight: 16 },
  modalBackdrop: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(11, 30, 20, 0.45)' },
  modalDismissArea: { flex: 1 },
  modalSheet: {
    backgroundColor: COLORS.background,
    borderTopLeftRadius: 27,
    borderTopRightRadius: 27,
    paddingHorizontal: 22,
    paddingTop: 11,
    paddingBottom: 30,
    gap: 12,
  },
  modalHandle: { width: 38, height: 4, backgroundColor: '#C8D0C8', borderRadius: 5, alignSelf: 'center', marginBottom: 3 },
  modalTopRow: { flexDirection: 'row', alignItems: 'center' },
  closeButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.surface,
  },
  modalProductTitle: { color: COLORS.text, fontSize: 25, fontWeight: '800', letterSpacing: -0.5 },
  currentPriceCard: { padding: 15, backgroundColor: COLORS.paleGreen, borderRadius: 17, gap: 2 },
  modalLowestPrice: { color: COLORS.green, fontSize: 30, fontWeight: '800' },
  compareTitle: { color: COLORS.text, fontSize: 16, fontWeight: '700', marginTop: 2 },
  compareRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    paddingVertical: 7,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  storeAvatar: { width: 34, height: 34, borderRadius: 12, backgroundColor: '#E5EEE6', alignItems: 'center', justifyContent: 'center' },
  storeInitial: { color: COLORS.green, fontWeight: '800' },
  compareStore: { flex: 1, gap: 2 },
  compareStoreName: { color: COLORS.text, fontSize: 13, fontWeight: '700' },
  compareStock: { color: COLORS.muted, fontSize: 10 },
  lowestTag: { color: COLORS.green, backgroundColor: COLORS.paleGreen, borderRadius: 9, paddingHorizontal: 7, paddingVertical: 4, fontSize: 10, fontWeight: '700' },
  comparePrice: { color: COLORS.text, fontSize: 14, fontWeight: '700', minWidth: 68, textAlign: 'right' },
  modalDisclaimer: { color: COLORS.muted, fontSize: 10, textAlign: 'center' },
  modalActions: { flexDirection: 'row', gap: 9, marginTop: 2 },
  watchButton: {
    flex: 1,
    minHeight: 46,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 14,
  },
  watchButtonText: { color: COLORS.green, fontSize: 12, fontWeight: '700' },
  primaryButton: {
    flexDirection: 'row',
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    paddingHorizontal: 15,
    backgroundColor: COLORS.green,
    borderRadius: 14,
  },
  primaryButtonText: { color: '#FFFFFF', fontWeight: '700', fontSize: 13 },
  strategyPanel: { padding: 15, borderRadius: 19, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, gap: 10 },
  strategyRow: { flexDirection: 'row', gap: 8 },
  strategyButton: { flex: 1, minHeight: 67, flexDirection: 'row', gap: 7, alignItems: 'center', padding: 9, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, backgroundColor: '#FFFFFF' },
  strategyButtonActive: { backgroundColor: COLORS.paleGreen, borderColor: '#A8DFC0' },
  strategyText: { flex: 1, gap: 2 },
  strategyTitle: { color: COLORS.text, fontSize: 11, fontWeight: '700' },
  strategySubtitle: { color: COLORS.muted, fontSize: 9 },
  basketHint: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: COLORS.paleGreen, borderRadius: 12, paddingHorizontal: 9, paddingVertical: 6 },
  basketHintText: { color: COLORS.green, fontSize: 10, fontWeight: '700' },
  basketProduct: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: COLORS.surface, borderColor: COLORS.border, borderWidth: 1, padding: 12, borderRadius: 17 },
  basketProductDetails: { flex: 1, gap: 3 },
  basketLineTotal: { alignSelf: 'flex-start', color: COLORS.text, fontSize: 14, fontWeight: '800' },
  quantityControl: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 3 },
  quantityButton: { width: 27, height: 27, borderRadius: 10, backgroundColor: COLORS.paleGreen, alignItems: 'center', justifyContent: 'center' },
  quantityText: { color: COLORS.text, minWidth: 14, textAlign: 'center', fontSize: 12, fontWeight: '700' },
  summaryCard: { backgroundColor: COLORS.surface, borderRadius: 20, borderWidth: 1, borderColor: COLORS.border, padding: 17, gap: 10 },
  summaryTotal: { color: COLORS.text, fontSize: 31, fontWeight: '800' },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, borderTopColor: COLORS.border, paddingTop: 9 },
  summaryLabel: { color: COLORS.muted, fontSize: 12 },
  summaryValue: { color: COLORS.text, fontSize: 12, fontWeight: '700' },
  planButton: { marginTop: 2 },
  metricGrid: { flexDirection: 'row', gap: 8 },
  metricCard: { flex: 1, minHeight: 116, padding: 10, borderRadius: 16, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, gap: 4 },
  metricLabel: { color: COLORS.muted, fontSize: 9, lineHeight: 12 },
  metricValue: { color: COLORS.text, fontSize: 17, fontWeight: '800' },
  metricHint: { color: COLORS.muted, fontSize: 8, lineHeight: 11 },
  chartCard: { backgroundColor: COLORS.surface, padding: 15, borderRadius: 19, borderWidth: 1, borderColor: COLORS.border, gap: 14 },
  chartHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  chartValuePill: { backgroundColor: COLORS.paleGreen, borderRadius: 14, paddingHorizontal: 10, paddingVertical: 7 },
  chartValueText: { color: COLORS.green, fontSize: 13, fontWeight: '800' },
  chart: { height: 142, flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', gap: 5 },
  chartColumn: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', gap: 5, height: '100%' },
  chartBarValue: { height: 13, color: COLORS.muted, fontSize: 8, fontWeight: '600' },
  chartNegative: { color: COLORS.orange },
  chartBarTrack: { width: '100%', flex: 1, justifyContent: 'flex-end', alignItems: 'center' },
  chartBar: { width: 17, borderTopLeftRadius: 6, borderTopRightRadius: 6, backgroundColor: '#81D9A8' },
  chartBarNegative: { backgroundColor: '#F4B09B' },
  chartBarLatest: { backgroundColor: COLORS.green },
  chartMonth: { color: COLORS.muted, fontSize: 9 },
  chartFootnote: { color: COLORS.muted, fontSize: 10, lineHeight: 15 },
  aiCard: { padding: 16, borderRadius: 19, backgroundColor: '#E5F8EC', gap: 9 },
  aiCardHeader: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  aiIcon: { height: 32, width: 32, borderRadius: 11, backgroundColor: '#C8F1D7', alignItems: 'center', justifyContent: 'center' },
  aiLabel: { color: COLORS.green, fontSize: 12, fontWeight: '800', flex: 1 },
  ruleBasedTag: { backgroundColor: '#C8F1D7', borderRadius: 9, paddingHorizontal: 7, paddingVertical: 4 },
  ruleBasedTagText: { color: COLORS.green, fontSize: 8, fontWeight: '800' },
  aiHeadline: { color: COLORS.text, fontSize: 16, fontWeight: '800' },
  aiBody: { color: '#536157', fontSize: 12, lineHeight: 18 },
  aiSource: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingTop: 5 },
  aiSourceText: { color: COLORS.green, fontSize: 10, fontWeight: '600', flex: 1 },
  aiFootnote: { color: COLORS.muted, fontSize: 10, lineHeight: 15, borderTopWidth: 1, borderTopColor: '#CDEBD8', paddingTop: 8 },
  watchedSection: { gap: 10 },
  watchedRow: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 16, padding: 11 },
  watchedDetails: { flex: 1, gap: 3 },
  watchedPrice: { color: COLORS.text, fontSize: 13, fontWeight: '800' },
  profileCard: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 11, backgroundColor: COLORS.surface, borderRadius: 20, borderWidth: 1, borderColor: COLORS.border, padding: 15 },
  avatar: { width: 49, height: 49, borderRadius: 17, backgroundColor: COLORS.paleGreen, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: COLORS.green, fontSize: 15, fontWeight: '800' },
  profileIdentity: { flex: 1, gap: 4 },
  profileName: { color: COLORS.text, fontSize: 17, fontWeight: '800' },
  profileSubtext: { color: COLORS.muted, fontSize: 10 },
  profileStats: { width: '100%', flexDirection: 'row', borderTopWidth: 1, borderTopColor: COLORS.border, paddingTop: 12, gap: 10 },
  profileStat: { flex: 1, gap: 4 },
  profileStatValue: { color: COLORS.green, fontSize: 19, fontWeight: '800' },
  settingsCard: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 19, paddingHorizontal: 13 },
  settingRow: { minHeight: 77, flexDirection: 'row', alignItems: 'center', gap: 9, borderBottomWidth: 1, borderBottomColor: COLORS.border, paddingVertical: 10 },
  settingIcon: { width: 34, height: 34, borderRadius: 12, backgroundColor: COLORS.paleGreen, alignItems: 'center', justifyContent: 'center' },
  settingCopy: { flex: 1, gap: 3 },
  settingTitle: { color: COLORS.text, fontSize: 12, fontWeight: '700' },
  settingSubtitle: { color: COLORS.muted, fontSize: 9, lineHeight: 13 },
  budgetControl: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  currencyPrefix: { color: COLORS.muted, fontSize: 10 },
  budgetInput: { width: 48, paddingVertical: 5, paddingHorizontal: 4, color: COLORS.text, fontSize: 13, fontWeight: '700', textAlign: 'center', borderBottomWidth: 1, borderBottomColor: COLORS.border },
  saveButton: { backgroundColor: COLORS.green, paddingHorizontal: 8, paddingVertical: 7, borderRadius: 9 },
  saveButtonText: { color: '#FFFFFF', fontSize: 10, fontWeight: '700' },
  savedNotice: { color: COLORS.green, fontSize: 11, fontWeight: '600', paddingTop: 8 },
  budgetError: { color: '#A53F32', fontSize: 11, fontWeight: '600', paddingTop: 8 },
  areaSelect: { flexDirection: 'row', alignItems: 'center', gap: 3, paddingHorizontal: 9, paddingVertical: 7, borderRadius: 10, backgroundColor: COLORS.paleGreen },
  areaSelectText: { color: COLORS.green, fontSize: 10, fontWeight: '700' },
  privacyNote: { flexDirection: 'row', alignItems: 'flex-start', gap: 9, padding: 13, borderRadius: 15, backgroundColor: '#E5F8EC' },
  privacyText: { flex: 1, gap: 4 },
  privacyTitle: { color: COLORS.text, fontSize: 11, fontWeight: '700' },
  privacyBody: { color: COLORS.muted, fontSize: 10, lineHeight: 14 },
});
