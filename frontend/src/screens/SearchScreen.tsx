import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { DemoLabel, ProductCard, ScreenHeader, SearchBar } from '../components/Common';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { CATEGORIES } from '../data/products';
import { Category, Product } from '../types';
import { bestPrice } from '../utils/pricing';

export function SearchScreen({
  shoppingArea,
  onChangeArea,
  search,
  category,
  products,
  onChangeSearch,
  onChangeCategory,
  onOpenProduct,
  onAddProduct,
}: {
  shoppingArea: string;
  onChangeArea: () => void;
  search: string;
  category: Category;
  products: Product[];
  onChangeSearch: (value: string) => void;
  onChangeCategory: (category: Category) => void;
  onOpenProduct: (product: Product) => void;
  onAddProduct: (product: Product) => void;
}) {
  const [sortOrder, setSortOrder] = useState<'lowest' | 'highest' | 'name'>('lowest');
  const sortedProducts = [...products].sort((first, second) => {
    if (sortOrder === 'name') return first.name.localeCompare(second.name);
    const difference = bestPrice(first).price - bestPrice(second).price;
    return sortOrder === 'lowest' ? difference : -difference;
  });
  const sortLabel =
    sortOrder === 'lowest'
      ? 'Lowest price'
      : sortOrder === 'highest'
        ? 'Highest price'
        : 'Name A–Z';

  return (
    <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled">
      <ScreenHeader
        title="Find the best price"
        shoppingArea={shoppingArea}
        onChangeArea={onChangeArea}
      />
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
        <Pressable
          style={styles.sortPill}
          onPress={() =>
            setSortOrder((current) =>
              current === 'lowest' ? 'highest' : current === 'highest' ? 'name' : 'lowest',
            )
          }
          accessibilityRole="button"
          accessibilityLabel={`Sort products. Current sort: ${sortLabel}`}
        >
          <Ionicons name="swap-vertical" size={15} color={COLORS.green} />
          <Text style={styles.sortText}>{sortLabel}</Text>
        </Pressable>
      </View>
      <DemoLabel />
      {products.length > 0 ? (
        <View style={styles.productList}>
          {sortedProducts.map((product) => (
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
