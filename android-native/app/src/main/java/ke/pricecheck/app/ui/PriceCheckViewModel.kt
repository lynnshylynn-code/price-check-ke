package ke.pricecheck.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import ke.pricecheck.app.AppContainer
import ke.pricecheck.app.R
import ke.pricecheck.app.data.AppPreferences
import ke.pricecheck.app.data.AreaMarketData
import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.FoodInflationData
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.data.ShoppingArea
import ke.pricecheck.app.domain.answerFromDataset
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException
import org.json.JSONException

enum class PriceCheckTab {
    HOME,
    SEARCH,
    BASKET,
    TRENDS,
    PROFILE,
    WATCHLIST,
}

enum class ProductSort {
    LOWEST_PRICE,
    HIGHEST_PRICE,
    NAME,
}

data class PriceCheckUiState(
    val preferences: AppPreferences = AppPreferences(),
    val selectedTab: PriceCheckTab = PriceCheckTab.HOME,
    val searchQuery: String = "",
    val selectedCategory: String = "All",
    val productSort: ProductSort = ProductSort.LOWEST_PRICE,
    val selectedYear: Int? = null,
    val marketData: FoodInflationData? = null,
    val marketLoading: Boolean = true,
    val marketError: String? = null,
    val areaMarketData: AreaMarketData? = null,
    val areaMarketLoading: Boolean = true,
    val areaMarketError: String? = null,
    val areaMarketEmpty: Boolean = false,
    val question: String = "",
    val answer: String? = null,
    val answerIsOffline: Boolean = false,
    val answerSourceName: String? = null,
    val answerSourceUrl: String? = null,
    val answerCoverageStart: String? = null,
    val answerCoverageEnd: String? = null,
    val aiLoading: Boolean = false,
    val aiError: String? = null,
    val budgetInput: String? = null,
    val budgetError: Int? = null,
)

