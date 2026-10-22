package ke.pricecheck.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class OrderLineRequest(
    val listingId: String,
    val quantity: Int,
)

data class OrderRecord(
    val id: String,
    val status: String,
    val store: String,
    val subtotal: Double,
    val deliveryFee: Double?,
)

interface OrderRepository {
    suspend fun create(
        store: String,
        items: List<OrderLineRequest>,
        address: String,
        phone: String,
        latitude: Double?,
        longitude: Double?,
    ): OrderRecord

    suspend fun pay(orderId: String): OrderRecord
    suspend fun status(orderId: String): OrderRecord
    suspend fun cancel(orderId: String): OrderRecord
    suspend fun delete(orderId: String)
}

class HttpOrderRepository(private val apiBaseUrl: String) : OrderRepository {
    override suspend fun create(
        store: String,
        items: List<OrderLineRequest>,
        address: String,
        phone: String,
        latitude: Double?,
        longitude: Double?,
    ): OrderRecord = withContext(Dispatchers.IO) {
        val jsonItems = JSONArray().apply {
            items.forEach { put(JSONObject().put("listing_id", it.listingId).put("quantity", it.quantity)) }
        }
        val body = JSONObject()
            .put("store", store)
            .put("items", jsonItems)
            .put("delivery_address", address)
            .put("phone", phone)
        if (latitude != null && longitude != null) {
            body.put("latitude", latitude).put("longitude", longitude)
        }
        request("POST", "/api/v1/orders", body)
    }

    override suspend fun pay(orderId: String): OrderRecord = withContext(Dispatchers.IO) {
        request("POST", "/api/v1/orders/$orderId/pay", JSONObject())
    }

    override suspend fun status(orderId: String): OrderRecord = withContext(Dispatchers.IO) {
        request("GET", "/api/v1/orders/$orderId")
    }

    override suspend fun cancel(orderId: String): OrderRecord = withContext(Dispatchers.IO) {
        request("POST", "/api/v1/orders/$orderId/cancel", JSONObject())
    }

    override suspend fun delete(orderId: String) = withContext(Dispatchers.IO) {
        val connection = URL("${apiBaseUrl.trimEnd('/')}/api/v1/orders/$orderId")
            .openConnection() as HttpURLConnection
        connection.requestMethod = "DELETE"
        connection.connectTimeout = 8_000
        connection.readTimeout = 8_000
        try {
            check(connection.responseCode in 200..299) { errorMessage(connection) }
        } finally {
            connection.disconnect()
        }
    }

    private fun request(method: String, path: String, body: JSONObject? = null): OrderRecord {
        val connection = URL("${apiBaseUrl.trimEnd('/')}$path").openConnection() as HttpURLConnection
        connection.requestMethod = method
        connection.connectTimeout = 8_000
        connection.readTimeout = 8_000
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.bufferedWriter().use { it.write(body.toString()) }
        }
        try {
            check(connection.responseCode in 200..299) { errorMessage(connection) }
            val response = JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
            return OrderRecord(
                id = response.getString("id"),
                status = response.getString("status"),
                store = response.getString("store"),
                subtotal = response.getDouble("subtotal"),
                deliveryFee = if (response.isNull("delivery_fee")) null
                else response.getDouble("delivery_fee"),
            )
        } finally {
            connection.disconnect()
        }
    }

    private fun errorMessage(connection: HttpURLConnection): String {
        val stream = connection.errorStream ?: return "Order request failed (${connection.responseCode})."
        val error = runCatching { JSONObject(stream.bufferedReader().use { it.readText() }).optString("detail") }
            .getOrNull()
        return error?.takeIf(String::isNotBlank) ?: "Order request failed (${connection.responseCode})."
    }
}
