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

data class BasketEntry(val productId: String, val quantity: Int)

data class AppPreferences(
    val basket: Map<String, Int> = emptyMap(),
    val watchedProductIds: Set<String> = emptySet(),
    val weeklyBudget: Int = 700,
    val shoppingArea: ShoppingArea = ShoppingArea.NAIROBI,
    val basketStrategy: BasketStrategy = BasketStrategy.LOWEST_PER_ITEM,
)

enum class ShoppingArea {
    NAIROBI,
    MOMBASA,
    KISUMU,
    NAKURU,
}

enum class BasketStrategy {
    LOWEST_PER_ITEM,
    SINGLE_STORE,
}

class PreferenceRepository(context: Context) {
    private val dataStore = context.applicationContext.priceCheckDataStore

    val preferences: Flow<AppPreferences> = dataStore.data.map { values ->
        val decodedBasket = JSONObject(values[BASKET] ?: "{}")
        val basket = decodedBasket.keys().asSequence().mapNotNull { productId ->
            val quantity = decodedBasket.optInt(productId, 0)
            if (quantity > 0) productId to quantity else null
        }.toMap()
        AppPreferences(
            basket = basket,
            watchedProductIds = values[WATCHED] ?: emptySet(),
            weeklyBudget = values[BUDGET] ?: 700,
            shoppingArea = values[AREA]?.let { stored ->
                ShoppingArea.entries.firstOrNull { area ->
                    area.name.equals(stored, ignoreCase = true)
                }
            } ?: ShoppingArea.NAIROBI,
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

    suspend fun changeBasket(productId: String, amount: Int) {
        dataStore.edit { values ->
            val basket = JSONObject(values[BASKET] ?: "{}")
            val nextQuantity = basket.optInt(productId, 0) + amount
            if (nextQuantity > 0) basket.put(productId, nextQuantity) else basket.remove(productId)
            values[BASKET] = basket.toString()
        }
    }

    suspend fun setWatched(productId: String, watched: Boolean) {
        dataStore.edit { values ->
            val next = (values[WATCHED] ?: emptySet()).toMutableSet()
            if (watched) next.add(productId) else next.remove(productId)
            values[WATCHED] = next
        }
    }

    suspend fun setBudget(amount: Int) {
        dataStore.edit { it[BUDGET] = amount }
    }

    suspend fun setBasketStrategy(strategy: BasketStrategy) {
        dataStore.edit { it[STRATEGY] = strategy.name }
    }

    private companion object {
        val BASKET = stringPreferencesKey("basket")
        val WATCHED = androidx.datastore.preferences.core.stringSetPreferencesKey("watched")
        val BUDGET = intPreferencesKey("weekly_budget")
        val AREA = stringPreferencesKey("shopping_area")
        val STRATEGY = stringPreferencesKey("basket_strategy")
    }
}
