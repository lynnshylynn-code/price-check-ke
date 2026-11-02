package ke.pricecheck.app.ui

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performScrollTo
import ke.pricecheck.app.data.FoodInflationData
import ke.pricecheck.app.data.MarketObservation
import ke.pricecheck.app.data.MarketSeries
import ke.pricecheck.app.data.MarketSummary
import ke.pricecheck.app.ui.screens.TrendsScreen
import org.junit.Rule
import org.junit.Test

class AssistantChatScreenTest {
    @get:Rule val composeRule = createComposeRule()

    @Test fun sendingQuestionShowsUserAndAssistantBubbles() {
        val initial = PriceCheckUiState(marketData = sampleMarket, marketLoading = false)
        val state = mutableStateOf(initial)
        composeRule.setContent {
            PriceCheckTheme {
                TrendsScreen(
                    state = state.value,
                    products = emptyList(),
                    onQuestion = { question -> state.value = state.value.copy(question = question) },
                    onAsk = {
                        val question = state.value.question
                        state.value = state.value.copy(
                            question = "",
                            assistantMessages = listOf(
                                AssistantChatMessage("user", question),
                                AssistantChatMessage("assistant", "A grounded response.", "cheapest_item"),
                            ),
                        )
                    },
                    onNewChat = { state.value = state.value.copy(assistantMessages = emptyList()) },
                    onSelectYear = {}, onRefresh = {}, onOpenProduct = {}, onAddProduct = {},
                    onToggleWatched = {},
                )
            }
        }
        composeRule.onNodeWithText("Your question").performScrollTo().performTextInput("cheapest milk")
        composeRule.onNodeWithText("Send").performScrollTo().performClick()
        composeRule.onNodeWithText("cheapest milk").assertIsDisplayed()
        composeRule.onNodeWithText("A grounded response.").assertIsDisplayed()
    }

    private companion object {
        val sampleMarket = FoodInflationData(
            series = MarketSeries(
                "Kenya", "National market average", "World Bank RTFP",
                "https://example.org/data", "Jan 2022", "Aug 2022", 2022,
            ),
            summary = MarketSummary(
                1, 1.0, "Jan 2022", 1.0, "Aug 2022", 1.0, "Jul 2022", 0.0,
                "Aug 2022", 1.0, "Sample summary",
            ),
            observations = listOf(MarketObservation(2022, "Aug", 8, 1.0)),
        )
    }
}
