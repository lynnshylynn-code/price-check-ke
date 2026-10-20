package ke.pricecheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.unit.dp
import ke.pricecheck.app.R
import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.ui.PriceCheckUiState
import ke.pricecheck.app.ui.components.DemoNotice
import ke.pricecheck.app.ui.components.SectionTitle

@Composable
fun BasketScreen(
    state: PriceCheckUiState,
    products: List<Product>,
    onChangeQuantity: (String, Int) -> Unit,
    onChangeStrategy: (BasketStrategy) -> Unit,
    onBrowse: () -> Unit,
    onShare: () -> Unit,
    total: Int,
    lowestPerItemTotal: Int,
    singleStoreTotal: Int?,
    bestSingleStore: String?,
) {
    val basketProducts = state.preferences.basket.mapNotNull { (id, quantity) ->
        products.find { it.id == id }?.let { it to quantity }
    }

    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            SectionTitle(
                stringResource(R.string.your_basket),
                pluralStringResource(
                    R.plurals.basket_item_count,
                    state.preferences.basket.values.sum(),
                    state.preferences.basket.values.sum(),
                ),
            )
        }
        item { DemoNotice(stringResource(R.string.demo_prices_notice)) }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = state.preferences.basketStrategy == BasketStrategy.LOWEST_PER_ITEM,
                    onClick = { onChangeStrategy(BasketStrategy.LOWEST_PER_ITEM) },
                    label = { Text(stringResource(R.string.strategy_lowest_per_item)) },
                )
                FilterChip(
                    selected = state.preferences.basketStrategy == BasketStrategy.SINGLE_STORE,
                    onClick = { onChangeStrategy(BasketStrategy.SINGLE_STORE) },
                    enabled = bestSingleStore != null,
                    label = { Text(stringResource(R.string.strategy_one_store)) },
                )
            }
        }
        if (basketProducts.isEmpty()) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(stringResource(R.string.basket_empty))
                    Button(onClick = onBrowse) { Text(stringResource(R.string.browse_products)) }
                }
            }
        } else {
            items(basketProducts, key = { it.first.id }) { (product, quantity) ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(product.name, style = MaterialTheme.typography.titleMedium)
                        Text(
                            stringResource(
                                R.string.basket_product_price,
                                product.size,
                                product.lowestPrice.price,
                            ),
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            OutlinedButton(onClick = { onChangeQuantity(product.id, -1) }) {
                                Text(stringResource(R.string.decrease_quantity))
                            }
                            Text(
                                stringResource(R.string.quantity, quantity),
                                modifier = Modifier.padding(top = 12.dp),
                            )
                            OutlinedButton(onClick = { onChangeQuantity(product.id, 1) }) {
                                Text(stringResource(R.string.increase_quantity))
                            }
                        }
                    }
                }
            }
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text(stringResource(R.string.estimated_demo_total), style = MaterialTheme.typography.titleMedium)
                        Text(stringResource(R.string.ksh_amount, total), style = MaterialTheme.typography.headlineMedium)
                        if (state.preferences.basketStrategy == BasketStrategy.SINGLE_STORE && bestSingleStore != null) {
                            Text(stringResource(R.string.single_store_total, bestSingleStore))
                        } else {
                            Text(stringResource(R.string.lowest_item_total_disclaimer))
                        }
                        Text(stringResource(R.string.weekly_budget_amount, state.preferences.weeklyBudget))
                        Text(stringResource(R.string.basket_lowest_item_summary, lowestPerItemTotal))
                        if (bestSingleStore != null && singleStoreTotal != null) {
                            Text(stringResource(R.string.basket_single_store_summary, bestSingleStore, singleStoreTotal))
                        }
                        TextButton(onClick = onShare) { Text(stringResource(R.string.share_basket)) }
                    }
                }
            }
        }
    }
}
