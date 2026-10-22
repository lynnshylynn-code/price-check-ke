package ke.pricecheck.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.unit.dp
import ke.pricecheck.app.R
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.ui.PriceCheckUiState
import ke.pricecheck.app.ui.ProductSort
import ke.pricecheck.app.ui.components.DemoNotice
import ke.pricecheck.app.ui.components.ProductCard
import ke.pricecheck.app.ui.components.SectionTitle

@Composable
fun SearchScreen(
    state: PriceCheckUiState,
    products: List<Product>,
    categories: List<String>,
    onSearch: (String) -> Unit,
    onCategory: (String) -> Unit,
    onSort: () -> Unit,
    onOpenProduct: (Product) -> Unit,
    onAddProduct: (Product) -> Unit,
    onToggleWatched: (String) -> Unit,
) {
    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            SectionTitle(
                stringResource(R.string.find_best_price),
                stringResource(
                    if (state.productsAreDemo) R.string.search_subtitle
                    else R.string.search_snapshot_subtitle,
                ),
            )
        }
        item {
            OutlinedTextField(
                value = state.searchQuery,
                onValueChange = onSearch,
                modifier = Modifier.fillMaxWidth(),
                label = { Text(stringResource(R.string.search_products)) },
                placeholder = { Text(stringResource(R.string.search_hint)) },
                singleLine = true,
            )
        }
        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(categories) { category ->
                    FilterChip(
                        selected = state.selectedCategory == category,
                        onClick = { onCategory(category) },
                        label = { Text(category) },
                    )
                }
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    pluralStringResource(R.plurals.product_count, products.size, products.size),
                    style = MaterialTheme.typography.titleMedium,
                )
                Button(onClick = onSort) {
                    androidx.compose.material3.Icon(Icons.Filled.MoreVert, contentDescription = null)
                    val label = when (state.productSort) {
                        ProductSort.LOWEST_PRICE -> stringResource(R.string.sort_lowest_price)
                        ProductSort.HIGHEST_PRICE -> stringResource(R.string.sort_highest_price)
                        ProductSort.NAME -> stringResource(R.string.sort_name)
                    }
                    Text(label, modifier = Modifier.padding(start = 6.dp))
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
        if (products.isEmpty()) {
            item {
                Text(
                    stringResource(R.string.no_matching_products),
                    modifier = Modifier.padding(16.dp),
                )
            }
        } else {
            items(products, key = Product::id) { product ->
                ProductCard(
                    product = product,
                    watched = product.id in state.preferences.watchedProductIds,
                    onOpen = { onOpenProduct(product) },
                    onAdd = { onAddProduct(product) },
                    onToggleWatched = { onToggleWatched(product.id) },
                )
            }
        }
    }
}
