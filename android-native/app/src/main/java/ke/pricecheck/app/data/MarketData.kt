package ke.pricecheck.app.data

data class MarketObservation(
    val year: Int,
    val month: String,
    val monthNumber: Int,
    val value: Double,
)

data class MarketSummary(
    val observationCount: Int,
    val meanValue: Double,
    val minimumMonth: String,
    val minimumValue: Double,
    val latestMonth: String,
    val latestValue: Double,
    val previousMonth: String,
    val changeFromPrevious: Double,
    val peakMonth: String,
    val peakValue: Double,
    val narrative: String,
)

data class MarketSeries(
    val country: String,
    val marketScope: String,
    val sourceName: String,
    val sourceUrl: String,
    val coverageStart: String,
    val coverageEnd: String,
    val year: Int,
)

data class FoodInflationData(
    val series: MarketSeries,
    val summary: MarketSummary,
    val observations: List<MarketObservation>,
)

data class MarketPricePoint(
    val market: String,
    val county: String,
    val date: String,
    val commodity: String,
    val price: Double,
    val currency: String,
    val unit: String,
)

data class AreaMarketData(
    val area: String,
    val sourceName: String,
    val sourceUrl: String,
    val coverageStart: String,
    val coverageEnd: String,
    val latestMonth: String,
    val prices: List<MarketPricePoint>,
)

data class MarketListing(
    val name: String,
    val county: String,
    val region: String,
    val availableCommodities: Set<String>,
)

data class MarketArea(
    val county: String,
    val markets: List<String>,
    val availableCommodities: Set<String>,
)

data class MarketPriceSeries(
    val sourceName: String,
    val sourceUrl: String,
    val coverageStart: String?,
    val coverageEnd: String?,
    val prices: List<MarketPricePoint>,
)

data class MarketQuestionAnswer(
    val answer: String,
    val sourceName: String,
    val sourceUrl: String,
    val coverageStart: String,
    val coverageEnd: String,
)
