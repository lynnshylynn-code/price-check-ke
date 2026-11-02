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
import ke.pricecheck.app.data.MarketArea
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.data.defaultMarketCounty
import ke.pricecheck.app.domain.answerFromDataset
import ke.pricecheck.app.domain.BasketLine
import ke.pricecheck.app.domain.BasketPricing
import ke.pricecheck.app.domain.StoreAvailability
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.Job
import java.io.IOException
import org.json.JSONException
import org.json.JSONArray
import org.json.JSONObject

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

data class AssistantChatMessage(
    val role: String,
    val text: String,
    val intent: String? = null,
    val sourceName: String? = null,
    val coverageStart: String? = null,
    val coverageEnd: String? = null,
    val confidencePercent: Int? = null,
)

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
    val marketAreas: List<MarketArea> = emptyList(),
    val marketDirectoryLoading: Boolean = true,
    val marketDirectoryError: String? = null,
    val question: String = "",
    val answer: String? = null,
    val answerIsOffline: Boolean = false,
    val answerSourceName: String? = null,
    val answerSourceUrl: String? = null,
    val answerCoverageStart: String? = null,
    val answerCoverageEnd: String? = null,
    val answerIntent: String? = null,
    val answerIntentConfidence: Double? = null,
    val answerSources: List<ke.pricecheck.app.data.MarketAnswerSource> = emptyList(),
    val aiLoading: Boolean = false,
    val aiError: String? = null,
    val budgetInput: String? = null,
    val budgetError: Int? = null,
    val productsAreDemo: Boolean = true,
    val productDataLabel: String = "",
    val productsLoading: Boolean = true,
    val productsError: String? = null,
    val assistantMessages: List<AssistantChatMessage> = emptyList(),
    val assistantContextJson: String? = null,
    val assistantSuggestions: List<String> = emptyList(),
)