class PriceCheckViewModel(
    private val container: AppContainer,
) : ViewModel() {
    val products: List<Product> = container.products.products
    val categories: List<String> = container.products.categories

    private val mutableState = MutableStateFlow(PriceCheckUiState())

    val uiState: StateFlow<PriceCheckUiState> = combine(
        mutableState,
        container.preferences.preferences.catch { error ->
            if (error is IOException) emit(AppPreferences()) else throw error
        },
    ) { state, preferences ->
        state.copy(preferences = preferences)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PriceCheckUiState())

    init {
        refreshMarket()
        viewModelScope.launch {
            container.preferences.preferences
                .map { it.shoppingArea }
                .distinctUntilChanged()
                .collect(::refreshAreaMarket)
        }
    }

    fun selectTab(tab: PriceCheckTab) = mutableState.update { it.copy(selectedTab = tab) }

    fun setSearchQuery(query: String) = mutableState.update { it.copy(searchQuery = query) }

    fun setCategory(category: String) =
        mutableState.update { it.copy(selectedCategory = category) }

    fun cycleSort() = mutableState.update {
        val next = when (it.productSort) {
            ProductSort.LOWEST_PRICE -> ProductSort.HIGHEST_PRICE
            ProductSort.HIGHEST_PRICE -> ProductSort.NAME
            ProductSort.NAME -> ProductSort.LOWEST_PRICE
        }
        it.copy(productSort = next)
    }

    fun selectYear(year: Int) = mutableState.update { it.copy(selectedYear = year) }

    fun visibleProducts(state: PriceCheckUiState): List<Product> {
        val query = state.searchQuery.trim()
        val matchingProducts = products.filter { product ->
            (state.selectedCategory == "All" || product.category == state.selectedCategory) &&
                (query.isEmpty() ||
                    "${product.name} ${product.description} ${product.category}"
                        .contains(query, ignoreCase = true))
        }
        return when (state.productSort) {
            ProductSort.LOWEST_PRICE -> matchingProducts.sortedBy { it.lowestPrice.price }
            ProductSort.HIGHEST_PRICE -> matchingProducts.sortedByDescending { it.lowestPrice.price }
            ProductSort.NAME -> matchingProducts.sortedBy { it.name }
        }
    }

    fun changeBasket(productId: String, amount: Int) {
        viewModelScope.launch { container.preferences.changeBasket(productId, amount) }
    }

    fun toggleWatched(productId: String) {
        val current = uiState.value.preferences.watchedProductIds
        viewModelScope.launch {
            container.preferences.setWatched(productId, productId !in current)
        }
    }

    fun setBasketStrategy(strategy: BasketStrategy) {
        viewModelScope.launch { container.preferences.setBasketStrategy(strategy) }
    }

    fun basketTotal(
        state: PriceCheckUiState = uiState.value,
        strategy: BasketStrategy = state.preferences.basketStrategy,
    ): Int {
        val lines = state.preferences.basket.mapNotNull { (id, quantity) ->
            container.products.findById(id)?.let { ke.pricecheck.app.domain.BasketLine(it, quantity) }
        }
        return ke.pricecheck.app.domain.BasketPricing.total(lines, strategy)
    }

    fun bestSingleStoreTotal(state: PriceCheckUiState = uiState.value) =
        ke.pricecheck.app.domain.BasketPricing.eligibleStoreTotals(
            state.preferences.basket.mapNotNull { (id, quantity) ->
                container.products.findById(id)?.let { ke.pricecheck.app.domain.BasketLine(it, quantity) }
            },
        ).firstOrNull()

    fun setBudgetInput(value: String) = mutableState.update {
        it.copy(budgetInput = value.filter(Char::isDigit), budgetError = null)
    }

    fun setShoppingArea(area: ShoppingArea) {
        viewModelScope.launch { container.preferences.setShoppingArea(area) }
    }

    private fun refreshAreaMarket(area: ShoppingArea) {
        mutableState.update {
            it.copy(areaMarketData = null, areaMarketLoading = true, areaMarketError = null, areaMarketEmpty = false)
        }
        viewModelScope.launch {
            try {
                val data = container.market.loadAreaPrices(area)
                mutableState.update {
                    it.copy(areaMarketData = data, areaMarketLoading = false, areaMarketEmpty = data.prices.isEmpty())
                }
            } catch (error: Exception) {
                mutableState.update {
                    it.copy(
                        areaMarketLoading = false,
                        areaMarketError = error.message ?: container.strings(R.string.market_load_failed),
                    )
                }
            }
        }
    }

    fun saveBudget() {
        val amount = (mutableState.value.budgetInput
            ?: mutableState.value.preferences.weeklyBudget.toString()).toIntOrNull()
        if (amount == null || amount <= 0) {
            mutableState.update { it.copy(budgetError = R.string.budget_validation_error) }
            return
        }
        viewModelScope.launch {
            container.preferences.setBudget(amount)
            mutableState.update { it.copy(budgetError = null, budgetInput = amount.toString()) }
        }
    }

    fun refreshMarket() {
        refreshAreaMarket(uiState.value.preferences.shoppingArea)
        mutableState.update { it.copy(marketLoading = true, marketError = null) }
        viewModelScope.launch {
            try {
                val data = container.market.loadFoodInflation()
                mutableState.update {
                    it.copy(
                        marketData = data,
                        marketLoading = false,
                        marketError = null,
                        selectedYear = it.selectedYear ?: data.series.year,
                    )
                }
            } catch (error: IOException) {
                mutableState.update {
                    it.copy(
                        marketLoading = false,
                        marketError = error.message ?: container.strings(R.string.market_load_failed),
                    )
                }
            } catch (error: JSONException) {
                mutableState.update {
                    it.copy(
                        marketLoading = false,
                        marketError = error.message ?: container.strings(R.string.dataset_load_failed),
                    )
                }
            }
        }
    }

    fun setQuestion(question: String) = mutableState.update {
        it.copy(question = question.take(500), aiError = null)
    }

    fun askQuestion() {
        val state = mutableState.value
        val data = state.marketData ?: return
        val question = state.question.trim()
        if (question.length < 3 || state.aiLoading) return

        val fallback = answerFromDataset(question, data)
        mutableState.update {
            it.copy(
                answer = fallback,
                answerIsOffline = true,
                aiLoading = true,
                aiError = null,
            )
        }
        viewModelScope.launch {
            try {
                val answer = container.market.askQuestion(question)
                mutableState.update {
                    it.copy(
                        answer = answer.answer,
                        answerIsOffline = false,
                        aiLoading = false,
                        answerSourceName = answer.sourceName,
                        answerSourceUrl = answer.sourceUrl,
                        answerCoverageStart = answer.coverageStart,
                        answerCoverageEnd = answer.coverageEnd,
                    )
                }
            } catch (error: IOException) {
                mutableState.update {
                    it.copy(
                        answer = fallback,
                        answerIsOffline = true,
                        aiLoading = false,
                        answerSourceName = data.series.sourceName,
                        answerSourceUrl = data.series.sourceUrl,
                        answerCoverageStart = data.series.coverageStart,
                        answerCoverageEnd = data.series.coverageEnd,
                        aiError = error.message ?: container.strings(R.string.live_ai_error),
                    )
                }
            } catch (error: JSONException) {
                mutableState.update {
                    it.copy(
                        answer = fallback,
                        answerIsOffline = true,
                        aiLoading = false,
                        aiError = error.message ?: container.strings(R.string.live_ai_error),
                    )
                }
            }
        }
    }

    fun simulateQuestion() {
        val state = mutableState.value
        val data = state.marketData ?: return
        val question = state.question.trim()
        if (question.length < 3 || state.aiLoading) return
        mutableState.update {
            it.copy(
                answer = answerFromDataset(question, data),
                answerIsOffline = true,
                answerSourceName = data.series.sourceName,
                answerSourceUrl = data.series.sourceUrl,
                answerCoverageStart = data.series.coverageStart,
                answerCoverageEnd = data.series.coverageEnd,
                aiError = null,
            )
        }
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            if (modelClass.isAssignableFrom(PriceCheckViewModel::class.java)) {
                return PriceCheckViewModel(container) as T
            }
            error("Unsupported ViewModel: ${modelClass.name}")
        }
    }
}
