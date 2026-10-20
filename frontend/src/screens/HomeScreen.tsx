import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { CategoryTile, DemoLabel, ProductCard, SavingsCard, ScreenHeader, SearchBar, SectionHeading } from '../components/Common';
import { MarketPricesCard } from '../components/MarketPricesCard';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { CATEGORIES } from '../data/products';
import { useAreaMarketPrices } from '../hooks/useAreaMarketPrices';
import { Category, Product } from '../types';

export function HomeScreen({
  shoppingArea,
  onChangeArea,
  basketCount,
  products,
  onSearch,
  onCategory,
  onOpenProduct,
  onAddProduct,
  onTrends,
}: {
  shoppingArea: string;
  onChangeArea: () => void;
  basketCount: number;
  products: Product[];
  onSearch: () => void;
  onCategory: (category: Category) => void;
  onOpenProduct: (product: Product) => void;
  onAddProduct: (product: Product) => void;
  onTrends: () => void;
}) {
  const [localHour, setLocalHour] = useState(() => new Date().getHours());
  const marketPrices = useAreaMarketPrices(shoppingArea);

  useEffect(() => {
    const timer = setInterval(() => {
      const currentHour = new Date().getHours();
      setLocalHour((previousHour) => (previousHour === currentHour ? previousHour : currentHour));
    }, 60_000);

    return () => clearInterval(timer);
  }, []);

  const featured = products.slice(0, 3);
  const greeting =
    localHour < 5
      ? 'Good night'
      : localHour < 12
        ? 'Good morning'
        : localHour < 17
          ? 'Good afternoon'
          : localHour < 21
            ? 'Good evening'
            : 'Good night';
  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader
        title={greeting}
        shoppingArea={shoppingArea}
        onChangeArea={onChangeArea}
      />
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
      <MarketPricesCard {...marketPrices} />
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
