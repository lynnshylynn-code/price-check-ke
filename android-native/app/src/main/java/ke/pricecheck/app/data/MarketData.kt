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
