import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Keyboard, Pressable, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { BottomNavigation } from './components/BottomNavigation';
import { ProductModal, ShoppingAreaModal } from './components/Common';
import { styles } from './constants/styles';
import { COLORS } from './constants/theme';
import { ShoppingArea } from './constants/shoppingAreas';
import { useBasketPricing } from './hooks/useBasketPricing';
import { useProductCatalog } from './hooks/useProductCatalog';
import { usePersistentPreferences } from './hooks/usePersistentPreferences';
import { basketPrice, bestPrice, compareBasketStores } from './utils/pricing';
import { Category, Product, Tab } from './types';
import { BasketScreen } from './screens/BasketScreen';
import { HomeScreen } from './screens/HomeScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { SearchScreen } from './screens/SearchScreen';
import { TrendsScreen } from './screens/TrendsScreen';

export default function App() {
  return (
    <SafeAreaProvider>
      <PriceCheckApp />
    </SafeAreaProvider>
  );
}

function PriceCheckApp() {
  const insets = useSafeAreaInsets();
  const { preferences, setPreferences, isReady: preferencesReady, storageError } =
    usePersistentPreferences();
  const productCatalog = useProductCatalog();
  const basketPricingState = useBasketPricing(preferences.basket);
  const [tab, setTab] = useState<Tab>('Home');
  const [category, setCategory] = useState<Category>('All');
  const [search, setSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [areaPickerVisible, setAreaPickerVisible] = useState(false);
  const [budgetError, setBudgetError] = useState('');
  const [savedNotice, setSavedNotice] = useState(false);
  const [basketNotice, setBasketNotice] = useState('');
  const { basket, watchedIds, weeklyBudget, savedBudget, shoppingArea } =
    preferences;
  const products = productCatalog.products;

  const filteredProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return products.filter((product) => {
      const matchesCategory = category === 'All' || product.category === category;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        `${product.name} ${product.description} ${product.category}`.toLowerCase().includes(normalizedSearch);
      return matchesCategory && matchesSearch;
    }).sort((a, b) => bestPrice(a).price - bestPrice(b).price);
  }, [category, products, search]);

  const localBasketStoreComparison = compareBasketStores(basket, products);
  const basketStoreComparison =
    basketPricingState.pricing?.store_totals ?? localBasketStoreComparison;
  const cheapestBasketStore = basketPricingState.pricing
    ? basketPricingState.pricing.best_single_store
    : localBasketStoreComparison[0]?.store ?? null;
  const localBasketTotal = basket.reduce((total, line) => {
    const product = products.find((item) => item.id === line.productId);
    if (!product) return total;
    return total + basketPrice(product, line.strategy, cheapestBasketStore).price * line.quantity;
  }, 0);
  const basketTotal = basketPricingState.pricing?.total ?? localBasketTotal;

  const navigateToSearch = (query = '') => {
    setSearch(query);
    setCategory('All');
    setTab('Search');
  };

  const addToBasket = (product: Product) => {
    setPreferences((current) => {
      const strategy = current.basket[0]?.strategy ?? 'lowest';
      const existing = current.basket.find((line) => line.productId === product.id);
      const next = existing
        ? current.basket.map((line) =>
            line.productId === product.id ? { ...line, quantity: line.quantity + 1 } : line,
          )
        : [...current.basket, { productId: product.id, quantity: 1, strategy }];
      if (strategy === 'single' && compareBasketStores(next, products).length === 0) {
        return { ...current, basket: next.map((line) => ({ ...line, strategy: 'lowest' })) };
      }
      return { ...current, basket: next };
    });
    setBasketNotice(`${product.name} added to basket`);
    setSelectedProduct(null);
  };

  useEffect(() => {
    if (!basketNotice) return;
    const timeout = setTimeout(() => setBasketNotice(''), 2400);
    return () => clearTimeout(timeout);
  }, [basketNotice]);

  const toggleWatch = (productId: string) => {
    setPreferences((current) => ({
      ...current,
      watchedIds: current.watchedIds.includes(productId)
        ? current.watchedIds.filter((id) => id !== productId)
        : [...current.watchedIds, productId],
    }));
  };

  const updateQuantity = (productId: string, change: number) => {
    setPreferences((current) => ({
      ...current,
      basket: current.basket
        .map((line) =>
          line.productId === productId
            ? { ...line, quantity: Math.max(0, line.quantity + change) }
            : line,
        )
        .filter((line) => line.quantity > 0),
    }));
  };

  const setBasketStrategy = (strategy: 'lowest' | 'single') => {
    if (strategy === 'single' && basketStoreComparison.length === 0) return;
    setPreferences((current) => ({
      ...current,
      basket: current.basket.map((line) => ({ ...line, strategy })),
    }));
  };

  const saveBudget = () => {
    const amount = Number(weeklyBudget);
    if (!Number.isFinite(amount) || amount <= 0) {
      setBudgetError('Enter a budget greater than KSh 0.');
      return;
    }
    setPreferences((current) => ({ ...current, savedBudget: amount }));
    setBudgetError('');
    setSavedNotice(true);
    Keyboard.dismiss();
  };

  const basketCount = basket.reduce((total, line) => total + line.quantity, 0);
  const changeShoppingArea = () => {
    setAreaPickerVisible(true);
  };
  const selectShoppingArea = (area: ShoppingArea) => {
    setPreferences((current) => ({ ...current, shoppingArea: area }));
    setAreaPickerVisible(false);
  };

  if (!preferencesReady) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top']}>
        <View style={styles.app}>
          <View style={styles.emptyState}>
            <ActivityIndicator color={COLORS.green} />
            <Text style={styles.emptyBody}>Loading your saved basket and settings…</Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar style="dark" />
      <View style={styles.app}>
        {tab === 'Home' && (
          <HomeScreen
            shoppingArea={shoppingArea}
            onChangeArea={changeShoppingArea}
            basketCount={basketCount}
            products={products}
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
            onChangeArea={changeShoppingArea}
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
            products={products}
            pricing={basketPricingState.pricing}
            pricingError={basketPricingState.error}
            pricingLoading={basketPricingState.loading}
            storeComparison={basketStoreComparison}
            budget={savedBudget}
            shoppingArea={shoppingArea}
            onChangeArea={changeShoppingArea}
            singleStore={cheapestBasketStore}
            onChangeQuantity={updateQuantity}
            onSetStrategy={setBasketStrategy}
            onSearch={() => navigateToSearch()}
          />
        )}
        {tab === 'Trends' && (
          <TrendsScreen
            watchedIds={watchedIds}
            shoppingArea={shoppingArea}
            onChangeArea={changeShoppingArea}
            onOpenProduct={setSelectedProduct}
            onBrowse={() => navigateToSearch()}
            products={products}
          />
        )}
        {tab === 'Profile' && (
          <ProfileScreen
            shoppingArea={shoppingArea}
            onChangeArea={changeShoppingArea}
            weeklyBudget={weeklyBudget}
            onChangeBudget={(value) => {
              setPreferences((current) => ({
                ...current,
                weeklyBudget: value.replace(/[^0-9]/g, ''),
              }));
              setSavedNotice(false);
              setBudgetError('');
            }}
            onSaveBudget={saveBudget}
            budgetError={budgetError}
            storageError={storageError}
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
        {basketNotice !== '' && (
          <View style={styles.basketNotice} accessibilityLiveRegion="polite">
            <Text style={styles.basketNoticeText} accessibilityRole="alert">
              {basketNotice}
            </Text>
            <Pressable
              onPress={() => {
                setBasketNotice('');
                setTab('Basket');
              }}
              accessibilityRole="button"
              accessibilityLabel="View basket"
            >
              <Text style={styles.basketNoticeAction}>View basket</Text>
            </Pressable>
          </View>
        )}
      </View>
      <ProductModal
        product={selectedProduct}
        watched={selectedProduct ? watchedIds.includes(selectedProduct.id) : false}
        onClose={() => setSelectedProduct(null)}
        onToggleWatch={() => selectedProduct && toggleWatch(selectedProduct.id)}
        onAdd={() => selectedProduct && addToBasket(selectedProduct)}
      />
      <ShoppingAreaModal
        visible={areaPickerVisible}
        selectedArea={shoppingArea}
        onSelect={selectShoppingArea}
        onClose={() => setAreaPickerVisible(false)}
      />
    </SafeAreaView>
  );
}
