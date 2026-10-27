package ke.pricecheck.app.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class ListingsRepository(
    context: Context,
    private val apiBaseUrl: String,
) : ProductRepository {
    private val applicationContext = context.applicationContext
    @Volatile private var currentProducts: List<Product>
    @Volatile private var currentIsDemo = false
    @Volatile private var currentDataLabel = SNAPSHOT_LABEL

    init {
        try {
            val source = applicationContext.assets.open(ASSET_NAME)
                .bufferedReader()
                .use { it.readText() }
            val payload = JSONObject(source)
            currentProducts = parseListings(payload.getJSONArray("items"))
            currentDataLabel = payload.optString("snapshot_label", SNAPSHOT_LABEL)
        } catch (_: Exception) {
            currentProducts = InMemoryProductRepository().products
            currentIsDemo = true
            currentDataLabel = DEMO_LABEL
        }
    }

    override val products: List<Product> get() = currentProducts
    override val isDemoData: Boolean get() = currentIsDemo
    override val dataLabel: String get() = currentDataLabel
    override val categories: List<String>
        get() = listOf("All") + currentProducts.map(Product::category).distinct().sorted()

    override fun findById(productId: String): Product? =
        currentProducts.firstOrNull { it.id == productId }

    override suspend fun refresh(): Boolean = withContext(Dispatchers.IO) {
        try {
            val rows = JSONArray()
            var offset = 0
            var total = Int.MAX_VALUE
            var label = SNAPSHOT_LABEL
            while (offset < total) {
                val connection = URL(
                    "${apiBaseUrl.trimEnd('/')}/api/v1/listings?limit=100&offset=$offset",
                ).openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 8_000
                connection.readTimeout = 8_000
                try {
                    val status = connection.responseCode
                    val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                    val body = stream.bufferedReader().use { it.readText() }
                    check(status in 200..299) { "Listing API returned HTTP $status" }
                    val page = JSONObject(body)
                    label = page.optString("data_label", SNAPSHOT_LABEL)
                    total = page.optInt("total", 0)
                    val items = page.getJSONArray("items")
                    for (index in 0 until items.length()) rows.put(items.getJSONObject(index))
                    if (items.length() == 0) break
                    offset += items.length()
                } finally {
                    connection.disconnect()
                }
            }
            check(rows.length() > 0) { "The listing API returned no items." }
            currentProducts = parseListings(rows)
            currentIsDemo = false
            currentDataLabel = label
            true
        } catch (_: Exception) {
            false
        }
    }

    internal companion object {
        const val SNAPSHOT_LABEL = "snapshot 20 Oct 2026"
        const val DEMO_LABEL = "Demo supermarket prices only; not live retailer data."
        const val ASSET_NAME = "listings_snapshot.json"

        fun parseListings(items: JSONArray): List<Product> {
            val rows = (0 until items.length()).map(items::getJSONObject)
            val grouped = rows.groupBy { row ->
                val name = normalize(row.optString("item_name"))
                val size = normalize(row.optString("pack_size"))
                "$name|$size"
            }
            return grouped.toSortedMap().map { (key, group) ->
                val first = group.first()
                val digest = MessageDigest.getInstance("SHA-256")
                    .digest(key.toByteArray())
                    .take(10)
                    .joinToString("") { "%02x".format(it) }
                val prices = group.map { row ->
                    val rawPrice = row.getDouble("price_kes")
                    require(rawPrice % 1.0 == 0.0) {
                        "A fractional KES listing cannot be displayed as an integer price."
                    }
                    StorePrice(
                        store = row.getString("supermarket"),
                        price = rawPrice.toInt(),
                        stock = "",
                        listingId = row.getString("id"),
                        productUrl = row.optString("product_url").takeIf(String::isNotBlank),
                        unitPrice = row.optDouble("unit_price").takeUnless(Double::isNaN),
                    )
                }.sortedBy(StorePrice::price)
                Product(
                    id = "snapshot-$digest",
                    name = first.getString("item_name"),
                    size = first.optString("pack_size"),
                    description = first.optString("data_notes"),
                    category = first.optString("category", "Other"),
                    prices = prices,
                    isDemoData = false,
                    dataLabel = SNAPSHOT_LABEL,
                    predictedFoodGroup = first.optString("food_group").takeIf(String::isNotBlank),
                    predictedNova = first.optString("nova").takeIf(String::isNotBlank),
                )
            }
        }

        private fun normalize(value: String) = value.lowercase()
            .replace(Regex("[^a-z0-9]+"), " ")
            .trim()
    }
}
