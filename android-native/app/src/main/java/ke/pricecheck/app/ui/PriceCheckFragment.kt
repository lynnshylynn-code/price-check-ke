package ke.pricecheck.app.ui

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.core.os.bundleOf
import androidx.navigation.fragment.findNavController
import ke.pricecheck.app.PriceCheckApplication
import ke.pricecheck.app.R
import ke.pricecheck.app.navigation.NavArgs

class PriceCheckFragment : Fragment() {
    private val viewModel: PriceCheckViewModel by activityViewModels {
        PriceCheckViewModel.Factory(
            (requireActivity().application as PriceCheckApplication).container,
        )
    }
    private val checkoutViewModel: CheckoutViewModel by activityViewModels {
        CheckoutViewModel.Factory(
            (requireActivity().application as PriceCheckApplication).container,
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate: initialize shopping screen")
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View = ComposeView(requireContext()).apply {
        setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
        setContent {
            PriceCheckApp(
                viewModel = viewModel,
                onOpenWatchlist = {
                    findNavController().navigate(R.id.action_priceCheckFragment_to_watchlistFragment)
                },
                onStoreHandoff = { storeName, basket ->
                    checkoutViewModel.prepareOrder(storeName, viewModel.products, basket)
                    findNavController().navigate(
                        R.id.action_priceCheckFragment_to_storeHandoffFragment,
                        bundleOf(NavArgs.STORE_NAME to storeName),
                    )
                },
                onOrderFromStore = { store, basket ->
                    checkoutViewModel.prepareOrder(store, viewModel.products, basket)
                    findNavController().navigate(
                        R.id.action_priceCheckFragment_to_storeHandoffFragment,
                        bundleOf(NavArgs.STORE_NAME to store),
                    )
                },
            )
        }
    }

    override fun onStart() {
        super.onStart()
        Log.d(TAG, "onStart: shopping screen is visible")
    }

    override fun onResume() {
        super.onResume()
        Log.d(TAG, "onResume: shopping screen is interactive")
    }

    override fun onPause() {
        Log.d(TAG, "onPause: shopping screen is losing focus")
        super.onPause()
    }

    override fun onStop() {
        Log.d(TAG, "onStop: shopping screen is no longer visible")
        super.onStop()
    }

    override fun onDestroyView() {
        Log.d(TAG, "onDestroyView: release Compose view")
        super.onDestroyView()
    }

    override fun onDestroy() {
        Log.d(TAG, "onDestroy: release shopping screen")
        super.onDestroy()
    }

    private companion object {
        const val TAG = "PriceCheckFragmentLifecycle"
    }
}
