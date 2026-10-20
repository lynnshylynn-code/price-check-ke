package ke.pricecheck.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class MarketRepository(private val baseUrl: String) {
    suspend fun loadFoodInflation(): FoodInflationData = withContext(Dispatchers.IO) {
        val payload = request("/api/v1/market/food-inflation")
        val seriesJson = payload.getJSONObject("series")
        val summaryJson = payload.getJSONObject("summary")
        val observationsJson = payload.getJSONArray("observations")
        val observations = List(observationsJson.length()) { index ->
            val item = observationsJson.getJSONObject(index)
            MarketObservation(
                year = item.getInt("year"),
                month = item.getString("month"),
                monthNumber = item.getInt("month_number"),
                value = item.getDouble("value"),
            )
        }
        if (observations.isEmpty()) throw IOException("The market API returned no observations.")

        FoodInflationData(
            series = MarketSeries(
                country = seriesJson.getString("country"),
                marketScope = seriesJson.getString("market_scope"),
                sourceName = seriesJson.getString("source_name"),
                sourceUrl = seriesJson.getString("source_url"),
                coverageStart = seriesJson.getString("coverage_start"),
                coverageEnd = seriesJson.getString("coverage_end"),
                year = seriesJson.getInt("year"),
            ),
            summary = MarketSummary(
                observationCount = summaryJson.getInt("observation_count"),
                meanValue = summaryJson.getDouble("mean_value"),
                minimumMonth = summaryJson.getString("minimum_month"),
                minimumValue = summaryJson.getDouble("minimum_value"),
                latestMonth = summaryJson.getString("latest_month"),
                latestValue = summaryJson.getDouble("latest_value"),
                previousMonth = summaryJson.getString("previous_month"),
                changeFromPrevious = summaryJson.getDouble("change_from_previous"),
                peakMonth = summaryJson.getString("peak_month"),
                peakValue = summaryJson.getDouble("peak_value"),
                narrative = summaryJson.getString("narrative"),
            ),
            observations = observations,
        )
    }

    suspend fun askQuestion(question: String): String = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("question", question)
        request("/api/v1/ai/market-question", payload).getString("answer")
    }

    private fun request(path: String, body: JSONObject? = null): JSONObject {
        val connection = URL("$baseUrl$path").openConnection() as HttpURLConnection
        try {
            connection.requestMethod = if (body == null) "GET" else "POST"
            connection.connectTimeout = 8_000
            connection.readTimeout = 20_000
            connection.setRequestProperty("Accept", "application/json")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.bufferedWriter(Charsets.UTF_8).use { writer ->
                    writer.write(body.toString())
                }
            }

            val status = connection.responseCode
            val responseStream =
                if (status in 200..299) connection.inputStream else connection.errorStream
            val responseText = responseStream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }
                ?: throw IOException("The market API returned an empty response (HTTP $status).")
            val responseJson = JSONObject(responseText)
            if (status !in 200..299) {
                val detail = responseJson.optString("detail").ifBlank {
                    "The market API request failed (HTTP $status)."
                }
                throw IOException(detail)
            }
            return responseJson
        } finally {
            connection.disconnect()
        }
    }
}
