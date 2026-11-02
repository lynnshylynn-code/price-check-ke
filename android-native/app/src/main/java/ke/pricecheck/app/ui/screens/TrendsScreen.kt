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
import ke.pricecheck.app.ui.AssistantChatMessage
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
    onNewChat: () -> Unit,
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
            item { AiQuestionCard(state, onQuestion, onAsk, onNewChat) }
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
    onNewChat: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text(stringResource(R.string.ai_card_title), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(R.string.ai_card_description))
            Text(stringResource(R.string.assistant_chat_note), style = MaterialTheme.typography.bodySmall)
            Text(stringResource(R.string.assistant_chat_privacy), style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onNewChat) { Text(stringResource(R.string.assistant_new_chat)) }
                TextButton(onClick = onNewChat) { Text(stringResource(R.string.assistant_clear_chat)) }
            }
            LazyColumn(
                modifier = Modifier.fillMaxWidth().height(260.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.assistantMessages) { message: AssistantChatMessage ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (message.role == "user") Arrangement.End else Arrangement.Start,
                    ) {
                        Card(
                            modifier = Modifier.fillMaxWidth(0.88f),
                            colors = androidx.compose.material3.CardDefaults.cardColors(
                                containerColor = if (message.role == "user")
                                    MaterialTheme.colorScheme.primaryContainer
                                else MaterialTheme.colorScheme.surfaceVariant,
                            ),
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(message.text)
                                if (message.intent != null && message.confidencePercent != null) {
                                    Text(
                                        stringResource(
                                            R.string.assistant_understood_as,
                                            message.intent,
                                            message.confidencePercent,
                                        ),
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                                if (message.role == "assistant" && message.sourceName != null) {
                                    Text(
                                        stringResource(
                                            R.string.assistant_chat_source,
                                            message.sourceName.orEmpty(),
                                            message.coverageStart.orEmpty(),
                                            message.coverageEnd.orEmpty(),
                                        ),
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                            }
                        }
                    }
                }
                if (state.aiLoading) item { Text(stringResource(R.string.assistant_typing)) }
            }
            if (state.assistantSuggestions.isNotEmpty()) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.assistantSuggestions.take(3)) { suggestion ->
                        FilterChip(selected = false, onClick = { onQuestion(suggestion) }, label = { Text(suggestion) })
                    }
                }
            }
            OutlinedTextField(
                value = state.question,
                onValueChange = onQuestion,
                modifier = Modifier.fillMaxWidth(),
                label = { Text(stringResource(R.string.your_question)) },
                placeholder = { Text(stringResource(R.string.assistant_message_hint)) },
                minLines = 1,
                maxLines = 3,
            )
            Button(onClick = onAsk, enabled = state.question.isNotBlank() && !state.aiLoading) {
                Text(if (state.aiLoading) stringResource(R.string.contacting_ai)
                     else stringResource(R.string.assistant_send))
            }
            if (state.aiError != null) {
                Text(
                    stringResource(R.string.live_ai_unavailable, state.aiError),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
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
