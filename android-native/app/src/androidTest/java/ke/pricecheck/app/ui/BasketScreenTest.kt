package ke.pricecheck.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollTo
import ke.pricecheck.app.data.AppPreferences
import ke.pricecheck.app.data.BasketStrategy
import ke.pricecheck.app.data.ProductCatalog
import ke.pricecheck.app.ui.screens.BasketScreen
import org.junit.Rule
import org.junit.Test

class BasketScreenTest {
    @get:Rule val composeRule = createComposeRule()

    @Test fun basketShowsBothPricingStrategiesForTwoProducts() {
        val products = ProductCatalog.products.filter { it.id in setOf("bread", "yoghurt") }
        val state = PriceCheckUiState(
            preferences = AppPreferences(
                basket = mapOf("bread" to 1, "yoghurt" to 1),
                basketStrategy = BasketStrategy.LOWEST_PER_ITEM,
            ),
        )
        composeRule.setContent {
            PriceCheckTheme {
                BasketScreen(
                    state = state,
                    products = products,
                    onChangeQuantity = { _, _ -> },
                    onChangeStrategy = {},
                    onBrowse = {},
                    onShare = {},
                    total = 175,
                    lowestPerItemTotal = 175,
                    singleStoreTotal = 180,
                    bestSingleStore = "Naivas",
                    storeOptions = emptyList(),
                    onOrderFromStore = {},
                )
            }
        }

        composeRule.onNodeWithText("Your basket").assertIsDisplayed()
        composeRule.onNodeWithText("Lowest per item: KSh 175").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("One store (Naivas): KSh 180").performScrollTo().assertIsDisplayed()
    }
}
