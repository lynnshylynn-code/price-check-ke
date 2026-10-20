package ke.pricecheck.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.json.JSONObject

private val Context.priceCheckDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "price_check_preferences",
)

data class AppPreferences(
    val basket: Map<String, Int> = emptyMap(),
    val watchedProductIds: Set<String> = emptySet(),
    val weeklyBudget: Int = 700,
    val shoppingArea: String = "Kitui",
    val basketStrategy: BasketStrategy = BasketStrategy.LOWEST_PER_ITEM,
)

enum class BasketStrategy {
    LOWEST_PER_ITEM,
    SINGLE_STORE,
}

interface PreferencesStore {
    val preferences: Flow<AppPreferences>
    suspend fun changeBasket(productId: String, amount: Int)
    suspend fun setWatched(productId: String, watched: Boolean)
    suspend fun setBudget(amount: Int)
    suspend fun setBasketStrategy(strategy: BasketStrategy)
    suspend fun setShoppingArea(county: String)
}

class PreferenceRepository(context: Context) : PreferencesStore {
    private val dataStore = context.applicationContext.priceCheckDataStore

    override val preferences: Flow<AppPreferences> = dataStore.data.map { values ->
        val decodedBasket = JSONObject(values[BASKET] ?: "{}")
        val basket = decodedBasket.keys().asSequence().mapNotNull { productId ->
            val quantity = decodedBasket.optInt(productId, 0)
            if (quantity > 0) productId to quantity else null
        }.toMap()
        AppPreferences(
            basket = basket,
            watchedProductIds = values[WATCHED] ?: emptySet(),
            weeklyBudget = values[BUDGET] ?: 700,
            // Earlier releases stored enum names (for example, NAIROBI). Keep the raw value;
            // MarketRepository resolves it case-insensitively against the live county list.
            shoppingArea = values[AREA]?.takeIf(String::isNotBlank) ?: "Kitui",
            basketStrategy = values[STRATEGY]
                ?.let { stored ->
                    when (stored.lowercase()) {
                        "single" -> BasketStrategy.SINGLE_STORE
                        else -> BasketStrategy.entries.firstOrNull {
                            it.name.equals(stored, ignoreCase = true)
                        }
                    }
                }
                ?: BasketStrategy.LOWEST_PER_ITEM,
        )
    }

    override suspend fun changeBasket(productId: String, amount: Int) {
        dataStore.edit { values ->
            val basket = JSONObject(values[BASKET] ?: "{}")
            val nextQuantity = basket.optInt(productId, 0) + amount
            if (nextQuantity > 0) basket.put(productId, nextQuantity) else basket.remove(productId)
            values[BASKET] = basket.toString()
        }
    }

    override suspend fun setWatched(productId: String, watched: Boolean) {
        dataStore.edit { values ->
            val next = (values[WATCHED] ?: emptySet()).toMutableSet()
            if (watched) next.add(productId) else next.remove(productId)
            values[WATCHED] = next
        }
    }

    override suspend fun setBudget(amount: Int) {
        dataStore.edit { it[BUDGET] = amount }
    }

    override suspend fun setBasketStrategy(strategy: BasketStrategy) {
        dataStore.edit { it[STRATEGY] = strategy.name }
    }

    override suspend fun setShoppingArea(county: String) {
        dataStore.edit { it[AREA] = county }
    }

    private companion object {
        val BASKET = stringPreferencesKey("basket")
        val WATCHED = androidx.datastore.preferences.core.stringSetPreferencesKey("watched")
        val BUDGET = intPreferencesKey("weekly_budget")
        val AREA = stringPreferencesKey("shopping_area")
        val STRATEGY = stringPreferencesKey("basket_strategy")
    }
}
