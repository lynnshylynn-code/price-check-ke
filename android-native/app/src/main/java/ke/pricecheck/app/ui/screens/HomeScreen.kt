package ke.pricecheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.tooling.preview.Preview
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.data.MarketArea
import ke.pricecheck.app.R
import ke.pricecheck.app.ui.PriceCheckUiState
import ke.pricecheck.app.ui.PriceCheckTheme
import ke.pricecheck.app.ui.components.DemoNotice
import ke.pricecheck.app.ui.components.InfoCard
import ke.pricecheck.app.ui.components.MarketLoadState
import ke.pricecheck.app.ui.components.ProductCard
import ke.pricecheck.app.ui.components.SectionTitle
import ke.pricecheck.app.ui.components.SectionTitle

@Composable
fun HomeScreen(
    state: PriceCheckUiState,
    products: List<Product>,
    categories: List<String>,
    onSearch: () -> Unit,
    onCategory: (String) -> Unit,
    onOpenProduct: (Product) -> Unit,
    onAddProduct: (Product) -> Unit,
    onTrends: () -> Unit,
    onRefresh: () -> Unit,
    onToggleWatched: (String) -> Unit,
    onArea: (String) -> Unit,
) {
    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text(stringResource(R.string.home_welcome), style = MaterialTheme.typography.headlineMedium)
                Text(
                    stringResource(
                        if (state.productsAreDemo) R.string.home_subtitle
                        else R.string.home_subtitle_snapshot,
                    ),
                )
            }
        }
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(stringResource(R.string.weekly_budget), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.ksh_amount, state.preferences.weeklyBudget), style = MaterialTheme.typography.headlineSmall)
                    Text(
                        stringResource(
                            if (state.productsAreDemo) R.string.budget_saved_demo_prices
                            else R.string.budget_saved_snapshot,
                        ),
                    )
                }
            }
        }
        item {
            OutlinedTextField(
                value = "",
                onValueChange = {},
                modifier = Modifier.fillMaxWidth(),
                readOnly = true,
                label = { Text(stringResource(R.string.search_products)) },
                placeholder = { Text(stringResource(R.string.home_search_hint)) },
                trailingIcon = {
                    OutlinedButton(onClick = onSearch) { Text(stringResource(R.string.tab_search)) }
                },
            )
        }
        item { SectionTitle(stringResource(R.string.browse_categories)) }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(categories.drop(1)) { category ->
                    FilterChip(
                        selected = false,
                        onClick = { onCategory(category) },
                        label = { Text(category) },
                    )
                }
            }
        }
        item {
            DemoNotice(
                stringResource(
                    if (state.productsAreDemo) R.string.demo_prices_notice
                    else R.string.snapshot_listing_notice,
                ),
            )
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.shopping_area), style = MaterialTheme.typography.titleMedium)
                if (state.marketDirectoryLoading || state.marketDirectoryError != null) {
                    MarketLoadState(
                        loading = state.marketDirectoryLoading,
                        error = state.marketDirectoryError,
                        onRetry = onRefresh,
                    )
                } else {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(state.marketAreas, key = MarketArea::county) { area ->
                            FilterChip(
                                selected = state.preferences.shoppingArea == area.county,
                                onClick = { onArea(area.county) },
                                label = { Text(area.county) },
                            )
                        }
                    }
                }
                Text(stringResource(R.string.demo_area_disclaimer), style = MaterialTheme.typography.bodySmall)
            }
        }
        items(products, key = Product::id) { product ->
            ProductCard(
                product = product,
                watched = product.id in state.preferences.watchedProductIds,
                onOpen = { onOpenProduct(product) },
                onAdd = { onAddProduct(product) },
                onToggleWatched = { onToggleWatched(product.id) },
            )
        }
        item {
            MarketLoadState(loading = state.areaMarketLoading, error = state.areaMarketError, onRetry = onRefresh)
        }
        state.areaMarketData?.let { data ->
            item {
                InfoCard(
                    title = stringResource(R.string.market_data_title),
                    body = buildString {
                        append(stringResource(R.string.market_data_source, data.sourceName))
                        append('\n')
                        if (data.coverageStart.isNotBlank() && data.coverageEnd.isNotBlank()) {
                            append(stringResource(R.string.market_data_coverage, data.coverageStart, data.coverageEnd))
                        } else {
                            append(stringResource(R.string.market_no_coverage))
                        }
                        append('\n')
                        if (data.latestMonth.isNotBlank()) {
                            append(stringResource(R.string.market_data_latest_month, data.latestMonth))
                        } else {
                            append(stringResource(R.string.market_no_latest))
                        }
                        listOf("maize", "beans").forEach { commodity ->
                            if (data.prices.none { it.commodity == commodity }) {
                                append('\n')
                                append(stringResource(R.string.market_commodity_empty, stringResource(marketCommodityLabel(commodity))))
                            }
                        }
                        data.prices.forEach { price ->
                            append('\n')
                            val commodityLabel = stringResource(
                                marketCommodityLabel(price.commodity),
                            )
                            append(stringResource(R.string.market_price_line, price.market, commodityLabel, price.price, price.currency, price.unit, price.date))
                        }
                    },
                )
            }
        }
        item {
            Button(onClick = onTrends, modifier = Modifier.fillMaxWidth()) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    androidx.compose.material3.Icon(Icons.Filled.Add, contentDescription = null)
                    Text(stringResource(R.string.explore_trends_ai))
                }

            }
        }
    }
}

private fun marketCommodityLabel(commodity: String): Int = when (commodity) {
    "maize" -> R.string.market_maize
    else -> R.string.market_beans
}

@Preview(showBackground = true)
@Composable
private fun HomeWelcomePreview() {
    PriceCheckTheme {
        SectionTitle(stringResource(R.string.home_welcome), stringResource(R.string.home_subtitle))
    }
}
