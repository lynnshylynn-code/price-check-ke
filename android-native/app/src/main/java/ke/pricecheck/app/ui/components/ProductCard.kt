package ke.pricecheck.app.ui.components

import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.ui.tooling.preview.Preview
import ke.pricecheck.app.R
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.data.ProductCatalog
import ke.pricecheck.app.ui.PriceCheckTheme

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ProductCard(
    product: Product,
    watched: Boolean,
    onOpen: () -> Unit,
    onAdd: () -> Unit,
    onToggleWatched: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var contextMenuExpanded by remember { mutableStateOf(false) }
    val haptics = LocalHapticFeedback.current
    Box(modifier = modifier.fillMaxWidth()) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .combinedClickable(
                    onClick = onOpen,
                    onLongClick = {
                        haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                        contextMenuExpanded = true
                    },
                ),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(product.category.uppercase(), style = MaterialTheme.typography.labelSmall)
                    Text("${product.name} · ${product.size}", style = MaterialTheme.typography.titleMedium)
                    Text(product.description, style = MaterialTheme.typography.bodySmall)
                    Text(
                        stringResource(
                            if (product.isDemoData) R.string.best_illustrative_price
                            else R.string.best_snapshot_price,
                            product.lowestPrice.price,
                            product.lowestPrice.store,
                        ),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                Column {
                    IconButton(onClick = onAdd) {
                        Icon(
                            Icons.Filled.Add,
                            contentDescription = stringResource(R.string.add_product_to_basket, product.name),
                        )
                    }
                    IconButton(onClick = onToggleWatched) {
                        Icon(
                            Icons.Filled.Favorite,
                            contentDescription = if (watched) {
                                stringResource(R.string.remove_from_watchlist)
                            } else {
                                stringResource(R.string.add_to_watchlist)
                            },
                            tint = if (watched) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
        DropdownMenu(
            expanded = contextMenuExpanded,
            onDismissRequest = { contextMenuExpanded = false },
        ) {
            DropdownMenuItem(
                text = { Text(stringResource(R.string.add_to_basket)) },
                leadingIcon = { Icon(Icons.Filled.ShoppingCart, contentDescription = null) },
                onClick = {
                    contextMenuExpanded = false
                    onAdd()
                },
            )
            DropdownMenuItem(
                text = {
                    Text(
                        stringResource(
                            if (watched) R.string.remove_from_watchlist
                            else R.string.watch_this_product,
                        ),
                    )
                },
                leadingIcon = { Icon(Icons.Filled.Favorite, contentDescription = null) },
                onClick = {
                    contextMenuExpanded = false
                    onToggleWatched()
                },
            )
        }

    }
}

@Preview(showBackground = true)
@Composable
private fun ProductCardPreview() {
    PriceCheckTheme {
        ProductCard(
            product = ProductCatalog.products.first(),
            watched = false,
            onOpen = {},
            onAdd = {},
            onToggleWatched = {},
        )
    }
}
