package ke.pricecheck.app

import android.os.Bundle
import android.util.Log
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.setupActionBarWithNavController
import com.google.android.material.appbar.MaterialToolbar
import ke.pricecheck.app.R

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate: initialize navigation host")
        setContentView(R.layout.activity_main)
        val toolbar = findViewById<MaterialToolbar>(R.id.main_toolbar)
        setSupportActionBar(toolbar)
        val navHostFragment =
            supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController
        val appBarConfiguration = AppBarConfiguration(
            setOf(R.id.priceCheckFragment),
        )
        setupActionBarWithNavController(navController, appBarConfiguration)
        navController.addOnDestinationChangedListener { _, destination, _ ->
            toolbar.visibility =
                if (destination.id == R.id.priceCheckFragment) View.GONE else View.VISIBLE
        }
    }

    override fun onSupportNavigateUp(): Boolean {
        val navHostFragment =
            supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        return navHostFragment.navController.navigateUp() || super.onSupportNavigateUp()
    }

    override fun onStart() {
        super.onStart()
        Log.d(TAG, "onStart: activity is visible")
    }

    override fun onResume() {
        super.onResume()
        Log.d(TAG, "onResume: activity is ready for interaction")
    }

    override fun onRestart() {
        super.onRestart()
        Log.d(TAG, "onRestart: activity is returning to the foreground")
    }

    override fun onPause() {
        Log.d(TAG, "onPause: activity is losing focus")
        super.onPause()
    }

    override fun onStop() {
        Log.d(TAG, "onStop: activity is no longer visible")
        super.onStop()
    }

    override fun onDestroy() {
        Log.d(TAG, "onDestroy: release activity resources")
        super.onDestroy()
    }

    private companion object {
        const val TAG = "PriceCheckLifecycle"
    }
}
