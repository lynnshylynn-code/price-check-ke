package ke.pricecheck.app.data

interface ProductRepository {
    val products: List<Product>

    fun findById(productId: String): Product?
}

class InMemoryProductRepository : ProductRepository {
    override val products: List<Product> = ProductCatalog.products
    private val productsById = products.associateBy(Product::id)

    override fun findById(productId: String): Product? = productsById[productId]
}
