import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { PriceSeriesResponse } from '../types/market';

function monthLabel(value: string): string {
  const [year, month] = value.split('-');
  const monthName = new Date(Date.UTC(Number(year), Number(month) - 1, 1)).toLocaleString(
    'en',
    { month: 'short', timeZone: 'UTC' },
  );
  return `${monthName} ${year}`;
}

function LatestCommodityRows({
  title,
  series,
}: {
  title: string;
  series: PriceSeriesResponse | null;
}) {
  const latestDate = series?.observations.reduce(
    (latest, observation) => (observation.date > latest ? observation.date : latest),
    '',
  );
  const latest = series?.observations.filter((observation) => observation.date === latestDate) ?? [];

  return (
    <View style={styles.marketCommodity}>
      <Text style={styles.marketCommodityTitle}>{title}</Text>
      {latest.length > 0 ? (
        <>
          {latest.slice(0, 4).map((observation) => (
            <View
              key={`${observation.market}-${observation.date}`}
              style={styles.marketPriceRow}
            >
              <Text style={styles.marketName}>{observation.market}</Text>
              <Text style={styles.marketPrice}>
                {observation.currency} {observation.price.toLocaleString('en-KE')} / kg
              </Text>
            </View>
          ))}
          {latest.length > 4 && (
            <Text style={styles.marketMuted}>
              And {latest.length - 4} other source market{latest.length - 4 === 1 ? '' : 's'}
            </Text>
          )}
          <Text style={styles.marketMuted}>Latest record: {monthLabel(latest[0].date.slice(0, 7))}</Text>
        </>
      ) : (
        <Text style={styles.marketMuted}>
          No {title.toLowerCase()} price observations are available for this area.
        </Text>
      )}
    </View>
  );
}

export function MarketPricesCard({
  area,
  beans,
  maize,
  loading,
  error,
  fromCache,
}: {
  area: string;
  beans: PriceSeriesResponse | null;
  maize: PriceSeriesResponse | null;
  loading: boolean;
  error: string | null;
  fromCache: boolean;
}) {
  return (
    <View style={styles.marketPricesCard}>
      <View style={styles.marketPricesHeader}>
        <View style={styles.marketPricesIcon}>
          <Ionicons name="analytics-outline" size={18} color={COLORS.green} />
        </View>
        <View style={styles.marketPricesHeading}>
          <Text style={styles.marketPricesTitle}>World Bank market data · {area}</Text>
          <Text style={styles.marketPricesSubtitle}>Observed prices · KES per kg · not supermarket prices</Text>
        </View>
        {loading && <ActivityIndicator size="small" color={COLORS.green} />}
      </View>
      <LatestCommodityRows title="Beans" series={beans} />
      <LatestCommodityRows title="Maize" series={maize} />
      {(error || fromCache) && (
        <Text style={styles.marketStatusText}>
          {fromCache ? `Showing saved data. ${error ?? ''}` : error}
        </Text>
      )}
      <Text style={styles.marketSourceText}>
        {beans?.source_name ?? maize?.source_name ?? 'World Bank Kenya RTFP'}
      </Text>
    </View>
  );
}
