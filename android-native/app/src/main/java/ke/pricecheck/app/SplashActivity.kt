package ke.pricecheck.app

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.addCallback
import androidx.appcompat.app.AppCompatActivity

class SplashActivity : AppCompatActivity() {
    private val mainHandler = Handler(Looper.getMainLooper())
    private val openMainRunnable = Runnable {
        if (!isFinishing && !isDestroyed) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)
        mainHandler.postDelayed(openMainRunnable, SPLASH_DELAY_MS)
        onBackPressedDispatcher.addCallback(this) {
            mainHandler.removeCallbacks(openMainRunnable)
            finish()
        }
    }

    override fun onDestroy() {
        mainHandler.removeCallbacks(openMainRunnable)
        super.onDestroy()
    }

    private companion object {
        const val SPLASH_DELAY_MS = 1_750L
    }
}