class PriceCheckViewModel(
    private val container: AppContainer,
) : ViewModel() {
    val products: List<Product> get() = container.products.products
    val categories: List<String> get() = container.products.categories

    private val mutableState = MutableStateFlow(
        PriceCheckUiState(
            productsAreDemo = container.products.isDemoData,
            productDataLabel = container.products.dataLabel,
        ),
    )
    private var areaPreferenceJob: Job? = null

    val uiState: StateFlow<PriceCheckUiState> = combine(
        mutableState,
        container.preferences.preferences.catch { error ->
            if (error is IOException) emit(AppPreferences()) else throw error
        },
    ) { state, preferences ->
        state.copy(preferences = preferences)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), PriceCheckUiState())

    init {
        viewModelScope.launch { restoreAssistantConversation() }
        refreshListings()
        refreshFoodInflation()
        refreshMarketAreas()
    }

    fun refreshListings() {
        viewModelScope.launch {
            val loaded = container.products.refresh()
            mutableState.update {
                it.copy(
                    productsAreDemo = container.products.isDemoData,
                    productDataLabel = container.products.dataLabel,
                    productsLoading = false,
                    productsError = if (loaded || !container.products.isDemoData) null
                    else container.strings(R.string.listing_snapshot_offline),
                )
            }
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

    fun setShoppingArea(county: String) {
        val canonicalCounty = mutableState.value.marketAreas
            .firstOrNull { it.county.equals(county, ignoreCase = true) }
            ?.county ?: return
        viewModelScope.launch { container.preferences.setShoppingArea(canonicalCounty) }
    }

    private fun refreshAreaMarket(county: String) {
        mutableState.update {
            it.copy(areaMarketData = null, areaMarketLoading = true, areaMarketError = null, areaMarketEmpty = false)
        }
        viewModelScope.launch {
            try {
                val data = container.market.loadAreaPrices(county)
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

    fun storeAvailability(state: PriceCheckUiState = uiState.value): List<StoreAvailability> =
        BasketPricing.storeAvailability(
            state.preferences.basket.mapNotNull { (id, quantity) ->
                container.products.findById(id)?.let { BasketLine(it, quantity) }
            },
        )

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
        refreshFoodInflation()
        refreshMarketAreas()
    }

    private fun refreshMarketAreas() {
        mutableState.update { it.copy(marketDirectoryLoading = true, marketDirectoryError = null) }
        viewModelScope.launch {
            try {
                val areas = container.market.loadMarketAreas()
                val storedCounty = container.preferences.preferences.first().shoppingArea
                val selectedCounty = defaultMarketCounty(areas, storedCounty)
                mutableState.update {
                    it.copy(marketAreas = areas, marketDirectoryLoading = false, marketDirectoryError = null)
                }
                if (selectedCounty == null) {
                    mutableState.update {
                        it.copy(marketDirectoryError = container.strings(R.string.market_areas_unavailable))
                    }
                    return@launch
                }
                if (selectedCounty != storedCounty) {
                    container.preferences.setShoppingArea(selectedCounty)
                }
                areaPreferenceJob?.cancel()
                areaPreferenceJob = launch {
                    container.preferences.preferences
                        .map { it.shoppingArea }
                        .distinctUntilChanged()
                        .collect { savedCounty ->
                            val county = defaultMarketCounty(areas, savedCounty) ?: return@collect
                            if (county != savedCounty) {
                                container.preferences.setShoppingArea(county)
                            } else {
                                refreshAreaMarket(county)
                            }
                        }
                }
            } catch (error: Exception) {
                mutableState.update {
                    it.copy(
                        marketDirectoryLoading = false,
                        marketDirectoryError = error.message ?: container.strings(R.string.market_areas_unavailable),
                    )
                }
            }
        }
    }

    private fun refreshFoodInflation() {
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

    fun useAssistantSuggestion(suggestion: String) = setQuestion(suggestion)

    fun newAssistantChat() = clearAssistantConversation()

    fun clearAssistantConversation() {
        mutableState.update {
            it.copy(
                assistantMessages = emptyList(), assistantContextJson = null,
                assistantSuggestions = emptyList(), answer = null, question = "",
                answerIntent = null, answerIntentConfidence = null, aiError = null,
            )
        }
        viewModelScope.launch { container.preferences.saveAssistantConversation("") }
    }

    private suspend fun restoreAssistantConversation() {
        val saved = container.preferences.preferences.first().assistantConversation
        if (saved.isBlank()) return
        runCatching {
            val json = JSONObject(saved)
            val array = json.optJSONArray("messages") ?: JSONArray()
            val messages = List(array.length()) { index ->
                val row = array.getJSONObject(index)
                AssistantChatMessage(
                    role = row.optString("role"), text = row.optString("text"),
                    intent = row.optString("intent").takeUnless { it.isBlank() || it == "null" },
                    sourceName = row.optString("source_name").takeUnless { it.isBlank() || it == "null" },
                    coverageStart = row.optString("coverage_start").takeUnless { it.isBlank() || it == "null" },
                    coverageEnd = row.optString("coverage_end").takeUnless { it.isBlank() || it == "null" },
                    confidencePercent = row.optInt("confidence_percent").takeIf { row.has("confidence_percent") },
                )
            }.takeLast(50)
            val context = json.optJSONObject("context")?.toString()
            mutableState.update { it.copy(assistantMessages = messages, assistantContextJson = context) }
        }
    }

    private fun saveAssistantConversation(state: PriceCheckUiState) {
        val messages = JSONArray()
        state.assistantMessages.takeLast(50).forEach { message ->
            messages.put(JSONObject().put("role", message.role).put("text", message.text)
                .put("intent", message.intent).put("source_name", message.sourceName)
                .put("coverage_start", message.coverageStart).put("coverage_end", message.coverageEnd)
                .put("confidence_percent", message.confidencePercent))
        }
        val payload = JSONObject().put("messages", messages)
        state.assistantContextJson?.let { runCatching { JSONObject(it) }.getOrNull() }
            ?.let { payload.put("context", it) }
        viewModelScope.launch {
            container.preferences.saveAssistantConversation(payload.toString())
        }
    }

    fun askQuestion() {
        val state = mutableState.value
        val data = state.marketData ?: return
        val question = state.question.trim()
        if (question.length < 3 || state.aiLoading) return

        val fallback = answerFromDataset(question, data)
        val userMessage = AssistantChatMessage("user", question)
        mutableState.update {
            it.copy(
                answer = fallback,
                answerIsOffline = true,
                aiLoading = true,
                aiError = null,
                assistantMessages = (it.assistantMessages + userMessage).takeLast(50),
            )
        }
        saveAssistantConversation(mutableState.value)
        viewModelScope.launch {
            try {
                val answer = container.market.askQuestion(question, state.assistantContextJson)
                mutableState.update {
                    it.copy(
                        answer = answer.answer,
                        answerIsOffline = false,
                        aiLoading = false,
                        answerSourceName = answer.sourceName,
                        answerSourceUrl = answer.sourceUrl,
                        answerCoverageStart = answer.coverageStart,
                        answerCoverageEnd = answer.coverageEnd,
                        answerIntent = answer.intent,
                        answerIntentConfidence = answer.intentConfidence,
                        answerSources = answer.sources,
                        assistantContextJson = answer.contextJson,
                        assistantSuggestions = answer.suggestions,
                        assistantMessages = (it.assistantMessages + AssistantChatMessage(
                            "assistant", answer.answer, answer.intent, answer.sourceName,
                            answer.coverageStart, answer.coverageEnd,
                            (answer.intentConfidence * 100).toInt(),
                        )).takeLast(50),
                    )
                }
                saveAssistantConversation(mutableState.value)
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
                        assistantMessages = (it.assistantMessages + AssistantChatMessage(
                            "assistant", fallback,
                        )).takeLast(50),
                    )
                }
                saveAssistantConversation(mutableState.value)
            } catch (error: JSONException) {
                mutableState.update {
                    it.copy(
                        answer = fallback,
                        answerIsOffline = true,
                        aiLoading = false,
                        aiError = error.message ?: container.strings(R.string.live_ai_error),
                        assistantMessages = (it.assistantMessages + AssistantChatMessage(
                            "assistant", fallback,
                        )).takeLast(50),
                    )
                }
                saveAssistantConversation(mutableState.value)
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
