package ke.pricecheck.app

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.commit
import ke.pricecheck.app.ui.PriceCheckFragment

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate: initialize Compose UI")
        if (savedInstanceState == null) {
            supportFragmentManager.commit {
                setReorderingAllowed(true)
                replace(android.R.id.content, PriceCheckFragment())
            }
        }
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

    override fun onSupportNavigateUp(): Boolean {
        if (supportFragmentManager.backStackEntryCount > 0) {
            supportFragmentManager.popBackStack()
            return true
        }
        return super.onSupportNavigateUp()
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
