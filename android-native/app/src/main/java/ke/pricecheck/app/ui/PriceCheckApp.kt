package ke.pricecheck.app.ui

import android.content.Intent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Add
import androidx.activity.compose.BackHandler
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ke.pricecheck.app.AboutActivity
import ke.pricecheck.app.R
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.ui.components.OptionsMenu
import ke.pricecheck.app.ui.screens.BasketScreen
import ke.pricecheck.app.ui.screens.HomeScreen
import ke.pricecheck.app.ui.screens.ProfileScreen
import ke.pricecheck.app.ui.screens.SearchScreen
import ke.pricecheck.app.ui.screens.TrendsScreen

@Composable
fun PriceCheckApp(
    viewModel: PriceCheckViewModel,
    onOpenWatchlist: () -> Unit,
    onOrderFromStore: (String, Map<String, Int>) -> Unit,
    onStoreHandoff: (String, Map<String, Int>) -> Unit,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var selectedProduct by remember { mutableStateOf<Product?>(null) }
    val basketShareLines = mutableListOf<String>()
    for ((id, quantity) in state.preferences.basket) {
        val product = viewModel.products.find { it.id == id }
        if (product != null) {
            basketShareLines.add(
                stringResource(R.string.basket_share_line, product.name, product.size, quantity),
            )
        }
    }
    val basketShareTitle = stringResource(R.string.basket_share_title)
    val basketShareTotal = stringResource(R.string.basket_share_total, viewModel.basketTotal(state))
    val basketShareText = buildString {
        append(basketShareTitle)
        if (basketShareLines.isNotEmpty()) {
            append('\n')
            append(basketShareLines.joinToString("\n"))
        }
        append('\n')
        append(basketShareTotal)
    }
    val shareBasketLabel = stringResource(R.string.share_basket)

    PriceCheckTheme {
        BackHandler(enabled = state.selectedTab != PriceCheckTab.HOME) {
            viewModel.selectTab(PriceCheckTab.HOME)
        }
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            topBar = {
                PriceCheckTopBar(
                    onRefresh = viewModel::refreshMarket,
                    onAbout = { context.startActivity(Intent(context, AboutActivity::class.java)) },
                )
            },
            bottomBar = {
                AppNavigationBar(
                    selected = state.selectedTab,
                    basketCount = state.preferences.basket.values.sum(),
                    onSelect = { tab ->
                        if (tab == PriceCheckTab.WATCHLIST) onOpenWatchlist()
                        else viewModel.selectTab(tab)
                    },
                )
            },
        ) { contentPadding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(contentPadding),
            ) {
                val openProduct: (Product) -> Unit = { selectedProduct = it }
                when (state.selectedTab) {
                    PriceCheckTab.HOME -> HomeScreen(
                        state = state,
                        products = viewModel.products.take(3),
                        categories = viewModel.categories,
                        onSearch = {
                            viewModel.setSearchQuery("")
                            viewModel.selectTab(PriceCheckTab.SEARCH)
                        },
                        onCategory = {
                            viewModel.setCategory(it)
                            viewModel.selectTab(PriceCheckTab.SEARCH)
                        },
                        onOpenProduct = openProduct,
                        onAddProduct = { viewModel.changeBasket(it.id, 1) },
                        onTrends = { viewModel.selectTab(PriceCheckTab.TRENDS) },
                        onRefresh = viewModel::refreshMarket,
                        onToggleWatched = viewModel::toggleWatched,
                        onArea = viewModel::setShoppingArea,
                    )
                    PriceCheckTab.SEARCH -> SearchScreen(
                        state = state,
                        products = viewModel.visibleProducts(state),
                        categories = viewModel.categories,
                        onSearch = viewModel::setSearchQuery,
                        onCategory = viewModel::setCategory,
                        onSort = viewModel::cycleSort,
                        onOpenProduct = openProduct,
                        onAddProduct = { viewModel.changeBasket(it.id, 1) },
                        onToggleWatched = viewModel::toggleWatched,
                    )
                    PriceCheckTab.BASKET -> BasketScreen(
                        state = state,
                        products = viewModel.products,
                        onChangeQuantity = viewModel::changeBasket,
                        onChangeStrategy = viewModel::setBasketStrategy,
                        onBrowse = { viewModel.selectTab(PriceCheckTab.SEARCH) },
                        onStoreHandoff = { store -> onStoreHandoff(store, state.preferences.basket) },
                        onShare = {
                            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, basketShareText)
                            }
                            context.startActivity(
                                Intent.createChooser(shareIntent, shareBasketLabel),
                            )
                        },
                        total = viewModel.basketTotal(state),
                        lowestPerItemTotal = viewModel.basketTotal(state, ke.pricecheck.app.data.BasketStrategy.LOWEST_PER_ITEM),
                        singleStoreTotal = viewModel.bestSingleStoreTotal(state)?.total,
                        bestSingleStore = viewModel.bestSingleStoreTotal(state)?.store,
                        storeOptions = viewModel.storeAvailability(state),
                        onOrderFromStore = { store ->
                            onOrderFromStore(store, state.preferences.basket)
                        },
                    )
                    PriceCheckTab.TRENDS -> TrendsScreen(
                        state = state,
                        products = viewModel.products,
                        onQuestion = viewModel::setQuestion,
                        onAsk = viewModel::askQuestion,
                        onSimulate = viewModel::simulateQuestion,
                        onSelectYear = viewModel::selectYear,
                        onRefresh = viewModel::refreshMarket,
                        onOpenProduct = openProduct,
                        onAddProduct = { viewModel.changeBasket(it.id, 1) },
                        onToggleWatched = viewModel::toggleWatched,
                    )
                    PriceCheckTab.PROFILE -> ProfileScreen(
                        state = state,
                        onBudgetInput = viewModel::setBudgetInput,
                        onSaveBudget = viewModel::saveBudget,
                    )
                    PriceCheckTab.WATCHLIST -> Unit
                }
            }
        }

        selectedProduct?.let { product ->
            ProductComparisonDialog(
                product = product,
                onDismiss = { selectedProduct = null },
                onAdd = {
                    viewModel.changeBasket(product.id, 1)
                    selectedProduct = null
                },
            )
        }

    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PriceCheckTopBar(
    onRefresh: () -> Unit,
    onAbout: () -> Unit,
) {
    TopAppBar(
        title = { Text(stringResource(R.string.app_name)) },
        actions = {
            OptionsMenu(onRefresh = onRefresh, onAbout = onAbout)
        },
    )
}

