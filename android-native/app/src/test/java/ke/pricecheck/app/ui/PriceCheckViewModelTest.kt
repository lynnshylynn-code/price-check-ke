package ke.pricecheck.app.ui

import androidx.lifecycle.ViewModel
import ke.pricecheck.app.AppContainer
import ke.pricecheck.app.data.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestCoroutineScheduler
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class PriceCheckViewModelTest {
    @After fun resetMainDispatcher() = Dispatchers.resetMain()

    @Test fun changingAreaLoadsPricesForTheSelectedCounty() = runTest {
        val store = FakePreferences()
        val market = FakeMarket()
        val viewModel = viewModel(store, market, testScheduler)
        backgroundScope.launch { viewModel.uiState.collect {} }
        advanceUntilIdle()

        viewModel.setShoppingArea("Mombasa")
        advanceUntilIdle()

        assertEquals("Mombasa", viewModel.uiState.value.areaMarketData?.area)
    }

    @Test fun marketStateCoversLoadingErrorAndEmptyResponses() = runTest {
        val failedMarket = FakeMarket().apply { areaError = IOException("network down") }
        val failed = viewModel(FakePreferences(), failedMarket, testScheduler)
        backgroundScope.launch { failed.uiState.collect {} }
        assertTrue(failed.uiState.value.areaMarketLoading)
        advanceUntilIdle()
        assertEquals("network down", failed.uiState.value.areaMarketError)

        val emptyMarket = FakeMarket().apply { emptyArea = true }
        val empty = viewModel(FakePreferences(), emptyMarket, testScheduler)
        backgroundScope.launch { empty.uiState.collect {} }
        advanceUntilIdle()
        assertNotNull(empty.uiState.value.areaMarketData)
        assertTrue(empty.uiState.value.areaMarketData!!.prices.isEmpty())
        assertNull(empty.uiState.value.areaMarketError)
    }

    @Test fun basketAndWatchlistChangesPersistThroughPreferencesStore() = runTest {
        val store = FakePreferences()
        val viewModel = viewModel(store, FakeMarket(), testScheduler)
        backgroundScope.launch { viewModel.uiState.collect {} }
        advanceUntilIdle()

        viewModel.changeBasket("beans", 1)
        viewModel.toggleWatched("beans")
        advanceUntilIdle()
        assertEquals(1, viewModel.uiState.value.preferences.basket["beans"])
        assertTrue("beans" in viewModel.uiState.value.preferences.watchedProductIds)

        viewModel.changeBasket("beans", -1)
        viewModel.toggleWatched("beans")
        advanceUntilIdle()
        assertFalse("beans" in viewModel.uiState.value.preferences.basket)
        assertFalse("beans" in viewModel.uiState.value.preferences.watchedProductIds)
    }

    @Test fun liveAiAnswerRetainsItsSourceAndCoverage() = runTest {
        val viewModel = viewModel(FakePreferences(), FakeMarket(), testScheduler)
        backgroundScope.launch { viewModel.uiState.collect {} }
        advanceUntilIdle()
        viewModel.setQuestion("Latest market change?")
        viewModel.askQuestion()
        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertEquals("The dataset answer", state.answer)
        assertEquals("World Bank RTFP", state.answerSourceName)
        assertEquals("https://example.org/data", state.answerSourceUrl)
        assertEquals("2022-01-01", state.answerCoverageStart)
        assertEquals("2022-08-01", state.answerCoverageEnd)
    }

    private fun viewModel(
        preferences: FakePreferences,
        market: FakeMarket,
        scheduler: TestCoroutineScheduler,
    ): PriceCheckViewModel {
        Dispatchers.setMain(StandardTestDispatcher(scheduler))
        return PriceCheckViewModel(
            AppContainer(
                preferences = preferences,
                market = market,
                products = TestProducts,
                strings = { "error" },
            ),
        )
    }

    private class FakePreferences : PreferencesStore {
        private val state = MutableStateFlow(AppPreferences())
        override val preferences = state
        override suspend fun changeBasket(productId: String, amount: Int) = state.update { current ->
            val items = current.basket.toMutableMap()
            val next = (items[productId] ?: 0) + amount
            if (next > 0) items[productId] = next else items.remove(productId)
            current.copy(basket = items)
        }
        override suspend fun setWatched(productId: String, watched: Boolean) = state.update {
            it.copy(watchedProductIds = it.watchedProductIds.toMutableSet().apply {
                if (watched) add(productId) else remove(productId)
            })
        }
        override suspend fun setBudget(amount: Int) { state.update { it.copy(weeklyBudget = amount) } }
        override suspend fun setBasketStrategy(strategy: BasketStrategy) { state.update { it.copy(basketStrategy = strategy) } }
        override suspend fun setShoppingArea(county: String) { state.update { it.copy(shoppingArea = county) } }
    }

    private class FakeMarket : MarketDataSource {
        var areaError: Exception? = null
        var emptyArea = false
        override suspend fun loadMarketAreas() = listOf(
            MarketArea("Kitui", listOf("Kitui"), setOf("beans", "maize")),
            MarketArea("Mombasa", listOf("Mombasa"), setOf("beans")),
        )
        override suspend fun loadAreaPrices(county: String): AreaMarketData {
            areaError?.let { throw it }
            return AreaMarketData(county, "World Bank RTFP", "https://example.org/data", "2022-01-01", "2022-08-01", "Aug 2022", if (emptyArea) emptyList() else listOf(MarketPricePoint(county, county, "2022-08-01", "beans", 130.0, "KES", "1 kg")))
        }
        override suspend fun loadFoodInflation() = sampleInflation
        override suspend fun askQuestion(question: String) = MarketQuestionAnswer("The dataset answer", "World Bank RTFP", "https://example.org/data", "2022-01-01", "2022-08-01")
    }

    private object TestProducts : ProductRepository {
        override val products = listOf(Product("beans", "Beans", "1 kg", "Dry beans", "Pantry", listOf(StorePrice("Naivas", 100, "In stock"))))
        override val categories = listOf("All", "Pantry")
        override fun findById(productId: String) = products.find { it.id == productId }
    }

    private companion object {
        val sampleInflation = FoodInflationData(
            MarketSeries("Kenya", "National market average", "World Bank RTFP", "https://example.org/data", "Jan 2022", "Aug 2022", 2022),
            MarketSummary(2, 1.5, "Jan 2022", 1.0, "Aug 2022", 2.0, "Jul 2022", 1.0, "Aug 2022", 2.0, "",),
            listOf(MarketObservation(2022, "Jul", 7, 1.0), MarketObservation(2022, "Aug", 8, 2.0)),
        )
    }
}
