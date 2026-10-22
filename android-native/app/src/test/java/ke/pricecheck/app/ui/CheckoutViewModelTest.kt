package ke.pricecheck.app.ui

import ke.pricecheck.app.AppContainer
import ke.pricecheck.app.R
import ke.pricecheck.app.data.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException

@OptIn(ExperimentalCoroutinesApi::class)
class CheckoutViewModelTest {
    private val item = Product(
        "flour",
        "Ajab Flour",
        "2kg",
        "",
        "pantry",
        listOf(StorePrice("Carrefour", 178, "", "listing-1", "https://example.test/item")),
        isDemoData = false,
    )

    @After fun tearDown() = Dispatchers.resetMain()

    @Test fun validatesAddressAndNormalizesKenyanPhones() {
        assertNotNull(CheckoutValidation.addressError("short"))
        assertNull(CheckoutValidation.addressError("123 Example Road, Nairobi"))
        assertEquals("254712345678", CheckoutValidation.normalizedPhone("0712 345 678"))
        assertEquals("254112345678", CheckoutValidation.normalizedPhone("+254 112 345 678"))
        assertNull(CheckoutValidation.normalizedPhone("not a phone"))
    }

    @Test fun emptyCheckoutFormShowsBothInlineErrorsAndDoesNotCallRepository() = runTest {
        val orders = FakeOrders()
        val viewModel = newViewModel(orders)
        viewModel.prepareOrder("Carrefour", listOf(item), emptyMap())
        viewModel.submit("", "")
        assertEquals(R.string.checkout_address_error, viewModel.uiState.value.addressError)
        assertEquals(R.string.checkout_phone_error, viewModel.uiState.value.phoneError)
        assertEquals(0, orders.createCalls)
    }

    @Test fun validCheckoutCreatesAndPaysThenSavesOrderId() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val preferences = FakePreferences()
        val orders = FakeOrders()
        val viewModel = newViewModel(orders, preferences)
        viewModel.prepareOrder("Carrefour", listOf(item), mapOf(item.id to 2))
        viewModel.submit("123 Example Road Nairobi", "0712345678")
        advanceUntilIdle()
        assertEquals(1, orders.createCalls)
        assertEquals(1, orders.payCalls)
        assertEquals("order-1", viewModel.uiState.value.orderId)
        assertEquals("paid_sandbox", viewModel.uiState.value.orderStatus)
        assertEquals("order-1", preferences.value.value.lastOrderId)
        assertEquals("254712345678", orders.lastPhone)
    }

    private fun newViewModel(
        orders: FakeOrders,
        preferences: FakePreferences = FakePreferences(),
    ) = CheckoutViewModel(
        AppContainer(
            preferences = preferences,
            market = FakeMarket(),
            products = object : ProductRepository {
                override val products = listOf(item)
                override val categories = listOf("All", "pantry")
                override fun findById(productId: String) = products.firstOrNull { it.id == productId }
            },
            orders = orders,
            strings = { id -> if (id == R.string.checkout_order_error) "Could not create order: %1\$s" else "error" },
        ),
    )

    private class FakePreferences : PreferencesStore {
        val value = MutableStateFlow(AppPreferences())
        override val preferences = value
        override suspend fun changeBasket(productId: String, amount: Int) = Unit
        override suspend fun setWatched(productId: String, watched: Boolean) = Unit
        override suspend fun setBudget(amount: Int) = Unit
        override suspend fun setBasketStrategy(strategy: BasketStrategy) = Unit
        override suspend fun setShoppingArea(county: String) = Unit
        override suspend fun setLastOrderId(orderId: String?) {
            value.value = value.value.copy(lastOrderId = orderId)
        }
    }

    private class FakeOrders : OrderRepository {
        var createCalls = 0
        var payCalls = 0
        var lastPhone: String? = null
        override suspend fun create(
            store: String,
            items: List<OrderLineRequest>,
            address: String,
            phone: String,
            latitude: Double?,
            longitude: Double?,
        ): OrderRecord {
            createCalls++
            lastPhone = phone
            assertEquals(listOf(OrderLineRequest("listing-1", 2)), items)
            return OrderRecord("order-1", "created", store, 356.0, null)
        }

        override suspend fun pay(orderId: String): OrderRecord {
            payCalls++
            return OrderRecord(orderId, "paid_sandbox", "Carrefour", 356.0, null)
        }

        override suspend fun status(orderId: String) = OrderRecord(orderId, "payment_pending", "Carrefour", 356.0, null)
        override suspend fun cancel(orderId: String) = OrderRecord(orderId, "cancelled", "Carrefour", 356.0, null)
        override suspend fun delete(orderId: String) = Unit
    }

    private class FakeMarket : MarketDataSource {
        override suspend fun loadMarketAreas(): List<MarketArea> = throw IOException("unused")
        override suspend fun loadFoodInflation(): FoodInflationData = throw IOException("unused")
        override suspend fun loadAreaPrices(county: String): AreaMarketData = throw IOException("unused")
        override suspend fun askQuestion(question: String): MarketQuestionAnswer = throw IOException("unused")
    }
}
