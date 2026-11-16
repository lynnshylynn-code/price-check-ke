import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { ScreenHeader, StrategyButton, SummaryRow } from '../components/Common';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { categoryCode } from '../data/products';
import type { BasketLine, BasketStoreTotal, Product } from '../types';
import { basketPrice, money, storeLocationLabel } from '../utils/pricing';
import { BasketPricingResponse } from '../types/market';

export function BasketScreen({
  basket,
  total,
  products,
  catalogLoading,
  catalogError,
  pricing,
  pricingError,
  pricingLoading,
  storeComparison,
  budget,
  shoppingArea,
  onChangeArea,
  singleStore,
  singleStoreLabel,
  onChangeQuantity,
  onSetStrategy,
  onSearch,
}: {
  basket: BasketLine[];
  total: number;
  products: Product[];
  catalogLoading: boolean;
  catalogError: string | null;
  pricing: BasketPricingResponse | null;
  pricingError: string | null;
  pricingLoading: boolean;
  storeComparison: BasketStoreTotal[];
  budget: number;
  shoppingArea: string;
  onChangeArea: () => void;
  singleStore: string | null;
  singleStoreLabel: string | null;
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
              const product = products.find((item) => item.id === line.productId);
              if (!product) return null;
              return storeLocationLabel(basketPrice(product, line.strategy, singleStore));
            })
            .filter(Boolean),
        ).size;
  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader
        title="Your smart basket"
        shoppingArea={shoppingArea}
        onChangeArea={onChangeArea}
      />
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
            title="One retailer location"
            subtitle={singleStoreLabel ? `${singleStoreLabel} is cheapest` : 'No complete location coverage'}
            icon="storefront-outline"
            disabled={!singleStore}
            onPress={() => onSetStrategy('single')}
          />
        </View>
      </View>
      <View style={styles.basketComparisonCard}>
        <View style={styles.basketComparisonHeading}>
          <View>
            <Text style={styles.basketComparisonEyebrow}>WHOLE BASKET COMPARISON</Text>
            <Text style={styles.sectionTitle}>Lowest complete location</Text>
          </View>
          <Text style={styles.basketComparisonCount}>
            All {basket.length} {basket.length === 1 ? 'item' : 'items'}
          </Text>
        </View>
        {storeComparison.length > 0 ? (
          storeComparison.map((item, index) => (
            <View
              key={item.store}
              style={[
                styles.basketComparisonRow,
                index === 0 && styles.basketComparisonRowBest,
              ]}
            >
              <View
                style={[
                  styles.basketComparisonRank,
                  index === 0 && styles.basketComparisonRankBest,
                ]}
              >
                <Text
                  style={[
                    styles.basketComparisonRankText,
                    index === 0 && styles.basketComparisonRankTextBest,
                  ]}
                >
                  {index + 1}
                </Text>
              </View>
              <View style={styles.basketComparisonStore}>
                <Text style={styles.basketComparisonStoreName}>{item.store}</Text>
                <Text style={styles.basketComparisonCaption}>
                  {index === 0
                    ? 'Lowest basket total'
                    : `${money(item.total - storeComparison[0].total)} more`}
                </Text>
              </View>
              {index === 0 && (
                <View style={styles.basketComparisonBestTag}>
                  <Text style={styles.basketComparisonBestTagText}>BEST</Text>
                </View>
              )}
              <Text style={styles.basketComparisonTotal}>{money(item.total)}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.emptyBody}>
            Add products with overlapping store prices to compare a complete basket.
          </Text>
        )}
        <Text style={styles.basketComparisonFootnote}>
          Prices include each item quantity and use observed listings, not checkout totals.
        </Text>
        {pricingLoading && <Text style={styles.marketMuted}>Refreshing observed listing prices…</Text>}
        {pricingError && (
          <Text style={styles.marketStatusText}>
            Could not refresh basket pricing: {pricingError}
          </Text>
        )}
        {catalogLoading && <Text style={styles.marketMuted}>Loading verified prices…</Text>}
        {catalogError && (
          <Text style={styles.marketStatusText}>
            Could not refresh the retailer catalog: {catalogError}
          </Text>
        )}
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
          <Text style={styles.basketHintText}>Observed prices</Text>
        </View>
      </View>
      {basket.some((line) => !products.some((product) => product.id === line.productId)) && (
        <Text style={styles.marketStatusText}>
          Some saved items do not have a verified listing in {shoppingArea}. They are excluded from totals.
        </Text>
      )}
      {basket.length > 0 ? (
        basket.map((line) => {
          const product = products.find((item) => item.id === line.productId);
          if (!product) {
            return (
              <View style={styles.basketProduct} key={line.productId}>
                <View style={styles.productBadge}>
                  <Text style={styles.productBadgeText}>?</Text>
                </View>
                <View style={styles.basketProductDetails}>
                  <Text style={styles.productName}>Saved item without a verified listing</Text>
                  <Text style={styles.productDescription}>
                    {line.productId} · excluded from price totals
                  </Text>
                  <Pressable
                    onPress={() => onChangeQuantity(line.productId, -line.quantity)}
                    accessibilityRole="button"
                    accessibilityLabel={`Remove unverified ${line.productId} from basket`}
                  >
                    <Text style={styles.linkText}>Remove</Text>
                  </Pressable>
                </View>
              </View>
            );
          }
          const fallbackPrice = basketPrice(product, line.strategy, singleStore);
          const pricedLine = pricing?.lines.find((item) => item.product_id === line.productId);
          const price = pricedLine?.unit_price ?? fallbackPrice.price;
          const selectedStore = pricedLine?.store ?? storeLocationLabel(fallbackPrice);
          return (
            <View style={styles.basketProduct} key={line.productId}>
              <View style={styles.productBadge}>
                <Text style={styles.productBadgeText}>{categoryCode[product.category]}</Text>
              </View>
              <View style={styles.basketProductDetails}>
                <Text style={styles.productName}>{product.name}</Text>
                <Text style={styles.productDescription}>
                  {product.size} · {selectedStore} · {money(price)} each
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
              <Text style={styles.basketLineTotal}>
                {money(pricedLine?.total ?? price * line.quantity)}
              </Text>
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
        <Text style={styles.modalDisclaimer}>
          Estimates use observed retailer listings; prices may change.
        </Text>
      </View>
    </ScrollView>
  );
}
