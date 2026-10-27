package ke.pricecheck.app.data

import org.json.JSONArray
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ListingsRepositoryParsingTest {
    @Test fun parsesRealListingFieldsAndGroupsExactCrossStoreItems() {
        val sample = JSONArray(
            """[
                {"id":"c4cdf7ab8d0eb535969450a9","supermarket":"Carrefour","item_name":"Ajab All Purpose Flour 2kg","price_kes":178.0,"pack_size":"2kg","unit_price":89.0,"category":"pantry","product_url":"https://www.carrefour.ke/mafken/en/plain-white-flour/ajab-all-purpose-flour-2kg/p/120048"},
                {"id":"8eb418f32c81d121009fe9ed","supermarket":"Naivas","item_name":"Ajab All Purpose Flour 2KG","price_kes":180.0,"pack_size":"2KG","unit_price":90.0,"category":"pantry","product_url":"https://naivas.online/ajab-flour-2kg","image":{"image_url":"https://images.openfoodfacts.org/images/products/123/flour.jpg","attribution":"Open Food Facts contributor: sample","source_page":"https://world.openfoodfacts.org/product/123","licence_note":"CC BY-SA; reviewed"}}
            ]""".trimIndent(),
        )
        val product = ListingsRepository.parseListings(sample).single()
        assertEquals("Ajab All Purpose Flour 2kg", product.name)
        assertEquals(2, product.prices.size)
        assertEquals(178, product.lowestPrice.price)
        assertEquals("c4cdf7ab8d0eb535969450a9", product.lowestPrice.listingId)
        assertTrue(product.lowestPrice.productUrl!!.startsWith("https://"))
        assertEquals("https://images.openfoodfacts.org/images/products/123/flour.jpg", product.image?.imageUrl)
        assertEquals("Open Food Facts contributor: sample", product.image?.attribution)
        assertFalse(product.isDemoData)
    }

    @Test fun leavesImageNullWhenTheBackendHasNoApprovedImage() {
        val items = JSONArray(
            """[{"id":"x","supermarket":"Naivas","item_name":"Test item","price_kes":12.0,"pack_size":"1kg","product_url":"https://example.test/item"}]""",
        )
        assertEquals(null, ListingsRepository.parseListings(items).single().image)
    }

    @Test(expected = IllegalArgumentException::class)
    fun refusesFractionalPricesInsteadOfRounding() {
        ListingsRepository.parseListings(
            JSONArray(
                """[{"id":"x","supermarket":"Naivas","item_name":"Test item","price_kes":12.5,"pack_size":"1kg","product_url":"https://example.test/item"}]""",
            ),
        )
    }
}
