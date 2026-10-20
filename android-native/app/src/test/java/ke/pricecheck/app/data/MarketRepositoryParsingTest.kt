package ke.pricecheck.app.data

import org.junit.Assert.*
import org.junit.Test

class MarketRepositoryParsingTest {
    private val repository = MarketRepository("http://localhost")

    @Test fun parsesTheBackendBeansPriceSeries() {
        val result = repository.parsePriceSeries(NAIROBI_BEANS_RESPONSE, "beans")

        assertEquals("World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP)", result.sourceName)
        assertEquals("https://microdata.worldbank.org/index.php/catalog/6167", result.sourceUrl)
        assertEquals("2022-01-01", result.coverageStart)
        assertEquals("2022-01-01", result.coverageEnd)
        assertEquals(1, result.prices.size)
        assertEquals("Kibra (Nairobi)", result.prices.single().market)
        assertEquals(130.0, result.prices.single().price, 0.0)
        assertEquals("KES", result.prices.single().currency)
        assertEquals("1 kg", result.prices.single().unit)
    }

    @Test fun parsesAnEmptyAreaCommoditySeriesWithoutCreatingPrices() {
        val result = repository.parsePriceSeries(EMPTY_NAIROBI_MAIZE_RESPONSE, "maize")

        assertTrue(result.prices.isEmpty())
        assertNull(result.coverageStart)
        assertNull(result.coverageEnd)
    }

    private companion object {
        // Schema and Nairobi observation are copied from the live endpoint contract and backend dataset tests.
        const val NAIROBI_BEANS_RESPONSE = """{"market":"Nairobi","commodity":"beans","unit":"1 kg","currency":"KES","source_name":"World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP)","source_url":"https://microdata.worldbank.org/index.php/catalog/6167","coverage_start":"2022-01-01","coverage_end":"2022-01-01","source_note":"Observed source-market prices in KES; one record per market and month. No missing values are interpolated and county selections are not averaged.","observations":[{"market":"Kibra (Nairobi)","county":"Nairobi","region":"Nairobi","date":"2022-01-01","commodity":"beans","price":130.0,"currency":"KES","unit":"1 kg"}]}"""
        const val EMPTY_NAIROBI_MAIZE_RESPONSE = """{"market":"Nairobi","commodity":"maize","unit":"1 kg","currency":"KES","source_name":"World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP)","source_url":"https://microdata.worldbank.org/index.php/catalog/6167","coverage_start":null,"coverage_end":null,"source_note":"Observed source-market prices in KES; one record per market and month.","observations":[]}"""
    }
}
