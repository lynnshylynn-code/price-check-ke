package ke.pricecheck.app.ui

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import androidx.compose.ui.platform.ViewCompositionStrategy
import ke.pricecheck.app.PriceCheckApplication
import ke.pricecheck.app.R
import kotlinx.coroutines.launch

class OrderStatusFragment : Fragment() {
    private val viewModel: CheckoutViewModel by activityViewModels {
        CheckoutViewModel.Factory((requireActivity().application as PriceCheckApplication).container)
    }
    private var notifiedOrderId: String? = null
    private var pendingNotification = false
    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted && pendingNotification) showPaidNotification()
        pendingNotification = false
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val manager = requireContext().getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    ORDER_CHANNEL,
                    getString(R.string.notification_channel_order),
                    NotificationManager.IMPORTANCE_DEFAULT,
                ).apply { description = getString(R.string.order_notification_channel_description) },
            )
        }
    }

    override fun onStart() {
        super.onStart()
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.restoreLastOrder()
            viewModel.startPolling()
        }
    }

    override fun onStop() {
        viewModel.stopPolling()
        super.onStop()
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View = ComposeView(requireContext()).apply {
        setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
        setContent {
            val state by viewModel.uiState.collectAsStateWithLifecycle()
            LaunchedEffect(state.orderStatus, state.orderId) {
                if (state.orderStatus == "paid_sandbox" && state.orderId != null &&
                    state.orderId != notifiedOrderId
                ) requestPaidNotification(state.orderId!!)
            }
            OrderStatusScreen(
                state = state,
                onCancel = viewModel::cancelOrder,
                onDelete = viewModel::deleteOrder,
            )
        }
    }

    private fun requestPaidNotification(orderId: String) {
        notifiedOrderId = orderId
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                requireContext(), Manifest.permission.POST_NOTIFICATIONS,
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingNotification = true
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else showPaidNotification()
    }

    private fun showPaidNotification() {
        val manager = requireContext().getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(
            NOTIFICATION_ID,
            NotificationCompat.Builder(requireContext(), ORDER_CHANNEL)
                .setSmallIcon(ke.pricecheck.app.R.drawable.ic_launcher_foreground)
                .setContentTitle(getString(R.string.notification_paid_title))
                .setContentText(getString(R.string.notification_paid_body))
                .setAutoCancel(true)
                .build(),
        )
    }

    companion object {
        private const val ORDER_CHANNEL = "prototype_order_updates"
        private const val NOTIFICATION_ID = 20261020
    }
}

@Composable
private fun OrderStatusScreen(
    state: CheckoutUiState,
    onCancel: () -> Unit,
    onDelete: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.order_status_title))
        Text(
            when (state.orderStatus) {
                "created" -> stringResource(R.string.order_status_created)
                "payment_pending" -> stringResource(R.string.order_status_payment_pending)
                "paid_sandbox" -> stringResource(R.string.order_status_paid_sandbox)
                "failed" -> stringResource(R.string.order_status_failed)
                "cancelled" -> stringResource(R.string.order_status_cancelled)
                else -> stringResource(R.string.order_status_unknown, state.orderStatus.orEmpty())
            },
        )
        Text(stringResource(R.string.checkout_prototype_banner))
        Text(stringResource(R.string.orders_data_prototype))
        if (state.submissionError != null) Text(state.submissionError)
        if (state.orderDeleted) Text(stringResource(R.string.order_deleted))
        Button(
            onClick = onCancel,
            enabled = state.orderStatus in setOf("created", "payment_pending", "failed"),
        ) { Text(stringResource(R.string.order_cancel)) }
        OutlinedButton(onClick = onDelete, enabled = state.orderId != null) {
            Text(stringResource(R.string.order_delete))
        }
    }
}
