import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import { AssistantChat } from '../components/AssistantChat';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from 'react-native';
import { MetricCard, ScreenHeader, SectionHeading } from '../components/Common';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { categoryCode } from '../data/products';
import { useFoodInflation } from '../hooks/useFoodInflation';
import { bestPrice, money } from '../utils/pricing';
import { Product } from '../types';

export function TrendsScreen({
  watchedIds,
  shoppingArea,
  onChangeArea,
  onOpenProduct,
  onBrowse,
  products,
}: {
  watchedIds: string[];
  shoppingArea: string;
  onChangeArea: () => void;
  onOpenProduct: (product: Product) => void;
  onBrowse: () => void;
  products: Product[];
}) {
  const { data, error, isLoading, retry } = useFoodInflation();
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const watchedProducts = products.filter((product) => watchedIds.includes(product.id));
  const availableYears = [...new Set(data?.observations.map((item) => item.year) ?? [])];
  const displayedYear =
    selectedYear !== null && availableYears.includes(selectedYear)
      ? selectedYear
      : (data?.series.year ?? 0);
  const observations = data?.observations.filter((item) => item.year === displayedYear) ?? [];
  const chartMaximum = Math.max(...observations.map((item) => Math.abs(item.value)), 1);

  return (
    <ScrollView contentContainerStyle={styles.screenContent} showsVerticalScrollIndicator={false}>
      <ScreenHeader
        title="Your price trends"
        shoppingArea={shoppingArea}
        onChangeArea={onChangeArea}
      />
      {isLoading && (
        <View style={styles.emptyState} accessibilityRole="progressbar">
          <ActivityIndicator color={COLORS.green} />
          <Text style={styles.emptyBody}>Loading Kenya food-market data…</Text>
        </View>
      )}
      {error && (
        <View style={styles.emptyState}>
          <Ionicons name="cloud-offline-outline" size={28} color={COLORS.green} />
          <Text style={styles.emptyTitle}>Market data unavailable</Text>
          <Text style={styles.emptyBody}>{error}</Text>
          <Pressable style={styles.primaryButton} onPress={retry} accessibilityRole="button">
            <Text style={styles.primaryButtonText}>Try again</Text>
          </Pressable>
        </View>
      )}
      {data && (
        <>
          <View style={styles.metricGrid}>
            <MetricCard
              icon="analytics-outline"
              label="Latest signal"
              value={`${data.summary.latest_value > 0 ? '+' : ''}${data.summary.latest_value}%`}
              hint={`Food index · ${data.summary.latest_month}`}
            />
            <MetricCard
              icon="eye-outline"
              label="Prices watched"
              value={String(watchedIds.length)}
              hint="Retail alerts are demo-only"
            />
            <MetricCard
              icon="calendar-outline"
              label="Monthly values"
              value={String(data.summary.observation_count)}
              hint={`${data.series.coverage_start}–${data.series.coverage_end}`}
            />
          </View>
          <View style={styles.chartCard}>
            <View style={styles.chartHeader}>
              <View>
                <Text style={styles.eyebrow}>
                  {data.series.market_scope} · {displayedYear}
                </Text>
                <Text style={styles.sectionTitle}>Food-price inflation signal</Text>
              </View>
              <View style={styles.chartValuePill}>
                <Text style={styles.chartValueText}>
                  {data.summary.latest_value > 0 ? '+' : ''}
                  {data.summary.latest_value}%
                </Text>
              </View>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.chipRow}
              accessibilityLabel="Select data year"
            >
              {availableYears.map((year) => (
                <Pressable
                  key={year}
                  style={[styles.filterChip, displayedYear === year && styles.filterChipActive]}
                  onPress={() => setSelectedYear(year)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: displayedYear === year }}
                >
                  <Text
                    style={[
                      styles.filterChipText,
                      displayedYear === year && styles.filterChipTextActive,
                    ]}
                  >
                    {year}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
            <View style={styles.chart}>
              {observations.map((item) => {
                const height = Math.max(8, (Math.abs(item.value) / chartMaximum) * 102);
                const negative = item.value < 0;
                return (
                  <View style={styles.chartColumn} key={`${item.year}-${item.month_number}`}>
                    <Text style={[styles.chartBarValue, negative && styles.chartNegative]}>
                      {item.value > 0 ? '+' : ''}
                      {item.value.toFixed(1)}
                    </Text>
                    <View style={styles.chartBarTrack}>
                      <View
                        style={[
                          styles.chartBar,
                          { height },
                          negative && styles.chartBarNegative,
                          item.year === data.series.year &&
                            item.month === data.summary.latest_month.slice(0, 3) &&
                            styles.chartBarLatest,
                        ]}
                      />
                    </View>
                    <Text style={styles.chartMonth}>{item.month}</Text>
                  </View>
                );
              })}
            </View>
            <Text style={styles.chartFootnote}>
              {data.series.indicator} ({data.series.unit}) · {data.series.market_id}.{' '}
              {data.series.source_note}
            </Text>
          </View>
          <AssistantChat />
        </>
      )}
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
