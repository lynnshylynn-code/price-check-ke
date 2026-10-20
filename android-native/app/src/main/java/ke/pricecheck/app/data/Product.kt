package ke.pricecheck.app.data

data class StorePrice(
    val store: String,
    val price: Int,
    val stock: String,
)

data class Product(
    val id: String,
    val name: String,
    val size: String,
    val description: String,
    val category: String,
    val prices: List<StorePrice>,
) {
    val lowestPrice: StorePrice
        get() = prices.minBy(StorePrice::price)
}

object ProductCatalog {
    val categories = listOf("All", "Dairy", "Bakery", "Pantry", "Produce")

    val products = listOf(
        Product("bread", "Supa Loaf Bread", "400g", "White sandwich loaf", "Bakery", listOf(
            StorePrice("Naivas", 65, "In stock"),
            StorePrice("Carrefour", 69, "In stock"),
            StorePrice("Jaza", 70, "In stock"),
            StorePrice("Quickmart", 72, "In stock"),
        )),
        Product("yoghurt", "KCC Yoghurt", "500ml", "Natural probiotic yoghurt", "Dairy", listOf(
            StorePrice("Jaza", 110, "In stock"),
            StorePrice("Naivas", 115, "In stock"),
            StorePrice("Carrefour", 119, "In stock"),
        )),
        Product("brookside-milk", "Brookside Milk", "1L", "Long life full cream", "Dairy", listOf(
            StorePrice("Carrefour", 139, "In stock"),
            StorePrice("Naivas", 145, "Low stock"),
            StorePrice("Jaza", 147, "In stock"),
            StorePrice("Quickmart", 150, "In stock"),
        )),
        Product("fresha-milk", "Fresha Milk", "1L", "Fresh whole milk", "Dairy", listOf(
            StorePrice("Naivas", 145, "In stock"),
            StorePrice("Jaza", 149, "In stock"),
            StorePrice("Quickmart", 152, "In stock"),
        )),
        Product("cooking-oil", "Fresh Fri Cooking Oil", "1L", "Pure vegetable oil", "Pantry", listOf(
            StorePrice("Carrefour", 245, "In stock"),
            StorePrice("Naivas", 252, "In stock"),
            StorePrice("Jaza", 256, "In stock"),
            StorePrice("Quickmart", 259, "In stock"),
        )),
        Product("sugar", "Kabras Sugar", "2kg", "Fine white sugar", "Pantry", listOf(
            StorePrice("Quickmart", 280, "In stock"),
            StorePrice("Naivas", 289, "In stock"),
            StorePrice("Jaza", 292, "In stock"),
            StorePrice("Carrefour", 295, "In stock"),
        )),
        Product("tomatoes", "Fresh Tomatoes", "1kg", "Fresh market tomatoes", "Produce", listOf(
            StorePrice("Naivas", 120, "In stock"),
            StorePrice("Carrefour", 135, "In stock"),
            StorePrice("Jaza", 125, "In stock"),
            StorePrice("Quickmart", 130, "In stock"),
        )),
        Product("onions", "Red Onions", "1kg", "Fresh red onions", "Produce", listOf(
            StorePrice("Naivas", 150, "In stock"),
            StorePrice("Carrefour", 160, "In stock"),
            StorePrice("Jaza", 145, "In stock"),
            StorePrice("Quickmart", 155, "In stock"),
        )),
        Product("maize-flour", "Soko Maize Flour", "2kg", "Fortified sifted maize flour", "Pantry", listOf(
            StorePrice("Naivas", 165, "In stock"),
            StorePrice("Carrefour", 172, "In stock"),
            StorePrice("Jaza", 168, "In stock"),
            StorePrice("Quickmart", 170, "In stock"),
        )),
        Product("eggs", "Farm Fresh Eggs", "Tray of 15", "Medium-size eggs", "Dairy", listOf(
            StorePrice("Naivas", 330, "In stock"),
            StorePrice("Carrefour", 345, "In stock"),
            StorePrice("Jaza", 325, "In stock"),
            StorePrice("Quickmart", 335, "In stock"),
        )),
    )
}
