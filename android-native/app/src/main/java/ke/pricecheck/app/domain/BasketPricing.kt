package ke.pricecheck.app.domain

import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.Product

data class BasketLine(val product: Product, val quantity: Int)

data class StoreTotal(val store: String, val total: Int)

object BasketPricing {
    fun eligibleStoreTotals(lines: List<BasketLine>): List<StoreTotal> {
        if (lines.isEmpty()) return emptyList()
        val stores = lines.first().product.prices.map { it.store }
        return stores.mapNotNull { store ->
            val total = lines.sumOf { line ->
                line.product.prices.firstOrNull { it.store == store }
                    ?.price
                    ?.times(line.quantity)
                    ?: return@mapNotNull null
            }
            StoreTotal(store, total)
        }.sortedBy(StoreTotal::total)
    }

    fun total(lines: List<BasketLine>, strategy: BasketStrategy): Int {
        if (strategy == BasketStrategy.SINGLE_STORE) {
            eligibleStoreTotals(lines).firstOrNull()?.let { return it.total }
        }
        return lines.sumOf { line -> line.product.lowestPrice.price * line.quantity }
    }
}
