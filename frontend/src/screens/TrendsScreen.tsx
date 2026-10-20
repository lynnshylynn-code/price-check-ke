import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';
import { MetricCard, ScreenHeader, SectionHeading } from '../components/Common';
import { COLORS } from '../constants/theme';
import { styles } from '../constants/styles';
import { categoryCode } from '../data/products';
import { useFoodInflation } from '../hooks/useFoodInflation';
import {
  askMarketQuestion,
  MarketQuestionAnswer,
  simulateMarketQuestion,
} from '../services/aiApi';
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
  const [question, setQuestion] = useState('');
  const [aiAnswer, setAiAnswer] = useState<MarketQuestionAnswer | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [simulationAnswer, setSimulationAnswer] = useState<MarketQuestionAnswer | null>(null);
  const [fallbackMode, setFallbackMode] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const watchedProducts = products.filter((product) => watchedIds.includes(product.id));
  const availableYears = [...new Set(data?.observations.map((item) => item.year) ?? [])];
  const displayedYear =
    selectedYear !== null && availableYears.includes(selectedYear)
      ? selectedYear
      : (data?.series.year ?? 0);
  const observations = data?.observations.filter((item) => item.year === displayedYear) ?? [];
  const chartMaximum = Math.max(...observations.map((item) => Math.abs(item.value)), 1);

  async function submitQuestion() {
    const submittedQuestion = question.trim();
    if (!submittedQuestion || isAsking) return;

    setIsAsking(true);
    setAiError(null);
    setAiAnswer(null);
    setSimulationAnswer(null);
    const requestController = new AbortController();
    const requestTimeout = setTimeout(() => requestController.abort(), 22_000);
    try {
      const [simulation, liveAnswer] = await Promise.allSettled([
        simulateMarketQuestion(submittedQuestion, requestController.signal),
        askMarketQuestion(submittedQuestion, requestController.signal),
      ]);
      if (simulation.status === 'fulfilled') {
        setSimulationAnswer(simulation.value);
        setFallbackMode(true);
      } else {
        setAiError(
          simulation.reason instanceof Error
            ? `Dataset answer unavailable: ${simulation.reason.message}`
            : 'Dataset answer unavailable.',
        );
      }
      if (liveAnswer.status === 'fulfilled') {
        setAiAnswer(liveAnswer.value);
        setSimulationAnswer(null);
        setFallbackMode(false);
        setAiError(null);
      } else {
        const reason =
          requestController.signal.aborted
            ? 'The live AI request timed out after 22 seconds.'
            : liveAnswer.reason instanceof Error
              ? liveAnswer.reason.message
              : 'The live AI service could not answer.';
        setAiError(
          simulation.status === 'fulfilled'
            ? `Live AI is unavailable (${reason}). Showing the API-generated dataset answer.`
            : `Live AI is unavailable (${reason}).`,
        );
      }
    } finally {
      clearTimeout(requestTimeout);
      setIsAsking(false);
    }
  }

  async function runDemoSimulation() {
    const submittedQuestion = question.trim();
    if (!submittedQuestion || isAsking) return;
    setIsAsking(true);
    setAiError(null);
    setAiAnswer(null);
    setSimulationAnswer(null);
    try {
      setSimulationAnswer(await simulateMarketQuestion(submittedQuestion));
      setFallbackMode(false);
    } catch (simulationError) {
      setAiError(
        simulationError instanceof Error
          ? `Dataset simulation unavailable: ${simulationError.message}`
          : 'Dataset simulation unavailable.',
      );
    } finally {
      setIsAsking(false);
    }
  }

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
          <View style={styles.aiCard}>
            <View style={styles.aiCardHeader}>
              <View style={styles.aiIcon}>
                <Ionicons name="sparkles" size={18} color={COLORS.green} />
              </View>
              <Text style={styles.aiLabel}>RTFP dataset exploration</Text>
              <View style={styles.ruleBasedTag}>
                <Text style={styles.ruleBasedTagText}>DESCRIPTIVE</Text>
              </View>
            </View>
            <Text style={styles.aiHeadline}>
              Summary of {data.summary.observation_count} monthly observations
            </Text>
            <Text style={styles.aiBody}>{data.summary.narrative}</Text>
            <Text style={styles.aiBody}>
              Mean: {data.summary.mean_value.toFixed(2)}% · Lowest: {data.summary.minimum_value}% (
              {data.summary.minimum_month}) · Highest: {data.summary.peak_value}% (
              {data.summary.peak_month})
            </Text>
            <View style={styles.aiSource}>
              <Ionicons name="document-text-outline" size={15} color={COLORS.green} />
              <Text style={styles.aiSourceText}>
                {data.series.source_name} · {data.series.country}
              </Text>
            </View>
            <Text style={styles.aiFootnote}>
              Descriptive analysis of the supplied RTFP dataset. It is not a generative AI result,
              forecast, or supermarket price.
            </Text>
          </View>
          <View style={styles.aiCard}>
            <View style={styles.aiCardHeader}>
              <View style={styles.aiIcon}>
                <Ionicons name="chatbubble-ellipses-outline" size={18} color={COLORS.green} />
              </View>
              <Text style={styles.aiLabel}>Ask AI about this dataset</Text>
              <View style={styles.ruleBasedTag}>
                <Text style={styles.ruleBasedTagText}>AI + FALLBACK</Text>
              </View>
            </View>
            <Text style={styles.aiBody}>
              Ask about historical trends from {data.series.coverage_start} to{' '}
              {data.series.coverage_end}. Avoid entering personal information.
            </Text>
            <View style={styles.simulationPromptRow}>
              <Pressable
                style={styles.filterChip}
                onPress={() => setQuestion('What was the latest food inflation reading?')}
                accessibilityRole="button"
              >
                <Text style={styles.filterChipText}>Latest reading</Text>
              </Pressable>
              <Pressable
                style={styles.filterChip}
                onPress={() => setQuestion('What was the average food inflation?')}
                accessibilityRole="button"
              >
                <Text style={styles.filterChipText}>Average reading</Text>
              </Pressable>
            </View>
            <TextInput
              style={styles.aiQuestionInput}
              value={question}
              onChangeText={setQuestion}
              placeholder="e.g. What was the biggest change?"
              placeholderTextColor={COLORS.muted}
              maxLength={500}
              multiline
              accessibilityLabel="Ask a question about Kenya food-price history"
              textAlignVertical="top"
            />
            <Pressable
              style={[styles.primaryButton, isAsking && styles.aiSubmitDisabled]}
              onPress={submitQuestion}
              disabled={isAsking || !question.trim()}
              accessibilityRole="button"
              accessibilityState={{ disabled: isAsking || !question.trim() }}
            >
              {isAsking ? (
                <ActivityIndicator color="#FFFFFF" size="small" />
              ) : (
                <Ionicons name="sparkles-outline" size={16} color="#FFFFFF" />
              )}
              <Text style={styles.primaryButtonText}>{isAsking ? 'Thinking…' : 'Ask AI'}</Text>
            </Pressable>
            <Pressable
              style={styles.simulationButton}
              onPress={runDemoSimulation}
              disabled={!question.trim() || isAsking}
              accessibilityRole="button"
              accessibilityState={{ disabled: !question.trim() || isAsking }}
            >
              <Ionicons name="play-circle-outline" size={17} color={COLORS.green} />
              <Text style={styles.simulationButtonText}>Run data simulation</Text>
            </Pressable>
            {aiError && (
              <Text style={styles.aiError} accessibilityRole="alert">
                {aiError}
              </Text>
            )}
            {simulationAnswer && (
              <View style={styles.simulationAnswer} accessibilityRole="summary">
                <View style={styles.aiCardHeader}>
                  <Text style={styles.aiHeadline}>
                    {fallbackMode ? 'Dataset answer' : 'Simulated response'}
                  </Text>
                  <View style={styles.simulationTag}>
                    <Text style={styles.simulationTagText}>
                      {fallbackMode
                        ? isAsking
                          ? 'LIVE AI PENDING'
                          : 'OFFLINE FALLBACK'
                        : 'NOT LIVE AI'}
                    </Text>
                  </View>
                </View>
                <Text style={styles.aiBody}>{simulationAnswer.answer}</Text>
                <Text style={styles.aiSourceText}>
                  Source: {simulationAnswer.source_name} · {simulationAnswer.coverage_start}–
                  {simulationAnswer.coverage_end}
                </Text>
                <Text style={styles.aiSourceText}>{simulationAnswer.source_url}</Text>
              </View>
            )}
            {aiAnswer && (
              <View style={styles.aiAnswer}>
                <View style={styles.aiCardHeader}>
                  <Text style={styles.aiHeadline}>Live AI answer</Text>
                  <View style={styles.liveAiTag}>
                    <Text style={styles.liveAiTagText}>OPENAI</Text>
                  </View>
                </View>
                <Text style={styles.aiBody}>{aiAnswer.answer}</Text>
                <Text style={styles.aiSourceText}>
                  Source: {aiAnswer.source_name} · {aiAnswer.coverage_start}–
                  {aiAnswer.coverage_end}
                </Text>
                <Text style={styles.aiSourceText}>{aiAnswer.source_url}</Text>
              </View>
            )}
            <Text style={styles.aiFootnote}>
              Live answers use OpenAI with data tools. If unavailable, the API provides a clearly
              labelled dataset answer. Neither is a live supermarket price or forecast.
            </Text>
          </View>
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
