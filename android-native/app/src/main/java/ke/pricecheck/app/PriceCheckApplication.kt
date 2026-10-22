package ke.pricecheck.app

import android.app.Application
import ke.pricecheck.app.data.MarketRepository
import ke.pricecheck.app.data.MarketDataSource
import ke.pricecheck.app.data.PreferenceRepository
import ke.pricecheck.app.data.PreferencesStore
import ke.pricecheck.app.data.ListingsRepository
import ke.pricecheck.app.data.ProductRepository
import ke.pricecheck.app.data.HttpOrderRepository
import ke.pricecheck.app.data.OrderRepository

class PriceCheckApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(
            preferences = PreferenceRepository(this),
            market = MarketRepository(BuildConfig.API_BASE_URL),
            products = ListingsRepository(this, BuildConfig.API_BASE_URL),
            orders = HttpOrderRepository(BuildConfig.API_BASE_URL),
            strings = resources::getString,
        )
    }
}

data class AppContainer(
    val preferences: PreferencesStore,
    val market: MarketDataSource,
    val products: ProductRepository,
    val orders: OrderRepository = HttpOrderRepository("http://127.0.0.1:8000"),
    val strings: (Int) -> String,
)
