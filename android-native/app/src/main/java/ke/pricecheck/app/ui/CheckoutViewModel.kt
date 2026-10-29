package ke.pricecheck.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import ke.pricecheck.app.AppContainer
import ke.pricecheck.app.R
import ke.pricecheck.app.data.OrderLineRequest
import ke.pricecheck.app.data.Product
import ke.pricecheck.app.data.StorePrice
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CheckoutLine(
    val product: Product,
    val quantity: Int,
    val storePrice: StorePrice?,
)

data class CheckoutUiState(
    val store: String = "",
    val lines: List<CheckoutLine> = emptyList(),
    val missingItems: List<String> = emptyList(),
    val addressError: Int? = null,
    val phoneError: Int? = null,
    val submissionError: String? = null,
    val submitting: Boolean = false,
    val orderId: String? = null,
    val orderStatus: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val orderDeleted: Boolean = false,
)

object CheckoutValidation {
    fun addressError(address: String): Int? =
        if (address.trim().length in 10..200) null else R.string.checkout_address_error

    fun normalizedPhone(value: String): String? {
        var digits = value.filter(Char::isDigit)
        if (digits.startsWith("0")) digits = "254" + digits.drop(1)
        else if (digits.startsWith("7") || digits.startsWith("1")) digits = "254$digits"
        return digits.takeIf { Regex("254[17]\\d{8}").matches(it) }
    }
}

class CheckoutViewModel(
    private val container: AppContainer,
) : ViewModel() {
    private val mutableState = MutableStateFlow(CheckoutUiState())
    val uiState: StateFlow<CheckoutUiState> = mutableState.asStateFlow()
    private var pollingJob: Job? = null

    fun prepareOrder(store: String, products: List<Product>, basket: Map<String, Int>) {
        val lines = basket.mapNotNull { (productId, quantity) ->
            products.firstOrNull { it.id == productId }?.let { product ->
                CheckoutLine(product, quantity, product.prices.firstOrNull { it.store == store })
            }
        }
        mutableState.value = CheckoutUiState(
            store = store,
            lines = lines,
            missingItems = lines.filter { it.storePrice == null }.map { it.product.name },
        )
    }

    fun setLocation(latitude: Double, longitude: Double) {
        mutableState.update { it.copy(latitude = latitude, longitude = longitude) }
    }

    fun submit(address: String, phone: String) {
        val normalized = CheckoutValidation.normalizedPhone(phone)
        val addressError = CheckoutValidation.addressError(address)
        val phoneError = if (normalized == null) R.string.checkout_phone_error else null
        val state = mutableState.value
        mutableState.update {
            it.copy(
                addressError = addressError,
                phoneError = phoneError,
                submissionError = null,
            )
        }
        if (addressError != null || phoneError != null || state.lines.isEmpty() || state.missingItems.isNotEmpty()) {
            if (state.lines.isEmpty() || state.missingItems.isNotEmpty()) {
                mutableState.update { it.copy(submissionError = container.strings(R.string.checkout_missing_lines_error)) }
            }
            return
        }
        viewModelScope.launch {
            mutableState.update { it.copy(submitting = true) }
            try {
                val created = container.orders.create(
                    store = state.store,
                    items = state.lines.mapNotNull { line ->
                        line.storePrice?.listingId?.let { OrderLineRequest(it, line.quantity) }
                    },
                    address = address.trim(),
                    phone = normalized!!,
                    latitude = state.latitude,
                    longitude = state.longitude,
                )
                container.preferences.setLastOrderId(created.id)
                mutableState.update { it.copy(orderId = created.id, orderStatus = created.status) }
                val paid = container.orders.pay(created.id)
                mutableState.update {
                    it.copy(submitting = false, orderStatus = paid.status, submissionError = null)
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                mutableState.update {
                    it.copy(
                        submitting = false,
                        submissionError = container.strings(R.string.checkout_order_error)
                            .format(error.message.orEmpty()),
                    )
                }
            }
        }
    }

    fun startPolling(orderId: String? = mutableState.value.orderId) {
        if (orderId.isNullOrBlank() || pollingJob?.isActive == true) return
        pollingJob = viewModelScope.launch {
            while (true) {
                try {
                    val order = container.orders.status(orderId)
                    mutableState.update { it.copy(orderStatus = order.status, orderId = order.id) }
                    if (order.status in TERMINAL_STATUSES) break
                } catch (cancelled: CancellationException) {
                    throw cancelled
                } catch (error: Exception) {
                    mutableState.update { it.copy(submissionError = error.message) }
                }
                delay(POLL_DELAY_MS)
            }
        }
    }

    fun stopPolling() {
        pollingJob?.cancel()
        pollingJob = null
    }

    fun cancelOrder() {
        val id = mutableState.value.orderId ?: return
        viewModelScope.launch {
            runCatching { container.orders.cancel(id) }
                .onSuccess { order -> mutableState.update { it.copy(orderStatus = order.status) } }
                .onFailure { error -> mutableState.update { it.copy(submissionError = error.message) } }
        }
    }

    fun deleteOrder() {
        val id = mutableState.value.orderId ?: return
        viewModelScope.launch {
            runCatching { container.orders.delete(id) }
                .onSuccess {
                    container.preferences.setLastOrderId(null)
                    mutableState.update { it.copy(orderId = null, orderStatus = null, orderDeleted = true) }
                }
                .onFailure { error -> mutableState.update { it.copy(submissionError = error.message) } }
        }
    }

    suspend fun restoreLastOrder() {
        val id = container.preferences.preferences.first().lastOrderId ?: return
        mutableState.update { it.copy(orderId = id) }
    }

    companion object {
        const val POLL_DELAY_MS = 3_000L
        val TERMINAL_STATUSES = setOf("paid_sandbox", "failed", "cancelled")
    }

    class Factory(private val container: AppContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(CheckoutViewModel::class.java))
            return CheckoutViewModel(container) as T
        }
    }
}
