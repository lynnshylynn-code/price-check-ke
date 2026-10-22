package ke.pricecheck.app.ui

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.fragment.app.commit
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.platform.ViewCompositionStrategy
import ke.pricecheck.app.R

class StoreHandoffFragment : Fragment() {
    private val viewModel: CheckoutViewModel by activityViewModels {
        CheckoutViewModel.Factory((requireActivity().application as ke.pricecheck.app.PriceCheckApplication).container)
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View = ComposeView(requireContext()).apply {
        setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
        setContent {
            val state by viewModel.uiState.collectAsStateWithLifecycle()
            HandoffScreen(
                state = state,
                onOpen = { url -> openListing(url) },
                onShare = { shareBasket(state) },
                onCheckout = {
                    parentFragmentManager.commit {
                        setReorderingAllowed(true)
                        replace(android.R.id.content, CheckoutFragment())
                        addToBackStack("checkout")
                    }
                },
            )
        }
    }

    private fun openListing(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(requireContext(), R.string.browser_unavailable, Toast.LENGTH_LONG).show()
        }
    }

    private fun shareBasket(state: CheckoutUiState) {
        val text = buildString {
            append(getString(R.string.share_basket_message, state.store))
            state.lines.forEach { line ->
                append("\n")
                append(getString(
                    R.string.handoff_line,
                    line.product.name,
                    line.product.size,
                    line.quantity,
                    (line.storePrice?.price ?: 0) * line.quantity,
                ))
            }
        }
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, text)
        }
        startActivity(Intent.createChooser(send, getString(R.string.share_chooser_title)))
    }
}

@Composable
private fun HandoffScreen(
    state: CheckoutUiState,
    onOpen: (String) -> Unit,
    onShare: () -> Unit,
    onCheckout: () -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(stringResource(R.string.order_handoff_title), style = MaterialTheme.typography.headlineSmall)
                Text(stringResource(R.string.order_handoff_intro))
                Text(stringResource(R.string.handoff_order_summary, state.store,
                    state.lines.sumOf { (it.storePrice?.price ?: 0) * it.quantity }))
            }
        }
        if (state.missingItems.isNotEmpty()) {
            item { Text(stringResource(R.string.store_missing_items, state.store, state.missingItems.joinToString())) }
        }
        items(state.lines, key = { it.product.id }) { line ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(R.string.handoff_line, line.product.name, line.product.size,
                        line.quantity, (line.storePrice?.price ?: 0) * line.quantity))
                    val url = line.storePrice?.productUrl
                    if (url != null) Button(onClick = { onOpen(url) }) {
                        Text(stringResource(R.string.open_on_store, state.store))
                    }
                }
            }
        }
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onShare) { Text(stringResource(R.string.share_store_basket)) }
                Button(onClick = onCheckout, enabled = state.lines.isNotEmpty() && state.missingItems.isEmpty()) {
                    Text(stringResource(R.string.checkout_title))
                }
            }
        }
    }
}
