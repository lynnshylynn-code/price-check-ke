package ke.pricecheck.app.domain

import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.ProductCatalog
import org.junit.Assert.assertEquals
import org.junit.Test

class BasketPricingTest {
    private val bread = ProductCatalog.products.first { it.id == "bread" }
    private val yoghurt = ProductCatalog.products.first { it.id == "yoghurt" }

    @Test
    fun lowestPerItemTotalsEachProductsCheapestPriceTimesQuantity() {
        val lines = listOf(BasketLine(bread, 2), BasketLine(yoghurt, 1))

        assertEquals(240, BasketPricing.total(lines, BasketStrategy.LOWEST_PER_ITEM))
    }

    @Test
    fun singleStoreTotalsOnlyStoresThatCarryEveryProduct() {
        val lines = listOf(BasketLine(bread, 2), BasketLine(yoghurt, 1))

        assertEquals(
            listOf(StoreTotal("Naivas", 245), StoreTotal("Jaza", 250), StoreTotal("Carrefour", 257)),
            BasketPricing.eligibleStoreTotals(lines),
        )
        assertEquals(245, BasketPricing.total(lines, BasketStrategy.SINGLE_STORE))
    }

    @Test
    fun emptyBasketHasZeroTotalAndNoEligibleStores() {
        assertEquals(0, BasketPricing.total(emptyList(), BasketStrategy.SINGLE_STORE))
        assertEquals(emptyList<StoreTotal>(), BasketPricing.eligibleStoreTotals(emptyList()))
    }
}
