package ke.pricecheck.app.ui

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.commit
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.platform.ViewCompositionStrategy
import ke.pricecheck.app.PriceCheckApplication
import ke.pricecheck.app.R

class CheckoutFragment : Fragment() {
    private val viewModel: CheckoutViewModel by activityViewModels {
        CheckoutViewModel.Factory((requireActivity().application as PriceCheckApplication).container)
    }
    private var locationPermissionDenied = false
    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) captureLastKnownLocation() else {
            locationPermissionDenied = true
            Toast.makeText(requireContext(), R.string.checkout_location_denied, Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View = ComposeView(requireContext()).apply {
        setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
        setContent {
            val state by viewModel.uiState.collectAsStateWithLifecycle()
            var navigated by remember { mutableStateOf(false) }
            LaunchedEffect(state.orderId) {
                if (state.orderId != null && !navigated) {
                    navigated = true
                    parentFragmentManager.commit {
                        setReorderingAllowed(true)
                        replace(android.R.id.content, OrderStatusFragment())
                        addToBackStack("order-status")
                    }
                }
            }
            CheckoutScreen(
                state = state,
                onSubmit = viewModel::submit,
                onUseLocation = ::requestLocation,
                locationDenied = locationPermissionDenied,
            )
        }
    }

    private fun requestLocation() {
        val granted = ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_COARSE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) captureLastKnownLocation()
        else locationPermission.launch(Manifest.permission.ACCESS_COARSE_LOCATION)
    }

    @Suppress("MissingPermission")
    private fun captureLastKnownLocation() {
        try {
            val manager = requireContext().getSystemService(Context.LOCATION_SERVICE) as LocationManager
            val last = manager.getProviders(true)
                .mapNotNull { provider -> manager.getLastKnownLocation(provider) }
                .maxByOrNull { it.time }
            if (last == null) {
                Toast.makeText(requireContext(), R.string.checkout_location_denied, Toast.LENGTH_LONG).show()
            } else viewModel.setLocation(last.latitude, last.longitude)
        } catch (_: SecurityException) {
            locationPermissionDenied = true
            Toast.makeText(requireContext(), R.string.checkout_location_denied, Toast.LENGTH_LONG).show()
        }
    }
}

@Composable
fun CheckoutScreen(
    state: CheckoutUiState,
    onSubmit: (String, String) -> Unit,
    onUseLocation: () -> Unit,
    locationDenied: Boolean = false,
) {
    var address by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(
                    stringResource(R.string.checkout_prototype_banner),
                    modifier = Modifier.padding(14.dp),
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
        item {
            Text(stringResource(R.string.checkout_title), style = MaterialTheme.typography.headlineSmall)
            Text(stringResource(R.string.handoff_order_summary, state.store,
                state.lines.sumOf { (it.storePrice?.price ?: 0) * it.quantity }))
        }
        items(state.lines, key = { it.product.id }) { line ->
            Text(stringResource(R.string.checkout_store_summary, line.product.name,
                line.product.size, line.quantity, (line.storePrice?.price ?: 0) * line.quantity))
        }
        item { Text(stringResource(R.string.checkout_delivery_fee)) }
        item {
            OutlinedTextField(
                value = address,
                onValueChange = { address = it },
                modifier = Modifier.fillMaxWidth().testTag("checkout-address"),
                label = { Text(stringResource(R.string.checkout_address)) },
                isError = state.addressError != null,
                supportingText = { state.addressError?.let { error -> Text(stringResource(error)) } },
            )
        }
        item {
            OutlinedTextField(
                value = phone,
                onValueChange = { phone = it },
                modifier = Modifier.fillMaxWidth().testTag("checkout-phone"),
                label = { Text(stringResource(R.string.checkout_phone)) },
                isError = state.phoneError != null,
                supportingText = { state.phoneError?.let { error -> Text(stringResource(error)) } },
            )
        }
        item {
            Text(stringResource(R.string.checkout_location_reason))
            Button(onClick = onUseLocation) { Text(stringResource(R.string.checkout_use_location)) }
            if (locationDenied) Text(stringResource(R.string.checkout_location_denied))
            if (state.latitude != null && state.longitude != null) {
                Text(stringResource(R.string.checkout_location_set))
            }
        }
        if (state.missingItems.isNotEmpty()) {
            item { Text(stringResource(R.string.store_missing_items, state.store, state.missingItems.joinToString())) }
        }
        if (state.submissionError != null) item { Text(state.submissionError) }
        item {
            Button(
                onClick = { onSubmit(address, phone) },
                enabled = !state.submitting,
                modifier = Modifier.fillMaxWidth().testTag("checkout-submit"),
            ) { Text(stringResource(R.string.checkout_submit)) }
        }
    }
}
