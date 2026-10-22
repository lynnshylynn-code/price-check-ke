package ke.pricecheck.app.ui

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import ke.pricecheck.app.R
import org.junit.Rule
import org.junit.Test

class CheckoutScreenTest {
    @get:Rule val composeRule = createComposeRule()

    @Test fun emptyCheckoutFormShowsAddressAndPhoneValidationErrors() {
        val state = mutableStateOf(CheckoutUiState())
        composeRule.setContent {
            CheckoutScreen(
                state = state.value,
                onSubmit = { address, phone ->
                    state.value = state.value.copy(
                        addressError = CheckoutValidation.addressError(address),
                        phoneError = if (CheckoutValidation.normalizedPhone(phone) == null) {
                            R.string.checkout_phone_error
                        } else null,
                    )
                },
                onUseLocation = {},
            )
        }
        composeRule.onNodeWithTag("checkout-submit").performClick()
        composeRule.onNodeWithText("Enter an address between 10 and 200 characters.")
            .assertIsDisplayed()
        composeRule.onNodeWithText("Enter a valid Kenyan mobile number.").assertIsDisplayed()
    }
}
