package ke.pricecheck.app.domain

import ke.pricecheck.app.data.FoodInflationData
import ke.pricecheck.app.data.MarketObservation
import ke.pricecheck.app.data.MarketSeries
import ke.pricecheck.app.data.MarketSummary
import org.junit.Assert.assertTrue
import org.junit.Test

class MarketQuestionAnswerTest {
    private val data = FoodInflationData(
        series = MarketSeries(
            country = "Kenya",
            marketScope = "National market average",
            sourceName = "World Bank Kenya RTFP",
            sourceUrl = "https://microdata.worldbank.org/index.php/catalog/6167",
            coverageStart = "Jul 2026",
            coverageEnd = "Aug 2026",
            year = 2026,
        ),
        summary = MarketSummary(
            observationCount = 2,
            meanValue = 9.88,
            minimumMonth = "Jul 2026",
            minimumValue = 9.3,
            latestMonth = "Aug 2026",
            latestValue = 10.46,
            previousMonth = "Jul 2026",
            changeFromPrevious = 1.16,
            peakMonth = "Aug 2026",
            peakValue = 10.46,
            narrative = "",
        ),
        observations = listOf(
            MarketObservation(2026, "Jul", 7, 9.3),
            MarketObservation(2026, "Aug", 8, 10.46),
        ),
    )

    @Test
    fun latestQuestionUsesTheDatasetAndPercentagePointChange() {
        val answer = answerFromDataset("What was the latest reading?", data)

        assertTrue(answer.contains("10.46%"))
        assertTrue(answer.contains("Aug 2026"))
        assertTrue(answer.contains("1.16 percentage points"))
    }

    @Test
    fun monthAndYearQuestionFindsTheMatchingObservation() {
        val answer = answerFromDataset("What happened in July 2026?", data)

        assertTrue(answer.contains("Jul 2026"))
        assertTrue(answer.contains("9.30%"))
    }

    @Test
    fun supermarketQuestionDoesNotInventAProductPrice() {
        val answer = answerFromDataset("How much is milk at the supermarket?", data)

        assertTrue(answer.contains("does not contain verified product or supermarket prices"))
    }

    @Test
    fun whyQuestionDoesNotClaimCausation() {
        val answer = answerFromDataset("Why did food inflation rise?", data)

        assertTrue(answer.contains("does not identify why"))
    }

    @Test
    fun unsupportedYearIsReportedAsMissing() {
        val answer = answerFromDataset("What happened in 2022?", data)

        assertTrue(answer.contains("no reported observations for 2022"))
    }
}
