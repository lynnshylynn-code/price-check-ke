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
import androidx.fragment.app.commit
import ke.pricecheck.app.PriceCheckApplication

class PriceCheckFragment : Fragment() {
    private val viewModel: PriceCheckViewModel by activityViewModels {
        PriceCheckViewModel.Factory(
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
                    parentFragmentManager.commit {
                        setReorderingAllowed(true)
                        replace(android.R.id.content, WatchlistFragment())
                        addToBackStack("watchlist")
                    }
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
