package ke.pricecheck.app

import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.NavUtils
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding

class AboutActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d(TAG, "onCreate: inflate About layout")
        setContentView(R.layout.activity_about)
        setSupportActionBar(findViewById(R.id.about_toolbar))
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        findViewById<android.view.View>(R.id.about_close).setOnClickListener { finish() }
        val root = findViewById<android.view.View>(R.id.about_root)
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.updatePadding(top = systemBars.top, bottom = systemBars.bottom)
            insets
        }
    }

    override fun onStart() { super.onStart(); Log.d(TAG, "onStart: activity is visible") }
    override fun onResume() { super.onResume(); Log.d(TAG, "onResume: activity is ready") }
    override fun onPause() { Log.d(TAG, "onPause: activity is losing focus"); super.onPause() }
    override fun onStop() { Log.d(TAG, "onStop: activity is no longer visible"); super.onStop() }
    override fun onRestart() { super.onRestart(); Log.d(TAG, "onRestart: activity is returning") }
    override fun onDestroy() { Log.d(TAG, "onDestroy: release activity resources"); super.onDestroy() }

    override fun onSupportNavigateUp(): Boolean {
        NavUtils.navigateUpFromSameTask(this)
        return true
    }

    private companion object { const val TAG = "PriceCheckLifecycle" }
}
