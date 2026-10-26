package ke.pricecheck.app.navigation

import androidx.core.os.bundleOf
import androidx.navigation.testing.TestNavHostController
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import ke.pricecheck.app.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class NavGraphInstrumentedTest {
    private lateinit var navController: TestNavHostController

    @Before
    fun setupNavController() {
        navController = TestNavHostController(ApplicationProvider.getApplicationContext())
        navController.setGraph(R.navigation.nav_graph)
        navController.setCurrentDestination(R.id.priceCheckFragment)
    }

    @Test
    fun homeNavigatesToWatchlist() {
        navController.navigate(R.id.action_priceCheckFragment_to_watchlistFragment)
        assertEquals(R.id.watchlistFragment, navController.currentDestination?.id)
    }

    @Test
    fun handoffCheckoutOrderStatusBackStackReturnsHome() {
        val storeName = "Naivas"
        navController.navigate(
            R.id.action_priceCheckFragment_to_storeHandoffFragment,
            bundleOf(NavArgs.STORE_NAME to storeName),
        )
        navController.navigate(
            R.id.action_storeHandoffFragment_to_checkoutFragment,
            bundleOf(NavArgs.STORE_NAME to storeName),
        )
        navController.navigate(
            R.id.action_checkoutFragment_to_orderStatusFragment,
            bundleOf(
                NavArgs.ORDER_ID to "demo-order-ref",
                NavArgs.STORE_NAME to storeName,
            ),
        )
        assertEquals(R.id.orderStatusFragment, navController.currentDestination?.id)
        assertTrue(navController.popBackStack())
        assertEquals(R.id.priceCheckFragment, navController.currentDestination?.id)
    }
}
