package ke.pricecheck.app.domain

import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.Product

data class BasketLine(val product: Product, val quantity: Int)

data class StoreTotal(val store: String, val total: Int)
data class StoreAvailability(val store: String, val total: Int?, val missingItems: List<String>)

object BasketPricing {
    fun storeAvailability(lines: List<BasketLine>): List<StoreAvailability> {
        if (lines.isEmpty()) return emptyList()
        val stores = lines.flatMap { line -> line.product.prices.map { it.store } }.toSet().sorted()
        return stores.map { store ->
            val missing = lines.filter { line -> line.product.prices.none { it.store == store } }
                .map { it.product.name }
            val total = if (missing.isEmpty()) lines.sumOf { line ->
                line.product.prices.first { it.store == store }.price * line.quantity
            } else null
            StoreAvailability(store, total, missing)
        }.sortedWith(compareBy<StoreAvailability> { it.total == null }.thenBy { it.total ?: Int.MAX_VALUE })
    }

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
