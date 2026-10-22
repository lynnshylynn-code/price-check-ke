package ke.pricecheck.app.data

interface ProductRepository {
    val products: List<Product>
    val categories: List<String>
    val isDemoData: Boolean get() = true
    val dataLabel: String get() = "Demo supermarket prices only; not live retailer data."

    suspend fun refresh(): Boolean = false

    fun findById(productId: String): Product?
}

class InMemoryProductRepository : ProductRepository {
    override val products: List<Product> = ProductCatalog.products
    override val categories: List<String> = ProductCatalog.categories
    private val productsById = products.associateBy(Product::id)

    override fun findById(productId: String): Product? = productsById[productId]
}
