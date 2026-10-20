package ke.pricecheck.app

import android.app.Application
import android.content.res.Resources
import ke.pricecheck.app.data.MarketRepository
import ke.pricecheck.app.data.PreferenceRepository
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
            resources = resources,
        )
    }
}

data class AppContainer(
    val preferences: PreferenceRepository,
    val market: MarketRepository,
    val products: ProductRepository,
    val resources: Resources,
)
