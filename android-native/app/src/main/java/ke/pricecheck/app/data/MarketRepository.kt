package ke.pricecheck.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

interface MarketDataSource {
    suspend fun loadMarketAreas(): List<MarketArea>
    suspend fun loadFoodInflation(): FoodInflationData
    suspend fun loadAreaPrices(county: String): AreaMarketData
    suspend fun askQuestion(question: String): MarketQuestionAnswer
}

class MarketRepository(private val baseUrl: String) : MarketDataSource {
    override suspend fun loadMarketAreas(): List<MarketArea> = withContext(Dispatchers.IO) {
        parseMarketAreas(request("/api/markets").toString())
    }

    override suspend fun loadAreaPrices(county: String): AreaMarketData = withContext(Dispatchers.IO) {
        val queryCounty = URLEncoder.encode(county, Charsets.UTF_8)
        val maize = parsePriceSeries(request("/api/prices?market=$queryCounty&commodity=maize").toString(), "maize")
        val beans = parsePriceSeries(request("/api/prices?market=$queryCounty&commodity=beans").toString(), "beans")
        val combined = maize.prices + beans.prices
        val latestDate = combined.maxOfOrNull { it.date }
        AreaMarketData(
            area = county,
            sourceName = maize.sourceName,
            sourceUrl = maize.sourceUrl,
            coverageStart = listOfNotNull(maize.coverageStart, beans.coverageStart).minOrNull().orEmpty(),
            coverageEnd = listOfNotNull(maize.coverageEnd, beans.coverageEnd).maxOrNull().orEmpty(),
            latestMonth = latestDate?.let {
                LocalDate.parse(it).format(DateTimeFormatter.ofPattern("MMM yyyy", Locale.getDefault()))
            }.orEmpty(),
            prices = combined.groupBy { it.market to it.commodity }.values.mapNotNull { points ->
                points.maxByOrNull { it.date }
            },
        )
    }

    internal fun parseMarketAreas(payload: String): List<MarketArea> {
        val markets = JSONObject(payload).getJSONArray("markets")
        val listings = List(markets.length()) { index ->
            val market = markets.getJSONObject(index)
            val commodities = market.getJSONArray("available_commodities")
            MarketListing(
                name = market.getString("name"),
                county = market.getString("county"),
                region = market.getString("region"),
                availableCommodities = List(commodities.length()) { commodities.getString(it) }.toSet(),
            )
        }
        return filterMarketAreas(listings)
    }
    internal fun parsePriceSeries(payload: String, expectedCommodity: String): MarketPriceSeries {
        val response = JSONObject(payload)
        val observations = response.getJSONArray("observations")
        val prices = List(observations.length()) { index ->
            val item = observations.getJSONObject(index)
            MarketPricePoint(
                market = item.getString("market"),
                county = item.getString("county"),
                date = item.getString("date"),
                commodity = item.getString("commodity"),
                price = item.getDouble("price"),
                currency = item.getString("currency"),
                unit = item.getString("unit"),
            ).also { require(it.commodity == expectedCommodity) }
        }
        return MarketPriceSeries(
            sourceName = response.getString("source_name"),
            sourceUrl = response.getString("source_url"),
            coverageStart = response.optString("coverage_start").takeIf(String::isNotBlank),
            coverageEnd = response.optString("coverage_end").takeIf(String::isNotBlank),
            prices = prices,
        )
    }
    override suspend fun loadFoodInflation(): FoodInflationData = withContext(Dispatchers.IO) {
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

    override suspend fun askQuestion(question: String): MarketQuestionAnswer = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("question", question)
        val response = request("/api/v1/ai/market-question", payload)
        MarketQuestionAnswer(
            answer = response.getString("answer"),
            sourceName = response.getString("source_name"),
            sourceUrl = response.getString("source_url"),
            coverageStart = response.getString("coverage_start"),
            coverageEnd = response.getString("coverage_end"),
        )
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

internal fun filterMarketAreas(listings: List<MarketListing>): List<MarketArea> =
    listings.asSequence()
        .filter { it.availableCommodities.isNotEmpty() }
        .groupBy(MarketListing::county)
        .map { (county, markets) ->
            MarketArea(
                county = county,
                markets = markets.map(MarketListing::name).distinct().sorted(),
                availableCommodities = markets.flatMap(MarketListing::availableCommodities).toSet(),
            )
        }
        .sortedBy(MarketArea::county)

internal fun defaultMarketCounty(areas: List<MarketArea>, storedCounty: String? = null): String? {
    areas.firstOrNull { it.county.equals(storedCounty?.trim(), ignoreCase = true) }?.let {
        return it.county
    }
    areas.firstOrNull {
        it.county.equals("Kitui", ignoreCase = true) &&
            setOf("beans", "maize").all(it.availableCommodities::contains)
    }?.let { return it.county }
    areas.firstOrNull { setOf("beans", "maize").all(it.availableCommodities::contains) }
        ?.let { return it.county }
    return areas.firstOrNull()?.county
}