@Composable
private fun ProductComparisonDialog(
    product: Product,
    onDismiss: () -> Unit,
    onAdd: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.product_title_size, product.name, product.size)) },
        text = {
            Column {
                Text(
                        stringResource(
                            if (product.isDemoData) R.string.product_demo_description
                            else R.string.product_snapshot_description,
                        ),
                )
                if (product.isDemoData && product.description.isNotBlank()) {
                    Text(product.description)
                }
                product.prices.sortedBy { it.price }.forEach { price ->
                    Text(
                        stringResource(
                            R.string.product_store_price,
                            price.store,
                            price.price,
                            price.stock.ifBlank { stringResource(R.string.listing_stock_unverified) },
                        ),
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onAdd) { Text(stringResource(R.string.add_to_basket)) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.close)) }
        },
    )
}

@Composable
private fun AppNavigationBar(
    selected: PriceCheckTab,
    basketCount: Int,
    onSelect: (PriceCheckTab) -> Unit,
) {
    NavigationBar {
        val destinations: List<Pair<PriceCheckTab, ImageVector>> = listOf(
            PriceCheckTab.HOME to Icons.Filled.Home,
            PriceCheckTab.SEARCH to Icons.Filled.Search,
            PriceCheckTab.BASKET to Icons.Filled.ShoppingCart,
            PriceCheckTab.WATCHLIST to Icons.Filled.Favorite,
            PriceCheckTab.TRENDS to Icons.Filled.Add,
            PriceCheckTab.PROFILE to Icons.Filled.Person,
        )
        destinations.forEach { (tab, icon) ->
            NavigationBarItem(
                selected = selected == tab,
                onClick = { onSelect(tab) },
                icon = {
                    if (tab == PriceCheckTab.BASKET && basketCount > 0) {
                        BadgedBox(
                            badge = {
                                Badge {
                                    Text(if (basketCount > 99) "99+" else basketCount.toString())
                                }
                            },
                        ) {
                            Icon(icon, contentDescription = null)
                        }
                    } else {
                        Icon(icon, contentDescription = null)
                    }
                },
                label = {
                    Text(
                        when (tab) {
                            PriceCheckTab.HOME -> stringResource(R.string.tab_home)
                            PriceCheckTab.SEARCH -> stringResource(R.string.tab_search)
                            PriceCheckTab.BASKET -> stringResource(R.string.tab_basket)
                            PriceCheckTab.WATCHLIST -> stringResource(R.string.tab_watchlist)
                            PriceCheckTab.TRENDS -> stringResource(R.string.tab_trends)
                            PriceCheckTab.PROFILE -> stringResource(R.string.tab_profile)
                        },
                    )
                },
            )
        }
    }
}
