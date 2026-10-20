package ke.pricecheck.app

import android.app.Application
import ke.pricecheck.app.data.MarketRepository
import ke.pricecheck.app.data.MarketDataSource
import ke.pricecheck.app.data.PreferenceRepository
import ke.pricecheck.app.data.PreferencesStore
import ke.pricecheck.app.data.InMemoryProductRepository
import ke.pricecheck.app.data.ProductRepository

class PriceCheckApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(
            preferences = PreferenceRepository(this),
            market = MarketRepository(BuildConfig.API_BASE_URL),
            products = InMemoryProductRepository(),
            strings = resources::getString,
        )
    }
}

data class AppContainer(
    val preferences: PreferencesStore,
    val market: MarketDataSource,
    val products: ProductRepository,
    val strings: (Int) -> String,
)
