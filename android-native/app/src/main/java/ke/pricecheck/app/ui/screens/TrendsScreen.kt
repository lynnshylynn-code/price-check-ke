package ke.pricecheck.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.tooling.preview.Preview
import ke.pricecheck.app.R
import ke.pricecheck.app.data.FoodInflationData
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.ui.PriceCheckUiState
import ke.pricecheck.app.ui.PriceCheckTheme
import ke.pricecheck.app.ui.components.DemoNotice
import ke.pricecheck.app.ui.components.InfoCard
import ke.pricecheck.app.ui.components.MarketLoadState
import ke.pricecheck.app.ui.components.MetricRow
import ke.pricecheck.app.ui.components.ProductCard
import ke.pricecheck.app.ui.components.SectionTitle
import kotlin.math.abs

@Composable
fun TrendsScreen(
    state: PriceCheckUiState,
    products: List<Product>,
    onQuestion: (String) -> Unit,
    onAsk: () -> Unit,
    onSimulate: () -> Unit,
    onSelectYear: (Int) -> Unit,
    onRefresh: () -> Unit,
    onOpenProduct: (Product) -> Unit,
    onAddProduct: (Product) -> Unit,
    onToggleWatched: (String) -> Unit,
) {
    val data = state.marketData
    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            SectionTitle(
                stringResource(R.string.trends_title),
                stringResource(R.string.trends_subtitle),
            )
        }
        item {
            MarketLoadState(
                loading = state.marketLoading && data == null,
                error = state.marketError.takeIf { data == null },
                onRetry = onRefresh,
            )
        }
        if (data != null) {
            item { SummaryCard(data) }
            item {
                val years = data.observations.map { it.year }.distinct()
                val selectedYear = state.selectedYear ?: data.series.year
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        stringResource(R.string.monthly_index_year, selectedYear),
                        style = MaterialTheme.typography.titleMedium,
                    )
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(years) { year ->
                            FilterChip(
                                selected = year == selectedYear,
                                onClick = { onSelectYear(year) },
                                label = { Text(year.toString()) },
                            )
                        }
                    }
                    val selectedObservations = data.observations.filter { it.year == selectedYear }
                    val maxValue = selectedObservations.maxOfOrNull { abs(it.value) }?.coerceAtLeast(1.0) ?: 1.0
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(selectedObservations) { observation ->
                            val barHeight = animateDpAsState(
                                targetValue = (12 + 70 * abs(observation.value) / maxValue).dp,
                                label = "trend_bar_height",
                            ).value
                            Column(
                                modifier = Modifier.width(42.dp).height(132.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Bottom,
                            ) {
                                Text(
                                    "%.1f".format(java.util.Locale.ROOT, observation.value),
                                    style = MaterialTheme.typography.labelSmall,
                                )
                                Box(
                                    modifier = Modifier
                                        .padding(vertical = 5.dp)
                                        .width(20.dp)
                                        .height(barHeight)
                                        .background(
                                            if (observation.value < 0) MaterialTheme.colorScheme.error
                                            else MaterialTheme.colorScheme.primary,
                                            RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp),
                                        ),
                                )
                                Text(observation.month, style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
            item {
                Text(
                    stringResource(R.string.trends_indicator, data.series.marketScope),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            item {
                InfoCard(
                    title = stringResource(R.string.source_and_coverage),
                    body = stringResource(
                        R.string.source_coverage_body,
                        data.series.sourceName,
                        data.series.coverageStart,
                        data.series.coverageEnd,
                        data.series.sourceUrl,
                    ),
                )
            }
            item { AiQuestionCard(state, onQuestion, onAsk, onSimulate, data) }
            item { DemoNotice(stringResource(R.string.watchlist_local_notice)) }
            items(state.preferences.watchedProductIds.toList(), key = { it }) { id ->
                val product = products.find { it.id == id }
                if (product != null) {
                    ProductCard(
                        product = product,
                        watched = true,
                        onOpen = { onOpenProduct(product) },
                        onAdd = { onAddProduct(product) },
                        onToggleWatched = { onToggleWatched(product.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun SummaryCard(data: FoodInflationData) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        MetricRow(
            label = stringResource(R.string.latest_signal),
            value = stringResource(R.string.latest_signal_value, data.summary.latestValue),
            supporting = stringResource(R.string.food_index_month, data.summary.latestMonth),
        )
        MetricRow(
            label = stringResource(R.string.reported_observations),
            value = data.summary.observationCount.toString(),
            supporting = stringResource(
                R.string.coverage_range,
                data.series.coverageStart,
                data.series.coverageEnd,
            ),
        )
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(stringResource(R.string.historical_summary), style = MaterialTheme.typography.titleMedium)
                Text(data.summary.narrative)
                Text(
                    stringResource(
                        R.string.historical_metrics,
                        data.summary.meanValue,
                        data.summary.minimumValue,
                        data.summary.minimumMonth,
                        data.summary.peakValue,
                        data.summary.peakMonth,
                    ),
                )
            }
        }
    }
}

@Composable
private fun AiQuestionCard(
    state: PriceCheckUiState,
    onQuestion: (String) -> Unit,
    onAsk: () -> Unit,
    onSimulate: () -> Unit,
    data: FoodInflationData,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Text(stringResource(R.string.ai_card_title), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(R.string.ai_card_description))
            val prompts = listOf(
                stringResource(R.string.ai_prompt_latest),
                stringResource(R.string.ai_prompt_average),
                stringResource(R.string.ai_prompt_month),
            )
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(prompts) { prompt ->
                    TextButton(onClick = { onQuestion(prompt) }) {
                        Text(prompt.substringBefore('?'))
                    }
                }
            }
            OutlinedTextField(
                value = state.question,
                onValueChange = onQuestion,
                modifier = Modifier.fillMaxWidth(),
                label = { Text(stringResource(R.string.your_question)) },
                placeholder = { Text(stringResource(R.string.ai_question_hint)) },
                minLines = 2,
                maxLines = 4,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = onAsk,
                    enabled = state.question.trim().length >= 3 && !state.aiLoading,
                ) {
                    Text(
                        if (state.aiLoading) stringResource(R.string.contacting_ai)
                        else stringResource(R.string.ask_ai),
                    )
                }
                OutlinedButton(
                    onClick = onSimulate,
                    enabled = state.question.trim().length >= 3 && !state.aiLoading,
                ) {
                    Text(stringResource(R.string.simulate))
                }
            }
            if (state.aiError != null) {
                Text(
                    stringResource(R.string.live_ai_unavailable, state.aiError),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            AnimatedVisibility(visible = state.answer != null) {
                state.answer?.let { answer ->
                    Card(
                        colors = androidx.compose.material3.CardDefaults.cardColors(
                            containerColor = if (state.answerIsOffline) {
                                MaterialTheme.colorScheme.tertiaryContainer
                            } else {
                                MaterialTheme.colorScheme.secondaryContainer
                            },
                        ),
                    ) {
                        Column(
                            modifier = Modifier.padding(14.dp),
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            Text(
                                when {
                                    state.aiLoading -> stringResource(R.string.dataset_answer_live_pending)
                                    state.answerIsOffline -> stringResource(R.string.offline_dataset_answer)
                                    else -> stringResource(R.string.live_ai_answer)
                                },
                                style = MaterialTheme.typography.titleSmall,
                            )
                            Text(answer)
                            state.answerIntent?.let { intent ->
                                Text(
                                    stringResource(
                                        R.string.assistant_understood_as,
                                        intent,
                                        ((state.answerIntentConfidence ?: 0.0) * 100).toInt(),
                                    ),
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            state.answerSourceName?.let { source ->
                                Text(
                                    stringResource(
                                        R.string.answer_source_details,
                                        source,
                                        state.answerCoverageStart.orEmpty(),
                                        state.answerCoverageEnd.orEmpty(),
                                        state.answerSourceUrl.orEmpty(),
                                    ),
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            state.answerSources.forEach { source ->
                                Text(
                                    stringResource(R.string.assistant_source_note, source.name, source.note),
                                    style = MaterialTheme.typography.bodySmall,
                                )
                                if (source.url.isNotBlank()) {
                                    Text(source.url, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun TrendsTitlePreview() {
    PriceCheckTheme {
        SectionTitle(
            stringResource(R.string.trends_title),
            stringResource(R.string.trends_subtitle),
        )
    }
}
